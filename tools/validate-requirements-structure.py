#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "requirements.md"
REQUIREMENTS_ROOT = ROOT / "docs" / "requirements"

CATEGORIES = {
    "business": ("bt", "БТ", (1, 2, 3)),
    "functional": ("ft", "ФТ", tuple(range(1, 12))),
    "quality": ("kach", "КАЧ", tuple(range(1, 7))),
    "rules": ("pr", "ПР", tuple(range(1, 7))),
    "user": ("pt", "ПТ", tuple(range(1, 5))),
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def expected_requirements() -> dict[Path, str]:
    result: dict[Path, str] = {}
    for category, (file_prefix, identifier_prefix, numbers) in CATEGORIES.items():
        for number in numbers:
            path = REQUIREMENTS_ROOT / category / f"{file_prefix}-{number}.md"
            result[path] = f"{identifier_prefix}-{number}"
    return result


def check_index(expected: dict[Path, str]) -> None:
    text = INDEX.read_text(encoding="utf-8")
    entries = re.findall(
        r"^- \[([^]]+)\]\((requirements/[^)]+\.md)\)$",
        text,
        flags=re.MULTILINE,
    )
    linked_paths = [INDEX.parent / link for _, link in entries]

    if len(linked_paths) != len(set(linked_paths)):
        fail("docs/requirements.md contains duplicate requirement index entries")

    missing = sorted(set(expected) - set(linked_paths))
    unexpected = sorted(set(linked_paths) - set(expected))
    if missing:
        fail(
            "docs/requirements.md does not link: "
            + ", ".join(str(path.relative_to(ROOT)) for path in missing),
        )
    if unexpected:
        fail(
            "docs/requirements.md links unexpected files: "
            + ", ".join(str(path.relative_to(ROOT)) for path in unexpected),
        )
    for label, link in entries:
        path = INDEX.parent / link
        if not label.startswith(expected[path]):
            fail(
                f"docs/requirements.md labels {link} as {label!r}, "
                f"expected {expected[path]}",
            )


def check_requirement_file(path: Path, identifier: str) -> None:
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r"^# (.+)$", text, flags=re.MULTILINE)
    if len(headings) != 1 or not headings[0].startswith(identifier):
        fail(
            f"{path.relative_to(ROOT)} must have one H1 starting with "
            f"{identifier}",
        )
    if text.count("## Требование") != 1:
        fail(f"{path.relative_to(ROOT)} must have one requirement section")
    if not re.search(r"^## Требование\n\n\S", text, flags=re.MULTILINE):
        fail(f"{path.relative_to(ROOT)} has an empty requirement section")
    if "[К списку требований](../../requirements.md)" not in text:
        fail(f"{path.relative_to(ROOT)} has no link to the requirements index")


def check_tree(expected: dict[Path, str]) -> None:
    actual = set(REQUIREMENTS_ROOT.rglob("*.md"))
    missing = sorted(set(expected) - actual)
    unexpected = sorted(actual - set(expected))
    if missing:
        fail(
            "missing requirement files: "
            + ", ".join(str(path.relative_to(ROOT)) for path in missing),
        )
    if unexpected:
        fail(
            "unexpected requirement files: "
            + ", ".join(str(path.relative_to(ROOT)) for path in unexpected),
        )
    for path, identifier in expected.items():
        check_requirement_file(path, identifier)


def main() -> None:
    expected = expected_requirements()
    check_tree(expected)
    check_index(expected)
    print(f"Requirements structure OK: {len(expected)} files")


if __name__ == "__main__":
    main()
