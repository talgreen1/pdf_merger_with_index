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

# --- Feature Flags ---
ENABLE_SUBFOLDER_INDEX = True  # Set to True to enable subfolder indexes

# --- Helpers ---
def reshape_hebrew(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

# --- Step 1: Collect all PDFs and their page counts ---
pdf_files = sorted(pdf_folder.rglob("*.pdf"), key=lambda p: p.stem.lower())  # Sort by filename only, case-insensitive
pdf_page_counts = [PdfReader(str(pdf)).get_num_pages() for pdf in pdf_files]

# --- Step 2: Create index PDF with Hebrew support and page numbers ---
def create_index(pdf_paths, output_path, font_path, start_page=1, pdf_page_counts=None, index_title=None, song_start_pages=None):
    pdfmetrics.registerFont(TTFont("HebrewFont", str(font_path)))
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    c.setFont("HebrewFont", 20)
    # Use custom index title if provided, else default
    title_to_draw = reshape_hebrew(index_title) if index_title else reshape_hebrew(INDEX_TITLE)
    c.drawRightString(width - 2 * cm, height - 2 * cm, title_to_draw)
    c.setFont("HebrewFont", 14)

    y = height - 3.5 * cm
    # Add column headers
    c.setFont("HebrewFont", 16)
    col_title = reshape_hebrew(COL_TITLE)
    col_page = reshape_hebrew(COL_PAGE)
    right_margin = width - 2 * cm
    left_margin = 2 * cm
    c.drawRightString(right_margin, y, col_title)
    c.drawString(left_margin, y, col_page)
    y -= 1.2 * cm
    c.setFont("HebrewFont", 14)

    songs_per_page = int((height - 5.5 * cm) // (1 * cm))
    # --- Use song_start_pages if provided, else fallback to old logic ---
    if song_start_pages is not None:
        song_start_pages_iter = iter(song_start_pages)
    else:
        page_num = start_page
        song_start_pages_iter = iter([page_num + sum(pdf_page_counts[:i]) for i in range(len(pdf_paths))])

    for i, path in enumerate(pdf_paths, start=1):
        title = path.stem
        song_page = next(song_start_pages_iter)
        page_str = str(song_page)
        title_str = reshape_hebrew(f"{i}. {title}")
        page_width = c.stringWidth(page_str, "HebrewFont", 14)
        title_width = c.stringWidth(title_str, "HebrewFont", 14)
        right_margin = width - 2 * cm
        left_margin = 2 * cm
        c.drawRightString(right_margin, y, title_str)
        c.drawString(left_margin, y, page_str)
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

# --- New: Collect all indexes (main + subfolders) ---
index_pdfs = []
index_page_counts = []

# Main index
main_index_pages = estimate_index_pages(len(pdf_files))
main_index_pdf = output_folder / "index_main_temp.pdf"
create_index(pdf_files, main_index_pdf, hebrew_font_path, start_page=main_index_pages + 1, pdf_page_counts=pdf_page_counts)
index_pdfs.append(main_index_pdf)
index_page_counts.append(main_index_pages)

# Subfolder indexes
subfolder_infos = []
if ENABLE_SUBFOLDER_INDEX:
    print("[DEBUG] ENABLE_SUBFOLDER_INDEX is True. Checking subfolders...")
    for subfolder in [f for f in pdf_folder.iterdir() if f.is_dir()]:
        print(f"[DEBUG] Checking subfolder: {subfolder}")
        subfolder_pdfs = sorted([p for p in subfolder.glob("*.pdf")], key=lambda p: p.stem.lower())
        if not subfolder_pdfs:
            print(f"[DEBUG] No PDFs found in {subfolder}, skipping.")
            continue
        subfolder_page_counts = [PdfReader(str(pdf)).get_num_pages() for pdf in subfolder_pdfs]
        subfolder_index_pdf = output_folder / f"index_{subfolder.name}_temp.pdf"
        folder_name = subfolder.name
        subfolder_infos.append((subfolder_pdfs, subfolder_page_counts, subfolder_index_pdf, folder_name))

# Calculate start pages for each index
current_start_page = sum(index_page_counts) + 1  # Songs start after all indexes
subfolder_index_pages = []
for pdfs, page_counts, index_path, folder_name in subfolder_infos:
    num_pages = estimate_index_pages(len(pdfs))
    subfolder_index_pages.append(num_pages)
    index_pdfs.append(index_path)
    index_page_counts.append(num_pages)

# Regenerate all indexes with correct start_page
main_index_pages = index_page_counts[0]
create_index(pdf_files, main_index_pdf, hebrew_font_path, start_page=main_index_pages + 1, pdf_page_counts=pdf_page_counts)

start_page = main_index_pages + 1
for i, (pdfs, page_counts, index_path, folder_name) in enumerate(subfolder_infos):
    create_index(
        pdfs,
        index_path,
        hebrew_font_path,
        start_page=start_page,
        pdf_page_counts=page_counts,
        index_title=folder_name
    )
    start_page += index_page_counts[i + 1]  # i+1 because main index is at 0

# --- Build a map from each PDF path to its start page in the merged PDF ---
# Calculate total index pages
num_index_pages = sum(index_page_counts)
# Calculate start page for each song in merged order
pdf_start_page_map = {}
cum_page = num_index_pages + 1
for pdf, page_count in zip(pdf_files, pdf_page_counts):
    pdf_start_page_map[pdf] = cum_page
    cum_page += page_count

# --- Regenerate all indexes using the page map ---
# Main index
main_index_song_start_pages = [pdf_start_page_map[p] for p in pdf_files]
create_index(
    pdf_files,
    main_index_pdf,
    hebrew_font_path,
    start_page=None,
    pdf_page_counts=pdf_page_counts,
    song_start_pages=main_index_song_start_pages
)

# Subfolder indexes
for pdfs, page_counts, index_path, folder_name in subfolder_infos:
    subfolder_song_start_pages = [pdf_start_page_map[p] for p in pdfs]
    create_index(
        pdfs,
        index_path,
        hebrew_font_path,
        start_page=None,
        pdf_page_counts=page_counts,
        index_title=folder_name,
        song_start_pages=subfolder_song_start_pages
    )

# --- Step 3: Merge all indexes + all songs ---
merger = PdfMerger()
for idx_pdf in index_pdfs:
    merger.append(str(idx_pdf))
for pdf in pdf_files:
    merger.append(str(pdf))

temp_merged_path = output_folder / "temp_merged.pdf"
merger.write(str(temp_merged_path))
merger.close()

# --- Step 4: Add page numbers to all pages ---
def add_page_numbers(input_path, output_path, num_index_pages):
    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    total_pages = len(reader.pages)
    song_page_number = 1
    for i, page in enumerate(reader.pages):
        if i < num_index_pages:
            # Index pages: copy as-is, no page number
            writer.add_page(page)
            continue
        # Song pages: add page number starting from 1
        packet_path = output_folder / "page_number.pdf"
        packet = canvas.Canvas(str(packet_path), pagesize=A4)
        packet.setFont("Helvetica", 16)
        page_number = f"{song_page_number}"
        if PAGE_NUMBER_POSITION in ("both", "left"):
            packet.drawString(2 * cm, 1.5 * cm, page_number)
        if PAGE_NUMBER_POSITION in ("both", "right"):
            packet.drawRightString(A4[0] - 2 * cm, 1.5 * cm, page_number)
        packet.save()

        overlay = PdfReader(str(packet_path)).pages[0]
        page.merge_page(overlay)
        writer.add_page(page)

        packet_path.unlink()  # delete the temp page number after use
        song_page_number += 1

    with open(output_path, "wb") as f:
        writer.write(f)

add_page_numbers(temp_merged_path, output_pdf, sum(index_page_counts))

# --- Cleanup ---
for idx_pdf in index_pdfs:
    if idx_pdf.exists():
        idx_pdf.unlink()
if temp_merged_path.exists():
    temp_merged_path.unlink()

print(f"\u2705 Done! Songbook with Hebrew & page numbers: {output_pdf}")
