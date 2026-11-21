#!/usr/bin/env python3
"""Add an approved deal-form submission to the newest data/<year>.yaml.

Run by .github/workflows/deal-intake.yml after the maintainer labels a
submission 'approved'. Everything in the form is untrusted input, so:

  - it arrives only through environment variables, never a shell expansion,
  - every value is collapsed to one line, length-limited and written as a
    quoted YAML string,
  - the deal is inserted as text into the matching section, so the rest of
    the file keeps its formatting and comments and the PR diff shows exactly
    one new block.

generate.py --validate runs right after this and does the real checks
(https, no Amazon/marketplace/affiliate/payment links, duplicates, dates).

Outputs:
  pr-body.md        body for the pull request
  intake-error.md   written on failure; posted back to the issue
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# What an empty issue-form field can come through as.
NO_RESPONSE = {"", "_no response_", "none", "n/a", "-"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GITHUB_HANDLE = re.compile(r"^(?!-)(?!.*--)[A-Za-z0-9-]{1,39}(?<!-)$")
LIMITS = {"section": 60, "vendor": 80, "url": 500, "deal": 200, "code": 120,
          "starts": 10, "ends": 10, "focus": 40, "notes": 500, "source": 500,
          "relationship": 80}


def fail(message: str) -> None:
    Path("intake-error.md").write_text(message + "\n", encoding="utf-8")
    print(f"::error::{message}")
    sys.exit(1)


def clean(form: dict, key: str) -> str:
    """One line of plain text, or '' when the field was left empty."""
    value = form.get(key, "")
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    text = " ".join(str(value or "").split())  # collapses newlines and tabs
    if text.lower() in NO_RESPONSE:
        return ""
    limit = LIMITS.get(key, 200)
    if len(text) > limit:
        fail(f"'{key}' is longer than {limit} characters.")
    return text


def q(text: str) -> str:
    """A YAML double-quoted scalar. JSON string syntax is valid YAML."""
    return json.dumps(text, ensure_ascii=False)


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def newest_data_file() -> Path:
    paths = sorted(p for p in DATA_DIR.glob("*.yaml") if re.fullmatch(r"\d{4}", p.stem))
    if not paths:
        fail("No data/<year>.yaml file found.")
    return max(paths, key=lambda p: int(p.stem))


def find_section_id(data: dict, wanted_title: str) -> str:
    sections = data.get("sections") or []
    for section in sections:
        if isinstance(section, dict) and str(section.get("title", "")).strip().casefold() \
                == wanted_title.strip().casefold():
            return str(section["id"])
    titles = ", ".join(str(s.get("title")) for s in sections if isinstance(s, dict))
    fail(f"Section '{wanted_title}' doesn't match any section title in the data file ({titles}).")
    return ""  # unreachable


def section_span(lines: list[str], sid: str) -> tuple[int, int, int]:
    """Return (item_start, item_end, item_indent) for the section whose id is sid."""
    id_line = re.compile(r"^\s*(-\s+)?id:\s*[\"']?" + re.escape(sid) + r"[\"']?\s*(#.*)?$")
    for i, line in enumerate(lines):
        if id_line.match(line):
            break
    else:
        fail(f"Couldn't find section id '{sid}' in the data file.")
    # The list item starts at the nearest '- ' at or above the id line.
    start = i
    while start >= 0 and not lines[start].lstrip().startswith("- "):
        start -= 1
    if start < 0:
        fail(f"Couldn't find where section '{sid}' starts.")
    item_indent = indent_of(lines[start])
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped or stripped.startswith("#"):
            continue
        if indent_of(lines[j]) <= item_indent:
            end = j
            break
    return start, end, item_indent


def deal_indents(lines: list[str], start: int, end: int) -> tuple[int, int] | None:
    """(dash indent, key indent) of an existing deal, searching start..end."""
    for i in range(start, end):
        m = re.match(r"^(\s*)-\s+vendor:", lines[i])
        if m:
            dash = len(m.group(1))
            for j in range(i + 1, end):
                if lines[j].strip() and not lines[j].strip().startswith("#"):
                    return dash, indent_of(lines[j])
            return dash, dash + 2
    return None


def main() -> None:
    raw = os.environ.get("DEAL_JSON", "")
    try:
        form = json.loads(raw)
    except json.JSONDecodeError:
        fail("Couldn't read the form submission.")
    if not isinstance(form, dict):
        fail("Couldn't read the form submission.")

    author = os.environ.get("ISSUE_AUTHOR", "").strip()
    issue = os.environ.get("ISSUE_NUMBER", "").strip()

    fields = {k: clean(form, k) for k in LIMITS}
    for required in ("section", "vendor", "url", "deal"):
        if not fields[required]:
            fail(f"'{required}' is required.")
    for key in ("starts", "ends"):
        if fields[key] and not DATE.match(fields[key]):
            fail(f"'{key}' must be a date written like 2026-12-01 (got {fields[key]!r}).")
    if not fields["ends"]:
        fail("'ends' is required. Year-round offers are added by hand, so mention it in the issue.")

    checks = form.get("checks") or []
    if isinstance(checks, str):
        checks = [checks]
    wants_credit = any("credited" in str(c).lower() for c in checks)
    via = author if wants_credit and GITHUB_HANDLE.match(author) else ""

    codes = [c.strip() for c in fields["code"].split(",") if c.strip()]

    path = newest_data_file()
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        fail(f"{path.name} isn't a mapping.")
    sid = find_section_id(data, fields["section"])

    lines = text.splitlines()
    start, end, item_indent = section_span(lines, sid)

    indents = deal_indents(lines, start, end) or deal_indents(lines, 0, len(lines))
    if indents is None:
        indents = (item_indent + 4, item_indent + 6)
    dash, key = indents
    pad, kpad = " " * dash, " " * key

    block = [f"{pad}- vendor: {q(fields['vendor'])}",
             f"{kpad}url: {q(fields['url'])}",
             f"{kpad}deal: {q(fields['deal'])}"]
    if len(codes) == 1:
        block.append(f"{kpad}code: {q(codes[0])}")
    elif codes:
        block.append(f"{kpad}code: [{', '.join(q(c) for c in codes)}]")
    if fields["starts"]:
        block.append(f"{kpad}starts: {fields['starts']}")
    block.append(f"{kpad}ends: {fields['ends']}")
    if fields["focus"]:
        block.append(f"{kpad}focus: {q(fields['focus'])}")
    if fields["notes"]:
        block.append(f"{kpad}notes: {q(fields['notes'])}")
    if via:
        block.append(f"{kpad}via: {q('@' + via)}")

    # An empty section written as 'deals: []' becomes a block list.
    for i in range(start, end):
        if re.match(r"^\s*deals:\s*\[\s*\]\s*(#.*)?$", lines[i]):
            lines[i] = lines[i].split("deals:")[0] + "deals:"
    # Insert after the section's last line of content.
    insert_at = start + 1
    for i in range(start, end):
        if lines[i].strip() and not lines[i].strip().startswith("#"):
            insert_at = i + 1
    lines[insert_at:insert_at] = block
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    relationship = fields["relationship"] or "not stated"
    source = fields["source"]
    body = [
        f"Closes #{issue}" if issue.isdigit() else "",
        "",
        f"**Vendor:** {fields['vendor']}  ",
        f"**Section:** {fields['section']}  ",
        f"**Submitted by:** @{author}  " if GITHUB_HANDLE.match(author) else "",
        f"**Relationship to vendor:** {relationship}  ",
        f"**Announcement (verify before merging):** `{source}`" if source else
        "**Announcement:** none given, so check the vendor page directly.",
        "",
        "Validated by `generate.py --validate`. README and the JSON feed regenerate on merge.",
    ]
    Path("pr-body.md").write_text("\n".join(l for l in body if l is not None) + "\n",
                                  encoding="utf-8")
    print(f"Added {fields['vendor']} to section '{sid}' in {path.name}.")


if __name__ == "__main__":
    main()
