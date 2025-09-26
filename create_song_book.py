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

# --- Font Configuration ---
# Available font options for non-separate indexes:
# - "Lucida": Uses Lucida Sans Unicode (better for mixed languages, current default)
# - "David": Uses David Hebrew font (original Hebrew-focused font)
INDEX_FONT_TYPE = "David"  # Options: "Lucida", "David"

# Font sizes for different index elements
INDEX_TITLE_FONT_SIZE = 16      # Size for main index titles
INDEX_HEADER_FONT_SIZE = 16     # Size for column headers ("שם השיר", "עמוד")
INDEX_SONG_FONT_SIZE = 14       # Size for song entries
SEPARATE_INDEX_FONT_SIZE_RATIO = 1  # Ratio for separate index font size (multiplied by INDEX_SONG_FONT_SIZE)

# --- Constants ---
COL_TITLE = "שם השיר"
COL_PAGE = "עמוד"
INDEX_TITLE = "רגע של אור - כל השירים"
PAGE_NUMBER_POSITION = "left"  # Options: "both", "left", "right"
INDEX_LINE_SPACING = 0.8 * cm  # Space between song lines in the index

# --- Feature Flags ---
ENABLE_SUBFOLDER_INDEX = True  # Set to True to enable subfolder indexes

# --- Helpers ---
def reshape_hebrew(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def split_long_text(canvas_obj, text, font_name, font_size, max_width, right_margin, left_margin):
    """
    Split long text into multiple lines that fit within the available width.

    Args:
        canvas_obj: ReportLab canvas object
        text: Text to split
        font_name: Font name to use
        font_size: Font size
        max_width: Maximum width available for text
        right_margin: Right margin position
        left_margin: Left margin position

    Returns:
        List of text lines that fit within max_width
    """
    # Check if text fits in one line
    text_width = canvas_obj.stringWidth(text, font_name, font_size)
    if text_width <= max_width:
        return [text]

    # Text is too long, need to split
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        # Try adding the next word
        test_line = current_line + (" " if current_line else "") + word
        test_width = canvas_obj.stringWidth(test_line, font_name, font_size)

        if test_width <= max_width:
            current_line = test_line
        else:
            # Current line is full, start a new line
            if current_line:
                lines.append(current_line)
                current_line = word
            else:
                # Single word is too long, force split
                lines.append(word)
                current_line = ""

    # Add the remaining line
    if current_line:
        lines.append(current_line)

    return lines

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
    # Register fonts based on configuration
    if INDEX_FONT_TYPE == "Lucida":
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
                        pdfmetrics.registerFont(TTFont("IndexFont", path))
                        lucida_registered = True
                        print(f"[DEBUG] Registered Lucida font from: {path}")
                        break
                except:
                    continue

            if not lucida_registered:
                print("[DEBUG] Could not find Lucida Sans Unicode, using Hebrew font as fallback")
                pdfmetrics.registerFont(TTFont("IndexFont", str(font_path)))

        except Exception as e:
            print(f"[DEBUG] Font registration failed, using Hebrew font as fallback: {e}")
            pdfmetrics.registerFont(TTFont("IndexFont", str(font_path)))
    else:  # INDEX_FONT_TYPE == "David"
        # Use David Hebrew font
        pdfmetrics.registerFont(TTFont("IndexFont", str(font_path)))
        print(f"[DEBUG] Registered David Hebrew font from: {font_path}")

    # Always register Lucida for separate indexes (mixed language support)
    try:
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
                    break
            except:
                continue

        if not lucida_registered:
            pdfmetrics.registerFont(TTFont("LucidaFont", str(font_path)))

    except Exception as e:
        pdfmetrics.registerFont(TTFont("LucidaFont", str(font_path)))
    
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # For separate indexes with mixed languages, try to use a more universal approach
    is_separate_index = index_title and "(נפרד)" in index_title
    
    c.setFont("IndexFont", INDEX_TITLE_FONT_SIZE)
    # Use custom index title if provided, else default
    title_to_draw = reshape_hebrew(index_title) if index_title else reshape_hebrew(INDEX_TITLE)
    c.drawRightString(width - 2 * cm, height - 2 * cm, title_to_draw)

    y = height - 3.5 * cm
    # Add column headers
    c.setFont("IndexFont", INDEX_HEADER_FONT_SIZE)
    col_title = reshape_hebrew(COL_TITLE)
    col_page = reshape_hebrew(COL_PAGE)
    right_margin = width - 2 * cm
    left_margin = 2 * cm
    c.drawRightString(right_margin, y, col_title)
    c.drawString(left_margin, y, col_page)
    y -= 1.2 * cm
    c.setFont("IndexFont", INDEX_SONG_FONT_SIZE)

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
        
        right_margin = width - 2 * cm
        left_margin = 2 * cm

        # For separate indexes, don't add numbering; for regular indexes, add numbering
        if is_separate_index:
            # For separate indexes with mixed languages, use smaller font and process Hebrew parts
            separate_font_size = int(INDEX_SONG_FONT_SIZE * SEPARATE_INDEX_FONT_SIZE_RATIO)

            # Process the title to reverse only Hebrew parts
            def fix_hebrew_in_mixed_text(text):
                import re
                # Split text by common separators while preserving them
                parts = re.split(r'( - | \- )', text)
                processed_parts = []

                for part in parts:
                    if part in [' - ', r' \- ']:
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

            title_str = fix_hebrew_in_mixed_text(title)
            font_name = "LucidaFont"
            font_size = separate_font_size
        else:
            # For regular indexes, use numbering with Hebrew reshaping
            title_str = reshape_hebrew(f"{i}. {title}")
            font_name = "IndexFont"
            font_size = INDEX_SONG_FONT_SIZE

        # Calculate available width for title (total width minus page number and margins)
        c.setFont(font_name, font_size)
        page_width = c.stringWidth(page_str, font_name, font_size)
        available_width = right_margin - left_margin - page_width - 1 * cm  # Leave 1cm space between page and title

        # Split title into multiple lines if needed
        title_lines = split_long_text(c, title_str, font_name, font_size, available_width, right_margin, left_margin)

        # Check if we need a new page (consider all lines needed)
        lines_needed = len(title_lines)
        space_needed = lines_needed * INDEX_LINE_SPACING
        if y - space_needed < 2 * cm:
            c.showPage()
            c.setFont("IndexFont", INDEX_SONG_FONT_SIZE)
            y = height - 2 * cm

        # Draw the song entry with multiple lines
        current_y = y
        for line_idx, line in enumerate(title_lines):
            c.setFont(font_name, font_size)

            if line_idx == 0:
                # First line: draw page number and line
                c.drawString(left_margin, current_y, page_str)
                c.drawRightString(right_margin, current_y, line)

                # Add dots only on the first line
                line_width = c.stringWidth(line, font_name, font_size)
                dots_start_pos = left_margin + page_width + 0.3 * cm
                dots_end_pos = right_margin - line_width - 0.3 * cm

                if dots_end_pos > dots_start_pos:
                    num_dots = int((dots_end_pos - dots_start_pos) // c.stringWidth('.', font_name, font_size))
                    if num_dots > 0:
                        dots_str = '.' * num_dots
                        c.drawString(dots_start_pos, current_y, dots_str)
            else:
                # Additional lines: only draw the text (right-aligned)
                c.drawRightString(right_margin, current_y, line)

            current_y -= INDEX_LINE_SPACING

        # Update y position for next entry
        y = current_y
        if y < 2 * cm:
            c.showPage()
            c.setFont("IndexFont", INDEX_SONG_FONT_SIZE)
            y = height - 2 * cm

    c.save()

# --- Step 2.5: Estimate index page count ---
def estimate_index_pages(num_songs):
    height = A4[1]
    songs_per_page = int((height - 5.5 * cm) // INDEX_LINE_SPACING)
    return (num_songs + songs_per_page - 1) // songs_per_page

def create_artist_index(artist_songs, output_path, font_path, start_page=1, pdf_start_page_map=None):
    """
    Create an artist-based index PDF with configurable font support.

    Args:
        artist_songs (dict): Dictionary mapping artist names to list of (song_name, pdf_path) tuples
        output_path (Path): Output path for the artist index PDF
        font_path (Path): Path to font file
        start_page (int): Starting page number for songs
        pdf_start_page_map (dict): Mapping of PDF paths to their start pages in merged PDF
    """
    # Register fonts based on configuration (same logic as create_index)
    if INDEX_FONT_TYPE == "Lucida":
        # Try to register Lucida Sans Unicode for mixed language support
        try:
            lucida_paths = [
                "C:/Windows/Fonts/l_10646.ttf",  # Windows path
                "/System/Library/Fonts/LucidaGrande.ttc",  # macOS path
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"  # Linux fallback
            ]

            lucida_registered = False
            for path in lucida_paths:
                try:
                    if Path(path).exists():
                        pdfmetrics.registerFont(TTFont("IndexFont", path))
                        lucida_registered = True
                        print(f"[DEBUG] Registered Lucida font for artist index from: {path}")
                        break
                except:
                    continue

            if not lucida_registered:
                print("[DEBUG] Could not find Lucida Sans Unicode for artist index, using Hebrew font as fallback")
                pdfmetrics.registerFont(TTFont("IndexFont", str(font_path)))

        except Exception as e:
            print(f"[DEBUG] Font registration failed for artist index, using Hebrew font as fallback: {e}")
            pdfmetrics.registerFont(TTFont("IndexFont", str(font_path)))
    else:  # INDEX_FONT_TYPE == "David"
        # Use David Hebrew font
        pdfmetrics.registerFont(TTFont("IndexFont", str(font_path)))
        print(f"[DEBUG] Registered David Hebrew font for artist index from: {font_path}")

    # Create canvas
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Title
    title = reshape_hebrew("אומנים")
    c.setFont('IndexFont', INDEX_TITLE_FONT_SIZE)
    c.drawRightString(width - 2 * cm, height - 2 * cm, title)

    # Column headers - match regular index format
    y = height - 3.5 * cm
    c.setFont('IndexFont', INDEX_HEADER_FONT_SIZE)
    col_title = reshape_hebrew(COL_TITLE)  # "שם השיר"
    col_page = reshape_hebrew(COL_PAGE)    # "עמוד"
    right_margin = width - 2 * cm
    left_margin = 2 * cm
    c.drawRightString(right_margin, y, col_title)
    c.drawString(left_margin, y, col_page)
    y -= 1.2 * cm
    c.setFont('IndexFont', INDEX_SONG_FONT_SIZE)

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

            # Prepare for multi-line text drawing
            page_str = str(page_num)
            c.setFont("IndexFont", INDEX_SONG_FONT_SIZE)
            page_width = c.stringWidth(page_str, "IndexFont", INDEX_SONG_FONT_SIZE)
            available_width = right_margin - left_margin - page_width - 1 * cm  # Leave 1cm space

            # Split title into multiple lines if needed
            title_lines = split_long_text(c, display_text, "IndexFont", INDEX_SONG_FONT_SIZE, available_width, right_margin, left_margin)

            # Check if we need a new page (consider all lines needed)
            lines_needed = len(title_lines)
            space_needed = lines_needed * INDEX_LINE_SPACING
            if y - space_needed < 3 * cm:
                c.showPage()
                c.setFont('IndexFont', INDEX_SONG_FONT_SIZE)
                y = height - 2 * cm

            # Draw the song entry with multiple lines
            current_y = y
            for line_idx, line in enumerate(title_lines):
                c.setFont("IndexFont", INDEX_SONG_FONT_SIZE)

                if line_idx == 0:
                    # First line: draw page number and line
                    c.drawString(left_margin, current_y, page_str)
                    c.drawRightString(right_margin, current_y, line)

                    # Add dots only on the first line
                    line_width = c.stringWidth(line, "IndexFont", INDEX_SONG_FONT_SIZE)
                    dots_start_pos = left_margin + page_width + 0.3 * cm
                    dots_end_pos = right_margin - line_width - 0.3 * cm

                    if dots_end_pos > dots_start_pos:
                        num_dots = int((dots_end_pos - dots_start_pos) // c.stringWidth('.', "IndexFont", INDEX_SONG_FONT_SIZE))
                        if num_dots > 0:
                            dots_str = '.' * num_dots
                            c.drawString(dots_start_pos, current_y, dots_str)
                else:
                    # Additional lines: only draw the text (right-aligned)
                    c.drawRightString(right_margin, current_y, line)

                current_y -= INDEX_LINE_SPACING

            # Update y position for next entry
            y = current_y

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

def add_post_process_links(pdf_path):
    """
    Post-process the final PDF to add individual clickable links for each page number.
    This approach simulates the exact layout logic to find precise positions.
    """
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    # First, find where the songs actually start by looking for page numbers
    total_pages = len(reader.pages)
    first_song_page_idx = None

    # Look for the first page with a page number "1" at the bottom
    for page_idx in range(total_pages):
        try:
            page = reader.pages[page_idx]
            text = page.extract_text()
            # Look for page number "1" that's likely at the bottom
            if '1' in text:
                # Check if this looks like a song page (has page number at bottom)
                lines = text.split('\n')
                for line in lines[-3:]:  # Check last few lines
                    if line.strip() == '1':
                        first_song_page_idx = page_idx
                        break
                if first_song_page_idx is not None:
                    break
        except:
            continue

    if first_song_page_idx is None:
        print("[ERROR] Could not find first song page!")
        return

    print(f"[DEBUG] First song page found at PDF index {first_song_page_idx}")

    # Create a mapping: displayed_page_number -> actual_pdf_page_index
    page_number_to_pdf_index = {}
    current_song_page = 1

    for pdf_idx in range(first_song_page_idx, total_pages):
        page_number_to_pdf_index[current_song_page] = pdf_idx
        current_song_page += 1

    print(f"[DEBUG] Mapped {len(page_number_to_pdf_index)} page numbers to PDF indices")

    # Process each index page individually
    links_added = 0
    for page_idx in range(first_song_page_idx):
        page = reader.pages[page_idx]

        # Use the same layout logic as in create_index function
        songs_per_page = int((A4[1] - 5.5 * cm) // INDEX_LINE_SPACING)
        y_start = A4[1] - 3.5 * cm - 1.2 * cm  # Same as in create_index

        try:
            # Extract text to understand the content structure
            text = page.extract_text()
            lines = text.split('\n')

            # Find all numbers that could be page numbers
            page_numbers_found = []
            for line in lines:
                line = line.strip()
                # Look for standalone numbers that could be page numbers
                if line.isdigit():
                    try:
                        page_num = int(line)
                        if 1 <= page_num <= 150:  # Reasonable range for song page numbers
                            page_numbers_found.append(page_num)
                    except:
                        pass
                # Also check for numbers at the beginning of lines (before dots)
                elif '.' in line and line.split('.')[0].strip().isdigit():
                    try:
                        page_num = int(line.split('.')[0].strip())
                        if 1 <= page_num <= 150:
                            page_numbers_found.append(page_num)
                    except:
                        pass

            # Remove duplicates while preserving order
            unique_page_numbers = []
            seen = set()
            for num in page_numbers_found:
                if num not in seen and num in page_number_to_pdf_index:
                    unique_page_numbers.append(num)
                    seen.add(num)


            # Create individual links for each page number found
            y = y_start
            for i, page_num in enumerate(unique_page_numbers):
                if i >= songs_per_page:  # Don't exceed expected songs per page
                    break

                if page_num in page_number_to_pdf_index:
                    target_pdf_idx = page_number_to_pdf_index[page_num]

                    # Create a small, precise link area for this specific page number
                    page_str = str(page_num)
                    approx_char_width = INDEX_SONG_FONT_SIZE * 0.6
                    text_width = len(page_str) * approx_char_width

                    x1 = 2 * cm - 0.2 * cm  # Slightly left of where page numbers are drawn
                    y1 = y - INDEX_SONG_FONT_SIZE
                    x2 = x1 + text_width + 0.4 * cm  # Slightly wider than text
                    y2 = y + 0.2 * cm  # Slightly taller than text

                    add_link_annotation(page, (x1, y1, x2, y2), target_pdf_idx)
                    links_added += 1

                y -= INDEX_LINE_SPACING

        except Exception as e:
            print(f"[DEBUG] Could not process page {page_idx}: {e}")

        writer.add_page(page)

    # Add the rest of the pages (songs) without modification
    for page_idx in range(first_song_page_idx, total_pages):
        writer.add_page(reader.pages[page_idx])

    # Save the updated PDF
    with open(str(pdf_path), "wb") as f:
        writer.write(f)

    print(f"[DEBUG] Added {links_added} individual page number links successfully")

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

add_post_process_links(output_pdf)

# --- Cleanup ---
for idx_pdf in index_pdfs:
    if idx_pdf.exists():
        idx_pdf.unlink()
if temp_merged_path.exists():
    temp_merged_path.unlink()

print(f"\u2705 Done! Songbook with Hebrew & page numbers: {output_pdf}")
