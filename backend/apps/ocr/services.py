from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.exceptions import Conflict
from apps.customers.models import Customer
from apps.materials.models import Material, MaterialAlias

from .extractor import ExtractionError, extract_text
from .models import OCRExtraction
from .parser import parse_po_text


def run_extraction(ex):
    """(Re)run text extraction + parsing for an extraction record. Never raises for bad documents:
    the failure is stored on the record with a clear message."""
    if ex.status in (OCRExtraction.CONVERTED,):
        raise Conflict("This extraction has already been converted to a purchase order.")
    f = ex.source_file
    try:
        result = extract_text(f.path, ex.original_filename)
        customers = list(Customer.objects.filter(is_active=True).values_list("id", "name"))
        materials = list(Material.objects.filter(is_active=True).values_list("id", "name", "material_code"))
        aliases = dict(MaterialAlias.objects.values_list("normalized", "material_id"))
        parsed = parse_po_text(result.text, customers, materials, aliases, result.ocr_confidence)
        parsed["warnings"] = result.warnings + parsed["warnings"]
        ex.raw_text = result.text
        ex.engine = result.engine
        ex.ocr_confidence = result.ocr_confidence
        ex.extracted_data = parsed
        ex.draft_data = {}
        ex.verified_data = {}
        ex.error_message = ""
        ex.status = OCRExtraction.PROCESSED
    except ExtractionError as exc:
        ex.status = OCRExtraction.FAILED
        ex.error_message = str(exc)
    ex.save()
    msg = getattr(ex.attachment, "message", None) if ex.attachment_id else None
    if msg and msg.status == "new" and ex.status == OCRExtraction.PROCESSED:
        msg.status = "scanned"
        msg.save(update_fields=["status"])
    return ex


def scan_attachment(attachment, user=None):
    ex = attachment.extractions.exclude(status=OCRExtraction.CONVERTED).first()
    if ex is None:
        ex = OCRExtraction.objects.create(
            attachment=attachment, original_filename=attachment.filename, content_type=attachment.content_type, created_by=user
        )
    return run_extraction(ex)


def _validate_form(form, user):
    """Run the full purchase-order validation without creating anything."""
    from apps.purchase_orders.serializers import PurchaseOrderSerializer

    ser = PurchaseOrderSerializer(data=form, context={"request": type("R", (), {"user": user})()})
    ser.is_valid(raise_exception=True)
    return ser


def verify_extraction(ex, form, user):
    if ex.status in (OCRExtraction.FAILED, OCRExtraction.PENDING):
        raise Conflict("This document has no extracted data to verify.")
    if ex.status == OCRExtraction.CONVERTED:
        raise Conflict("Already converted to a purchase order.")
    _validate_form(form, user)
    ex.verified_data = form
    ex.draft_data = form
    ex.status = OCRExtraction.VERIFIED
    ex.verified_by = user
    ex.verified_at = timezone.now()
    ex.save()
    msg = ex.attachment.message if ex.attachment_id else None
    if msg and msg.status in ("new", "scanned"):
        msg.status = "verified"
        msg.save(update_fields=["status"])
    return ex


@transaction.atomic
def create_po_from_extraction(ex, user, save_aliases=True):
    from apps.purchase_orders import services as po_services
    from apps.purchase_orders.serializers import PurchaseOrderSerializer

    ex = OCRExtraction.objects.select_for_update().get(pk=ex.pk)
    if ex.status == OCRExtraction.CONVERTED:
        raise Conflict("This document has already been converted to a purchase order.")
    if ex.status != OCRExtraction.VERIFIED or not ex.verified_data:
        raise Conflict("Extracted data must be verified by a user before a purchase order can be created.")
    ser = _validate_form(ex.verified_data, user)
    data = dict(ser.validated_data)
    items = data.pop("items")
    msg = ex.attachment.message if ex.attachment_id else None
    data["source"] = "email" if msg else "upload"
    po = po_services.create_purchase_order(data, items, user)
    f = ex.source_file
    with f.open("rb") as fh:
        po.attachment.save(ex.original_filename, ContentFile(fh.read()), save=True)
    if save_aliases:
        for it in items:
            desc = (it.get("original_description") or "").strip()
            if desc and not MaterialAlias.objects.filter(normalized=MaterialAlias.normalize(desc)).exists() \
                    and desc.lower() != it["material"].name.lower():
                MaterialAlias.objects.create(material=it["material"], description=desc)
    ex.linked_po = po
    ex.status = OCRExtraction.CONVERTED
    ex.save(update_fields=["linked_po", "status", "updated_at"])
    if msg:
        msg.status = "converted"
        msg.converted_po = po
        msg.save(update_fields=["status", "converted_po"])
    return po
