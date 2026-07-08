---
name: meeting-match
description: Run the reMarkable meeting-match pipeline - pull new handwritten notebooks from the reMarkable cloud, transcribe the handwriting, match each notebook to the Google Calendar meeting it was written in, cross-link Granola/Fireflies transcripts, and file everything into Notion. Use when the user says "run the pipeline", "sync my remarkable", "match my notes", or on a scheduled run.
---

# reMarkable meeting-match pipeline

Turn raw handwritten notebooks into meeting-linked, searchable knowledge. Follow
the phases in order. Never commit or expose note content outside the approved
destinations (Notion workspace, this session). Note content may include
confidential Endeavor material — it must not be pushed to GitHub, pasted into
public services, or left in files that aren't gitignored.

## Phase 0 — Pull

```bash
bash scripts/bootstrap.sh
.venv/bin/python scripts/pull_notes.py          # add --all for a full first sync, --limit N to cap
```

- If bootstrap fails on a missing `REMARKABLE_TOKEN`, stop and tell the user to
  complete SETUP.md step 1. Do not improvise other auth paths.
- If `workdir/manifest.json` has no documents, report "nothing new" and stop.
- Entries with an `"error"` field: mention them in the final report; their state
  is not marked done, so they retry next run.

## Phase 1 — Transcribe

For each manifest document, Read its rendered `pages` (PNG images) and produce:

- A faithful transcript of the handwriting (mark illegible words `[?]`).
  Preserve structure: headings, bullets, arrows, boxes, margin notes.
- Action items: anything starred, boxed, checkboxed, or phrased as a to-do.
- Signals for matching: any date/time written on the page, names of people,
  company/project names, and whether the notebook name looks like a meeting
  title (notebooks created by reMarkable's Meeting Notes tool are named after
  the calendar event).

Skip documents that are clearly not meeting notes (books, imported PDFs with no
annotations, sketches) — file them under "Not meeting-related" in the report and
still mark them done.

## Phase 2 — Match to meetings

For each transcribed notebook:

1. Establish the candidate time window: from `previously_processed` (or 7 days
   before `modified` if null) to `modified`.
2. Fetch calendar events in that window with `mcp__Google_Calendar__list_events`
   (startTime/endTime, primary calendar).
3. Match, in order of confidence:
   - **Title match** — notebook name ≈ event title (Meeting Notes tool).
   - **Explicit date/attendees** — a date or attendee names written on the page
     matching an event.
   - **Time overlap** — notebook modified during or shortly after an event.
4. One notebook may span several meetings (people reuse notebooks); match at
   page level when page content clearly changes topic.
5. If nothing matches confidently, file it as **Unmatched** — never guess a
   meeting association and present it as fact; note it as a suggestion instead.

Then enrich each matched meeting:

- `mcp__Granola__list_meetings` (custom range around the event) and
  `mcp__Fireflies__fireflies_get_transcripts` equivalents via search — if the
  same meeting was recorded, capture the note/transcript link for cross-linking.
  Do not paste whole transcripts into Notion; link them.

## Phase 3 — File into Notion

Destination: a Notion database named **"reMarkable Meeting Notes"**.

- Find it with `mcp__Notion__notion-search`. If it doesn't exist, create it
  (private page in the user's space) with properties: `Meeting` (title),
  `Date` (date), `Calendar event` (text), `Attendees` (text),
  `Notebook` (text), `Match` (select: Title / Content / Time overlap /
  Unmatched), `Granola` (url), `Fireflies` (url), `Action items` (text).
- One page per meeting (or per unmatched notebook). Page body: a short summary,
  the action items, then the full transcript. If the same meeting page already
  exists from a previous run, update it rather than duplicating.
- reMarkable page images/PDF stay local; the transcript is the artifact.

## Phase 4 — Finish

```bash
.venv/bin/python scripts/pull_notes.py --mark-done
git add state/state.json && git commit -m "Record processed notebooks" && git push -u origin <current branch>
```

Report to the user: documents processed, meetings matched (with Notion links),
unmatched notebooks, failures, and anything deferred by the per-run limit.
Frame any content interpretation (especially about entrepreneurs/companies) as
a draft for human review, per Endeavor AI policy.
