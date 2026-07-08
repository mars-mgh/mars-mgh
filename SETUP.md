# Setup — one-time steps

Two things need you personally: pairing with your reMarkable account, and
(optionally) turning on the built-in Meeting Notes tool on the tablet.

## 1. Pair with your reMarkable account (~2 minutes)

1. Go to <https://my.remarkable.com/pair/app> and copy the one-time code
   (valid for ~5 minutes).
2. In a Claude Code session in this repo, say:
   *"register my remarkable with code XXXXXXXX"* — or run
   `bash scripts/register.sh XXXXXXXX` yourself. It prints a long device token.
3. Save that token as an environment secret named `REMARKABLE_TOKEN` in this
   Claude Code environment's settings (Environment → Environment variables).
   It's long-lived; you won't need the code again.

Every session in this environment can then reach your tablet's cloud library —
both the pipeline scripts and the `remarkable` MCP server in `.mcp.json`.

## 2. Turn on reMarkable's own Meeting Notes (recommended, on the tablet)

You have Connect, so this is included: on the tablet (software 3.27+), link
your Google Calendar (Settings → Integrations). The home screen then shows
upcoming events and one tap creates a notebook pre-titled with the meeting
name and attendees. This makes the pipeline's meeting-matching near-perfect,
because notebook names equal calendar event titles.

Note: reMarkable allows two platform integrations per account; calendar uses
one slot.

## 3. First run

In a session here, say *"run the meeting-match pipeline"*. The first run does a
capped sync of your most recently modified notebooks (default 10), transcribes
them, matches them to your calendar, and creates the "reMarkable Meeting
Notes" database in Notion. Say *"pull everything"* for a full historical sync
in batches.

## 4. Put it on a schedule (optional)

Ask Claude to create a routine (e.g. daily at 6pm) that runs the pipeline in
this session. New handwriting then lands in Notion automatically.

## remarkable-mcp on your laptop (optional)

To query your tablet from Claude Desktop too, add to
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "remarkable": {
      "command": "uvx",
      "args": ["--from", "remarkable-mcp", "remarkable-mcp", "--read-only"],
      "env": { "REMARKABLE_TOKEN": "<same token>" }
    }
  }
}
```
