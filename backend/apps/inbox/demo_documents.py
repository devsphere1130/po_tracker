"""Generate demo attachments locally (no external libraries): a text-layer PDF and a PNG 'scan'."""
import io


def _esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(lines, title="Purchase Order"):
    """Build a one-page PDF (Helvetica, text layer) from a list of text lines."""
    content = ["BT", "/F1 10 Tf", "13 TL", "50 790 Td"]
    for i, line in enumerate(lines):
        content.append(f"({_esc(line)}) Tj")
        content.append("T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % n + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref))
    return out.getvalue()


def make_png(lines):
    """Render the lines to a PNG image (simulates a scanned/photographed PO for Tesseract)."""
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=26)
    width, line_h = 1500, 40
    img = Image.new("RGB", (width, line_h * (len(lines) + 3)), "white")
    draw = ImageDraw.Draw(img)
    y = line_h
    for line in lines:
        draw.text((50, y), line, fill="black", font=font)
        y += line_h
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
