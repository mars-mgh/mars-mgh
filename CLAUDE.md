# reMarkable meeting-match

Personal integration for Marta's reMarkable Paper Pro Move: pulls handwritten
notebooks from the reMarkable cloud, transcribes them with Claude vision,
matches them to Google Calendar meetings, cross-links Granola/Fireflies
transcripts, and files everything into the "reMarkable Meeting Notes" Notion
database.

## How to run

Invoke the `meeting-match` skill (it contains the full procedure), or manually:

```bash
bash scripts/bootstrap.sh        # install rmapi + write auth config from $REMARKABLE_TOKEN
python3 scripts/pull_notes.py    # pull changed notebooks, render pages to workdir/
# ... transcribe/match/file (see .claude/skills/meeting-match/SKILL.md) ...
python3 scripts/pull_notes.py --mark-done   # then commit state/state.json
```

`.mcp.json` also loads the `remarkable` MCP server (remarkable-mcp) for ad-hoc
queries against the tablet library ("what did I write yesterday?").

## Hard rules

- **Note content never goes to GitHub.** `workdir/`, PDFs, and PNGs are
  gitignored; only code and `state/state.json` (IDs + timestamps, no content)
  get committed.
- Handwritten notes may contain confidential Endeavor/EE material: destinations
  are the user's Notion workspace and this session only. No third-party
  services, no public hosting.
- `REMARKABLE_TOKEN` is a secret. Never print it, commit it, or write it
  anywhere but `~/.config/rmapi/rmapi.conf`.
- Setup steps that need the user (one-time pairing code, device settings) are
  in SETUP.md — don't work around missing auth.
