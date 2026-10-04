"""
generate_scanned_pdf.py
-----------------------
Generates a genuine image-only / scanned-page PDF for OCR fallback testing.
The PDF contains ONE page with an embedded PNG image (text rendered via PIL).
There is NO embedded text layer — PyMuPDF get_text() will return empty string.
"""

import io
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install pillow")
    sys.exit(1)

try:
    import pymupdf as fitz
except ImportError:
    print("ERROR: PyMuPDF not installed.")
    sys.exit(1)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "AUTOSAR_Scanned_HLD_ocr_test.pdf")

def create_scanned_pdf(output_path: str) -> None:
    """
    1. Render AUTOSAR HLD text as a PIL image (no text layer).
    2. Embed the image into a new PDF page.
    3. Save — resulting PDF has zero embedded text.
    """
    # --- Step 1: Render text onto a white A4 image (300 DPI → 2480x3508 px) ---
    width, height = 2480, 3508
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to use a system monospace font; fall back to default
    font_large = None
    font_normal = None
    font_small = None
    for fname in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "cour.ttf", "Courier New.ttf"]:
        for fdir in [
            "C:/Windows/Fonts",
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/liberation",
        ]:
            fpath = os.path.join(fdir, fname)
            if os.path.exists(fpath):
                try:
                    font_large  = ImageFont.truetype(fpath, 72)
                    font_normal = ImageFont.truetype(fpath, 48)
                    font_small  = ImageFont.truetype(fpath, 36)
                    break
                except Exception:
                    pass
        if font_large:
            break

    if not font_large:
        # PIL default bitmap font — very small but guaranteed present
        font_large  = ImageFont.load_default()
        font_normal = font_large
        font_small  = font_large

    # Scanned AUTOSAR HLD content
    lines = [
        ("AUTOSAR High-Level Design — Scanned Reference Copy", font_large, 100),
        ("", font_small, 170),
        ("Document: BCM Scanned Baseline — For OCR Verification Only", font_small, 210),
        ("", font_small, 250),
        ("7. Scanned Section — Memory Mapping Configuration", font_large, 300),
        ("", font_small, 370),
        ("The Body Control Module (BCM) memory layout follows AUTOSAR", font_normal, 420),
        ("MemMap specification. Each Software Component (SWC) is", font_normal, 490),
        ("assigned a dedicated memory section:", font_normal, 560),
        ("", font_small, 620),
        ("  BodyControlSWC   -> ASIL-B RAM Section 0x20000000-0x20007FFF", font_normal, 660),
        ("  DoorControlSWC   -> ASIL-B RAM Section 0x20008000-0x2000FFFF", font_normal, 730),
        ("  LightingSWC      -> ASIL-A RAM Section 0x20010000-0x20017FFF", font_normal, 800),
        ("  PowerDistribSWC  -> QM RAM Section    0x20018000-0x2001FFFF", font_normal, 870),
        ("", font_small, 930),
        ("End-to-End (E2E) Profile 01 is applied on all ASIL-B signals.", font_normal, 980),
        ("ISO 26262 memory partitioning enforced via MPU configuration.", font_normal, 1050),
        ("", font_small, 1110),
        ("8. AUTOSAR Component Runnable Configuration (Scanned)", font_large, 1160),
        ("", font_small, 1230),
        ("  Run_ReadDoorSensors   Period: 20ms   Priority: 5", font_normal, 1280),
        ("  Run_ProcessDoorEvents Period: 10ms   Priority: 8", font_normal, 1350),
        ("  Run_LightControl      Period: 50ms   Priority: 3", font_normal, 1420),
        ("", font_small, 1490),
        ("Scanned page — no embedded text layer present.", font_small, 1550),
    ]

    for text, font, y in lines:
        if text:
            draw.text((100, y), text, fill=(0, 0, 0), font=font)

    # --- Step 2: Convert PIL image to bytes ---
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG", dpi=(300, 300))
    img_bytes.seek(0)

    # --- Step 3: Embed image into a PDF page (no text layer) ---
    pdf_doc = fitz.open()
    # A4 page in points (72 DPI): 595 x 842 pt
    page = pdf_doc.new_page(width=595, height=842)

    # Insert image filling the entire page — NO text is inserted
    rect = fitz.Rect(0, 0, 595, 842)
    page.insert_image(rect, stream=img_bytes.read())

    pdf_doc.save(output_path)
    pdf_doc.close()

    print(f"Scanned PDF written to: {output_path}")

    # --- Step 4: Verify that get_text() returns empty ---
    verify_doc = fitz.open(output_path)
    native_text = verify_doc[0].get_text("text").strip()
    verify_doc.close()
    print(f"Native text layer length: {len(native_text)} chars (should be 0 or minimal)")
    if len(native_text) < 40:
        print("VERIFIED: Page has no meaningful native text layer — OCR will be required.")
    else:
        print(f"WARNING: Native text found: {native_text[:100]!r}")

if __name__ == "__main__":
    create_scanned_pdf(OUTPUT_PATH)
