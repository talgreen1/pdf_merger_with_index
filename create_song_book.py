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

# --- Constants ---
COL_TITLE = "שם השיר"
COL_PAGE = "עמוד"
INDEX_TITLE = "שירון - תוכן עניינים"
PAGE_NUMBER_POSITION = "left"  # Options: "both", "left", "right"

# --- Helpers ---
def reshape_hebrew(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

# --- Step 1: Collect all PDFs and their page counts ---
pdf_files = sorted(pdf_folder.rglob("*.pdf"), key=lambda p: p.stem.lower())  # Sort by filename only, case-insensitive
pdf_page_counts = [PdfReader(str(pdf)).get_num_pages() for pdf in pdf_files]

# --- Step 2: Create index PDF with Hebrew support and page numbers ---
def create_index(pdf_paths, output_path, font_path, start_page=1, pdf_page_counts=None):
    pdfmetrics.registerFont(TTFont("HebrewFont", str(font_path)))
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    c.setFont("HebrewFont", 20)
    c.drawRightString(width - 2 * cm, height - 2 * cm, reshape_hebrew(INDEX_TITLE))
    c.setFont("HebrewFont", 14)

    y = height - 3.5 * cm
    # Add column headers
    c.setFont("HebrewFont", 16)
    col_title = reshape_hebrew(COL_TITLE)
    col_page = reshape_hebrew(COL_PAGE)
    # Calculate header positions
    right_margin = width - 2 * cm
    left_margin = 2 * cm
    # Song title header (right-aligned)
    c.drawRightString(right_margin, y, col_title)
    # Page number header (left-aligned)
    c.drawString(left_margin, y, col_page)
    y -= 1.2 * cm
    c.setFont("HebrewFont", 14)

    songs_per_page = int((height - 5.5 * cm) // (1 * cm))  # Estimate how many fit per page
    page_num = start_page
    song_start_pages = []
    for i, (path, song_pages) in enumerate(zip(pdf_paths, pdf_page_counts), start=1):
        song_start_pages.append(page_num)
        page_num += song_pages

    page_num_iter = iter(song_start_pages)
    for i, path in enumerate(pdf_paths, start=1):
        title = path.stem  # Filename without extension
        song_page = next(page_num_iter)
        # Prepare strings
        page_str = str(song_page)
        title_str = reshape_hebrew(f"{i}. {title}")
        # Calculate widths
        page_width = c.stringWidth(page_str, "HebrewFont", 14)
        title_width = c.stringWidth(title_str, "HebrewFont", 14)
        # Set positions
        right_margin = width - 2 * cm
        left_margin = 2 * cm
        # Draw title (right-aligned)
        c.drawRightString(right_margin, y, title_str)
        # Draw page number (left-aligned)
        c.drawString(left_margin, y, page_str)
        # Draw dots between page number and title
        dots_start_pos = left_margin + page_width + 0.3 * cm
        dots_end_pos = right_margin - title_width - 0.3 * cm
        num_dots = int((dots_end_pos - dots_start_pos) // c.stringWidth('.', "HebrewFont", 14))
        dots_str = '.' * num_dots
        c.drawString(dots_start_pos, y, dots_str)
        y -= 1 * cm
        if y < 2 * cm:
            c.showPage()
            c.setFont("HebrewFont", 14)
            y = height - 2 * cm

    c.save()

# --- Step 2.5: Estimate index page count ---
def estimate_index_pages(num_songs):
    height = A4[1]
    songs_per_page = int((height - 5.5 * cm) // (1 * cm))
    return (num_songs + songs_per_page - 1) // songs_per_page

index_pages = estimate_index_pages(len(pdf_files))
create_index(pdf_files, index_pdf, hebrew_font_path, start_page=index_pages + 1, pdf_page_counts=pdf_page_counts)

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
        packet_path = output_folder / "page_number.pdf"
        packet = canvas.Canvas(str(packet_path), pagesize=A4)
        packet.setFont("Helvetica", 16)
        page_number = f"{i + 1}"
        if PAGE_NUMBER_POSITION in ("both", "left"):
            packet.drawString(2 * cm, 1.5 * cm, page_number)
        if PAGE_NUMBER_POSITION in ("both", "right"):
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
