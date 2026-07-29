# Chapters and Collections Feature Plan

## Status

Implemented on 2026-07-28. This document records the design, implementation
stages, validation rules, and acceptance criteria used for the feature.

## Objective

Add an optional `book.json` manifest that gives explicit control over:

- which song collections exist;
- which PDFs belong to each collection;
- how collections are grouped into ordered chapters;
- which indexes are created for every chapter;
- the order of all indexes at the beginning of the book; and
- the order of all song sections after the indexes.

The same resolved book structure must be used for both PDF and DOCX output.

## Agreed Behavior

### Collections

A collection represents a named set of songs. It points to a folder under the
configured PDF root.

By default, a collection contains the union of:

1. all PDF files directly inside its folder; and
2. all PDFs named in the folder's `more.txt`.

This supports all three useful folder forms:

- PDFs only;
- `more.txt` only (a virtual collection); and
- PDFs plus `more.txt`.

Songs that appear both physically in the folder and in `more.txt` are included
only once.

### Chapters

A chapter is an ordered song section. It contains one or more collections and
one or more index definitions.

The order of the `chapters` array controls song-section order. The order of a
chapter's `collections` array controls collection order inside that chapter.

### Indexes

Every index appears at the beginning of the book, before every song page.

The default index order is:

1. chapter order from `book.json`; then
2. index order inside each chapter.

An index can cover:

- the entire resolved chapter (`"scope": "chapter"`); or
- one named collection (`"collection": "happy"`).

A collection index is always intersected with its resolved chapter. For
example, a song moved from the happy folder to the popular chapter must not
remain in the happy index in the main chapter.

### Song Ownership

By default, every physical PDF appears exactly once in the song pages.

Ownership is resolved for the complete manifest before chapters are emitted.
It does not depend on chapter order.

Claims have the following precedence:

1. A song explicitly named by a collection's `more.txt` is claimed by the
   chapter containing that collection.
2. Otherwise, the song belongs to the chapter that includes its physical
   folder collection.

This rule is needed for the current input layout:

- `הפופולרים/more.txt` names songs physically stored in `שירים שמחים` and
  `שירים שקטים`.
- `שירים יווניים/more.txt` names songs physically stored in `שירים שקטים`.

The explicit list claims move those songs to their intended chapters without
requiring manual `exclude` entries.

If explicit lists in different chapters claim the same PDF, configuration
loading must fail with a clear error. Silently choosing one chapter would make
the generated book unpredictable.

## Proposed Manifest

The manifest is named `book.json` and is placed directly inside `pdf_folder`.
All folder and file paths in it are relative to `pdf_folder`.

```json
{
  "version": 1,
  "allow_duplicate_songs": false,
  "unassigned_song_policy": "error",
  "collections": {
    "popular": {
      "title": "הפופולרים",
      "folder": "הפופולרים"
    },
    "happy": {
      "title": "שירים שמחים",
      "folder": "שירים שמחים"
    },
    "quiet": {
      "title": "שירים שקטים",
      "folder": "שירים שקטים"
    },
    "russian": {
      "title": "שירים רוסיים",
      "folder": "שירים רוסיים"
    },
    "french": {
      "title": "שירים צרפתיים",
      "folder": "שירים צרפתיים"
    },
    "spanish": {
      "title": "שירים ספרדיים",
      "folder": "שירים ספרדיים"
    },
    "greek": {
      "title": "שירים יווניים",
      "folder": "שירים יווניים"
    },
    "english": {
      "title": "שירים באנגלית",
      "folder": "שירים באנגלית"
    },
    "holidays": {
      "title": "שירי חגים",
      "folder": "שירי חגים"
    },
    "medleys": {
      "title": "מחרוזות",
      "folder": "מחרוזות"
    }
  },
  "chapters": [
    {
      "id": "popular",
      "title": "הפופולרים",
      "collections": ["popular"],
      "indexes": [
        {
          "title": "הפופולרים",
          "scope": "chapter"
        }
      ]
    },
    {
      "id": "main",
      "title": "השירים המרכזיים",
      "collections": ["happy", "quiet"],
      "indexes": [
        {
          "title": "כל השירים",
          "scope": "chapter"
        },
        {
          "title": "שירים שמחים",
          "collection": "happy"
        },
        {
          "title": "שירים שקטים",
          "collection": "quiet"
        }
      ]
    },
    {
      "id": "languages-and-holidays",
      "title": "שפות וחגים",
      "collections": [
        "russian",
        "french",
        "spanish",
        "greek",
        "english",
        "holidays"
      ],
      "indexes": [
        {
          "title": "שירים רוסיים",
          "collection": "russian"
        },
        {
          "title": "שירים צרפתיים",
          "collection": "french"
        },
        {
          "title": "שירים ספרדיים",
          "collection": "spanish"
        },
        {
          "title": "שירים יווניים",
          "collection": "greek"
        },
        {
          "title": "שירים באנגלית",
          "collection": "english"
        },
        {
          "title": "שירי חגים",
          "collection": "holidays"
        }
      ]
    },
    {
      "id": "medleys",
      "title": "מחרוזות",
      "collections": ["medleys"],
      "indexes": [
        {
          "title": "מחרוזות",
          "scope": "chapter"
        }
      ]
    }
  ]
}
```

For the current `C:\temp\songs\pdfs` contents, this resolves to:

| Chapter | Song count | Index count |
| --- | ---: | ---: |
| Popular | 11 | 1 |
| Main happy and quiet songs | 53 | 3 |
| Languages and holidays | 30 | 6 |
| Medleys | 3 | 1 |
| **Total** | **97 unique PDFs** | **11 indexes** |

## Manifest Reference

### Top-Level Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `version` | integer | yes | Schema version. Initially only `1` is accepted. |
| `allow_duplicate_songs` | boolean | no | Whether a PDF may be emitted in more than one chapter. Default: `false`. |
| `unassigned_song_policy` | string | no | Handling for discovered PDFs not assigned to a chapter: `error`, `warn`, or `ignore`. Default: `error`. |
| `collections` | object | yes | Collection definitions keyed by stable collection ID. |
| `chapters` | array | yes | Ordered chapter definitions. |

`allow_duplicate_songs` is included in the schema for future control. Version 1
should fully implement and test the default `false` behavior first. Enabling
duplicates must not be accepted until page mapping, bookmarks, and indexes have
defined behavior for repeated source PDFs.

### Collection Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `title` | string | yes | Human-readable collection name. |
| `folder` | string | yes | Folder relative to `pdf_folder`. |
| `include_pdfs` | boolean | no | Include direct `*.pdf` files. Default: `true`. |
| `include_list` | string or `null` | no | List filename inside the folder. Default: `"more.txt"`. |
| `recursive` | boolean | no | Include PDFs below nested folders. Default: `false`. |
| `sort` | string | no | Song ordering: initially `alphabetical` or `list`. Default: `alphabetical`. |

For `"sort": "list"`, entries from `more.txt` retain file order and direct PDFs
not present in the list are appended alphabetically. For `"sort":
"alphabetical"`, the complete deduplicated union is sorted by filename stem,
case-insensitively.

Collection IDs are stable machine-readable references and need not match folder
names or displayed titles.

### Chapter Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | Unique stable chapter ID. |
| `title` | string | yes | Human-readable chapter title. Reserved for metadata and future divider pages. |
| `collections` | array of strings | yes | Ordered collection IDs used by the chapter. |
| `indexes` | array | yes | Ordered index definitions. |

Chapter titles do not add divider pages in version 1. The first implementation
changes logical song ordering only. Divider pages can be introduced later
without changing collection or index semantics.

### Index Fields

Each index must specify exactly one of `scope` and `collection`.

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `title` | string | yes | Displayed index title. |
| `scope` | string | conditional | `"chapter"` includes all songs owned by the chapter. |
| `collection` | string | conditional | Includes songs from this collection that are owned by the current chapter. |
| `sort` | string | no | Initially `alphabetical`, `collection`, or `artists`. Default: `alphabetical`. |
| `include_songs_without_artist` | boolean | no | Include filenames without a valid `Song title - Artist` pattern. Default: `true`. |

The existing artist index can be represented as:

```json
{
  "title": "אומנים",
  "scope": "chapter",
  "sort": "artists",
  "include_songs_without_artist": false
}
```

`"sort": "collection"` preserves the chapter's resolved content order.

## Resolution Algorithm

The implementation should construct a normalized book plan before rendering
anything.

### Phase 1: Load and Validate JSON

1. Read the repository-root `book.json` as UTF-8, resolving its collection
   paths relative to `pdf_folder`.
2. Reject malformed JSON with line and column information.
3. Validate `version`.
4. Validate required fields and types.
5. Reject unknown collection references and duplicate chapter IDs.
6. Reject index definitions that specify neither or both of `scope` and
   `collection`.
7. Reject index collection references that are not included by that chapter.
8. Resolve every configured path and ensure it remains under `pdf_folder`.

Unknown keys should be rejected rather than ignored so spelling mistakes do not
silently change the generated book.

### Phase 2: Discover Physical PDFs

1. Discover all PDFs under `pdf_folder`.
2. Resolve every PDF to an absolute normalized `Path`.
3. Build:
   - a path-to-page-count map;
   - a filename-to-paths map; and
   - a physical parent-folder map.
4. Preserve all matching paths for duplicate filenames. Do not silently let one
   filename overwrite another.

### Phase 3: Resolve Collections

For each collection:

1. Validate that its folder exists.
2. Add physical PDFs according to `include_pdfs` and `recursive`.
3. If `include_list` is not `null` and the file exists, read it using
   `utf-8-sig`.
4. Ignore blank lines.
5. Resolve every listed filename:
   - no match: configuration error naming the collection, list, and line;
   - more than one match: ambiguity error listing every candidate path;
   - one match: add the canonical PDF path.
6. Deduplicate by canonical path.
7. Apply the configured collection sort.
8. Retain origin metadata for every membership:
   - `physical`;
   - `list`; or
   - both.

Origin metadata is required for ownership precedence.

### Phase 4: Resolve Ownership

1. Map every collection to the chapter that includes it.
2. Gather all list-based claims for each PDF.
3. If list claims target different chapters, fail with a conflict error.
4. Assign each list-claimed PDF to the claiming chapter.
5. For remaining PDFs, gather physical collection claims.
6. If physical claims target different chapters, fail with a conflict error.
7. Assign each remaining PDF to its physical collection's chapter.
8. Apply `unassigned_song_policy` to discovered PDFs with no owner.
9. Assert that every emitted PDF has one owner when duplicates are disabled.

Multiple collections in the same chapter may contain the same song. This is
not an ownership conflict; the song is emitted once in that chapter and may
appear in more than one index if configured.

### Phase 5: Materialize Chapters

For every chapter in manifest order:

1. Visit its collections in configured order.
2. Keep only songs owned by that chapter.
3. Deduplicate songs already added by an earlier collection in the same
   chapter.
4. Append the remaining songs using collection order.

The concatenation of all resolved chapter songs becomes the single canonical
`song_merge_order`.

### Phase 6: Materialize Indexes

For every chapter and index in manifest order:

1. Resolve the index's candidate songs.
2. Intersect candidates with the chapter's owned songs.
3. Deduplicate by canonical path.
4. Apply the index sort.
5. Reject or warn about an empty index according to one documented policy. The
   recommended initial behavior is an error because an empty configured index
   usually indicates a mistake.

The flattened result becomes the canonical `resolved_indexes` list used by both
output formats.

## Proposed Internal Model

Configuration parsing and resolution should be separated from rendering. A
small new module such as `book_config.py` should define structures equivalent
to:

```python
@dataclass
class CollectionDefinition:
    id: str
    title: str
    folder: Path
    include_pdfs: bool
    include_list: str | None
    recursive: bool
    sort: str


@dataclass
class ResolvedCollection:
    definition: CollectionDefinition
    songs: list[Path]
    listed_songs: set[Path]
    physical_songs: set[Path]


@dataclass
class IndexDefinition:
    title: str
    scope: str | None
    collection: str | None
    sort: str


@dataclass
class ResolvedIndex:
    chapter_id: str
    title: str
    songs: list[Path]
    sort: str


@dataclass
class ResolvedChapter:
    id: str
    title: str
    songs: list[Path]
    indexes: list[ResolvedIndex]


@dataclass
class BookPlan:
    chapters: list[ResolvedChapter]
    indexes: list[ResolvedIndex]
    song_merge_order: list[Path]
    song_owner: dict[Path, str]
```

Use syntax compatible with the project's supported Python version when
implementing these types.

Renderers should consume `BookPlan`; they should not rediscover folders,
interpret `more.txt`, or make ownership decisions.

## Integration with the Current Pipeline

The current generator performs discovery and special-case ordering directly in
`create_song_book.py`. The implementation should replace manifest-mode
special cases with the normalized plan.

### PDF Generation

1. Load either a manifest plan or a legacy plan.
2. Count pages once for every unique PDF.
3. Build song start pages from `BookPlan.song_merge_order`.
4. Render every `ResolvedIndex` in order.
5. Merge all rendered indexes.
6. Merge all song PDFs in canonical song order.
7. Add continuous song-page numbers beginning at 1 after the index pages.
8. Create links and bookmarks from the same canonical page map.

Index rendering must receive explicit `(display label, PDF path, page number)`
entries. Link generation must use the same resolved index entries rather than
reconstructing index order independently.

### DOCX Generation

Refactor `word_songbook.create_word_songbook` to accept:

- the resolved ordered indexes;
- the canonical song order; and
- the canonical song start-page map.

The Word output must match PDF chapter order and index membership. Existing
bookmark-backed links remain unchanged conceptually.

### Artist Index

Artist grouping becomes an index sorting mode instead of a globally generated
special index. Artist extraction continues to use the existing filename
convention.

### Legacy Markers

In manifest mode:

- `book.json` is authoritative for membership, chapter order, and indexes;
- `.separate` does not control membership or song placement;
- automatic subfolder indexes are not created unless represented in the
  manifest; and
- `more.txt` is read as part of its declared collection.

Presentation behavior currently associated with `.column` can remain
temporarily supported by the renderer, but it must not affect ownership.
Eventually it should become an explicit index layout property.

## Backward Compatibility

If `book.json` does not exist, generation must retain the existing behavior:

- automatic recursive PDF discovery;
- popular-folder-first handling;
- `more.txt` custom indexes;
- `.separate` collections;
- `.column` layout markers;
- automatic subfolder indexes; and
- the configured Word index ordering.

The implementation should create a legacy `BookPlan` adapter so the rendering
pipeline can become plan-based without maintaining two separate renderers.

No existing input folder should be required to adopt `book.json`.

## Error Messages and Diagnostics

Manifest errors should be actionable and include the relevant IDs and paths.
Required cases include:

- malformed JSON;
- unsupported schema version;
- missing collection folder;
- missing list entry;
- ambiguous duplicate filename;
- collection referenced by an unknown ID;
- collection index not present in its chapter;
- PDF list-claimed by different chapters;
- physical collection included by different chapters;
- empty chapter;
- empty configured index;
- unassigned PDF; and
- configured path escaping `pdf_folder`.

Before rendering, print a concise plan summary:

```text
[PLAN] 4 chapters, 11 indexes, 97 unique PDFs
[PLAN] popular: 11 songs, 1 index
[PLAN] main: 53 songs, 3 indexes
[PLAN] languages-and-holidays: 30 songs, 6 indexes
[PLAN] medleys: 3 songs, 1 index
```

## Implementation Stages

### Stage 1: Configuration Parser

- Add `book_config.py`.
- Add data structures for definitions and resolved plans.
- Load UTF-8 JSON.
- Implement strict schema validation.
- Implement safe relative-path resolution.

### Stage 2: Collection Resolution

- Resolve direct and recursive physical PDFs.
- Resolve `more.txt` references using `utf-8-sig`.
- Detect missing and ambiguous filenames.
- Deduplicate the combined collection.
- Preserve membership origin metadata.
- Implement alphabetical and list ordering.

### Stage 3: Ownership and Chapter Resolution

- Implement list-claim precedence.
- Detect cross-chapter conflicts.
- Implement unassigned-song policy.
- Build canonical chapter songs and `song_merge_order`.
- Build resolved indexes by intersecting collection membership with ownership.

### Stage 4: PDF Pipeline Integration

- Replace manifest-mode discovery and special-case ordering with `BookPlan`.
- Generate page maps from canonical song order.
- Generate indexes from `ResolvedIndex`.
- Align index links with actual rendered entries.
- Preserve continuous song numbering.

### Stage 5: DOCX Pipeline Integration

- Change the Word generator interface to consume normalized indexes.
- Preserve index order, song order, bookmarks, and links.
- Verify that PDF and DOCX contain identical song membership.

### Stage 6: Legacy Adapter

- Convert current no-manifest discovery into a `BookPlan`.
- Keep old marker behavior unchanged.
- Remove duplicated rendering branches after parity is verified.

### Stage 7: Documentation and Migration

- Mark chapters as implemented in the README.
- Add a complete `book.json` example.
- Document migration from `.separate` and `WORD_INDEX_ORDER`.
- Document validation errors and ownership rules.

## Test Plan

### Unit Tests

- Folder with PDFs only.
- Folder with `more.txt` only.
- Folder containing both PDFs and `more.txt`.
- Same PDF found physically and in the same folder's list.
- Same PDF included by two collections in one chapter.
- List claim overriding a physical-folder claim in another chapter.
- Conflicting list claims from different chapters.
- Missing list entry.
- Ambiguous filename in two physical folders.
- UTF-8 BOM in `more.txt`.
- Blank lines and duplicate lines.
- Alphabetical and list sorting.
- Unknown manifest fields and collection IDs.
- Path traversal outside `pdf_folder`.
- Unassigned PDF policies.

### Integration Tests

- Generate the four-chapter example and assert 97 unique PDFs.
- Assert chapter counts of 11, 53, 30, and 3.
- Assert index counts of 1, 3, 6, and 1.
- Assert all 11 indexes precede the first song page.
- Assert every index page number targets the correct song page.
- Assert popular and Greek songs do not occur in the main song pages.
- Assert main happy and quiet indexes exclude moved songs.
- Assert PDF and DOCX use the same song order.
- Assert DOCX links target the correct bookmarks.
- Run an existing folder without `book.json` and compare legacy output
  membership and ordering.

### Manual Visual Verification

- Verify Hebrew index titles and RTL entry rendering.
- Verify compact and multi-page indexes.
- Verify the transition from the last index to the first chapter.
- Verify chapter boundaries in song order.
- Click representative links from every index.
- Open the DOCX in Word and test representative Ctrl+Click links.

## Acceptance Criteria

The feature is complete when:

1. `book.json` can describe the agreed four-chapter book without manual
   exclusions.
2. A collection combines physical PDFs and its `more.txt`.
3. Explicit list membership moves songs out of their physical-folder chapter.
4. Every song is emitted exactly once by default.
5. Conflicting ownership produces an actionable error.
6. All configured indexes appear at the beginning in manifest order.
7. Index membership reflects final chapter ownership.
8. PDF and DOCX song order and index membership match.
9. Index page numbers, PDF links, outlines, and Word bookmarks remain correct.
10. Existing no-manifest usage continues to work.

## Deferred Enhancements

The following are intentionally outside the first implementation:

- visible chapter divider pages;
- restarting page numbers per chapter;
- repeated PDFs in multiple chapters;
- arbitrary include/exclude expressions;
- glob-based collection definitions;
- nested chapters;
- per-index font and column layout in the JSON;
- a JSON Schema file or graphical configuration editor; and
- automatic conversion of legacy markers into `book.json`.

These can be added later without changing the core collection, ownership, and
chapter model.
