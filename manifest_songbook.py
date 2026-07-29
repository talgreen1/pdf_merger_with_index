"""Render a normalized BookPlan to DOCX."""

from pathlib import Path

from pypdf import PdfReader

from word_songbook import create_word_songbook_from_plan


def _build_song_page_map(songs):
    page_counts = {}
    start_pages = {}
    next_page = 1
    for path in songs:
        count = PdfReader(str(path)).get_num_pages()
        page_counts[path] = count
        start_pages[path] = next_page
        next_page += count
    return page_counts, start_pages


def generate_manifest_songbook(
    plan,
    output_docx,
    word_index_entry_spacing_pt=5,
):
    """Generate a Word songbook from a fully resolved manifest plan."""
    output_docx = Path(output_docx)
    output_docx.parent.mkdir(parents=True, exist_ok=True)

    _page_counts, song_start_pages = _build_song_page_map(plan.song_merge_order)
    print(
        "[PLAN] {} chapters, {} indexes, {} unique PDFs".format(
            len(plan.chapters),
            len(plan.indexes),
            len(plan.song_merge_order),
        )
    )
    for warning in plan.warnings:
        print("[WARNING] {}".format(warning))
    for chapter in plan.chapters:
        print(
            "[PLAN] {}: {} songs, {} indexes".format(
                chapter.id, len(chapter.songs), len(chapter.indexes)
            )
        )

    create_word_songbook_from_plan(
        output_path=output_docx,
        indexes=[
            (
                resolved_index.title,
                resolved_index.entries,
                resolved_index.start_on_new_page,
            )
            for resolved_index in plan.indexes
        ],
        songs=plan.song_merge_order,
        song_start_pages=song_start_pages,
        index_entry_spacing_pt=word_index_entry_spacing_pt,
    )

    print(
        "[DONE] Manifest DOCX created with chapters and indexes: {}".format(
            output_docx
        )
    )
    return output_docx
