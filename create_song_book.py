from pathlib import Path
from pypdf import PdfMerger, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import arabic_reshaper
from bidi.algorithm import get_display

# --- Config ---
pdf_folder = Path("c:/temp/songs/pdfs/")  # Folder for input PDF files
output_folder = Path("c:/temp/songs/Res/")  # Folder for final output PDF
output_pdf = output_folder / "Full_Songbook.pdf"
index_pdf = output_folder / "index_temp.pdf"
output_folder.mkdir(parents=True, exist_ok=True)
hebrew_font_path = Path(__file__).parent / "david.ttf"  # Font should be in the project directory

# --- Helpers ---
def reshape_hebrew(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

# --- Step 1: Collect all PDFs ---
pdf_files = sorted(pdf_folder.glob("*.pdf"))

# --- Step 2: Create index PDF with Hebrew support ---
def create_index(pdf_paths, output_path, font_path):
    pdfmetrics.registerFont(TTFont("HebrewFont", str(font_path)))
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    c.setFont("HebrewFont", 20)
    c.drawRightString(width - 2 * cm, height - 2 * cm, reshape_hebrew("\u05e9\u05d9\u05e8\u05d5\u05df - \u05ea\u05d5\u05db\u05df \u05e2\u05d9\u05e0\u05d9\u05d9\u05df"))
    c.setFont("HebrewFont", 14)

    y = height - 3.5 * cm
    for i, path in enumerate(pdf_paths, start=1):
        title = path.stem  # Filename without extension
        c.drawRightString(width - 2 * cm, y, reshape_hebrew(f"{i}. {title}"))
        y -= 1 * cm
        if y < 2 * cm:
            c.showPage()
            c.setFont("HebrewFont", 14)
            y = height - 2 * cm

    c.save()

create_index(pdf_files, index_pdf, hebrew_font_path)

# --- Step 3: Merge index + all songs ---
merger = PdfMerger()
merger.append(str(index_pdf))
for pdf in pdf_files:
    merger.append(str(pdf))

temp_merged_path = output_folder / "temp_merged.pdf"
merger.write(str(temp_merged_path))
merger.close()

# --- Step 4: Add page numbers to all pages ---
def add_page_numbers(input_path, output_path):
    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        packet_path = output_folder / "page_number.pdf"  # Use output_folder instead of undefined folder_path
        packet = canvas.Canvas(str(packet_path), pagesize=A4)
        packet.setFont("Helvetica", 10)
        page_number = f"{i + 1}"
        packet.drawRightString(A4[0] - 2 * cm, 1.5 * cm, page_number)
        packet.save()

        overlay = PdfReader(str(packet_path)).pages[0]
        page.merge_page(overlay)
        writer.add_page(page)

        packet_path.unlink()  # delete the temp page number after use

    with open(output_path, "wb") as f:
        writer.write(f)

add_page_numbers(temp_merged_path, output_pdf)

# --- Cleanup ---
index_pdf.unlink()
temp_merged_path.unlink()

print(f"\u2705 Done! Songbook with Hebrew & page numbers: {output_pdf}")
