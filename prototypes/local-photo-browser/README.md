# Local photo browser prototype

A standalone, offline photo browser: folder and metadata filters on the left,
responsive thumbnail grid in the middle, image inspector on the right. Select a
photo for details; open the larger preview and use arrow keys or Escape.
This is a browsing prototype, not an editor or an ACDSee database reader.

## Start with synthetic photos

Requires Python 3.11+ and Pillow (the same pinned dependency as the gallery).
No Node, Docker, API keys, AI service, or model download is needed to run it.
From the repository root:

```sh
cd prototypes/local-photo-browser
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m local_browser demo .demo
python -m local_browser serve .demo/photos --metadata .demo/metadata.json --data-dir .catalog
```

Open **http://127.0.0.1:8080**. Stop with Ctrl+C. `demo` intentionally refuses to
write into an existing directory; skip that command on later starts.
If port 8080 is busy, add `--port 8081` to `serve`.

For a real library, use a separate catalog directory (do not overlap it with the
photo folder, including ancestors). Quote paths containing spaces:

```sh
python -m local_browser serve "/path/to/photos" --data-dir "/path/to/browser-catalog"
# Windows example:
python -m local_browser serve "D:\Photos" --data-dir "C:\Users\Adrian\PhotoBrowserCatalog"
```

Startup scans the folder recursively before serving. Restart to rescan, or use
`scan` in place of `serve` for indexing without the browser. There is no watcher
or background auto-rescan. Unchanged size + nanosecond mtime reuses cached
previews. Changing files while scanning is discouraged; detected changes are
reported for retry. A file replaced with identical size and mtime is not detected.

## Included behavior

- Read-only indexing of JPEG, PNG, WebP, TIFF and BMP, including EXIF orientation.
- Separate SQLite catalog and 400 px thumbnails / 1600 px previews. Dimensions
  are bounded on both axes; no upscaling. Originals are never served or written.
- Filter by folder (exact folder, not descendants), camera, lens, category, tag,
  capture/date range and ISO range. Search filenames and metadata text.
- Sort by date, filename, camera, ISO or file size; 100 photos per page, lazy images.
- EXIF capture time is unzoned camera time. When absent, date sorting/filtering
  uses file modification time in UTC; the inspector labels both explicitly.
- Unreadable files are reported; unsupported common RAW/HEIC/video extensions
  are counted. Symlink files/directories are skipped. No RAW decoder is included.
- Missing records keep their metadata but disappear from the grid after a scan.
  Incomplete directory traversal does not mark unseen records missing.
- Local HTTP server binds only to 127.0.0.1. Host/Origin/Fetch-Site checks reject
  other websites; fixed static routes and catalog IDs prevent arbitrary file reads.
  This is for one trusted local user, not a network service or production hosting.

## Categories, tags and the importer boundary

EXIF usually supplies technical metadata, not this app's categories/tags.
Those remain empty unless supplied by an annotation manifest. The demo includes
one. `--metadata path/to/metadata.json` accepts this neutral format:

```json
{
  "Coast/example.jpg": {
    "category": "landscape",
    "tags": ["Halifax", "sunset"],
    "caption": "Evening light",
    "description": "Human-authored description"
  }
}
```

Keys are exact, case-sensitive paths relative to the photo folder, using `/`.
Optional fields: title, caption, description, alt_text, location, category, tags.
Tags are an array of strings; other fields are strings or null. Explicit manifest
values overwrite those fields during a scan. Other editorial fields survive
rescans; extracted technical fields refresh if the file changes. GPS location is
re-extracted on change unless the manifest overrides it. No sidecars are written.
The manifest is supplied explicitly; arbitrary neighboring files are not loaded.

`Catalog` in `local_browser/catalog.py` is the storage protocol used by scanner
and HTTP server. `SQLiteCatalog` is one implementation; a test indexes into an
in-memory replacement. Records separate identity/path/fingerprint/presence from
metadata. The SQLite schema has a version marker and rejects unrelated databases.
A future importer can normalize exports into the manifest or implement the
protocol without changing the UI. It should preserve provenance, source IDs and
unmapped fields in an extension namespace, and validate matching before writing.
Do not point this app at the production gallery database or an ACDSee database.

## What was reused

Inspected Hensler Photography at commit
`990ba75d5976612fb3acb0374aa3dfcaea409784`:

| Existing component | Reuse / deliberate adaptation |
| --- | --- |
| `api/database.py`, `images` | Reuses metadata vocabulary: original_filename, camera_make/model/camera, lens, focal_length, aperture, shutter_speed, iso, date_taken, location, category, tags, dimensions, caption and description. New independent schema, no production migrations or user/publish state. Tags are normalized arrays in JSON. |
| `api/services/exif.py` | Adapts EXIF field mapping, combined camera name, ISO date parsing, exposure formatting and decimal GPS convention using Pillow's EXIF reader. Handles orientation; no dependency on production logging or piexif. |
| `api/services/image_processor.py` | Adapts Pillow/LANCZOS/WebP quality-85 derivative approach and 400 px thumbnail convention. Writes only to external cache, never beside originals; uses bounded dimensions and atomic replacement. |
| AI metadata pipeline | Preserves its caption/description/category/tag vocabulary. Does not import or invoke the paid AI service; no generated claims about real photos. |
| Frontend | New vanilla HTML/CSS/JS local browsing interface. No production templates, public-gallery assets, auth, analytics or Caddy configuration are changed. |

### Orchard Photos review

Reviewed [README](https://github.com/chaseleantj/orchard-photos/blob/main/README.md)
and [architecture](https://github.com/chaseleantj/orchard-photos/blob/main/docs/how-it-works.md).
Orchard is a useful reference for local-first scanning, separate caches, loopback
request checks, and model-versioned search indexes. This prototype uses those
architectural ideas; **no Orchard source code is copied** and it is not a runtime
dependency.

Potential next experiments, outside this PR:

1. Opt-in SigLIP2 text/image similarity with a separate model-versioned index.
   Explicit consent for initial model download; show execution device and errors.
2. Duplicate/burst grouping with a reversible "show every file" control. Preserve
   each file's identity and provenance, rather than collapsing metadata silently.
3. A visual similarity map; evaluate usefulness against a plain folder/date grid.

Orchard's documented Windows DirectML path may be relevant to Adrian's AMD GPU;
this prototype makes no hardware performance claims and runs no embeddings.

## ACDSee import: still unknown

We have not inspected Adrian's ACDSee version, database files, export options,
sidecars, or local photo library. The gallery's SQLite schema is **not** ACDSee's
proprietary catalog. Unknowns include schema/encryption/version compatibility;
which categories, hierarchy, tags, ratings, labels, captions and edit history can
be exported; embedded versus catalog-only data; and how file IDs/drive letters
map to originals after moves. No importer or metadata recovery is claimed.

Next input needed for that separate task: ACDSee product/version and a small
sanitized export or copied sample catalog with a few corresponding sample files.
Keep the original database backed up and unopened by experimental write tools.
Matching must use path/content evidence, not filenames alone.

## Tests

```sh
# In prototypes/local-photo-browser, after installing requirements:
python -m unittest discover -s tests -v
python -m compileall -q local_browser
node --check local_browser/static/app.js

# Optional browser smoke, from repository root; uses existing dev dependencies:
npm ci
npx playwright install chromium
node prototypes/local-photo-browser/tests/ui-smoke.cjs
```

The smoke test generates its own temporary photos, starts port 8080, checks grid,
preview navigation, filters, empty states, and narrow-screen overflow, then cleans
up only its temporary fixture. Stop other services on port 8080 first.
The focused GitHub workflow runs both tests; no production deployment is added.

Backend tests verify source hashes and mtimes, incremental cache reuse, changed/
missing/returning files, malformed files, EXIF/rotation, exact filters and stable
pagination, unsafe query handling, foreign DB rejection, path overlap, symlinks,
request-origin protection and a replacement storage adapter.

## Prototype limits

Indexing is synchronous and decodes images serially; no large-library performance
claim. Filters use SQLite JSON queries and are not optimized for millions of rows.
No native folder picker, editor, ratings UI, XMP/IPTC parser, RAW/HEIC/video support,
full-resolution viewer, color-managed print proofing, semantic search, or ACDSee
import yet. Multi-page TIFFs use the first frame. Camera dates are not timezone
normalized. Old derivative versions remain cached; cache pruning is a follow-up.
Path-based identities do not yet follow renames. The catalog stores local paths
and may contain GPS; keep its data directory private. It is not automatically
uploaded or committed. There are no runtime network calls beyond loopback.
