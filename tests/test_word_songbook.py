import unittest

from docx import Document

from word_songbook import _add_index_page


class WordSongbookTests(unittest.TestCase):
    def test_start_on_new_page_starts_index_heading_on_new_page(self):
        document = Document()

        _add_index_page(
            document,
            "Second index",
            [],
            {},
            {},
            5,
            page_break_before=True,
        )

        self.assertTrue(
            document.paragraphs[0].paragraph_format.page_break_before
        )

    def test_index_heading_has_no_page_break_by_default(self):
        document = Document()

        _add_index_page(
            document,
            "First index",
            [],
            {},
            {},
            5,
        )

        self.assertFalse(
            document.paragraphs[0].paragraph_format.page_break_before
        )


if __name__ == "__main__":
    unittest.main()
