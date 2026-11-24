"""Repeatable demo data. Records are looked up by natural key (customer code, material code, PO number
per customer, mailbox external id) and only created when missing, so re-running never duplicates or
overwrites user-created or user-edited records."""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CompanyProfile
from apps.customers.models import Customer
from apps.inbox import demo_data
from apps.inbox.models import InboxMessage
from apps.inbox.providers import RawAttachment, RawMessage
from apps.inbox.services import import_message
from apps.inbox.views import ensure_connections
from apps.materials.models import Material
from apps.ocr import services as ocr_services
from apps.purchase_orders import services as po_services
from apps.purchase_orders.models import PurchaseOrder
from apps.supply_tracking import services as supply_services

CUSTOMERS = [
    ("CUST-001", "Apex Engineering Works Pvt Ltd", "Rahul Deshmukh", "purchase@apexengg.example", "9822012345", "27AABCA1234F1Z5", "Plot 14, MIDC Bhosari, Pune 411026"),
    ("CUST-002", "Bharat Auto Components Ltd", "Sneha Iyer", "procurement@bharatauto.example", "9845098450", "29AAACB5678G1Z2", "Hosur Road, Bengaluru 560100"),
    ("CUST-003", "Sunrise Infra Projects LLP", "Mahesh Patel", "accounts@sunriseinfra.example", "9898098980", "24AAFCS9012H1ZP", "SG Highway, Ahmedabad 380054"),
    ("CUST-004", "TechnoFab Industries Pvt Ltd", "Vikram Nair", "vikram.nair@technofab.example", "9840012345", "33AAGCT3456J1Z9", "SIPCOT Industrial Park, Chennai 602105"),
    ("CUST-005", "Kalyani Heavy Machines Ltd", "Anil Kapoor", "anil@kalyanimachines.example", "9810011122", "07AAHCK7890L1ZV", "Sector 18, Gurugram 122015"),
    ("CUST-006", "Metro Rail Constructions Ltd", "Priya Sen", "orders@metrorail.example", "9830098300", "19AAICM2345N1Z4", "Salt Lake Sector V, Kolkata 700091"),
]
MATERIALS = [
    ("MAT-001", "Hex Bolt M10x50 Zinc Plated", "Fasteners", "NOS", "12.50"),
    ("MAT-002", "MS Plate 10mm", "Steel", "KG", "68.00"),
    ("MAT-003", "Copper Wire 2.5 sqmm", "Electrical", "MTR", "24.00"),
    ("MAT-004", "Hydraulic Oil ISO 68", "Lubricants", "LTR", "185.00"),
    ("MAT-005", "Ball Bearing 6205", "Bearings", "NOS", "145.00"),
    ("MAT-006", "PVC Pipe 110mm", "Piping", "MTR", "210.00"),
    ("MAT-007", "Welding Electrode 3.15mm", "Consumables", "KG", "95.00"),
    ("MAT-008", "Safety Helmet", "Safety", "NOS", "260.00"),
]
# (po_number, customer idx, po days ago, delivery days from today, [(material idx, qty, price)],
#  [(supply days ago, line idx, qty, challan)], cancelled, source)
POS = [
    ("APX/PO/2026/0412", 0, 20, 10, [(0, 500, 12.50), (1, 250, 68)], [(10, 0, 500, "DC-1001"), (5, 1, 100, "DC-1009")], False, "email"),  # partial
    ("APX/PO/2026/0388", 0, 60, -20, [(4, 100, 145)], [(40, 0, 60, "DC-0932")], False, "manual"),  # partial + overdue
    ("BAC-7702", 1, 45, -5, [(3, 200, 185), (4, 50, 145)], [], False, "manual"),  # pending + overdue
    ("BAC-7745", 1, 30, 20, [(4, 150, 145)], [(25, 0, 150, "DC-0988")], False, "manual"),  # fulfilled
    ("SIP-2101", 2, 50, 15, [(5, 600, 210), (7, 80, 260)], [(30, 0, 200, "DC-0950"), (12, 1, 80, "DC-1003")], False, "manual"),  # partial
    ("SIP-2150", 2, 15, 30, [(5, 300, 210)], [], False, "manual"),  # pending
    ("TF/2026/0150", 3, 40, 5, [(6, 200, 95), (2, 2000, 24)], [(20, 0, 200, "DC-0970"), (18, 1, 2000, "DC-0971")], False, "upload"),  # fulfilled
    ("TF/2026/0172", 3, 12, 25, [(2, 1500, 24), (0, 800, 12.5)], [(5, 0, 500, "DC-1012")], False, "manual"),  # partial
    ("KHM-5420", 4, 70, -30, [(7, 300, 260)], [], True, "manual"),  # cancelled
    ("KHM-5488", 4, 25, 12, [(1, 1200, 68), (6, 60, 95)], [(10, 1, 60, "DC-1002")], False, "manual"),  # partial
    ("MRC/701", 5, 35, 8, [(5, 250, 210)], [(20, 0, 250, "DC-0975")], False, "manual"),  # fulfilled
    ("MRC/744", 5, 8, 35, [(5, 500, 210), (3, 100, 185)], [], False, "manual"),  # pending
    ("MRC/760", 5, 90, -45, [(7, 150, 260)], [], True, "manual"),  # cancelled
    ("APX/PO/2026/0420", 0, 5, 40, [(1, 800, 68), (0, 2000, 12.5), (4, 30, 145)], [(1, 0, 300, "DC-1015")], False, "manual"),  # partial
]


class Command(BaseCommand):
    help = "Seed repeatable demo data (customers, materials, POs, supplies, inbox emails, OCR records)."

    @transaction.atomic
    def handle(self, *args, **opts):
        today = timezone.localdate()
        created = {"customers": 0, "materials": 0, "pos": 0, "supplies": 0, "emails": 0}

        profile = CompanyProfile.load()
        if profile.name == "My Supplier Company":
            profile.name, profile.email = "Demo Supplier Industries", "sales@demosupplier.example"
            profile.address = "Industrial Area Phase 2, Pune"
            profile.save()

        cust = []
        for code, name, person, email, mobile, gst, addr in CUSTOMERS:
            obj = Customer.objects.filter(customer_code=code).first() or Customer.objects.filter(name__iexact=name).first()
            if obj is None:
                obj = Customer.objects.create(customer_code=code, name=name, contact_person=person, email=email, mobile=mobile,
                                              gst_number=gst, billing_address=addr, shipping_address=addr)
                created["customers"] += 1
            cust.append(obj)

        mats = []
        for code, name, cat, uom, rate in MATERIALS:
            obj = Material.objects.filter(material_code=code).first() or Material.objects.filter(name__iexact=name).first()
            if obj is None:
                obj = Material.objects.create(material_code=code, name=name, category=cat, uom=uom, default_rate=Decimal(rate),
                                              description=f"{name} - standard supply grade")
                created["materials"] += 1
            mats.append(obj)

        for number, ci, po_ago, deliv, lines, supplies, cancelled, source in POS:
            customer = cust[ci]
            if PurchaseOrder.objects.filter(customer=customer, po_number__iexact=number).exists():
                continue
            items = [{"material": mats[m], "original_description": mats[m].name, "ordered_quantity": Decimal(q), "uom": mats[m].uom,
                      "unit_price": Decimal(str(p))} for m, q, p in lines]
            po_date = today - timedelta(days=po_ago)
            po = po_services.create_purchase_order(
                {"po_number": number, "customer": customer, "po_date": po_date, "delivery_date": today + timedelta(days=deliv),
                 "source": source, "notes": "Demo purchase order"}, items)
            created["pos"] += 1
            po_items = list(po.items.all())
            for ago, line_idx, qty, challan in supplies:
                sdate = max(today - timedelta(days=ago), po_date)
                supply_services.record_supply(po, po_items[line_idx], sdate, Decimal(qty), challan, "Demo supply entry")
                created["supplies"] += 1
            if cancelled:
                po_services.cancel_purchase_order(po, "Customer cancelled the order (demo)")

        # Inbox: 5 simulated emails (the other demo emails arrive via the "Sync Now" button)
        ensure_connections()
        for m in demo_data.build_demo_messages()[:5]:
            raw = RawMessage(m["external_id"], m["sender_name"], m["sender_email"], m["subject"], m["body"],
                             demo_data.received_at(m), [RawAttachment(**a) for a in m["attachments"]])
            msg, is_new = import_message(raw, "demo", is_demo=True)
            if is_new:
                created["emails"] += 1
                n = int(m["external_id"].split("-")[-1])
                att = msg.attachments.first()
                if n == 1:  # already converted: link to the seeded PO
                    po = PurchaseOrder.objects.filter(po_number="APX/PO/2026/0412", customer=cust[0]).first()
                    ex = ocr_services.scan_attachment(att)
                    if po:
                        ex.linked_po, ex.status = po, "converted"
                        ex.verified_data = ex.extracted_data.get("form", {})
                        ex.save()
                        msg.status, msg.converted_po = InboxMessage.CONVERTED, po
                        msg.save(update_fields=["status", "converted_po"])
                elif n in (2, 3):  # one high-confidence, one low-confidence extraction ready for review
                    ocr_services.scan_attachment(att)

        self.stdout.write(self.style.SUCCESS(f"Seed complete. Created: {created}"))
