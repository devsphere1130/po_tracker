"""Rule-based purchase order parser. It only reports what it can find in the text; anything it cannot
find stays empty with status 'missing' - values are never invented."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

OK, UNCERTAIN, MISSING = "ok", "uncertain", "missing"
OK_THRESHOLD = 0.8

UOM_MAP = {
    "nos": "NOS", "no": "NOS", "each": "NOS", "ea": "NOS", "pcs": "PCS", "pc": "PCS", "kg": "KG", "kgs": "KG",
    "mtr": "MTR", "mtrs": "MTR", "m": "MTR", "meter": "MTR", "meters": "MTR", "metre": "MTR", "metres": "MTR",
    "ltr": "LTR", "ltrs": "LTR", "litre": "LTR", "litres": "LTR", "liter": "LTR", "liters": "LTR", "l": "LTR",
    "box": "BOX", "boxes": "BOX", "set": "SET", "sets": "SET", "ton": "TON", "tons": "TON", "mt": "TON",
    "roll": "ROLL", "rolls": "ROLL", "bag": "BAG", "bags": "BAG",
}
UOM_RE = "|".join(sorted(UOM_MAP, key=len, reverse=True))
NUM = r"\d[\d,]*(?:\.\d+)?"
CUR = r"(?:Rs\.?|INR|₹)?\s*"
SERIAL = r"(?:\d{1,3}(?:[\.\)]\s*|\s{2,}))?"

ROW_FULL = re.compile(rf"^\s*{SERIAL}(?P<desc>.+?)\s+(?P<qty>{NUM})\s*(?P<uom>{UOM_RE})\.?\s+{CUR}(?P<rate>{NUM})\s+{CUR}(?P<total>{NUM})\s*$", re.I)
ROW_NO_TOTAL = re.compile(rf"^\s*{SERIAL}(?P<desc>.+?)\s+(?P<qty>{NUM})\s*(?P<uom>{UOM_RE})\.?\s+{CUR}(?P<rate>{NUM})\s*$", re.I)
ROW_QTY_ONLY = re.compile(rf"^\s*{SERIAL}(?P<desc>.+?)\s+(?P<qty>{NUM})\s*(?P<uom>{UOM_RE})\.?\s*$", re.I)

DATE_FORMATS = [
    ("%d/%m/%Y", 0.85), ("%d-%m-%Y", 0.85), ("%d.%m.%Y", 0.85), ("%Y-%m-%d", 0.95), ("%d %b %Y", 0.95),
    ("%d %B %Y", 0.95), ("%d-%b-%Y", 0.95), ("%b %d, %Y", 0.9), ("%B %d, %Y", 0.9),
    ("%d/%m/%y", 0.6), ("%d-%m-%y", 0.6), ("%d.%m.%y", 0.6),
]
DATE_TOKEN = re.compile(
    r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}[ \-][A-Za-z]{3,9}[ \-,]+\d{4}|[A-Za-z]{3,9} \d{1,2}, \d{4}"
)


def _field(value=None, confidence=0.0, source=""):
    if value in (None, ""):
        return {"value": None, "confidence": 0.0, "status": MISSING, "source": ""}
    return {"value": value, "confidence": round(confidence, 2), "status": OK if confidence >= OK_THRESHOLD else UNCERTAIN, "source": source}


def to_decimal(s):
    try:
        return Decimal(str(s).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def parse_date(token):
    token = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", token.strip(), flags=re.I).replace("'", "")
    for fmt, conf in DATE_FORMATS:
        try:
            return datetime.strptime(token, fmt).date(), conf
        except ValueError:
            continue
    return None, 0.0


def _find_date(text, label_re):
    for m in re.finditer(rf"(?:{label_re})[^\n\d]{{0,25}}?({DATE_TOKEN.pattern})", text, re.I):
        d, conf = parse_date(m.group(1))
        if d:
            return d, conf, m.group(0).strip()
    return None, 0.0, ""


def _po_number(text):
    pats = [
        (r"(?:purchase\s+order|p\.?\s?o\.?|order)\s*(?:no\.?|number|num|#)\s*[:#\-]?\s*([A-Za-z0-9][A-Za-z0-9\-/_.]{2,})", 0.92),
        (r"\bP\.?O\.?\s*[:#\-]\s*([A-Za-z0-9][A-Za-z0-9\-/_.]{2,})", 0.7),
    ]
    for pat, conf in pats:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).rstrip(".,"), conf, m.group(0).strip()
    return None, 0.0, ""


def _match_customer(name, customers):
    """customers: iterable of (id, name). Returns (id|None, confidence)."""
    if not name:
        return None, 0.0
    norm = lambda s: re.sub(r"\b(pvt|private|ltd|limited|llp|the|co|company)\b\.?", "", re.sub(r"[^a-z0-9 ]", " ", s.lower())).split()
    target = " ".join(norm(name))
    best, best_id = 0.0, None
    for cid, cname in customers:
        cand = " ".join(norm(cname))
        score = SequenceMatcher(None, target, cand).ratio()
        if target and cand and (target in cand or cand in target):
            score = max(score, 0.88)
        if score > best:
            best, best_id = score, cid
    if best >= 0.85:
        return best_id, 0.92
    if best >= 0.6:
        return best_id, 0.6
    return None, 0.0


def _customer_name(text):
    m = re.search(r"(?:buyer|customer|bill(?:ed)?\s*to|ordered\s*by|company)\s*[:\-]\s*([^\n]+)", text, re.I)
    if m:
        return m.group(1).strip(), 0.85, m.group(0).strip()
    for line in text.splitlines():
        if re.search(r"\b(ltd|limited|pvt|llp|industries|corporation|enterprises|works)\b", line, re.I):
            return line.strip(), 0.5, line.strip()
    return None, 0.0, ""


def _total(text):
    m = None
    for m in re.finditer(rf"(?:grand\s+total|total\s+amount|po\s+total|net\s+total|order\s+total|total)\s*(?:\(.*?\))?\s*[:\-]?\s*{CUR}({NUM})", text, re.I):
        pass  # keep the last total-like match (grand total usually at the bottom)
    if m:
        return to_decimal(m.group(1)), 0.9, m.group(0).strip()
    return None, 0.0, ""


def _norm_uom(raw):
    return UOM_MAP.get(raw.lower().rstrip("."), "")


def _match_material(desc, materials, aliases):
    """materials: (id, name, code); aliases: {normalized_description: material_id}."""
    norm = " ".join(desc.lower().split())
    if norm in aliases:
        return aliases[norm], 0.98
    best, best_id = 0.0, None
    for mid, name, code in materials:
        score = SequenceMatcher(None, norm, name.lower()).ratio()
        if name.lower() in norm or norm in name.lower():
            score = max(score, 0.9)
        if score > best:
            best, best_id = score, mid
    if best >= 0.85:
        return best_id, best
    if best >= 0.6:
        return best_id, best  # weak suggestion: flagged as uncertain by caller
    return None, 0.0


def parse_po_text(text, customers=(), materials=(), aliases=None, ocr_confidence=None):
    aliases = aliases or {}
    ocr_factor = 1.0 if ocr_confidence is None else max(0.5, min(1.0, ocr_confidence + 0.1))
    warnings = []

    po_no, c, src = _po_number(text)
    delivery, dc, dsrc = _find_date(text, r"delivery(?:\s*(?:date|by|schedule))?|deliver\s*by|required\s*(?:by|date)|due\s*date|expected\s*delivery")
    # PO date: labelled; avoid grabbing the delivery line
    scrubbed = text.replace(dsrc, "") if dsrc else text
    po_date, pc, psrc = _find_date(scrubbed, r"(?:po|order|purchase\s*order)\s*date|dated|date|dt\.?")
    if not po_date:
        m = DATE_TOKEN.search(scrubbed)
        if m:
            d, conf = parse_date(m.group(0))
            if d:
                po_date, pc, psrc = d, min(conf, 0.5), m.group(0)
                warnings.append("PO date was not labelled; the first date found in the document was used.")
    cust_name, cc, csrc = _customer_name(text)
    cust_id, match_conf = _match_customer(cust_name, customers)
    total, tc, tsrc = _total(text)

    items, unparsed = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m, kind = ROW_FULL.match(line), "full"
        if not m:
            m, kind = ROW_NO_TOTAL.match(line), "no_total"
        if not m:
            m, kind = ROW_QTY_ONLY.match(line), "qty_only"
        if not m:
            if len(re.findall(NUM, line)) >= 3 and not re.search(r"total|date|gst|phone|tel", line, re.I):
                unparsed.append(line)
            continue
        desc = re.sub(r"\s{2,}", " ", m.group("desc")).strip(" -:")
        if re.match(r"^(total|grand|sub)", desc, re.I) or not re.search(r"[A-Za-z]{2}", desc):
            continue
        qty = to_decimal(m.group("qty"))
        rate = to_decimal(m.group("rate")) if kind != "qty_only" else None
        line_total = to_decimal(m.group("total")) if kind == "full" else None
        flags, conf = [], 0.92 * ocr_factor
        if rate is None:
            flags.append("rate_missing"); conf = min(conf, 0.4)
        if line_total is None:
            flags.append("line_total_missing"); conf = min(conf, 0.6)
        elif rate is not None and qty is not None and abs(qty * rate - line_total) > max(Decimal("1"), line_total * Decimal("0.01")):
            flags.append("line_total_mismatch"); conf = min(conf, 0.45)
        mat_id, mconf = _match_material(desc, materials, aliases)
        if mat_id is None:
            flags.append("material_unmapped")
        elif mconf < 0.85:
            flags.append("material_match_weak")
        items.append({
            "description": desc, "quantity": str(qty), "uom": _norm_uom(m.group("uom")),
            "unit_price": None if rate is None else str(rate), "line_total": None if line_total is None else str(line_total),
            "material_id": mat_id, "material_match_confidence": round(mconf, 2), "confidence": round(conf, 2),
            "flags": flags, "raw": line,
        })
    for line in unparsed:
        warnings.append(f"Could not parse line: '{line}'")
    if not items:
        warnings.append("No line items could be recognised in this document.")

    computed = sum((to_decimal(i["line_total"]) or (to_decimal(i["quantity"]) * to_decimal(i["unit_price"]) if i["unit_price"] else Decimal(0))) for i in items) if items else None
    if total is not None and computed is not None and abs(total - computed) > Decimal("1"):
        warnings.append(f"Stated PO total {total} differs from the sum of line totals {computed}.")
        tc = min(tc, 0.5)

    header = {
        "po_number": _field(po_no, c * ocr_factor, src),
        "customer_name": _field(cust_name, cc * ocr_factor, csrc),
        "po_date": _field(po_date.isoformat() if po_date else None, pc * ocr_factor, psrc),
        "delivery_date": _field(delivery.isoformat() if delivery else None, dc * ocr_factor, dsrc),
        "po_total": _field(str(total) if total is not None else None, tc * ocr_factor, tsrc),
    }
    header["customer_name"]["matched_customer_id"] = cust_id
    if cust_name and cust_id is None:
        header["customer_name"]["status"] = UNCERTAIN
        warnings.append("Customer name does not match any customer in the master list.")
    elif cust_id and match_conf < OK_THRESHOLD:
        header["customer_name"]["status"] = UNCERTAIN
    if delivery is None:
        warnings.append("Delivery date could not be found.")

    form = {
        "customer": cust_id, "po_number": po_no or "", "po_date": header["po_date"]["value"] or "",
        "delivery_date": header["delivery_date"]["value"] or "", "notes": "",
        "items": [
            {"material": i["material_id"] if "material_match_weak" not in i["flags"] else None,
             "original_description": i["description"], "ordered_quantity": i["quantity"], "uom": i["uom"],
             "unit_price": i["unit_price"] or ""}
            for i in items
        ],
    }
    return {
        "header": header, "items": items, "warnings": warnings,
        "computed_total": str(computed) if computed is not None else None, "form": form,
    }
