from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from manifest_songbook import generate_manifest_songbook


class ManifestSongbookTests(unittest.TestCase):
    @patch("manifest_songbook.create_word_songbook_from_plan")
    @patch("manifest_songbook.PdfReader")
    def test_generates_only_docx(self, pdf_reader, create_word):
        pdf_reader.return_value.get_num_pages.return_value = 2
        song = Path("song.pdf")
        resolved_index = SimpleNamespace(
            title="All",
            entries=[("Song", song)],
            start_on_new_page=False,
        )
        chapter = SimpleNamespace(
            id="chapter",
            songs=[song],
            indexes=[resolved_index],
        )
        plan = SimpleNamespace(
            chapters=[chapter],
            indexes=[resolved_index],
            song_merge_order=[song],
            warnings=[],
        )

        with TemporaryDirectory() as directory:
            output_docx = Path(directory) / "book.docx"

            result = generate_manifest_songbook(plan, output_docx)

            self.assertEqual(result, output_docx)
            self.assertEqual(list(Path(directory).glob("*.pdf")), [])
            create_word.assert_called_once_with(
                output_path=output_docx,
                indexes=[("All", [("Song", song)], False)],
                songs=[song],
                song_start_pages={song: 1},
                document_title="רגע של אור - ספר שירים",
                document_title_font_size_pt=24,
                index_entry_spacing_pt=5,
                index_title_font_size_pt=18,
                page_number_font_size_pt=14,
            )


if __name__ == "__main__":
    unittest.main()
