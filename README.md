# reMarkable meeting-match

Make handwritten reMarkable notes part of the meeting knowledge base: every
notebook gets pulled from the reMarkable cloud, transcribed by Claude,
matched to the Google Calendar meeting it was written in, cross-linked with
the Granola/Fireflies transcript of that meeting, and filed into a Notion
database — so Claude (and you) can search all of it later.

Nothing on the market does the retroactive note→meeting association: reMarkable's
own Meeting Notes tool (firmware 3.27, Connect) only works forward from an
upcoming event, and sync products like Scrybble/Remarkn are calendar-blind.
This repo closes that loop using tools already connected to Claude.

## Architecture

```
reMarkable cloud ──rmapi──▶ workdir/ (PDFs → PNGs)          [scripts/pull_notes.py]
                                │
                                ▼
                     Claude vision transcription             [meeting-match skill]
                                │
        Google Calendar ──▶ match by title / content / time
        Granola + Fireflies ──▶ cross-link transcripts
                                │
                                ▼
                  Notion: "reMarkable Meeting Notes" DB
```

State (which notebook versions were processed) is committed in
`state/state.json` — IDs and timestamps only. **Note content is never
committed**; `workdir/` is gitignored and the only destination is Notion.

## Components

- `scripts/bootstrap.sh` — installs [ddvk/rmapi](https://github.com/ddvk/rmapi)
  and writes its auth config from the `REMARKABLE_TOKEN` secret.
- `scripts/register.sh` — one-time pairing (one-time code → device token).
- `scripts/pull_notes.py` — incremental sync: lists the cloud library, pulls
  changed notebooks as annotated PDFs, renders pages to PNG, writes
  `workdir/manifest.json` for the skill to consume.
- `.claude/skills/meeting-match/` — the pipeline procedure Claude follows
  (transcribe → match → enrich → file → mark done).
- `.mcp.json` — loads [remarkable-mcp](https://github.com/SamMorrowDrums/remarkable-mcp)
  (read-only) so any session here can browse/search the tablet ad hoc.

Start with [SETUP.md](SETUP.md).
