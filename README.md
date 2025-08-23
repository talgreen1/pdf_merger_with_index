# Songbook PDF Merger with Index

This script combines multiple PDF files from one or more folders into a single songbook PDF, complete with an index of all songs and page numbers. If your songs are organized in several folders, the script will also generate a separate index for each folder.

## Features
- **Automatic PDF Merging:** Combines all PDFs from specified folders into a single PDF.
- **Alphabetical Sorting:** Songs are sorted alphabetically by filename.
- **Comprehensive Index:** Generates an index with song titles and their corresponding page numbers.
- **Per-Folder Indexes:** If multiple folders are provided, an additional index is created for each folder.
- **Page Numbering:** Adds page numbers to the final PDF.

## Requirements
- Python 3.7+
- All dependencies listed in `requirements.txt` (install with `pip install -r requirements.txt`)

## Usage

1. **Prepare your PDFs:**
   - Place your song PDFs in one or more folders. Each PDF should be named after the song title for best results.

2. **Run the script:**
   - Open a terminal in the project directory.
   - Run the script with the folders you want to merge. For example:
     ```sh
     python create_song_book.py folder1 folder2 folder3
     ```
   - You can specify as many folders as you like. The script will process all PDFs in the given folders.

3. **Output:**
   - The script will generate a merged PDF (e.g., `songbook_with_index.pdf`) in the current directory.
   - The output PDF will include:
     - An index of all songs (with page numbers)
     - Per-folder indexes (if multiple folders are used)
     - All songs, merged and sorted alphabetically
     - Page numbers on each page

## Notes
- The script uses a custom font (`david.ttf`) for Hebrew support. Ensure this file is present in the project directory.
- Temporary files are cleaned up automatically after the script runs.

## Example
```sh
python create_song_book.py my_songs hebrew_songs
```
This will merge all PDFs from `my_songs` and `hebrew_songs`, create a global index, and a separate index for each folder.

## Troubleshooting
- If you encounter missing dependencies, install them with:
  ```sh
  pip install -r requirements.txt
  ```
- Ensure all PDF files are not password-protected and are readable.

## License
This project is provided as-is for personal use.

