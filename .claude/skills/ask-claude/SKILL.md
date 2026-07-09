---
name: ask-claude
description: Read Marta's handwritten requests from the "Claude" folder on her reMarkable, act on them with connected tools (reversibly - drafts, briefs, research, task breakdowns), and send a typed answer PDF back to the tablet. Use when the user says "check my questions", "read my notes to you", "check the Claude folder", or on a scheduled run after meeting-match.
---

# Ask Claude — handwriting as input

Marta handwrites requests in the **/Claude** folder on her tablet (any notebook
in it). Each pipeline run turns those into completed or prepared work. Same
confidentiality rules as meeting-match: content stays in this session, Notion,
and her own tablet.

## Phase 0 — Pull

Reuse the meeting-match sync (`bash scripts/bootstrap.sh` +
`.venv/bin/python scripts/pull_notes.py` if not already run this session).
Select manifest documents whose `path` starts with `/Claude/`, skipping any
named like an answer (`Re *` — those are ours). If none changed, report
"no new requests" and stop.

## Phase 1 — Read and interpret

Read the rendered pages and transcribe. Split the content into discrete
requests and classify each:

- **Question** — answer it, using calendar/email/Notion/Granola/Drive context
  where it helps.
- **Task / to-do** — don't just list it back: do the preparable part. Break it
  into next steps, gather the context she'd need, link relevant meetings,
  docs, and threads.
- **Draft request** ("email X about Y", "reply to Z") — write the draft. Create
  it as a Gmail/Superhuman draft; NEVER send. Include the draft text in the
  answer too.
- **Research / prep** ("prep me for the call with X") — build a short brief
  from her meetings, email, Notion, and (only for public info) the web.

If an item is ambiguous, make the reasonable interpretation, do it, and note
the assumption in the answer — don't skip it.

## Phase 2 — Act (reversible only)

Allowed without asking: creating email drafts, Notion pages, task lists,
briefs, calendar event *suggestions* written into the answer. Not allowed
without explicit handwritten instruction AND user confirmation in the session:
sending email, messaging people, modifying/deleting existing calendar events,
anything visible to others. Per Endeavor AI policy, frame anything about
specific entrepreneurs/companies as draft input for her judgment.

## Phase 3 — Answer back to the tablet

Write the answer as markdown (concise, structured per request: what was done,
what's ready where, what needs her). Then:

```bash
.venv/bin/python scripts/send_to_tablet.py answer.md --title "Re: <notebook> <MMM D>" --folder /Claude
```

Also add durable outputs (briefs, drafts, task breakdowns) to Notion when
they're worth keeping beyond the day, and mention Notion links in the answer.

## Phase 4 — Finish

Mark processed docs done (they share state with meeting-match):

```bash
.venv/bin/python scripts/pull_notes.py --mark-done
git add state/state.json && git commit -m "Record processed notebooks" && git push -u origin <current branch>
```

Report in the session: requests found, actions taken, drafts created, and the
name of the answer document now on her tablet.
