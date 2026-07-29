"""Render a normalized BookPlan to PDF and DOCX."""

from io import BytesIO
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    FloatObject,
    NameObject,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

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


def _add_page_numbers(input_path, output_path, index_page_count, position):
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    song_page_number = 1
    for page_number, page in enumerate(reader.pages):
        if page_number >= index_page_count:
            packet = BytesIO()
            overlay_canvas = canvas.Canvas(packet, pagesize=A4)
            overlay_canvas.setFont("Helvetica", 16)
            label = str(song_page_number)
            if position in ("both", "left"):
                overlay_canvas.drawString(2 * cm, 1.5 * cm, label)
            if position in ("both", "right"):
                overlay_canvas.drawRightString(A4[0] - 2 * cm, 1.5 * cm, label)
            overlay_canvas.save()
            packet.seek(0)
            page.merge_page(PdfReader(packet).pages[0])
            song_page_number += 1
        writer.add_page(page)
    with Path(output_path).open("wb") as stream:
        writer.write(stream)


def _add_navigation(
    input_path,
    output_path,
    index_results,
    index_page_counts,
    songs,
    page_counts,
):
    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    total_index_pages = sum(index_page_counts)
    merged_song_pages = {}
    next_page = total_index_pages
    for song in songs:
        merged_song_pages[song] = next_page
        next_page += page_counts[song]
        writer.add_outline_item(song.stem, merged_song_pages[song])

    def add_internal_link(source_page_number, rect, target_page_number):
        source_page = writer.pages[source_page_number]
        target_page = writer.pages[target_page_number]
        annotation = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Link"),
                NameObject("/Rect"): ArrayObject(
                    [FloatObject(value) for value in rect]
                ),
                NameObject("/Border"): ArrayObject(
                    [FloatObject(0), FloatObject(0), FloatObject(0)]
                ),
                NameObject("/Dest"): ArrayObject(
                    [target_page.indirect_reference, NameObject("/Fit")]
                ),
                NameObject("/P"): source_page.indirect_reference,
            }
        )
        if source_page.annotations is None:
            source_page[NameObject("/Annots")] = ArrayObject()
        source_page.annotations.append(writer._add_object(annotation))

    index_offset = 0
    for placements, page_count in zip(index_results, index_page_counts):
        for local_page, rect, song in placements:
            add_internal_link(
                index_offset + local_page,
                rect,
                merged_song_pages[song],
            )
        index_offset += page_count

    with Path(output_path).open("wb") as stream:
        writer.write(stream)


def generate_manifest_songbook(
    plan,
    output_pdf,
    output_docx,
    output_folder,
    font_path,
    create_index,
    page_number_position="left",
    word_index_entry_spacing_pt=5,
):
    """Generate both outputs from a fully resolved manifest plan."""
    output_pdf = Path(output_pdf)
    output_docx = Path(output_docx)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    page_counts, song_start_pages = _build_song_page_map(
        plan.song_merge_order
    )
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

    with TemporaryDirectory(
        prefix="manifest_songbook_", dir=str(output_folder)
    ) as temp_directory:
        temp_root = Path(temp_directory)
        index_paths = []
        index_results = []
        index_page_counts = []

        for index_number, resolved_index in enumerate(plan.indexes):
            index_path = temp_root / "index_{:03d}.pdf".format(index_number)
            paths = resolved_index.songs
            placements = create_index(
                paths,
                index_path,
                font_path,
                start_page=1,
                pdf_page_counts=[page_counts[path] for path in paths],
                index_title=resolved_index.title,
                song_start_pages=[song_start_pages[path] for path in paths],
                display_labels=[
                    label for label, _path in resolved_index.entries
                ],
            )
            index_paths.append(index_path)
            index_results.append(placements)
            index_page_counts.append(
                PdfReader(str(index_path)).get_num_pages()
            )

        merged_path = temp_root / "merged.pdf"
        merger = PdfWriter()
        for index_path in index_paths:
            merger.append(str(index_path))
        for song in plan.song_merge_order:
            merger.append(str(song))
        with merged_path.open("wb") as stream:
            merger.write(stream)
        merger.close()

        numbered_path = temp_root / "numbered.pdf"
        _add_page_numbers(
            merged_path,
            numbered_path,
            sum(index_page_counts),
            page_number_position,
        )
        linked_path = temp_root / "linked.pdf"
        _add_navigation(
            numbered_path,
            linked_path,
            index_results,
            index_page_counts,
            plan.song_merge_order,
            page_counts,
        )
        shutil.copyfile(str(linked_path), str(output_pdf))

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
        "[DONE] Manifest PDF created with chapters and indexes: {}".format(
            output_pdf
        )
    )
    print(
        "[DONE] Manifest DOCX created with chapters and indexes: {}".format(
            output_docx
        )
    )
    return output_pdf, output_docx
