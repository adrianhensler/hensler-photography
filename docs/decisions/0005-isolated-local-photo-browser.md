# 0005 — Isolate the local photo browser and its catalog

- **Date:** 2026-10-22
- **Status:** proposed in prototype PR

## Context

Adrian wants an ACDSee-style browser for local originals, reusing useful gallery
work. The production image processor writes derivatives beside uploads and the
production database includes users, publishing and AI services. ACDSee's catalog
format and exports have not been inspected.

## Decision

Put the runnable prototype under `prototypes/local-photo-browser`, with only the
existing Pillow dependency and the Python standard library. Adapt EXIF/derivative
conventions and metadata names, but do not import production initialization or
services. Require a separate catalog/cache path. Keep a storage protocol and a
neutral annotation-manifest seam for future importers. Serve only cached previews
on loopback, with request-origin checks and no HTTP mutation endpoints.

## Consequences

No production routes, website assets or database are affected. A small amount of
image-processing logic is adapted locally to enforce different write boundaries;
shared extraction can be considered later with regression tests for both users.
ACDSee import requires evidence and explicit mapping; no proprietary-format guess
is embedded in the browser. Semantic search from Orchard remains an opt-in future
experiment, avoiding new heavy dependencies or model downloads in this prototype.
