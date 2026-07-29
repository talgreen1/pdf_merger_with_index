"""Load and resolve the optional chapters-and-collections book manifest."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


BOOK_CONFIG_FILENAME = "book.json"
SUPPORTED_VERSION = 1


class BookConfigError(ValueError):
    """Raised when book.json is invalid or cannot be resolved safely."""


@dataclass
class CollectionDefinition:
    id: str
    title: str
    folder: Path
    include_pdfs: bool = True
    include_list: Optional[str] = "more.txt"
    recursive: bool = False
    sort: str = "alphabetical"


@dataclass
class ResolvedCollection:
    definition: CollectionDefinition
    songs: List[Path] = field(default_factory=list)
    listed_songs: Set[Path] = field(default_factory=set)
    physical_songs: Set[Path] = field(default_factory=set)


@dataclass
class IndexDefinition:
    title: str
    scope: Optional[str] = None
    collection: Optional[str] = None
    sort: str = "alphabetical"
    include_songs_without_artist: bool = True


@dataclass
class ChapterDefinition:
    id: str
    title: str
    collections: List[str]
    indexes: List[IndexDefinition]


@dataclass
class ResolvedIndex:
    chapter_id: str
    title: str
    entries: List[Tuple[str, Path]]
    sort: str = "alphabetical"
    include_songs_without_artist: bool = True

    @property
    def songs(self):
        return [path for _label, path in self.entries]


@dataclass
class ResolvedChapter:
    id: str
    title: str
    songs: List[Path]
    indexes: List[ResolvedIndex]


@dataclass
class BookPlan:
    chapters: List[ResolvedChapter]
    indexes: List[ResolvedIndex]
    song_merge_order: List[Path]
    song_owner: Dict[Path, str]
    collections: Dict[str, ResolvedCollection]
    discovered_pdfs: List[Path]
    warnings: List[str] = field(default_factory=list)


TOP_LEVEL_KEYS = {
    "version",
    "allow_duplicate_songs",
    "unassigned_song_policy",
    "collections",
    "chapters",
}
COLLECTION_KEYS = {
    "title",
    "folder",
    "include_pdfs",
    "include_list",
    "recursive",
    "sort",
}
CHAPTER_KEYS = {"id", "title", "collections", "indexes"}
INDEX_KEYS = {
    "title",
    "scope",
    "collection",
    "sort",
    "include_songs_without_artist",
}
COLLECTION_SORTS = {"alphabetical", "list"}
INDEX_SORTS = {"alphabetical", "collection", "artists"}
UNASSIGNED_POLICIES = {"error", "warn", "ignore"}


def _expect_type(value, expected_type, location):
    if not isinstance(value, expected_type):
        raise BookConfigError(
            "{} must be {}, got {}".format(
                location, expected_type.__name__, type(value).__name__
            )
        )
    return value


def _require_string(mapping, key, location):
    if key not in mapping:
        raise BookConfigError("{} is missing required field '{}'".format(location, key))
    value = _expect_type(mapping[key], str, "{}.{}".format(location, key)).strip()
    if not value:
        raise BookConfigError("{}.{} must not be empty".format(location, key))
    return value


def _reject_unknown_keys(mapping, allowed, location):
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise BookConfigError(
            "{} contains unknown field(s): {}".format(location, ", ".join(unknown))
        )


def _is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_under_root(root, relative_path, location):
    candidate = (root / relative_path).resolve()
    if not _is_within(candidate, root):
        raise BookConfigError(
            "{} escapes the PDF root: {}".format(location, relative_path)
        )
    return candidate


def _load_json(config_path):
    try:
        with config_path.open("r", encoding="utf-8-sig") as stream:
            return json.load(stream)
    except json.JSONDecodeError as error:
        raise BookConfigError(
            "{} contains invalid JSON at line {}, column {}: {}".format(
                config_path, error.lineno, error.colno, error.msg
            )
        )


def _parse_collection_definitions(raw_collections, pdf_root):
    _expect_type(raw_collections, dict, "collections")
    if not raw_collections:
        raise BookConfigError("collections must not be empty")

    definitions = {}
    for collection_id, raw in raw_collections.items():
        if not isinstance(collection_id, str) or not collection_id.strip():
            raise BookConfigError("collection IDs must be non-empty strings")
        location = "collections.{}".format(collection_id)
        _expect_type(raw, dict, location)
        _reject_unknown_keys(raw, COLLECTION_KEYS, location)
        title = _require_string(raw, "title", location)
        folder_text = _require_string(raw, "folder", location)
        folder = _resolve_under_root(pdf_root, folder_text, "{}.folder".format(location))
        if not folder.is_dir():
            raise BookConfigError(
                "{}.folder does not exist or is not a folder: {}".format(
                    location, folder
                )
            )

        include_pdfs = raw.get("include_pdfs", True)
        _expect_type(include_pdfs, bool, "{}.include_pdfs".format(location))
        include_list = raw.get("include_list", "more.txt")
        if include_list is not None:
            _expect_type(include_list, str, "{}.include_list".format(location))
            if not include_list.strip():
                raise BookConfigError(
                    "{}.include_list must be a filename or null".format(location)
                )
            list_path = _resolve_under_root(
                folder, include_list, "{}.include_list".format(location)
            )
            if not _is_within(list_path, pdf_root):
                raise BookConfigError(
                    "{}.include_list escapes the PDF root".format(location)
                )

        recursive = raw.get("recursive", False)
        _expect_type(recursive, bool, "{}.recursive".format(location))
        sort = raw.get("sort", "alphabetical")
        _expect_type(sort, str, "{}.sort".format(location))
        if sort not in COLLECTION_SORTS:
            raise BookConfigError(
                "{}.sort must be one of: {}".format(
                    location, ", ".join(sorted(COLLECTION_SORTS))
                )
            )

        definitions[collection_id] = CollectionDefinition(
            id=collection_id,
            title=title,
            folder=folder,
            include_pdfs=include_pdfs,
            include_list=include_list,
            recursive=recursive,
            sort=sort,
        )
    return definitions


def _parse_index(raw, location):
    _expect_type(raw, dict, location)
    _reject_unknown_keys(raw, INDEX_KEYS, location)
    title = _require_string(raw, "title", location)
    scope = raw.get("scope")
    collection = raw.get("collection")
    if (scope is None) == (collection is None):
        raise BookConfigError(
            "{} must specify exactly one of 'scope' and 'collection'".format(location)
        )
    if scope is not None:
        _expect_type(scope, str, "{}.scope".format(location))
        if scope != "chapter":
            raise BookConfigError("{}.scope must be 'chapter'".format(location))
    if collection is not None:
        _expect_type(collection, str, "{}.collection".format(location))
    sort = raw.get("sort", "alphabetical")
    _expect_type(sort, str, "{}.sort".format(location))
    if sort not in INDEX_SORTS:
        raise BookConfigError(
            "{}.sort must be one of: {}".format(
                location, ", ".join(sorted(INDEX_SORTS))
            )
        )
    include_songs_without_artist = raw.get(
        "include_songs_without_artist", True
    )
    _expect_type(
        include_songs_without_artist,
        bool,
        "{}.include_songs_without_artist".format(location),
    )
    return IndexDefinition(
        title=title,
        scope=scope,
        collection=collection,
        sort=sort,
        include_songs_without_artist=include_songs_without_artist,
    )


def _parse_chapters(raw_chapters, collection_definitions):
    _expect_type(raw_chapters, list, "chapters")
    if not raw_chapters:
        raise BookConfigError("chapters must not be empty")

    chapters = []
    chapter_ids = set()
    collection_chapters = {}
    for chapter_number, raw in enumerate(raw_chapters):
        location = "chapters[{}]".format(chapter_number)
        _expect_type(raw, dict, location)
        _reject_unknown_keys(raw, CHAPTER_KEYS, location)
        chapter_id = _require_string(raw, "id", location)
        if chapter_id in chapter_ids:
            raise BookConfigError("duplicate chapter id: {}".format(chapter_id))
        chapter_ids.add(chapter_id)
        title = _require_string(raw, "title", location)

        raw_collection_ids = raw.get("collections")
        _expect_type(raw_collection_ids, list, "{}.collections".format(location))
        if not raw_collection_ids:
            raise BookConfigError("{}.collections must not be empty".format(location))
        collection_ids = []
        for item_number, collection_id in enumerate(raw_collection_ids):
            _expect_type(
                collection_id,
                str,
                "{}.collections[{}]".format(location, item_number),
            )
            if collection_id not in collection_definitions:
                raise BookConfigError(
                    "{} references unknown collection '{}'".format(
                        location, collection_id
                    )
                )
            if collection_id in collection_ids:
                raise BookConfigError(
                    "{} includes collection '{}' more than once".format(
                        location, collection_id
                    )
                )
            if collection_id in collection_chapters:
                raise BookConfigError(
                    "collection '{}' is included by both chapter '{}' and '{}'".format(
                        collection_id,
                        collection_chapters[collection_id],
                        chapter_id,
                    )
                )
            collection_chapters[collection_id] = chapter_id
            collection_ids.append(collection_id)

        raw_indexes = raw.get("indexes")
        _expect_type(raw_indexes, list, "{}.indexes".format(location))
        if not raw_indexes:
            raise BookConfigError("{}.indexes must not be empty".format(location))
        indexes = [
            _parse_index(item, "{}.indexes[{}]".format(location, index_number))
            for index_number, item in enumerate(raw_indexes)
        ]
        for index in indexes:
            if (
                index.collection is not None
                and index.collection not in collection_ids
            ):
                raise BookConfigError(
                    "index '{}' in chapter '{}' references collection '{}', "
                    "which is not in that chapter".format(
                        index.title, chapter_id, index.collection
                    )
                )
        chapters.append(
            ChapterDefinition(
                id=chapter_id,
                title=title,
                collections=collection_ids,
                indexes=indexes,
            )
        )

    unused = sorted(set(collection_definitions) - set(collection_chapters))
    if unused:
        raise BookConfigError(
            "collection(s) are not assigned to any chapter: {}".format(
                ", ".join(unused)
            )
        )
    return chapters, collection_chapters


def _resolve_list_entry(entry, pdf_root, filename_map, location):
    if "/" in entry or "\\" in entry:
        path = _resolve_under_root(pdf_root, entry, location)
        if not path.is_file() or path.suffix.casefold() != ".pdf":
            raise BookConfigError("{} references missing PDF: {}".format(location, entry))
        return path

    matches = filename_map.get(entry.casefold(), [])
    if not matches:
        raise BookConfigError("{} references missing PDF: {}".format(location, entry))
    if len(matches) > 1:
        raise BookConfigError(
            "{} references ambiguous filename '{}'; candidates: {}".format(
                location, entry, ", ".join(str(path) for path in matches)
            )
        )
    return matches[0]


def _resolve_collections(definitions, pdf_root, filename_map):
    resolved = {}
    for collection_id, definition in definitions.items():
        physical = []
        if definition.include_pdfs:
            iterator = (
                definition.folder.rglob("*.pdf")
                if definition.recursive
                else definition.folder.glob("*.pdf")
            )
            physical = sorted(
                (path.resolve() for path in iterator if path.is_file()),
                key=lambda path: (path.stem.casefold(), str(path).casefold()),
            )

        listed = []
        if definition.include_list is not None:
            list_path = (definition.folder / definition.include_list).resolve()
            if list_path.exists():
                with list_path.open("r", encoding="utf-8-sig") as stream:
                    for line_number, line in enumerate(stream, start=1):
                        entry = line.strip()
                        if not entry:
                            continue
                        listed.append(
                            _resolve_list_entry(
                                entry,
                                pdf_root,
                                filename_map,
                                "{} line {}".format(list_path, line_number),
                            )
                        )

        ordered = []
        seen = set()
        source_order = listed + physical if definition.sort == "list" else physical + listed
        for path in source_order:
            if path not in seen:
                ordered.append(path)
                seen.add(path)
        if definition.sort == "alphabetical":
            ordered.sort(key=lambda path: (path.stem.casefold(), str(path).casefold()))

        if not ordered:
            raise BookConfigError(
                "collection '{}' resolved to no PDFs (folder: {})".format(
                    collection_id, definition.folder
                )
            )
        resolved[collection_id] = ResolvedCollection(
            definition=definition,
            songs=ordered,
            listed_songs=set(listed),
            physical_songs=set(physical),
        )
    return resolved


def _extract_artist(filename_stem):
    if " - " not in filename_stem:
        return "", filename_stem
    song_name, artist_name = filename_stem.split(" - ", 1)
    return " ".join(artist_name.split()), " ".join(song_name.split())


def _make_entries(paths, sort):
    paths = list(paths)
    if sort == "alphabetical":
        paths.sort(key=lambda path: (path.stem.casefold(), str(path).casefold()))
        return [(path.stem, path) for path in paths]
    if sort == "artists":
        artist_entries = []
        for path in paths:
            artist, song = _extract_artist(path.stem)
            label = "{} - {}".format(artist, song) if artist else song
            artist_entries.append((artist.casefold(), song.casefold(), label, path))
        artist_entries.sort(key=lambda item: (item[0], item[1], str(item[3]).casefold()))
        return [(label, path) for _artist, _song, label, path in artist_entries]
    return [(path.stem, path) for path in paths]


def resolve_book_config(pdf_root, config_path=None):
    """Resolve book.json into a renderer-independent, validated BookPlan."""
    pdf_root = Path(pdf_root).resolve()
    config_path = (
        Path(config_path).resolve()
        if config_path is not None
        else pdf_root / BOOK_CONFIG_FILENAME
    )
    raw = _load_json(config_path)
    _expect_type(raw, dict, "book.json")
    _reject_unknown_keys(raw, TOP_LEVEL_KEYS, "book.json")

    version = raw.get("version")
    if version != SUPPORTED_VERSION:
        raise BookConfigError(
            "book.json version must be {}, got {!r}".format(
                SUPPORTED_VERSION, version
            )
        )
    allow_duplicates = raw.get("allow_duplicate_songs", False)
    _expect_type(allow_duplicates, bool, "book.json.allow_duplicate_songs")
    if allow_duplicates:
        raise BookConfigError(
            "allow_duplicate_songs=true is reserved for a future version"
        )
    unassigned_policy = raw.get("unassigned_song_policy", "error")
    _expect_type(
        unassigned_policy, str, "book.json.unassigned_song_policy"
    )
    if unassigned_policy not in UNASSIGNED_POLICIES:
        raise BookConfigError(
            "unassigned_song_policy must be one of: {}".format(
                ", ".join(sorted(UNASSIGNED_POLICIES))
            )
        )

    definitions = _parse_collection_definitions(
        raw.get("collections"), pdf_root
    )
    chapters, collection_chapters = _parse_chapters(
        raw.get("chapters"), definitions
    )

    discovered = sorted(
        (path.resolve() for path in pdf_root.rglob("*.pdf") if path.is_file()),
        key=lambda path: (path.stem.casefold(), str(path).casefold()),
    )
    filename_map = {}
    for path in discovered:
        filename_map.setdefault(path.name.casefold(), []).append(path)
    collections = _resolve_collections(definitions, pdf_root, filename_map)

    explicit_claims = {}
    physical_claims = {}
    for collection_id, collection in collections.items():
        chapter_id = collection_chapters[collection_id]
        for path in collection.listed_songs:
            explicit_claims.setdefault(path, set()).add(chapter_id)
        for path in collection.physical_songs:
            physical_claims.setdefault(path, set()).add(chapter_id)

    song_owner = {}
    for path, claimants in explicit_claims.items():
        if len(claimants) > 1:
            raise BookConfigError(
                "PDF '{}' is explicitly listed by collections in different "
                "chapters: {}".format(path.name, ", ".join(sorted(claimants)))
            )
        song_owner[path] = next(iter(claimants))
    for path, claimants in physical_claims.items():
        if path in song_owner:
            continue
        if len(claimants) > 1:
            raise BookConfigError(
                "PDF '{}' is physically claimed by collections in different "
                "chapters: {}".format(path.name, ", ".join(sorted(claimants)))
            )
        song_owner[path] = next(iter(claimants))

    warnings = []
    unassigned = [path for path in discovered if path not in song_owner]
    if unassigned:
        message = "{} PDF(s) are not assigned to a chapter: {}".format(
            len(unassigned), ", ".join(str(path.relative_to(pdf_root)) for path in unassigned)
        )
        if unassigned_policy == "error":
            raise BookConfigError(message)
        if unassigned_policy == "warn":
            warnings.append(message)

    resolved_chapters = []
    resolved_indexes = []
    song_merge_order = []
    for chapter in chapters:
        chapter_songs = []
        chapter_seen = set()
        for collection_id in chapter.collections:
            for path in collections[collection_id].songs:
                if song_owner.get(path) == chapter.id and path not in chapter_seen:
                    chapter_songs.append(path)
                    chapter_seen.add(path)
        if not chapter_songs:
            raise BookConfigError(
                "chapter '{}' resolved to no owned PDFs".format(chapter.id)
            )

        chapter_indexes = []
        for index in chapter.indexes:
            if index.scope == "chapter":
                candidates = list(chapter_songs)
            else:
                candidates = [
                    path
                    for path in collections[index.collection].songs
                    if song_owner.get(path) == chapter.id
                ]
            if not index.include_songs_without_artist:
                candidates = [
                    path
                    for path in candidates
                    if _extract_artist(path.stem)[0]
                ]
            entries = _make_entries(candidates, index.sort)
            if not entries:
                raise BookConfigError(
                    "index '{}' in chapter '{}' resolved to no PDFs".format(
                        index.title, chapter.id
                    )
                )
            resolved_index = ResolvedIndex(
                chapter_id=chapter.id,
                title=index.title,
                entries=entries,
                sort=index.sort,
                include_songs_without_artist=(
                    index.include_songs_without_artist
                ),
            )
            chapter_indexes.append(resolved_index)
            resolved_indexes.append(resolved_index)

        resolved_chapters.append(
            ResolvedChapter(
                id=chapter.id,
                title=chapter.title,
                songs=chapter_songs,
                indexes=chapter_indexes,
            )
        )
        song_merge_order.extend(chapter_songs)

    return BookPlan(
        chapters=resolved_chapters,
        indexes=resolved_indexes,
        song_merge_order=song_merge_order,
        song_owner=song_owner,
        collections=collections,
        discovered_pdfs=discovered,
        warnings=warnings,
    )

