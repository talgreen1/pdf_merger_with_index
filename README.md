# Songbook PDF Merger with Hebrew Index

This Python script automates the creation of a songbook PDF with Hebrew support, combining multiple PDF files into a single document with comprehensive indexing and page numbering.

## Features

- **Automatic PDF Merging:** Combines all PDFs from a specified directory (including subdirectories) into a single PDF
- **Hebrew Support:** Full Hebrew text support with proper right-to-left rendering using custom Hebrew font
- **Multiple Index Types:**
  - Main comprehensive index of all songs
  - **Artist index ("אומנים"):** Songs organized by artist name with format "Artist Name - Song Name"
  - Custom indexes based on `more.txt` files in subdirectories
  - **Separated indexes:** Independent song collections that appear in their own indexes and are excluded from the main index
  - Optional subfolder-specific indexes
- **Alphabetical Sorting:** Songs are sorted alphabetically by filename (case-insensitive)
- **Clickable Links:** Index entries are clickable and link directly to the corresponding song pages
- **Page Numbering:** Adds page numbers to all song pages
- **Smart Page Calculation:** Automatically estimates and adjusts for index page counts
- **Artist Name Extraction:** Automatically extracts artist information from filenames following the pattern "Song Name - Artist Name.pdf"

## Requirements

- Python 3.7+
- Required packages (install with `pip install -r requirements.txt`):
  - `pypdf` - PDF manipulation
  - `reportlab` - PDF generation
  - `arabic-reshaper` - Hebrew text reshaping
  - `python-bidi` - Bidirectional text support
- `david.ttf` - Hebrew font file (must be in the project directory)

## Configuration

Before running the script, you need to modify the configuration variables at the top of `create_song_book.py`:

```python
# --- Config ---
pdf_folder = Path("c:/temp/songs/pdfs/")  # Folder for input PDF files
output_folder = Path("c:/temp/songs/Res/")  # Folder for final output PDF
output_pdf = output_folder / "רגע של אור - שירים.pdf"  # Output filename
```

### Customizable Settings

- **EXTRA_INDEX_FILENAME**: Name of files containing custom song lists (default: `"more.txt"`)
- **INDEX_TITLE**: Main index title in Hebrew (default: `"רגע של אור - כל השירים"`)
- **PAGE_NUMBER_POSITION**: Where to place page numbers (`"left"`, `"right"`, or `"both"`)
- **INDEX_LINE_SPACING**: Spacing between songs in index (default: `0.8 * cm`)
- **INDEX_SONG_FONT_SIZE**: Font size for song names in index (default: `18`)
- **ENABLE_SUBFOLDER_INDEX**: Enable/disable automatic subfolder indexes (default: `True`)

## Usage

1. **Prepare your environment:**
   - Ensure `david.ttf` Hebrew font file is in the project directory
   - Install dependencies: `pip install -r requirements.txt`

2. **Organize your PDFs:**
   - Place your song PDFs in the configured input directory
   - Name each PDF file after the song title for best results
   - Optionally organize songs into subdirectories

3. **Create custom indexes (optional):**
   - Create `more.txt` files in subdirectories to define custom song orders
   - List one song filename per line in the desired order

4. **Configure the script:**
   - Edit the paths in `create_song_book.py` to match your directory structure
   - Adjust other settings as needed

5. **Run the script:**
   ```bash
   python create_song_book.py
   ```

## Output Structure

The script generates a single PDF with the following structure:

1. **Main Index** - Comprehensive list of all songs with page numbers (excluding separated songs)
2. **Artist Index** - Songs organized by artist name
3. **Custom Indexes** - Additional indexes based on `more.txt` files (if present)
4. **Separated Indexes** - Independent indexes for folders marked with `.separate` files
5. **Subfolder Indexes** - Separate indexes for each subdirectory (if enabled)
6. **Song Pages** - All PDF files merged in alphabetical order with page numbers
7. **Separated Song Pages** - Songs from separated folders, placed after regular songs

## Custom Index Files

You can create `more.txt` files in subdirectories to define custom song collections:

```
# Example more.txt content
song1.pdf
favorite_song.pdf
another_song.pdf
```

The script will create a separate index for these songs while still including them in the main index.

## Separated Index Feature

The separated index feature allows you to create completely independent song collections that are excluded from the main songbook but have their own dedicated indexes and appear at the end of the PDF.

### How to Create Separated Collections

1. **Create a `.separate` file:** Place an empty file named `.separate` in any subdirectory within your PDF folder
2. **Add songs to the folder:** All PDF files in folders containing a `.separate` file will be treated as separated songs
3. **Automatic processing:** The script will automatically:
   - Exclude these songs from the main index and artist index
   - Create a dedicated index for each separated folder
   - Place separated songs after all regular songs in the final PDF

### Example Structure

```
songs/
├── regular_song1.pdf          # Appears in main index
├── regular_song2.pdf          # Appears in main index
├── category1/
│   ├── song3.pdf             # Appears in main index
│   └── song4.pdf             # Appears in main index
└── special_collection/
    ├── .separate             # Marker file (empty)
    ├── special_song1.pdf     # Excluded from main index
    └── special_song2.pdf     # Excluded from main index
```

### Result

- **Main Index:** Contains `regular_song1.pdf`, `regular_song2.pdf`, `song3.pdf`, `song4.pdf`
- **Special Collection Index:** Contains only `special_song1.pdf`, `special_song2.pdf`
- **PDF Order:** Regular songs first, then separated songs at the end

### Use Cases

- **Guest collections:** Songs by visiting artists that should be separate from the main repertoire
- **Seasonal content:** Holiday or special event songs
- **Different languages:** Collections in different languages that need separate organization
- **Work-in-progress:** Draft songs that aren't ready for the main collection

## Hebrew Text Support

The script includes comprehensive Hebrew support:
- Right-to-left text rendering
- Proper Hebrew character shaping
- Bidirectional text algorithm support
- Custom Hebrew font integration

## File Structure Example

```
project/
├── create_song_book.py
├── david.ttf
├── requirements.txt
└── songs/
    ├── song1.pdf
    ├── song2.pdf
    ├── category1/
    │   ├── more.txt
    │   ├── song3.pdf
    │   └── song4.pdf
    └── special_collection/
        ├── .separate          # Marker for separated index
        ├── special_song1.pdf
        └── special_song2.pdf
```

## Troubleshooting

- **Missing dependencies:** Run `pip install -r requirements.txt`
- **Font issues:** Ensure `david.ttf` is in the project directory
- **Path errors:** Check that input and output directories exist and are accessible
- **PDF errors:** Ensure all PDF files are not password-protected and readable
- **Hebrew display issues:** Verify the Hebrew font file is properly installed

## Technical Details

- Uses `pypdf` for PDF manipulation and merging
- Uses `reportlab` for generating index pages
- Implements proper Hebrew text handling with `arabic-reshaper` and `python-bidi`
- Automatically calculates page offsets for accurate index page numbers
- Creates clickable links between index entries and song pages

## Filename Conventions

For optimal use of the artist index feature, follow these filename conventions:

### Artist-Song Pattern
Name your PDF files using the pattern: `"Song Name - Artist Name.pdf"`

**Examples:**
- `שיר יפה - דוד ברוזה.pdf` → Will appear in artist index as "דוד ברוזה - שיר יפה"
- `מלודיה - יהודית רביץ.pdf` → Will appear in artist index as "יהודית רביץ - מלודיה"
- `בלדה רומנטית - להקת הזמר.pdf` → Will appear in artist index as "להקת הזמר - בלדה רומנטית"

### Songs Without Artists
Files that don't follow the artist pattern will still be included in the main index and will appear in a separate "שירים ללא אומן" (Songs Without Artist) section in the artist index:
- `שיר ללא אומן.pdf` → Appears only in main index and "songs without artist" section

### Best Practices
- Use consistent spelling for artist names across files
- Avoid extra spaces around the dash separator
- Hebrew characters are fully supported in both song and artist names
- Multiple artists can be included: `שיר - אומן א' ואומן ב'.pdf`

## License

This project is provided as-is for personal use.