# Artist Index Feature Implementation Plan

## Overview

This document outlines the implementation plan for adding an artist-based index ("אומנים") to the Hebrew Songbook PDF Generator. The new index will list songs organized by artist names, displaying them in the format "Artist Name - Song Name" with correct page references.

## Feature Requirements

### Functional Requirements

1. **Artist Name Extraction**: Parse artist names from filenames that follow the pattern "Song Name - Artist Name.pdf"
2. **Index Creation**: Generate a new index titled "אומנים" (Artists)
3. **Display Format**: Show entries as "Artist Name - Song Name" (reversed from filename)
4. **Sorting**: Sort entries alphabetically by artist name (Hebrew alphabetical order)
5. **Page References**: Maintain accurate page numbers matching the original song locations
6. **Integration**: Seamlessly integrate with existing index system

### Non-Functional Requirements

1. **Performance**: Minimal impact on existing processing time
2. **Maintainability**: Follow existing code patterns and architecture
3. **Robustness**: Handle edge cases gracefully (missing artist names, special characters)
4. **Hebrew Support**: Full Hebrew text support with proper RTL rendering

## Technical Analysis

### Current Index System Architecture

The existing system creates multiple index types:
1. **Main Index**: All songs alphabetically by filename
2. **Custom Indexes**: Based on `more.txt` files in subdirectories  
3. **Subfolder Indexes**: Automatic indexes for directory organization

### Integration Points

The artist index will be integrated at the following locations in `create_song_book.py`:

1. **Line 110-118**: After main index creation
2. **Line 175-183**: In the index page calculation section
3. **Line 184-198**: In the index regeneration section

## Implementation Plan

### Phase 1: Artist Name Parsing Function

**Location**: Add after `reshape_hebrew()` function (around line 38)

```python
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
            return artist_name.strip(), song_name.strip()
    return None, filename_stem
```

### Phase 2: Artist Data Collection

**Location**: Add after line 107 (pdf_name_to_path creation)

```python
# --- Artist Index Data Collection ---
artist_songs = {}  # Dictionary: artist_name -> [(song_name, pdf_path, page_start)]
songs_without_artist = []  # List of songs without artist information

for pdf_path in pdf_files:
    artist_name, song_name = extract_artist_from_filename(pdf_path.stem)
    if artist_name:
        if artist_name not in artist_songs:
            artist_songs[artist_name] = []
        artist_songs[artist_name].append((song_name, pdf_path))
    else:
        songs_without_artist.append((pdf_path.stem, pdf_path))
```

### Phase 3: Artist Index Creation Function

**Location**: Add after `estimate_index_pages()` function (around line 105)

```python
def create_artist_index(artist_songs, songs_without_artist, output_path, font_path, 
                       start_page=1, pdf_start_page_map=None):
    """
    Create an artist-based index PDF with Hebrew support.
    
    Args:
        artist_songs (dict): Dictionary mapping artist names to list of (song_name, pdf_path) tuples
        songs_without_artist (list): List of (song_name, pdf_path) tuples for songs without artists
        output_path (Path): Output path for the artist index PDF
        font_path (Path): Path to Hebrew font file
        start_page (int): Starting page number for songs
        pdf_start_page_map (dict): Mapping of PDF paths to their start pages in merged PDF
    """
    # Register Hebrew font
    pdfmetrics.registerFont(TTFont('Hebrew', str(font_path)))
    
    # Create canvas
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # Title
    title = reshape_hebrew("אומנים")
    c.setFont('Hebrew', 16)
    title_width = c.stringWidth(title, 'Hebrew', 16)
    c.drawString((width - title_width) / 2, height - 2 * cm, title)
    
    # Column headers
    c.setFont('Hebrew', 12)
    col_title = reshape_hebrew(COL_TITLE)  # "שם השיר"
    col_page = reshape_hebrew(COL_PAGE)    # "עמוד"
    
    header_y = height - 3 * cm
    c.drawString(2 * cm, header_y, col_title)
    c.drawString(width - 3 * cm, header_y, col_page)
    
    # Draw header line
    c.line(2 * cm, header_y - 0.3 * cm, width - 2 * cm, header_y - 0.3 * cm)
    
    # Content
    y_position = header_y - 1 * cm
    c.setFont('Hebrew', INDEX_SONG_FONT_SIZE)
    
    # Sort artists alphabetically (Hebrew sorting)
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
            if y_position < 3 * cm:
                c.showPage()
                c.setFont('Hebrew', INDEX_SONG_FONT_SIZE)
                y_position = height - 2 * cm
            
            # Draw song entry
            c.drawString(2 * cm, y_position, display_text)
            c.drawString(width - 3 * cm, y_position, str(page_num))
            
            y_position -= INDEX_LINE_SPACING
    
    # Add songs without artist at the end (optional section)
    if songs_without_artist:
        # Add separator
        if y_position < 4 * cm:
            c.showPage()
            c.setFont('Hebrew', INDEX_SONG_FONT_SIZE)
            y_position = height - 2 * cm
        
        # Section header for songs without artist
        y_position -= INDEX_LINE_SPACING
        section_header = reshape_hebrew("שירים ללא אומן")
        c.setFont('Hebrew', 12)
        c.drawString(2 * cm, y_position, section_header)
        y_position -= INDEX_LINE_SPACING
        c.setFont('Hebrew', INDEX_SONG_FONT_SIZE)
        
        for song_name, pdf_path in songs_without_artist:
            display_text = reshape_hebrew(song_name)
            
            # Get page number
            if pdf_start_page_map and pdf_path in pdf_start_page_map:
                page_num = pdf_start_page_map[pdf_path]
            else:
                page_num = start_page  # Fallback
            
            # Check if we need a new page
            if y_position < 3 * cm:
                c.showPage()
                c.setFont('Hebrew', INDEX_SONG_FONT_SIZE)
                y_position = height - 2 * cm
            
            # Draw song entry
            c.drawString(2 * cm, y_position, display_text)
            c.drawString(width - 3 * cm, y_position, str(page_num))
            
            y_position -= INDEX_LINE_SPACING
    
    c.save()
```

### Phase 4: Integration with Main Workflow

**Location**: Modify the index creation section (around lines 110-118)

```python
# Main index
main_index_pages = estimate_index_pages(len(pdf_files))
main_index_pdf = output_folder / "index_main_temp.pdf"
create_index(pdf_files, main_index_pdf, hebrew_font_path, start_page=main_index_pages + 1, pdf_page_counts=pdf_page_counts)
index_pdfs.append(main_index_pdf)
index_page_counts.append(main_index_pages)

# Artist index
if artist_songs:  # Only create if there are songs with artists
    artist_index_pages = estimate_index_pages(
        sum(len(songs) for songs in artist_songs.values()) + len(songs_without_artist)
    )
    artist_index_pdf = output_folder / "index_artists_temp.pdf"
    # Note: We'll create this after pdf_start_page_map is built
    index_pdfs.append(artist_index_pdf)
    index_page_counts.append(artist_index_pages)
```

### Phase 5: Update Index Regeneration Section

**Location**: Modify around lines 184-198

```python
# Regenerate all indexes with correct start_page
main_index_pages = index_page_counts[0]
create_index(pdf_files, main_index_pdf, hebrew_font_path, start_page=main_index_pages + 1, pdf_page_counts=pdf_page_counts)

# Create artist index with correct page mapping
if artist_songs:
    artist_index_pdf = output_folder / "index_artists_temp.pdf"
    create_artist_index(
        artist_songs, 
        songs_without_artist, 
        artist_index_pdf, 
        hebrew_font_path, 
        start_page=sum(index_page_counts) + 1,
        pdf_start_page_map=pdf_start_page_map
    )
```

### Phase 6: Update Link Generation

**Location**: Modify the link generation section to include artist index links

The existing `add_all_index_links_with_pypdf()` function will need to be updated to handle the artist index links as well.

## Testing Strategy

### Unit Tests

1. **Artist Name Extraction**:
   - Test various filename patterns
   - Test edge cases (multiple dashes, Hebrew characters, special characters)
   - Test files without artist names

2. **Artist Index Creation**:
   - Test with various artist/song combinations
   - Test Hebrew text rendering
   - Test page number accuracy

### Integration Tests

1. **Full Workflow**: Test complete songbook generation with artist index
2. **Link Functionality**: Verify clickable links work correctly
3. **Page Numbering**: Ensure page numbers are accurate across all indexes

### Test Data

Create test PDF files with various naming patterns:
- `שיר יפה - דוד ברוזה.pdf`
- `מלודיה - יהודית רביץ.pdf`
- `שיר ללא אומן.pdf`

## Configuration Options

Add new configuration constants:

```python
# Artist index configuration
ENABLE_ARTIST_INDEX = True  # Enable/disable artist index creation
ARTIST_INDEX_TITLE = "אומנים"  # Title for artist index
INCLUDE_SONGS_WITHOUT_ARTIST = True  # Include section for songs without artists
```

## Error Handling

1. **Invalid Filenames**: Handle filenames that don't follow expected patterns
2. **Hebrew Encoding**: Ensure proper handling of Hebrew characters in filenames
3. **Missing Artists**: Gracefully handle songs without artist information
4. **Font Issues**: Handle Hebrew font loading errors

## Performance Considerations

1. **Memory Usage**: Artist data collection adds minimal memory overhead
2. **Processing Time**: Artist name extraction is O(n) operation
3. **Index Generation**: Similar performance to existing index creation

## Backward Compatibility

- All existing functionality remains unchanged
- New feature can be disabled via configuration
- No changes to existing file formats or APIs

## Documentation Updates

1. **README.md**: Add description of artist index feature
2. **API_DOCUMENTATION.md**: Document new functions
3. **TECHNICAL_DOCUMENTATION.md**: Update architecture section
4. **User Guide**: Add instructions for filename conventions

## Implementation Timeline

1. **Phase 1-2**: Artist parsing and data collection (2 hours)
2. **Phase 3**: Artist index creation function (3 hours)
3. **Phase 4-5**: Integration with main workflow (2 hours)
4. **Phase 6**: Link generation updates (2 hours)
5. **Testing**: Comprehensive testing (3 hours)
6. **Documentation**: Update all documentation (2 hours)

**Total Estimated Time**: 14 hours

## Questions for Clarification

Before implementation, please confirm:

1. **Filename Pattern**: Is the pattern always "Song Name - Artist Name.pdf" or are there variations?
2. **Hebrew Sorting**: Should artist names be sorted using Hebrew alphabetical order or Latin alphabetical order?
3. **Multiple Artists**: How should songs with multiple artists be handled (e.g., "Song - Artist1 & Artist2")?
4. **Artist Normalization**: Should artist names be normalized (e.g., removing extra spaces, standardizing punctuation)?
5. **Index Position**: Where should the artist index appear in the final PDF (after main index, before subfolder indexes, etc.)?
6. **Songs Without Artists**: Should songs without artist information be included in the artist index or omitted entirely?

## Risk Assessment

**Low Risk**:
- Feature is additive and doesn't modify existing functionality
- Uses established patterns from existing codebase
- Hebrew text processing already implemented

**Mitigation Strategies**:
- Comprehensive testing with various filename patterns
- Fallback handling for edge cases
- Configuration option to disable feature if issues arise

## Success Criteria

1. Artist index is generated correctly with proper Hebrew formatting
2. Page numbers accurately reference song locations
3. Clickable links function properly
4. Performance impact is minimal
5. All existing functionality continues to work unchanged
6. Code follows existing patterns and is maintainable