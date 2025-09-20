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
output_pdf = output_folder / "רגע של אור - שירים.pdf"
index_pdf = output_folder / "index_temp.pdf"
output_folder.mkdir(parents=True, exist_ok=True)
hebrew_font_path = Path(__file__).parent / "david.ttf"  # Font should be in the project directory

# --- Add this line: Configurable extra index file name ---
EXTRA_INDEX_FILENAME = "more.txt"  # Can be changed as needed

# --- Constants ---
COL_TITLE = "שם השיר"
COL_PAGE = "עמוד"
INDEX_TITLE = "רגע של אור - כל השירים"
PAGE_NUMBER_POSITION = "left"  # Options: "both", "left", "right"
INDEX_LINE_SPACING = 0.8 * cm  # Space between song lines in the index
INDEX_SONG_FONT_SIZE = 18  # Font size for songs in the index

# --- Feature Flags ---
ENABLE_SUBFOLDER_INDEX = True  # Set to True to enable subfolder indexes

# --- Helpers ---
def reshape_hebrew(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def extract_artist_from_filename(filename_stem):
    """
    Extract artist name from filename following pattern: "Song Name - Artist Name"

    Args:
        filename_stem (str): The filename without extension

    Returns:
        tuple: (artist_name, song_name) or (None, filename_stem) if no artist found
    """
    if ' - ' in filename_stem:
        parts = filename_stem.split(' - ', 1)  # Split only on first occurrence
        if len(parts) == 2:
            song_name, artist_name = parts
            # Normalize artist name (remove extra spaces, strip)
            artist_name = ' '.join(artist_name.strip().split())
            song_name = ' '.join(song_name.strip().split())
            return artist_name, song_name
    return None, filename_stem

# --- Step 1: Collect all PDFs and their page counts ---
all_pdf_files = sorted(pdf_folder.rglob("*.pdf"), key=lambda p: p.stem.lower())  # Sort by filename only, case-insensitive

# --- Separate Index Detection ---
separate_folders = []
separate_folder_songs = {}
separate_songs_set = set()

# Find all folders with .separate files
for folder in pdf_folder.rglob("*/"):
    if folder.is_dir():
        separate_file = folder / ".separate" 
        if separate_file.exists():
            separate_folders.append(folder)
            # Collect songs from this folder
            folder_songs = sorted([p for p in folder.glob("*.pdf")], key=lambda p: p.stem.lower())
            if folder_songs:
                separate_folder_songs[folder] = folder_songs
                separate_songs_set.update(folder_songs)
                print(f"[DEBUG] Found separate folder: {folder.name} with {len(folder_songs)} songs")

# Filter out separate songs from main collection
pdf_files = [p for p in all_pdf_files if p not in separate_songs_set]
pdf_page_counts = [PdfReader(str(pdf)).get_num_pages() for pdf in pdf_files]

print(f"[DEBUG] Total PDFs: {len(all_pdf_files)}, Regular PDFs: {len(pdf_files)}, Separate PDFs: {len(separate_songs_set)}")

# --- Step 2: Create index PDF with Hebrew support and page numbers ---
def create_index(pdf_paths, output_path, font_path, start_page=1, pdf_page_counts=None, index_title=None, song_start_pages=None):
    pdfmetrics.registerFont(TTFont("HebrewFont", str(font_path)))
    
    # Try to register Lucida Sans Unicode for mixed language support
    try:
        # Try common paths for Lucida Sans Unicode
        lucida_paths = [
            "C:/Windows/Fonts/l_10646.ttf",  # Windows path
            "/System/Library/Fonts/LucidaGrande.ttc",  # macOS path
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Linux fallback
        ]
        
        lucida_registered = False
        for path in lucida_paths:
            try:
                if Path(path).exists():
                    pdfmetrics.registerFont(TTFont("LucidaFont", path))
                    lucida_registered = True
                    print(f"[DEBUG] Registered Lucida font from: {path}")
                    break
            except:
                continue
        
        if not lucida_registered:
            print("[DEBUG] Could not find Lucida Sans Unicode, will try system fallback")
            
    except Exception as e:
        print(f"[DEBUG] Font registration failed: {e}")
        lucida_registered = False
    
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # For separate indexes with mixed languages, try to use a more universal approach
    is_separate_index = index_title and "(נפרד)" in index_title
    
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
    c.setFont("HebrewFont", INDEX_SONG_FONT_SIZE)

    songs_per_page = int((height - 5.5 * cm) // INDEX_LINE_SPACING)
    # --- Use song_start_pages if provided, else fallback to old logic ---
    if song_start_pages is not None:
        song_start_pages_iter = iter(song_start_pages)
    else:
        page_num = start_page
        song_start_pages_iter = iter([page_num + sum(pdf_page_counts[:i]) for i in range(len(pdf_paths))])

    for i, path in enumerate(pdf_paths, start=1):
        title = path.stem  # This gives filename without extension - that's what we want
        song_page = next(song_start_pages_iter)
        page_str = str(song_page)
        
        # For separate indexes, don't add numbering; for regular indexes, add numbering
        if is_separate_index:
            # For separate indexes with mixed languages, use smaller font and process Hebrew parts
            separate_font_size = int(INDEX_SONG_FONT_SIZE * 0.7)  # Make font 30% smaller
            
            # Process the title to reverse only Hebrew parts
            def fix_hebrew_in_mixed_text(text):
                import re
                # Split text by common separators while preserving them
                parts = re.split('( - | \- )', text)
                processed_parts = []
                
                for part in parts:
                    if part in [' - ', ' \- ']:
                        processed_parts.append(part)
                    else:
                        # Check if this part contains Hebrew characters
                        has_hebrew = any('\u0590' <= char <= '\u05FF' for char in part)
                        if has_hebrew and not any(char.isascii() and char.isalpha() for char in part):
                            # Pure Hebrew text - apply reshaping
                            processed_parts.append(reshape_hebrew(part))
                        else:
                            # Mixed or non-Hebrew text - keep as is
                            processed_parts.append(part)
                
                return ''.join(processed_parts)
            
            title_str = fix_hebrew_in_mixed_text(title)  # Remove the numbering (i.)
            
            # Try to use Lucida font for better mixed-language support
            try:
                if lucida_registered:
                    c.setFont("LucidaFont", separate_font_size)
                    page_width = c.stringWidth(page_str, "LucidaFont", separate_font_size)
                    title_width = c.stringWidth(title_str, "LucidaFont", separate_font_size)
                    font_used = "LucidaFont"
                else:
                    raise Exception("Lucida not available")
            except:
                # Fallback to Hebrew font
                c.setFont("HebrewFont", separate_font_size)
                page_width = c.stringWidth(page_str, "HebrewFont", separate_font_size)
                title_width = c.stringWidth(title_str, "HebrewFont", separate_font_size)
                font_used = "HebrewFont"
            
            right_margin = width - 2 * cm
            left_margin = 2 * cm
            c.drawRightString(right_margin, y, title_str)
            c.drawString(left_margin, y, page_str)
            
            # Switch back to Hebrew font for consistency
            c.setFont("HebrewFont", INDEX_SONG_FONT_SIZE)
        else:
            # For regular indexes, use numbering with Hebrew reshaping
            title_str = reshape_hebrew(f"{i}. {title}")
            page_width = c.stringWidth(page_str, "HebrewFont", INDEX_SONG_FONT_SIZE)
            title_width = c.stringWidth(title_str, "HebrewFont", INDEX_SONG_FONT_SIZE)
            right_margin = width - 2 * cm
            left_margin = 2 * cm
            c.drawRightString(right_margin, y, title_str)
            # Draw page number
            c.drawString(left_margin, y, page_str)
        # (Clickable link will be added in post-processing with pypdf)
        dots_start_pos = left_margin + page_width + 0.3 * cm
        dots_end_pos = right_margin - title_width - 0.3 * cm
        
        # Use appropriate font for dots calculation
        if is_separate_index and 'font_used' in locals() and font_used == "LucidaFont":
            num_dots = int((dots_end_pos - dots_start_pos) // c.stringWidth('.', "LucidaFont", separate_font_size))
            if num_dots > 0:  # Only draw dots if there's space
                dots_str = '.' * num_dots
                c.setFont("LucidaFont", separate_font_size)
                c.drawString(dots_start_pos, y, dots_str)
                c.setFont("HebrewFont", INDEX_SONG_FONT_SIZE)
        else:
            num_dots = int((dots_end_pos - dots_start_pos) // c.stringWidth('.', "HebrewFont", INDEX_SONG_FONT_SIZE))
            if num_dots > 0:  # Only draw dots if there's space
                dots_str = '.' * num_dots
                c.drawString(dots_start_pos, y, dots_str)
        y -= INDEX_LINE_SPACING
        if y < 2 * cm:
            c.showPage()
            c.setFont("HebrewFont", INDEX_SONG_FONT_SIZE)
            y = height - 2 * cm

    c.save()

# --- Step 2.5: Estimate index page count ---
def estimate_index_pages(num_songs):
    height = A4[1]
    songs_per_page = int((height - 5.5 * cm) // INDEX_LINE_SPACING)
    return (num_songs + songs_per_page - 1) // songs_per_page

def create_artist_index(artist_songs, output_path, font_path, start_page=1, pdf_start_page_map=None):
    """
    Create an artist-based index PDF with Hebrew support.

    Args:
        artist_songs (dict): Dictionary mapping artist names to list of (song_name, pdf_path) tuples
        output_path (Path): Output path for the artist index PDF
        font_path (Path): Path to Hebrew font file
        start_page (int): Starting page number for songs
        pdf_start_page_map (dict): Mapping of PDF paths to their start pages in merged PDF
    """
    # Register Hebrew font
    pdfmetrics.registerFont(TTFont('HebrewFont', str(font_path)))

    # Create canvas
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Title
    title = reshape_hebrew("אומנים")
    c.setFont('HebrewFont', 20)
    c.drawRightString(width - 2 * cm, height - 2 * cm, title)

    # Column headers - match regular index format
    y = height - 3.5 * cm
    c.setFont('HebrewFont', 16)
    col_title = reshape_hebrew(COL_TITLE)  # "שם השיר"
    col_page = reshape_hebrew(COL_PAGE)    # "עמוד"
    right_margin = width - 2 * cm
    left_margin = 2 * cm
    c.drawRightString(right_margin, y, col_title)
    c.drawString(left_margin, y, col_page)
    y -= 1.2 * cm
    c.setFont('HebrewFont', INDEX_SONG_FONT_SIZE)

    # Sort artists alphabetically using Hebrew sorting (case-insensitive)
    sorted_artists = sorted(artist_songs.keys(), key=lambda x: x.lower())

    for artist_name in sorted_artists:
        songs = artist_songs[artist_name]
        # Sort songs by song name within each artist
        songs.sort(key=lambda x: x[0].lower())

        for song_name, pdf_path in songs:
            # Format: "Artist Name - Song Name"
            display_text = f"{artist_name} - {song_name}"
            display_text = reshape_hebrew(display_text)

            # Get page number
            if pdf_start_page_map and pdf_path in pdf_start_page_map:
                page_num = pdf_start_page_map[pdf_path]
            else:
                page_num = start_page  # Fallback

            # Check if we need a new page
            if y < 3 * cm:
                c.showPage()
                c.setFont('HebrewFont', INDEX_SONG_FONT_SIZE)
                y = height - 2 * cm

            # Draw song entry with correct positioning and dots (like regular index)
            page_str = str(page_num)
            page_width = c.stringWidth(page_str, "HebrewFont", INDEX_SONG_FONT_SIZE)
            title_width = c.stringWidth(display_text, "HebrewFont", INDEX_SONG_FONT_SIZE)

            # Draw song name on the right, page number on the left (Hebrew RTL layout)
            c.drawRightString(right_margin, y, display_text)
            c.drawString(left_margin, y, page_str)

            # Add dots between page number and song name
            dots_start_pos = left_margin + page_width + 0.3 * cm
            dots_end_pos = right_margin - title_width - 0.3 * cm
            num_dots = int((dots_end_pos - dots_start_pos) // c.stringWidth('.', "HebrewFont", INDEX_SONG_FONT_SIZE))
            dots_str = '.' * num_dots
            c.drawString(dots_start_pos, y, dots_str)

            y -= INDEX_LINE_SPACING

    c.save()

# --- New: Map file name to full path for fast lookup ---
pdf_name_to_path = {p.name: p for p in pdf_files}

# --- Artist Index Data Collection (excluding separate songs) ---
artist_songs = {}  # Dictionary: artist_name -> [(song_name, pdf_path)]
songs_with_artists = set()  # Track which songs have artists to avoid duplicates

for pdf_path in pdf_files:  # pdf_files already excludes separate songs
    artist_name, song_name = extract_artist_from_filename(pdf_path.stem)
    if artist_name:
        if artist_name not in artist_songs:
            artist_songs[artist_name] = []
        artist_songs[artist_name].append((song_name, pdf_path))
        songs_with_artists.add(pdf_path)

print(f"[DEBUG] Found {len(artist_songs)} artists with {sum(len(songs) for songs in artist_songs.values())} songs")

# --- New: Collect all indexes (main + subfolders + extra indexes) ---
index_pdfs = []
index_page_counts = []

# Main index
main_index_pages = estimate_index_pages(len(pdf_files))
main_index_pdf = output_folder / "index_main_temp.pdf"
create_index(pdf_files, main_index_pdf, hebrew_font_path, start_page=main_index_pages + 1, pdf_page_counts=pdf_page_counts)
index_pdfs.append(main_index_pdf)
index_page_counts.append(main_index_pages)

# --- Extra indexes from עוד.txt files (recursive, robust) ---
extra_index_infos = []
for extra_index_file in pdf_folder.rglob(EXTRA_INDEX_FILENAME):
    folder = extra_index_file.parent
    print(f"[DEBUG] Found extra index file: {extra_index_file} in folder: {folder}")
    with extra_index_file.open("r", encoding="utf-8") as f:
        song_names = [line.strip() for line in f if line.strip()]
    print(f"[DEBUG] Song names in {extra_index_file}: {song_names}")
    # Songs listed in the text file
    matched_pdfs = [pdf_name_to_path[name] for name in song_names if name in pdf_name_to_path]
    # Songs physically present in the folder
    folder_pdfs = [p for p in folder.glob("*.pdf")]
    # Merge and deduplicate
    all_pdfs = []
    seen = set()
    for p in matched_pdfs + folder_pdfs:
        if p not in seen:
            all_pdfs.append(p)
            seen.add(p)
    # Sort by song title (case-insensitive)
    all_pdfs = sorted(all_pdfs, key=lambda p: p.stem.lower())
    print(f"[DEBUG] All PDFs for {folder.name}: {[str(p) for p in all_pdfs]}")
    if all_pdfs:
        # index_title = f"רגע של אור - {folder.name}"
        index_title = folder.name
        index_pdf_path = output_folder / f"index_{folder.name}_temp.pdf"
        num_pages = estimate_index_pages(len(all_pdfs))
        print(f"[DEBUG] Creating index PDF: {index_pdf_path} with {len(all_pdfs)} songs")
        create_index(all_pdfs, index_pdf_path, hebrew_font_path, start_page=num_pages + 1, pdf_page_counts=[PdfReader(str(pdf)).get_num_pages() for pdf in all_pdfs], index_title=index_title)
        index_pdfs.append(index_pdf_path)
        index_page_counts.append(num_pages)
        extra_index_infos.append((all_pdfs, index_pdf_path, index_title))
    else:
        print(f"[DEBUG] No PDFs for {extra_index_file}, skipping index creation.")

# --- Subfolder indexes ---
subfolder_infos = []
if ENABLE_SUBFOLDER_INDEX:
    print("[DEBUG] ENABLE_SUBFOLDER_INDEX is True. Checking subfolders...")
    for subfolder in [f for f in pdf_folder.iterdir() if f.is_dir()]:
        # Skip subfolder if it has an extra index file
        extra_index_file = subfolder / EXTRA_INDEX_FILENAME
        if extra_index_file.exists():
            print(f"[DEBUG] Skipping subfolder {subfolder} because it has an extra index file: {extra_index_file}")
            continue
        # Skip subfolder if it has a .separate file
        separate_file = subfolder / ".separate"
        if separate_file.exists():
            print(f"[DEBUG] Skipping subfolder {subfolder} because it has a .separate file: {separate_file}")
            continue
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

# Add artist index as the last regular index (if there are songs with artists)
artist_index_pdf = None
if artist_songs:
    total_artist_songs = sum(len(songs) for songs in artist_songs.values())
    artist_index_pages = estimate_index_pages(total_artist_songs)
    artist_index_pdf = output_folder / "index_artists_temp.pdf"
    index_pdfs.append(artist_index_pdf)
    index_page_counts.append(artist_index_pages)
    print(f"[DEBUG] Added artist index with {total_artist_songs} songs, estimated {artist_index_pages} pages")

# Add separate indexes at the end (for folders with .separate files)
separate_index_infos = []
for folder, folder_songs in separate_folder_songs.items():
    if folder_songs:
        separate_index_pages = estimate_index_pages(len(folder_songs))
        separate_index_pdf = output_folder / f"index_separate_{folder.name}_temp.pdf"
        index_pdfs.append(separate_index_pdf)
        index_page_counts.append(separate_index_pages)
        separate_index_infos.append((folder_songs, separate_index_pdf, folder.name))
        print(f"[DEBUG] Added separate index for folder '{folder.name}' with {len(folder_songs)} songs, estimated {separate_index_pages} pages")

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
# The first song should be page 1, second song is 1 + previous song's page count, etc.
pdf_start_page_map = {}
cum_page = 1

# Regular songs first
for pdf, page_count in zip(pdf_files, pdf_page_counts):
    pdf_start_page_map[pdf] = cum_page
    cum_page += page_count

# Separate songs after regular songs
separate_pdf_start_page_map = {}
for folder, folder_songs in separate_folder_songs.items():
    for pdf in folder_songs:
        page_count = PdfReader(str(pdf)).get_num_pages()
        separate_pdf_start_page_map[pdf] = cum_page
        cum_page += page_count

# Combine both maps for easier access
all_pdf_start_page_map = {**pdf_start_page_map, **separate_pdf_start_page_map}

# --- Regenerate all indexes using the page map ---
# Main index
main_index_song_start_pages = [pdf_start_page_map[p] for p in pdf_files]
create_index(
    pdf_files,
    main_index_pdf,
    hebrew_font_path,
    start_page=1,  # Fixed: pass a valid int
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
        start_page=1,  # Fixed: pass a valid int
        pdf_page_counts=page_counts,
        index_title=folder_name,
        song_start_pages=subfolder_song_start_pages
    )

# --- Extra indexes: Regenerate with correct song_start_pages ---
for all_pdfs, index_pdf_path, index_title in extra_index_infos:
    # Sort again to ensure order is correct after any changes
    all_pdfs_sorted = sorted(all_pdfs, key=lambda p: p.stem.lower())
    extra_song_start_pages = [pdf_start_page_map[p] for p in all_pdfs_sorted]
    create_index(
        all_pdfs_sorted,
        index_pdf_path,
        hebrew_font_path,
        start_page=1,
        pdf_page_counts=[PdfReader(str(pdf)).get_num_pages() for pdf in all_pdfs_sorted],
        index_title=index_title,
        song_start_pages=extra_song_start_pages
    )

# --- Artist index: Create with correct page numbers BEFORE merging ---
if artist_songs and artist_index_pdf:
    print("[DEBUG] Creating artist index with correct page numbers")
    create_artist_index(
        artist_songs,
        artist_index_pdf,
        hebrew_font_path,
        start_page=1,
        pdf_start_page_map=pdf_start_page_map
    )

# --- Create separate indexes with correct page numbers ---
for folder_songs, separate_index_pdf, folder_name in separate_index_infos:
    separate_song_start_pages = [separate_pdf_start_page_map[p] for p in folder_songs]
    create_index(
        folder_songs,
        separate_index_pdf,
        hebrew_font_path,
        start_page=1,
        pdf_page_counts=[PdfReader(str(pdf)).get_num_pages() for pdf in folder_songs],
        index_title=f"{folder_name} (נפרד)",
        song_start_pages=separate_song_start_pages
    )
    print(f"[DEBUG] Created separate index for folder '{folder_name}' with {len(folder_songs)} songs")

# --- Step 3: Merge all indexes + all songs ---
merger = PdfMerger()
# Add all index PDFs
for idx_pdf in index_pdfs:
    merger.append(str(idx_pdf))
# Add regular songs
for pdf in pdf_files:
    merger.append(str(pdf))
# Add separate songs at the end
for folder, folder_songs in separate_folder_songs.items():
    for pdf in folder_songs:
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

# Calculate ACTUAL index page counts from created PDFs
actual_index_page_counts = []
for idx_pdf in index_pdfs:
    if idx_pdf.exists():
        actual_pages = PdfReader(str(idx_pdf)).get_num_pages()
        actual_index_page_counts.append(actual_pages)
    else:
        actual_index_page_counts.append(0)


add_page_numbers(temp_merged_path, output_pdf, sum(actual_index_page_counts))

# --- Step 5: Add clickable links to all index page numbers using pypdf ---
from pypdf.generic import DictionaryObject, NameObject, ArrayObject, NumberObject

def add_link_annotation(page, rect, target_page_num):
    annotation = DictionaryObject()
    annotation.update({
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Rect"): ArrayObject([NumberObject(rect[0]), NumberObject(rect[1]), NumberObject(rect[2]), NumberObject(rect[3])]),
        NameObject("/Border"): ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)]),
        NameObject("/Dest"): ArrayObject([NumberObject(target_page_num), NameObject("/Fit")])
    })
    if "/Annots" in page:
        page["/Annots"].append(annotation)
    else:
        page[NameObject("/Annots")] = ArrayObject([annotation])

def add_all_index_links_with_pypdf(pdf_path, index_pdfs, index_page_counts, index_infos, pdf_start_page_map):
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    total_index_pages = sum(index_page_counts)
    
    # Create a mapping from PDF path to its actual position in the merged PDF
    # In the merged PDF: [indexes][regular_songs][separate_songs]...
    pdf_to_merged_position = {}
    current_position = total_index_pages  # Songs start after indexes
    
    # Regular songs first
    for pdf, page_count in zip(pdf_files, pdf_page_counts):
        pdf_to_merged_position[pdf] = current_position
        current_position += page_count
    
    # Separate songs after regular songs
    for folder, folder_songs in separate_folder_songs.items():
        for pdf in folder_songs:
            page_count = PdfReader(str(pdf)).get_num_pages()
            pdf_to_merged_position[pdf] = current_position
            current_position += page_count
    

    # Add bookmarks for each song start page
    for pdf, start_page in all_pdf_start_page_map.items():
        writer.add_outline_item(pdf.stem, pdf_to_merged_position[pdf])  # 0-based

    # For each index (main, subfolder, extra)
    page_offset = 0
    for idx, (pdfs, page_counts, index_path, index_title) in enumerate(index_infos):
        songs_per_page = int((A4[1] - 5.5 * cm) // INDEX_LINE_SPACING)
        y_start = A4[1] - 3.5 * cm - 1.2 * cm
        song_idx = 0
        for page_num in range(index_page_counts[idx]):
            page = reader.pages[page_offset + page_num]
            y = y_start  # Reset y for each page
            for line in range(songs_per_page):
                if song_idx >= len(pdfs):
                    break
                song_pdf = pdfs[song_idx]
                song_start_page = all_pdf_start_page_map[song_pdf]
                
                # Get the actual position in the merged PDF (0-based)
                target_page = pdf_to_merged_position[song_pdf]
                page_str = str(song_start_page)
                page_width = 20  # fallback width
                x1 = 2 * cm
                y1 = y
                x2 = x1 + page_width
                y2 = y + INDEX_SONG_FONT_SIZE
                add_link_annotation(page, (x1, y1, x2, y2), target_page)
                
                y -= INDEX_LINE_SPACING
                song_idx += 1
            writer.add_page(page)
        page_offset += index_page_counts[idx]
    # Add the rest of the pages (songs)
    for i in range(total_index_pages, len(reader.pages)):
        writer.add_page(reader.pages[i])
    # Save output
    with open(str(pdf_path), "wb") as f:
        writer.write(f)

# Prepare index_infos: (pdfs, page_counts, index_path, index_title) for all indexes
index_infos = []
# Main index
index_infos.append((pdf_files, pdf_page_counts, main_index_pdf, INDEX_TITLE))
# Subfolder indexes
for i, (pdfs, page_counts, index_path, folder_name) in enumerate(subfolder_infos):
    index_infos.append((pdfs, page_counts, index_path, folder_name))
# Extra indexes
for all_pdfs, index_pdf_path, index_title in extra_index_infos:
    all_pdfs_sorted = sorted(all_pdfs, key=lambda p: p.stem.lower())
    index_infos.append((all_pdfs_sorted, [PdfReader(str(pdf)).get_num_pages() for pdf in all_pdfs_sorted], index_pdf_path, index_title))

# Artist index
if artist_songs and artist_index_pdf:
    # Create ordered list of PDFs as they appear in the artist index
    artist_ordered_pdfs = []
    artist_ordered_page_counts = []
    # Sort artists alphabetically (same as in create_artist_index)
    sorted_artists = sorted(artist_songs.keys(), key=lambda x: x.lower())
    for artist_name in sorted_artists:
        songs = artist_songs[artist_name]
        # Sort songs by song name within each artist (same as in create_artist_index)
        songs.sort(key=lambda x: x[0].lower())
        for song_name, pdf_path in songs:
            artist_ordered_pdfs.append(pdf_path)
            artist_ordered_page_counts.append(PdfReader(str(pdf_path)).get_num_pages())

    index_infos.append((artist_ordered_pdfs, artist_ordered_page_counts, artist_index_pdf, "אומנים"))

# Separate indexes
for folder_songs, separate_index_pdf, folder_name in separate_index_infos:
    separate_page_counts = [PdfReader(str(pdf)).get_num_pages() for pdf in folder_songs]
    index_infos.append((folder_songs, separate_page_counts, separate_index_pdf, f"{folder_name} (נפרד)"))

add_all_index_links_with_pypdf(output_pdf, index_pdfs, index_page_counts, index_infos, all_pdf_start_page_map)

# --- Cleanup ---
for idx_pdf in index_pdfs:
    if idx_pdf.exists():
        idx_pdf.unlink()
if temp_merged_path.exists():
    temp_merged_path.unlink()

print(f"\u2705 Done! Songbook with Hebrew & page numbers: {output_pdf}")
