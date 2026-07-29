import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from book_config import BookConfigError, resolve_book_config


def _touch_pdf(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-test")


class BookConfigTests(unittest.TestCase):
    def _write_config(self, root, config):
        path = root / "book.json"
        path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        return path

    def test_folder_combines_physical_pdfs_and_more_txt(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "source" / "physical.pdf")
            _touch_pdf(root / "elsewhere" / "listed.pdf")
            (root / "source" / "more.txt").write_text(
                "listed.pdf\nphysical.pdf\n", encoding="utf-8"
            )
            config = {
                "version": 1,
                "unassigned_song_policy": "ignore",
                "collections": {
                    "combined": {"title": "Combined", "folder": "source"}
                },
                "chapters": [
                    {
                        "id": "chapter",
                        "title": "Chapter",
                        "collections": ["combined"],
                        "indexes": [{"title": "All", "scope": "chapter"}],
                    }
                ],
            }
            self._write_config(root, config)

            plan = resolve_book_config(root)

            self.assertEqual(
                {path.name for path in plan.song_merge_order},
                {"physical.pdf", "listed.pdf"},
            )
            self.assertEqual(len(plan.song_merge_order), 2)

    def test_more_txt_claim_overrides_physical_folder_chapter(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "main" / "moved.pdf")
            _touch_pdf(root / "main" / "stays.pdf")
            (root / "special").mkdir()
            (root / "special" / "more.txt").write_text(
                "moved.pdf\n", encoding="utf-8"
            )
            config = {
                "version": 1,
                "collections": {
                    "main": {"title": "Main", "folder": "main"},
                    "special": {"title": "Special", "folder": "special"},
                },
                "chapters": [
                    {
                        "id": "main",
                        "title": "Main",
                        "collections": ["main"],
                        "indexes": [
                            {"title": "All", "scope": "chapter"},
                            {"title": "Main", "collection": "main"},
                        ],
                    },
                    {
                        "id": "special",
                        "title": "Special",
                        "collections": ["special"],
                        "indexes": [
                            {"title": "Special", "scope": "chapter"}
                        ],
                    },
                ],
            }
            self._write_config(root, config)

            plan = resolve_book_config(root)

            self.assertEqual(
                [path.name for path in plan.chapters[0].songs], ["stays.pdf"]
            )
            self.assertEqual(
                [path.name for path in plan.chapters[1].songs], ["moved.pdf"]
            )
            self.assertEqual(
                [path.name for path in plan.chapters[0].indexes[1].songs],
                ["stays.pdf"],
            )

    def test_conflicting_explicit_claims_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "native" / "song.pdf")
            for folder in ("one", "two"):
                (root / folder).mkdir()
                (root / folder / "more.txt").write_text(
                    "song.pdf\n", encoding="utf-8"
                )
            config = {
                "version": 1,
                "unassigned_song_policy": "ignore",
                "collections": {
                    "one": {"title": "One", "folder": "one"},
                    "two": {"title": "Two", "folder": "two"},
                },
                "chapters": [
                    {
                        "id": "one",
                        "title": "One",
                        "collections": ["one"],
                        "indexes": [{"title": "One", "scope": "chapter"}],
                    },
                    {
                        "id": "two",
                        "title": "Two",
                        "collections": ["two"],
                        "indexes": [{"title": "Two", "scope": "chapter"}],
                    },
                ],
            }
            self._write_config(root, config)

            with self.assertRaisesRegex(BookConfigError, "different chapters"):
                resolve_book_config(root)

    def test_ambiguous_list_filename_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "a" / "same.pdf")
            _touch_pdf(root / "b" / "same.pdf")
            (root / "virtual").mkdir()
            (root / "virtual" / "more.txt").write_text(
                "same.pdf\n", encoding="utf-8"
            )
            config = {
                "version": 1,
                "unassigned_song_policy": "ignore",
                "collections": {
                    "virtual": {"title": "Virtual", "folder": "virtual"}
                },
                "chapters": [
                    {
                        "id": "chapter",
                        "title": "Chapter",
                        "collections": ["virtual"],
                        "indexes": [{"title": "All", "scope": "chapter"}],
                    }
                ],
            }
            self._write_config(root, config)

            with self.assertRaisesRegex(BookConfigError, "ambiguous filename"):
                resolve_book_config(root)

    def test_unknown_manifest_field_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "songs" / "song.pdf")
            config = {
                "version": 1,
                "collections": {
                    "songs": {
                        "title": "Songs",
                        "folder": "songs",
                        "typo": True,
                    }
                },
                "chapters": [],
            }
            self._write_config(root, config)

            with self.assertRaisesRegex(BookConfigError, "unknown field"):
                resolve_book_config(root)

    def test_artist_sort_is_applied_only_to_the_configured_index(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "songs" / "Zebra - Beta.pdf")
            _touch_pdf(root / "songs" / "Alpha - Beta.pdf")
            _touch_pdf(root / "songs" / "Middle - Alpha.pdf")
            _touch_pdf(root / "songs" / "Solo.pdf")
            config = {
                "version": 1,
                "collections": {
                    "songs": {"title": "Songs", "folder": "songs"}
                },
                "chapters": [
                    {
                        "id": "chapter",
                        "title": "Chapter",
                        "collections": ["songs"],
                        "indexes": [
                            {"title": "By song", "scope": "chapter"},
                            {
                                "title": "By artist",
                                "scope": "chapter",
                                "sort": "artists",
                                "include_songs_without_artist": False,
                            },
                        ],
                    }
                ],
            }
            self._write_config(root, config)

            plan = resolve_book_config(root)

            self.assertEqual(
                [label for label, _path in plan.indexes[0].entries],
                ["Alpha - Beta", "Middle - Alpha", "Solo", "Zebra - Beta"],
            )
            self.assertEqual(
                [label for label, _path in plan.indexes[1].entries],
                ["Alpha - Middle", "Beta - Alpha", "Beta - Zebra"],
            )
            self.assertEqual(
                [path.stem for path in plan.song_merge_order],
                ["Alpha - Beta", "Middle - Alpha", "Solo", "Zebra - Beta"],
            )
            self.assertFalse(
                plan.indexes[1].include_songs_without_artist
            )

    def test_start_on_new_page_defaults_to_false_and_can_be_enabled(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "songs" / "song.pdf")
            config = {
                "version": 1,
                "collections": {
                    "songs": {"title": "Songs", "folder": "songs"}
                },
                "chapters": [
                    {
                        "id": "chapter",
                        "title": "Chapter",
                        "collections": ["songs"],
                        "indexes": [
                            {"title": "First", "scope": "chapter"},
                            {
                                "title": "Second",
                                "scope": "chapter",
                                "start_on_new_page": True,
                            },
                        ],
                    }
                ],
            }
            self._write_config(root, config)

            plan = resolve_book_config(root)

            self.assertFalse(plan.indexes[0].start_on_new_page)
            self.assertTrue(plan.indexes[1].start_on_new_page)

    def test_start_on_new_page_must_be_boolean(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _touch_pdf(root / "songs" / "song.pdf")
            config = {
                "version": 1,
                "collections": {
                    "songs": {"title": "Songs", "folder": "songs"}
                },
                "chapters": [
                    {
                        "id": "chapter",
                        "title": "Chapter",
                        "collections": ["songs"],
                        "indexes": [
                            {
                                "title": "All",
                                "scope": "chapter",
                                "start_on_new_page": "yes",
                            }
                        ],
                    }
                ],
            }
            self._write_config(root, config)

            with self.assertRaisesRegex(
                BookConfigError, r"start_on_new_page must be bool"
            ):
                resolve_book_config(root)


if __name__ == "__main__":
    unittest.main()
