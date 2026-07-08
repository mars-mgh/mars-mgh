#!/usr/bin/env python3
"""Pull new/changed reMarkable notebooks and render their pages to PNGs.

Produces workdir/manifest.json describing every changed document, with
rendered page images ready for Claude to transcribe. State (which document
versions have already been processed) lives in state/state.json.

Usage:
    python3 scripts/pull_notes.py              # pull changed docs, render pages
    python3 scripts/pull_notes.py --all        # ignore state, pull everything
    python3 scripts/pull_notes.py --limit 5    # cap docs per run (default 10)
    python3 scripts/pull_notes.py --mark-done  # record manifest docs in state

Requires: rmapi (scripts/bootstrap.sh installs it), pymupdf, REMARKABLE_TOKEN.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKDIR = REPO / "workdir"
STATE_FILE = REPO / "state" / "state.json"
MANIFEST = WORKDIR / "manifest.json"
RENDER_DPI = 150
MAX_PAGES_PER_DOC = 30


def rmapi_bin() -> str:
    local = REPO / "bin" / "rmapi"
    if local.exists():
        return str(local)
    if shutil.which("rmapi"):
        return "rmapi"
    sys.exit("rmapi not found — run scripts/bootstrap.sh first")


def rmapi_env() -> dict:
    # Pin the config path: a stray legacy ~/.rmapi (e.g. written by an
    # unauthenticated remarkable-mcp) would otherwise take precedence.
    conf = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "rmapi" / "rmapi.conf"
    return {**os.environ, "RMAPI_CONFIG": str(conf)}


def run_rmapi(args: list[str], cwd: Path | None = None) -> str:
    cmd = [rmapi_bin(), "-ni"] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                          timeout=600, env=rmapi_env())
    if proc.returncode != 0:
        raise RuntimeError(f"rmapi {' '.join(args)} failed:\n{proc.stderr or proc.stdout}")
    return proc.stdout


def list_documents() -> list[dict]:
    """Return all cloud entries (docs + folders) with id/name/type/parent/modifiedClient."""
    out = subprocess.run(
        [rmapi_bin(), "-ni", "-json", "find", "/"],
        capture_output=True, text=True, timeout=600, env=rmapi_env(),
    )
    if out.returncode != 0:
        raise RuntimeError(f"rmapi find failed:\n{out.stderr or out.stdout}")
    # Output may contain log lines before/after the JSON array.
    text = out.stdout
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise RuntimeError(f"could not locate JSON in rmapi output:\n{text[:500]}")
    return json.loads(text[start:end + 1])


def build_paths(entries: list[dict]) -> dict[str, str]:
    """Map entry id -> full path, reconstructed from parent links."""
    by_id = {e["id"]: e for e in entries}

    def path_of(entry_id: str) -> str:
        parts = []
        cur = by_id.get(entry_id)
        seen = set()
        while cur and cur["id"] not in seen:
            seen.add(cur["id"])
            parts.append(cur["name"])
            parent = cur.get("parent") or ""
            cur = by_id.get(parent)
        return re.sub("/+", "/", "/" + "/".join(reversed(parts)))

    return {e["id"]: path_of(e["id"]) for e in entries}


def in_trash(entry: dict, by_id: dict[str, dict]) -> bool:
    cur, seen = entry, set()
    while cur:
        parent = cur.get("parent") or ""
        if parent == "trash":
            return True
        if parent in seen or parent not in by_id:
            return False
        seen.add(parent)
        cur = by_id[parent]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"docs": {}}


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")[:60] or "doc"


def render_pdf(pdf: Path, out_dir: Path) -> list[str]:
    import fitz  # pymupdf

    pages = []
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc):
            if i >= MAX_PAGES_PER_DOC:
                break
            png = out_dir / f"page-{i + 1:03d}.png"
            page.get_pixmap(dpi=RENDER_DPI).save(png)
            pages.append(str(png.relative_to(REPO)))
    return pages


def fetch_and_render(doc_path: str, doc_dir: Path) -> tuple[list[str], str]:
    """Download a document archive and render its pages to PNGs.

    Handwritten pages (.rm, format v6 incl. Paper Pro) are rendered with
    remarkable_mcp's renderer; PDF/EPUB underlays fall back to pymupdf.
    Returns (page image paths, document kind).
    """
    import zipfile

    from remarkable_mcp.extract import _get_ordered_rm_files, render_rm_file_to_png

    run_rmapi(["get", doc_path], cwd=doc_dir)
    zips = list(doc_dir.glob("*.rmdoc")) + list(doc_dir.glob("*.zip"))
    if not zips:
        raise RuntimeError("rmapi get produced no archive")
    archive = doc_dir / "archive"
    with zipfile.ZipFile(zips[0]) as zf:
        zf.extractall(archive)

    rm_files = _get_ordered_rm_files(archive)
    pages = []
    if rm_files:
        for i, rm in enumerate(rm_files[:MAX_PAGES_PER_DOC]):
            png_bytes = render_rm_file_to_png(rm, background_color="#FFFFFF")
            if png_bytes:
                png = doc_dir / f"page-{i + 1:03d}.png"
                png.write_bytes(png_bytes)
                pages.append(str(png.relative_to(REPO)))
        return pages, "notebook"

    pdfs = list(archive.glob("*.pdf"))
    if pdfs:
        return render_pdf(pdfs[0], doc_dir), "pdf"
    raise RuntimeError("archive has no .rm pages and no PDF underlay")


def pull(args) -> None:
    entries = list_documents()
    by_id = {e["id"]: e for e in entries}
    paths = build_paths(entries)
    state = load_state()

    docs = [
        e for e in entries
        if e.get("type") == "DocumentType" and not in_trash(e, by_id)
    ]
    changed = [
        d for d in docs
        if args.all or state["docs"].get(d["id"]) != d.get("modifiedClient")
    ]
    # Most recently modified first; cap per run so a first sync stays manageable.
    changed.sort(key=lambda d: d.get("modifiedClient") or "", reverse=True)
    skipped = max(0, len(changed) - args.limit)
    changed = changed[: args.limit]

    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
    WORKDIR.mkdir(parents=True)

    manifest = {"documents": [], "skipped_changed_docs": skipped}
    for doc in changed:
        doc_dir = WORKDIR / f"{safe_name(doc['name'])}-{doc['id'][:8]}"
        doc_dir.mkdir(parents=True)
        try:
            pages, kind = fetch_and_render(paths[doc["id"]], doc_dir)
            manifest["documents"].append({
                "id": doc["id"],
                "name": doc["name"],
                "path": paths[doc["id"]],
                "kind": kind,
                "modified": doc.get("modifiedClient"),
                "previously_processed": state["docs"].get(doc["id"]),
                "tags": doc.get("tags") or [],
                "pages": pages,
            })
            print(f"pulled: {paths[doc['id']]} ({len(pages)} pages)")
        except Exception as exc:  # keep going; report failures in manifest
            manifest["documents"].append({
                "id": doc["id"],
                "name": doc["name"],
                "path": paths.get(doc["id"]),
                "modified": doc.get("modifiedClient"),
                "error": str(exc),
            })
            print(f"FAILED: {paths.get(doc['id'])}: {exc}", file=sys.stderr)

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    ok = [d for d in manifest["documents"] if "error" not in d]
    summary = f"\n{len(ok)} document(s) ready in {MANIFEST.relative_to(REPO)}"
    if skipped:
        summary += f" ({skipped} more changed docs deferred to next run)"
    print(summary)


def mark_done() -> None:
    if not MANIFEST.exists():
        sys.exit("no manifest to mark done — run a pull first")
    manifest = json.loads(MANIFEST.read_text())
    state = load_state()
    n = 0
    for doc in manifest["documents"]:
        if "error" not in doc and doc.get("modified"):
            state["docs"][doc["id"]] = doc["modified"]
            n += 1
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))
    print(f"recorded {n} document(s) in {STATE_FILE.relative_to(REPO)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="ignore state, pull everything")
    parser.add_argument("--limit", type=int, default=10, help="max docs per run")
    parser.add_argument("--mark-done", action="store_true",
                        help="record manifest docs as processed in state.json")
    args = parser.parse_args()

    if args.mark_done:
        mark_done()
        return

    if not os.environ.get("REMARKABLE_TOKEN") and not (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "rmapi" / "rmapi.conf"
    ).exists():
        sys.exit("REMARKABLE_TOKEN not set — see SETUP.md step 1")

    pull(args)


if __name__ == "__main__":
    main()
