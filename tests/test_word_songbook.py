import unittest

from docx import Document
from docx.oxml.ns import qn

from word_songbook import (
    _add_document_title,
    _add_index_page,
    _add_internal_link,
    _add_page_number_field,
)


class WordSongbookTests(unittest.TestCase):
    def test_document_title_uses_supplied_text(self):
        document = Document()

        _add_document_title(
            document, "רגע של אור - ספר שירים", font_size_pt=20
        )

        self.assertEqual(
            document.paragraphs[0].text, "רגע של אור - ספר שירים"
        )
        self.assertEqual(document.paragraphs[0].runs[0].font.size.pt, 20)

    def test_index_heading_uses_configured_font_size(self):
        document = Document()

        _add_index_page(
            document,
            "First index",
            [],
            {},
            {},
            5,
            index_title_font_size_pt=22,
        )

        self.assertEqual(document.paragraphs[0].runs[0].font.size.pt, 22)

    def test_footer_page_number_uses_configured_font_size(self):
        document = Document()
        paragraph = document.sections[0].footer.paragraphs[0]

        _add_page_number_field(paragraph, font_size_pt=14)

        size = paragraph.runs[0]._r.find(
            "{}/{}".format(qn("w:rPr"), qn("w:sz"))
        )
        self.assertEqual(size.get(qn("w:val")), "28")

    def test_internal_index_link_is_clickable_without_underline(self):
        document = Document()
        paragraph = document.add_paragraph()

        _add_internal_link(paragraph, "Song title", "song_0001")

        hyperlink = paragraph._p.find(qn("w:hyperlink"))
        self.assertIsNotNone(hyperlink)
        self.assertEqual(hyperlink.get(qn("w:anchor")), "song_0001")
        underline = hyperlink.find(
            "{}/{}".format(qn("w:r"), qn("w:rPr"))
        ).find(qn("w:u"))
        self.assertEqual(underline.get(qn("w:val")), "none")

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
