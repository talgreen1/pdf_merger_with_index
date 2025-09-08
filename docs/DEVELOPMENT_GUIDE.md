# Development Guide: Hebrew Songbook PDF Generator

## Development Environment Setup

### Prerequisites

- **Python 3.7+** (recommended: Python 3.9+)
- **Git** for version control
- **IDE/Editor** with Python support (VS Code, PyCharm, etc.)
- **Hebrew font file** (`david.ttf`)

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd hebrew-songbook-generator
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Hebrew font**:
   ```bash
   ls -la david.ttf  # Should exist in project root
   ```

5. **Run initial test**:
   ```bash
   python create_song_book.py
   ```

## Project Structure

```
hebrew-songbook-generator/
├── create_song_book.py          # Main application script
├── david.ttf                    # Hebrew font file
├── requirements.txt             # Python dependencies
├── README.md                    # User documentation
├── TECHNICAL_DOCUMENTATION.md   # Technical specifications
├── API_DOCUMENTATION.md         # API reference
├── DEVELOPMENT_GUIDE.md         # This file
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_hebrew_processing.py
│   ├── test_pdf_operations.py
│   ├── test_integration.py
│   └── fixtures/                # Test data
│       ├── sample_pdfs/
│       └── expected_outputs/
├── docs/                        # Additional documentation
│   ├── architecture.md
│   ├── deployment.md
│   └── troubleshooting.md
└── scripts/                     # Development utilities
    ├── setup_dev_env.py
    ├── run_tests.py
    └── generate_docs.py
```

## Code Architecture

### Module Organization

The current implementation is a single-file script. For development, consider refactoring into modules:

```python
# Proposed modular structure
songbook/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── pdf_processor.py      # PDF operations
│   ├── hebrew_text.py        # Hebrew text processing
│   ├── index_generator.py    # Index creation
│   └── link_manager.py       # Clickable links
├── config/
│   ├── __init__.py
│   ├── settings.py           # Configuration management
│   └── constants.py          # Application constants
├── utils/
│   ├── __init__.py
│   ├── file_utils.py         # File operations
│   └── validation.py         # Input validation
└── cli/
    ├── __init__.py
    └── main.py               # Command-line interface
```

### Design Patterns

#### 1. Builder Pattern for PDF Creation

```python
class SongbookBuilder:
    def __init__(self):
        self.pdf_files = []
        self.indexes = []
        self.config = {}
    
    def add_pdf_directory(self, path):
        """Add PDFs from directory"""
        return self
    
    def add_custom_index(self, name, songs):
        """Add custom index"""
        return self
    
    def set_hebrew_font(self, font_path):
        """Set Hebrew font"""
        return self
    
    def build(self, output_path):
        """Generate final songbook"""
        pass
```

#### 2. Strategy Pattern for Index Types

```python
class IndexStrategy:
    def create_index(self, songs, output_path):
        raise NotImplementedError

class MainIndexStrategy(IndexStrategy):
    def create_index(self, songs, output_path):
        # Main index implementation
        pass

class SubfolderIndexStrategy(IndexStrategy):
    def create_index(self, songs, output_path):
        # Subfolder index implementation
        pass

class ArtistIndexStrategy(IndexStrategy):
    def create_index(self, artist_songs, songs_without_artist, output_path):
        # Artist index implementation
        pass
```

#### 3. Factory Pattern for PDF Operations

```python
class PDFOperationFactory:
    @staticmethod
    def create_merger():
        return PdfMerger()
    
    @staticmethod
    def create_reader(path):
        return PdfReader(str(path))
    
    @staticmethod
    def create_writer():
        return PdfWriter()
```

## Development Workflow

### Git Workflow

1. **Feature Development**:
   ```bash
   git checkout -b feature/new-feature-name
   # Make changes
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/new-feature-name
   ```

2. **Bug Fixes**:
   ```bash
   git checkout -b fix/bug-description
   # Fix the bug
   git add .
   git commit -m "fix: resolve bug description"
   git push origin fix/bug-description
   ```

3. **Code Review Process**:
   - Create pull request
   - Ensure all tests pass
   - Request code review
   - Address feedback
   - Merge after approval

### Commit Message Convention

Follow conventional commits format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(hebrew): add support for Nikkud diacritics
fix(pdf): resolve page numbering offset issue
docs: update API documentation for index creation
refactor(core): extract PDF operations into separate module
```

## Testing Strategy

### Test Categories

1. **Unit Tests**: Individual function testing
2. **Integration Tests**: Component interaction testing
3. **End-to-End Tests**: Complete workflow testing
4. **Performance Tests**: Speed and memory usage testing

### Test Implementation

#### Unit Test Example

```python
# tests/test_hebrew_processing.py
import unittest
from songbook.core.hebrew_text import reshape_hebrew

class TestHebrewProcessing(unittest.TestCase):
    def test_reshape_hebrew_basic(self):
        """Test basic Hebrew text reshaping"""
        input_text = "שלום עולם"
        result = reshape_hebrew(input_text)
        
        self.assertIsInstance(result, str)
        self.assertNotEqual(result, input_text)
        self.assertGreater(len(result), 0)
    
    def test_reshape_hebrew_empty(self):
        """Test empty string handling"""
        result = reshape_hebrew("")
        self.assertEqual(result, "")
    
    def test_reshape_hebrew_mixed(self):
        """Test mixed Hebrew and English text"""
        input_text = "Hello שלום World עולם"
        result = reshape_hebrew(input_text)
        self.assertIsInstance(result, str)
```

#### Integration Test Example

```python
# tests/test_integration.py
import unittest
from pathlib import Path
from songbook.core.pdf_processor import PDFProcessor

class TestPDFIntegration(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = Path("tests/fixtures/sample_pdfs")
        self.output_dir = Path("tests/output")
        self.output_dir.mkdir(exist_ok=True)
    
    def test_complete_songbook_generation(self):
        """Test complete songbook generation process"""
        processor = PDFProcessor()
        
        # Add test PDFs
        processor.add_pdf_directory(self.test_data_dir)
        
        # Generate songbook
        output_path = self.output_dir / "test_songbook.pdf"
        processor.generate_songbook(output_path)
        
        # Verify output
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)
    
    def tearDown(self):
        # Cleanup test outputs
        for file in self.output_dir.glob("*.pdf"):
            file.unlink()
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_hebrew_processing.py

# Run with coverage
python -m pytest --cov=songbook tests/

# Run performance tests
python -m pytest tests/test_performance.py -v
```

## Artist Index Feature Development

### Overview

The artist index feature adds a new index type that organizes songs by artist name, displaying them in the format "Artist Name - Song Name". This section covers development considerations, testing strategies, and implementation details.

### Development Considerations

#### 1. Filename Pattern Recognition

**Pattern**: `"Song Name - Artist Name.pdf"`

**Implementation Strategy**:
```python
def extract_artist_from_filename(filename_stem: str) -> Tuple[Optional[str], str]:
    """
    Extract artist name from filename following pattern: "Song Name - Artist Name"

    Edge cases to handle:
    - Multiple dashes: Split only on first occurrence
    - Extra whitespace: Strip automatically
    - Hebrew characters: Full Unicode support
    - No artist separator: Return None gracefully
    """
    if ' - ' in filename_stem:
        parts = filename_stem.split(' - ', 1)  # Split only on first occurrence
        if len(parts) == 2:
            song_name, artist_name = parts
            return artist_name.strip(), song_name.strip()
    return None, filename_stem
```

**Testing Considerations**:
- Test with various Hebrew character combinations
- Test with multiple dashes in filename
- Test with extra whitespace
- Test with empty strings and edge cases
- Test with mixed Hebrew/Latin characters

#### 2. Data Structure Design

**Artist Data Collection**:
```python
# Primary data structures
artist_songs: Dict[str, List[Tuple[str, Path]]] = {}
songs_without_artist: List[Tuple[str, Path]] = []

# Performance considerations:
# - O(1) artist lookup
# - O(n) space complexity
# - Minimal memory overhead
```

**Memory Management**:
- Use generators for large file collections
- Implement lazy loading for PDF metadata
- Clean up temporary data structures after use

#### 3. Hebrew Text Processing

**Sorting Considerations**:
```python
# Hebrew alphabetical sorting
sorted_artists = sorted(artist_songs.keys(), key=lambda x: x.lower())

# Considerations:
# - Hebrew collation rules
# - Mixed Hebrew/Latin text
# - Diacritics and special characters
# - Case sensitivity in Hebrew context
```

**RTL Text Rendering**:
- Ensure proper bidirectional text handling
- Test with mixed RTL/LTR content
- Verify font rendering consistency

#### 4. Integration Points

**Main Workflow Integration**:
```python
# Integration locations in create_song_book.py:
# 1. After PDF collection (around line 107)
# 2. In index creation section (around line 110-118)
# 3. In page calculation section (around line 175-183)
# 4. In index regeneration section (around line 184-198)
```

**Error Handling Strategy**:
- Graceful degradation when artist extraction fails
- Fallback to main index if artist index creation fails
- Proper error logging and user feedback
- Configuration option to disable feature

### Testing Strategy

#### 1. Unit Tests

**Artist Name Extraction Tests**:
```python
def test_extract_artist_from_filename():
    # Test cases
    test_cases = [
        ("שיר יפה - דוד ברוזה", ("דוד ברוזה", "שיר יפה")),
        ("מלודיה - יהודית רביץ", ("יהודית רביץ", "מלודיה")),
        ("שיר ללא אומן", (None, "שיר ללא אומן")),
        ("שיר - אומן - פרטים", ("אומן - פרטים", "שיר")),
        ("", (None, "")),
        ("   שיר   -   אומן   ", ("אומן", "שיר")),  # Whitespace handling
    ]

    for filename, expected in test_cases:
        result = extract_artist_from_filename(filename)
        assert result == expected
```

**Artist Index Creation Tests**:
```python
def test_create_artist_index():
    # Test data setup
    artist_songs = {
        "דוד ברוזה": [("שיר יפה", Path("test1.pdf"))],
        "יהודית רביץ": [("מלודיה", Path("test2.pdf"))]
    }
    songs_without_artist = [("שיר ללא אומן", Path("test3.pdf"))]

    # Test index creation
    output_path = Path("test_artist_index.pdf")
    create_artist_index(
        artist_songs,
        songs_without_artist,
        output_path,
        Path("david.ttf")
    )

    # Verify output
    assert output_path.exists()
    # Additional PDF content verification
```

#### 2. Integration Tests

**Full Workflow Test**:
```python
def test_full_workflow_with_artist_index():
    # Setup test PDFs with artist naming pattern
    test_pdfs = [
        "שיר א - אומן א.pdf",
        "שיר ב - אומן ב.pdf",
        "שיר ללא אומן.pdf"
    ]

    # Run full songbook generation
    result = create_songbook(test_pdf_directory)

    # Verify artist index exists and is correct
    assert "index_artists_temp.pdf" in result.temp_files
    # Verify final PDF structure
```

#### 3. Performance Tests

**Large Dataset Test**:
```python
def test_artist_index_performance():
    # Generate large test dataset
    num_files = 1000
    test_files = generate_test_pdfs(num_files)

    # Measure performance
    start_time = time.time()
    result = process_artist_index(test_files)
    end_time = time.time()

    # Performance assertions
    assert end_time - start_time < 10.0  # Should complete within 10 seconds
    assert len(result.artist_songs) > 0
```

### Configuration Options

**Feature Configuration**:
```python
# Artist index configuration constants
ENABLE_ARTIST_INDEX = True  # Enable/disable artist index creation
ARTIST_INDEX_TITLE = "אומנים"  # Title for artist index
INCLUDE_SONGS_WITHOUT_ARTIST = True  # Include section for songs without artists
ARTIST_SORTING_LOCALE = "he_IL"  # Hebrew locale for sorting
```

**Development Configuration**:
```python
# Development-specific settings
DEBUG_ARTIST_EXTRACTION = False  # Enable debug logging for artist extraction
ARTIST_INDEX_VALIDATION = True  # Enable additional validation checks
PERFORMANCE_PROFILING = False  # Enable performance profiling
```

### Debugging and Troubleshooting

#### 1. Common Issues

**Artist Extraction Problems**:
- Inconsistent filename patterns
- Unicode encoding issues
- Extra whitespace in filenames
- Multiple dash separators

**Hebrew Text Issues**:
- Font registration failures
- RTL text rendering problems
- Character encoding issues
- Mixed language text handling

#### 2. Debugging Tools

**Logging Configuration**:
```python
import logging

# Configure logging for artist index debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('artist_index')

def extract_artist_from_filename(filename_stem: str) -> Tuple[Optional[str], str]:
    logger.debug(f"Processing filename: {filename_stem}")
    # ... implementation
    logger.debug(f"Extracted artist: {artist_name}, song: {song_name}")
    return artist_name, song_name
```

**Validation Functions**:
```python
def validate_artist_data(artist_songs: Dict[str, List[Tuple[str, Path]]]) -> bool:
    """Validate artist data structure integrity"""
    for artist, songs in artist_songs.items():
        if not isinstance(artist, str) or not artist.strip():
            logger.error(f"Invalid artist name: {artist}")
            return False

        for song_name, pdf_path in songs:
            if not isinstance(song_name, str) or not song_name.strip():
                logger.error(f"Invalid song name: {song_name}")
                return False

            if not pdf_path.exists():
                logger.error(f"PDF file not found: {pdf_path}")
                return False

    return True
```

### Future Enhancements

#### 1. Advanced Features

**Multi-Artist Support**:
- Handle songs with multiple artists
- Support for featured artists
- Artist collaboration detection

**Artist Metadata**:
- Extract additional metadata from filenames
- Support for genre classification
- Album/collection grouping

**Internationalization**:
- Support for multiple languages
- Configurable sorting rules
- Locale-specific formatting

#### 2. Performance Optimizations

**Caching Strategy**:
- Cache artist extraction results
- Implement incremental updates
- Optimize for large collections

**Parallel Processing**:
- Parallelize artist extraction
- Concurrent index generation
- Asynchronous PDF processing

## Code Quality Standards

### Code Style

Follow PEP 8 with these additions:

1. **Line Length**: 88 characters (Black formatter default)
2. **Import Organization**:
   ```python
   # Standard library imports
   from pathlib import Path
   import os
   
   # Third-party imports
   from pypdf import PdfReader
   from reportlab.pdfgen import canvas
   
   # Local imports
   from songbook.core import pdf_processor
   from songbook.utils import file_utils
   ```

3. **Type Hints**: Use type hints for all functions
   ```python
   from typing import List, Dict, Optional, Tuple
   
   def create_index(
       pdf_paths: List[Path],
       output_path: Path,
       font_path: Path,
       start_page: int = 1
   ) -> None:
       """Create index with type hints"""
       pass
   ```

### Code Formatting Tools

1. **Black**: Code formatter
   ```bash
   pip install black
   black create_song_book.py
   ```

2. **isort**: Import sorting
   ```bash
   pip install isort
   isort create_song_book.py
   ```

3. **flake8**: Linting
   ```bash
   pip install flake8
   flake8 create_song_book.py
   ```

4. **mypy**: Type checking
   ```bash
   pip install mypy
   mypy create_song_book.py
   ```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.950
    hooks:
      - id: mypy
```

Install and setup:
```bash
pip install pre-commit
pre-commit install
```

## Debugging Guidelines

### Logging Implementation

Add comprehensive logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('songbook.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_index(pdf_paths, output_path, font_path, **kwargs):
    logger.info(f"Creating index with {len(pdf_paths)} PDFs")
    logger.debug(f"Output path: {output_path}")
    
    try:
        # Index creation logic
        logger.info("Index created successfully")
    except Exception as e:
        logger.error(f"Index creation failed: {e}")
        raise
```

### Debug Mode

Add debug configuration:

```python
# config/settings.py
DEBUG = os.getenv('SONGBOOK_DEBUG', 'False').lower() == 'true'
VERBOSE_LOGGING = os.getenv('SONGBOOK_VERBOSE', 'False').lower() == 'true'

if DEBUG:
    # Enable detailed logging
    # Keep temporary files
    # Add debug output
    pass
```

### Common Debugging Scenarios

1. **Hebrew Text Issues**:
   ```python
   # Debug Hebrew text processing
   def debug_hebrew_text(text):
       print(f"Original: {repr(text)}")
       reshaped = arabic_reshaper.reshape(text)
       print(f"Reshaped: {repr(reshaped)}")
       final = get_display(reshaped)
       print(f"Final: {repr(final)}")
       return final
   ```

2. **PDF Processing Issues**:
   ```python
   # Debug PDF operations
   def debug_pdf_info(pdf_path):
       try:
           reader = PdfReader(str(pdf_path))
           print(f"PDF: {pdf_path}")
           print(f"Pages: {len(reader.pages)}")
           print(f"Encrypted: {reader.is_encrypted}")
           print(f"Metadata: {reader.metadata}")
       except Exception as e:
           print(f"Error reading {pdf_path}: {e}")
   ```

3. **Memory Usage Monitoring**:
   ```python
   import psutil
   import os
   
   def monitor_memory():
       process = psutil.Process(os.getpid())
       memory_mb = process.memory_info().rss / 1024 / 1024
       print(f"Memory usage: {memory_mb:.2f} MB")
   ```

## Performance Optimization

### Profiling

1. **cProfile for function-level profiling**:
   ```bash
   python -m cProfile -o profile_output.prof create_song_book.py
   python -m pstats profile_output.prof
   ```

2. **line_profiler for line-by-line profiling**:
   ```bash
   pip install line_profiler
   kernprof -l -v create_song_book.py
   ```

3. **memory_profiler for memory usage**:
   ```bash
   pip install memory_profiler
   python -m memory_profiler create_song_book.py
   ```

### Optimization Strategies

1. **Lazy Loading**:
   ```python
   class LazyPDFCollection:
       def __init__(self, directory):
           self.directory = directory
           self._pdf_files = None
       
       @property
       def pdf_files(self):
           if self._pdf_files is None:
               self._pdf_files = list(self.directory.glob("*.pdf"))
           return self._pdf_files
   ```

2. **Caching**:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_pdf_page_count(pdf_path: str) -> int:
       return PdfReader(pdf_path).get_num_pages()
   ```

3. **Parallel Processing**:
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   def process_pdfs_parallel(pdf_files):
       with ThreadPoolExecutor(max_workers=4) as executor:
           page_counts = list(executor.map(get_pdf_page_count, pdf_files))
       return page_counts
   ```

## Documentation Standards

### Docstring Format

Use Google-style docstrings:

```python
def create_index(
    pdf_paths: List[Path],
    output_path: Path,
    font_path: Path,
    start_page: int = 1,
    pdf_page_counts: Optional[List[int]] = None,
    index_title: Optional[str] = None,
    song_start_pages: Optional[List[int]] = None
) -> None:
    """Creates a PDF index with Hebrew support and page numbers.
    
    This function generates a comprehensive index for a collection of PDF files,
    with proper Hebrew text rendering and clickable page number links.
    
    Args:
        pdf_paths: List of PDF file paths to include in the index.
        output_path: Path where the generated index PDF will be saved.
        font_path: Path to the Hebrew TTF font file.
        start_page: Starting page number for songs. Defaults to 1.
        pdf_page_counts: Page counts for each PDF. If None, will be calculated.
        index_title: Custom title for the index. If None, uses default.
        song_start_pages: Starting page numbers for each song. If None, calculated.
    
    Returns:
        None. The function writes the index PDF to the specified output path.
    
    Raises:
        FileNotFoundError: If font file or PDF files are not found.
        PermissionError: If unable to write to output path.
        PDFError: If PDF generation fails.
    
    Example:
        >>> pdf_files = [Path("song1.pdf"), Path("song2.pdf")]
        >>> create_index(
        ...     pdf_paths=pdf_files,
        ...     output_path=Path("index.pdf"),
        ...     font_path=Path("david.ttf")
        ... )
    """
    pass
```

### Code Comments

1. **Explain Why, Not What**:
   ```python
   # Good: Explains reasoning
   # Use ceiling division to ensure we have enough pages for all songs
   pages_needed = (num_songs + songs_per_page - 1) // songs_per_page
   
   # Bad: States the obvious
   # Divide num_songs by songs_per_page
   pages_needed = num_songs // songs_per_page
   ```

2. **Complex Algorithm Explanations**:
   ```python
   def calculate_link_coordinates(page_num, song_index):
       """Calculate clickable link coordinates for index entries.
       
       The coordinate system uses PDF's bottom-left origin. We need to:
       1. Start from the top of the usable area (height - margins)
       2. Move down by line_spacing for each song
       3. Account for page breaks and multi-page indexes
       """
       # Implementation details...
   ```

## Release Process

### Version Management

Use semantic versioning (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

Example: `1.2.3`

### Release Checklist

1. **Pre-release**:
   - [ ] All tests passing
   - [ ] Documentation updated
   - [ ] Version number bumped
   - [ ] Changelog updated
   - [ ] Performance benchmarks run

2. **Release**:
   - [ ] Create release branch
   - [ ] Final testing on release branch
   - [ ] Tag release in Git
   - [ ] Build distribution packages
   - [ ] Upload to package repository

3. **Post-release**:
   - [ ] Merge release branch to main
   - [ ] Update development branch
   - [ ] Announce release
   - [ ] Monitor for issues

### Changelog Format

```markdown
# Changelog

## [1.2.0] - 2024-01-15

### Added
- Support for custom index ordering via more.txt files
- Clickable links in index entries
- Automatic bookmark generation

### Changed
- Improved Hebrew text rendering performance
- Updated PDF processing library to latest version

### Fixed
- Page numbering offset in multi-index documents
- Memory leak in temporary file handling

### Deprecated
- Old configuration format (will be removed in v2.0)

## [1.1.0] - 2023-12-01
...
```

## Contributing Guidelines

### Getting Started

1. **Fork the repository**
2. **Create feature branch**
3. **Make changes with tests**
4. **Submit pull request**

### Pull Request Process

1. **Description**: Clear description of changes
2. **Testing**: All tests must pass
3. **Documentation**: Update relevant documentation
4. **Code Review**: Address reviewer feedback
5. **Merge**: Squash and merge after approval

### Issue Reporting

Use issue templates:

```markdown
**Bug Report**
- Description: Clear description of the bug
- Steps to Reproduce: Numbered steps
- Expected Behavior: What should happen
- Actual Behavior: What actually happens
- Environment: OS, Python version, dependencies
- Additional Context: Screenshots, logs, etc.
```

### Feature Requests

```markdown
**Feature Request**
- Summary: Brief description of the feature
- Motivation: Why is this feature needed?
- Detailed Description: How should it work?
- Alternatives: Other solutions considered
- Additional Context: Examples, mockups, etc.
```

## Troubleshooting Common Issues

### Development Environment Issues

1. **Font Loading Problems**:
   ```bash
   # Verify font file
   file david.ttf
   # Should show: TrueType font data
   ```

2. **Dependency Conflicts**:
   ```bash
   # Create clean environment
   python -m venv fresh_env
   source fresh_env/bin/activate
   pip install -r requirements.txt
   ```

3. **Path Issues**:
   ```python
   # Use absolute paths for debugging
   pdf_folder = Path("/absolute/path/to/pdfs").resolve()
   print(f"PDF folder exists: {pdf_folder.exists()}")
   ```

### Runtime Issues

1. **Memory Problems**:
   - Monitor memory usage during processing
   - Process files in batches for large collections
   - Ensure temporary file cleanup

2. **PDF Processing Errors**:
   - Validate PDF files before processing
   - Handle encrypted PDFs gracefully
   - Check file permissions

3. **Hebrew Text Rendering**:
   - Verify font file integrity
   - Test with simple Hebrew strings
   - Check character encoding (UTF-8)

This development guide provides a comprehensive foundation for contributing to and maintaining the Hebrew Songbook PDF Generator project.