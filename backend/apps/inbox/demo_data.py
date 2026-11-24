"""Simulated mailbox content. These are NOT real emails; they exist so the inbox/OCR workflow
can be demonstrated without a connected Gmail/Microsoft account."""
from datetime import datetime, timedelta

from django.utils import timezone

from .demo_documents import make_pdf, make_png

HEADER_ROW = "Sr  Description                              Qty   Unit   Rate      Amount"


def _po_lines(buyer, addr, po_no, po_date, delivery, rows, total, extra=None):
    lines = ["PURCHASE ORDER", "", f"Buyer: {buyer}", addr, "", f"PO Number: {po_no}", f"PO Date: {po_date}"]
    if delivery:
        lines.append(f"Delivery Date: {delivery}")
    lines += ["", HEADER_ROW]
    for i, (desc, qty, uom, rate, amt) in enumerate(rows, 1):
        lines.append(f"{i}  {desc}  {qty}  {uom}  {rate}  {amt}")
    lines += ["", f"Grand Total: {total}"]
    lines += extra or []
    return lines


def _msg(n, sender_name, sender_email, subject, body, filename, lines, days_ago, kind="pdf", hours=10):
    content = make_pdf(lines) if kind == "pdf" else make_png(lines)
    return {
        "external_id": f"demo-msg-{n:03d}",
        "sender_name": sender_name,
        "sender_email": sender_email,
        "subject": subject,
        "body": body,
        "days_ago": days_ago,
        "hours": hours,
        "attachments": [{
            "external_id": f"demo-att-{n:03d}-1",
            "filename": filename,
            "content_type": "application/pdf" if kind == "pdf" else "image/png",
            "content": content,
        }],
    }


def build_demo_messages():
    """Return all simulated emails. The first five are seeded; the rest arrive via 'Sync Now'."""
    t = timezone.localdate()
    d = lambda n: (t - timedelta(days=n)).strftime("%d/%m/%Y")
    f = lambda n: (t + timedelta(days=n)).strftime("%d/%m/%Y")
    return [
        _msg(1, "Rahul Deshmukh", "purchase@apexengg.example", "PO APX/PO/2026/0412 - Fasteners & Plates",
             "Dear Supplier, please find attached our purchase order. Kindly confirm delivery.", "APX_PO_0412.pdf",
             _po_lines("Apex Engineering Works Pvt Ltd", "Plot 14, MIDC Bhosari, Pune", "APX/PO/2026/0412", d(20), f(10),
                       [("Hex Bolt M10x50 Zinc Plated", "500", "Nos", "12.50", "6,250.00"),
                        ("MS Plate 10mm", "250", "Kg", "68.00", "17,000.00")], "23,250.00"), 20),
        _msg(2, "Sneha Iyer", "procurement@bharatauto.example", "Purchase Order BAC-7781",
             "Please process the attached PO on priority.", "BAC-7781.pdf",
             _po_lines("Bharat Auto Components Ltd", "Hosur Road, Bengaluru", "BAC-7781", d(3), f(14),
                       [("Ball Bearing 6205", "120", "Nos", "145.00", "17,400.00"),
                        ("Hydraulic Oil ISO 68", "80", "Ltr", "185.00", "14,800.00")], "32,200.00"), 3),
        # Low-confidence document: no delivery date, wrong line total, missing rate, vague buyer text
        _msg(3, "Site Office", "accounts@sunriseinfra.example", "Order for site material - urgent",
             "Hi, order attached. Need material at site ASAP.", "scan_0098.pdf",
             ["ORDER FORM", "", "Customer: Sunrise Infra Proj.", "Ahmedabad", "",
              "Order No: SIP-2210", "Dated: 05/10/26", "", HEADER_ROW,
              "1  PVC Pipe 110 mm  300  Mtr  210.00  60,000.00",
              "2  Safety Helmets yellow  50  Nos", "", "Total: 61,000.00"], 2, hours=15),
        _msg(4, "Vikram Nair", "vikram.nair@technofab.example", "PO TF/2026/0198 attached",
             "Attached is our PO for welding consumables and cable.", "TF_2026_0198.pdf",
             _po_lines("TechnoFab Industries Pvt Ltd", "SIPCOT, Chennai", "TF/2026/0198", d(1), f(21),
                       [("Welding Electrode 3.15mm", "100", "Kg", "95.00", "9,500.00"),
                        ("Copper Wire 2.5 sqmm", "1000", "Mtr", "24.00", "24,000.00")], "33,500.00"), 1, hours=9),
        _msg(5, "Anil Kapoor", "anil@kalyanimachines.example", "RE: Purchase order KHM-5502",
             "Please confirm receipt of the order.", "KHM-5502.pdf",
             _po_lines("Kalyani Heavy Machines Ltd", "Sector 18, Gurugram", "KHM-5502", d(0), f(30),
                       [("Safety Helmet", "200", "Nos", "260.00", "52,000.00")], "52,000.00"), 0, hours=8),
        # --- arrive through the simulated "Sync Now" ---
        _msg(6, "Priya Sen", "orders@metrorail.example", "PO MRC/778 - PVC pipes",
             "Sharing PO for PVC pipes. Delivery to site store.", "MRC_778.pdf",
             _po_lines("Metro Rail Constructions Ltd", "Salt Lake, Kolkata", "MRC/778", d(0), f(25),
                       [("PVC Pipe 110mm", "400", "Mtr", "210.00", "84,000.00")], "84,000.00"), 0, hours=11),
        _msg(7, "Rahul Deshmukh", "purchase@apexengg.example", "PO APX/PO/2026/0431",
             "Second order for this month.", "APX_PO_0431.pdf",
             _po_lines("Apex Engineering Works Pvt Ltd", "Plot 14, MIDC Bhosari, Pune", "APX/PO/2026/0431", d(0), f(12),
                       [("Hex Bolt M10x50 Zinc Plated", "1000", "Nos", "12.50", "12,500.00"),
                        ("Ball Bearing 6205", "40", "Nos", "145.00", "5,800.00")], "18,300.00"), 0, hours=12),
        _msg(8, "Sneha Iyer", "procurement@bharatauto.example", "Scanned PO BAC-7790 (photo)",
             "Scanned copy of our PO attached (image).", "BAC-7790_scan.png",
             _po_lines("Bharat Auto Components Ltd", "Hosur Road, Bengaluru", "BAC-7790", d(0), f(18),
                       [("Hydraulic Oil ISO 68", "60", "Ltr", "185.00", "11,100.00")], "11,100.00"), 0, kind="png", hours=13),
    ]


def received_at(msg):
    base = timezone.localtime().replace(hour=msg["hours"], minute=15, second=0, microsecond=0)
    return base - timedelta(days=msg["days_ago"])


GENERATED_BUYERS = [
    ("Apex Engineering Works Pvt Ltd", "Plot 14, MIDC Bhosari, Pune", "purchase@apexengg.example", "Rahul Deshmukh", "APX/PO/2026/"),
    ("TechnoFab Industries Pvt Ltd", "SIPCOT, Chennai", "vikram.nair@technofab.example", "Vikram Nair", "TF/2026/"),
    ("Kalyani Heavy Machines Ltd", "Sector 18, Gurugram", "anil@kalyanimachines.example", "Anil Kapoor", "KHM-"),
    ("Metro Rail Constructions Ltd", "Salt Lake, Kolkata", "orders@metrorail.example", "Priya Sen", "MRC/"),
]
GENERATED_ROWS = [
    ("Hex Bolt M10x50 Zinc Plated", 12.50, "Nos"), ("MS Plate 10mm", 68.00, "Kg"), ("Copper Wire 2.5 sqmm", 24.00, "Mtr"),
    ("Hydraulic Oil ISO 68", 185.00, "Ltr"), ("Ball Bearing 6205", 145.00, "Nos"), ("PVC Pipe 110mm", 210.00, "Mtr"),
    ("Welding Electrode 3.15mm", 95.00, "Kg"), ("Safety Helmet", 260.00, "Nos"),
]


def build_generated_message(seq):
    """A fresh simulated PO email (unique id) for the 'Simulate incoming email' button."""
    import random
    from datetime import timedelta

    rnd = random.Random(seq)
    buyer, addr, email, person, prefix = GENERATED_BUYERS[seq % len(GENERATED_BUYERS)]
    t = timezone.localdate()
    po_no = f"{prefix}{9000 + seq}"
    rows, total = [], 0
    for desc, rate, uom in rnd.sample(GENERATED_ROWS, 2):
        qty = rnd.choice([20, 40, 60, 100, 150, 200])
        amt = round(qty * rate, 2)
        total += amt
        rows.append((desc, str(qty), uom, f"{rate:,.2f}", f"{amt:,.2f}"))
    lines = _po_lines(buyer, addr, po_no, t.strftime("%d/%m/%Y"), (t + timedelta(days=15)).strftime("%d/%m/%Y"), rows, f"{total:,.2f}")
    m = _msg(1000 + seq, person, email, f"New PO {po_no}", "Simulated incoming purchase order email.", f"{po_no.replace('/', '_')}.pdf", lines, 0, hours=timezone.localtime().hour)
    m["external_id"] = f"demo-gen-{seq:04d}"
    m["attachments"][0]["external_id"] = f"demo-gen-att-{seq:04d}"
    m["received_at"] = timezone.now()
    return m
