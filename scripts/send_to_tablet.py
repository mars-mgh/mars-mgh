#!/usr/bin/env python3
"""Render a markdown/text file to PDF and upload it to the reMarkable.

Used by the ask-claude skill to deliver typed answers back to the tablet.

Usage:
    .venv/bin/python scripts/send_to_tablet.py answer.md --title "Re: To do" --folder /Claude
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# reMarkable Paper Pro Move-friendly page: A5-ish portrait, generous margins
PAGE_W, PAGE_H = 445, 594
MARGIN = 36
BODY_SIZE = 11
LINE_GAP = 1.45


def rmapi_bin() -> str:
    local = REPO / "bin" / "rmapi"
    if local.exists():
        return str(local)
    return "rmapi"


def rmapi_env() -> dict:
    conf = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "rmapi" / "rmapi.conf"
    return {**os.environ, "RMAPI_CONFIG": str(conf)}


def run_rmapi(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run([rmapi_bin(), "-ni"] + args, capture_output=True,
                          text=True, timeout=300, env=rmapi_env())
    if check and proc.returncode != 0:
        raise RuntimeError(f"rmapi {' '.join(args)} failed:\n{proc.stderr or proc.stdout}")
    return proc


def markdown_to_pdf(text: str, pdf_path: Path, title: str) -> None:
    import fitz  # pymupdf

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN

    def new_page():
        nonlocal page, y
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        y = MARGIN

    def emit(line: str, size: float, bold: bool = False, indent: float = 0.0):
        nonlocal y
        font = "helvetica-bold" if bold else "helvetica"
        width = PAGE_W - 2 * MARGIN - indent
        # crude wrap: measure and split by words
        words = line.split()
        cur = ""
        lines = []
        for w in words:
            trial = (cur + " " + w).strip()
            if fitz.get_text_length(trial, fontname=font, fontsize=size) > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        lines.append(cur or "")
        for ln in lines:
            if y > PAGE_H - MARGIN:
                new_page()
            page.insert_text((MARGIN + indent, y), ln, fontsize=size, fontname=font)
            y += size * LINE_GAP

    emit(title, 16, bold=True)
    y += 6

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            y += BODY_SIZE * 0.7
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            level = len(m.group(1))
            y += 4
            emit(m.group(2), max(15 - level, BODY_SIZE + 1), bold=True)
            continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            emit("• " + strip_md(m.group(1)), BODY_SIZE, indent=10)
            continue
        m = re.match(r"^\s*(\d+)[.)]\s+(.*)", line)
        if m:
            emit(f"{m.group(1)}. " + strip_md(m.group(2)), BODY_SIZE, indent=10)
            continue
        emit(strip_md(line), BODY_SIZE)

    doc.save(pdf_path)
    doc.close()


def strip_md(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", s)
    return s


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="markdown or text file to send")
    parser.add_argument("--title", default=None, help="document title (defaults to filename)")
    parser.add_argument("--folder", default="/Claude", help="destination folder on the tablet")
    args = parser.parse_args()

    src = Path(args.source)
    title = args.title or src.stem
    safe = re.sub(r"[^A-Za-z0-9 ._-]+", "", title)[:60] or "Answer"

    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / f"{safe}.pdf"
        markdown_to_pdf(src.read_text(), pdf, title)
        run_rmapi(["mkdir", args.folder], check=False)  # ok if it already exists
        run_rmapi(["put", str(pdf), args.folder])

    print(f"sent: {args.folder}/{safe}")


if __name__ == "__main__":
    main()
