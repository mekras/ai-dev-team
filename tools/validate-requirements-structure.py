#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "05-requirements" / "README.md"
REQUIREMENTS_ROOT = ROOT / "docs" / "05-requirements"

CATEGORIES = {
    "business": ("bt", "БТ", (1, 2, 3)),
    "functional": ("ft", "ФТ", tuple(range(1, 41))),
    "quality": ("kach", "КАЧ", tuple(range(1, 10))),
    "rules": ("pr", "ПР", tuple(range(1, 9))),
    "user": ("pt", "ПТ", (1, 2, 3, 5, 6, 7)),
}

INLINE_REQUIREMENT_RE = re.compile(
    r"^\*\*((?:БТ|ПТ|ФТ|КАЧ|ПР)-\d+)(?:[ .(])",
    flags=re.MULTILINE,
)


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
    inline_requirements = INLINE_REQUIREMENT_RE.findall(text)
    if inline_requirements:
        fail(
            "docs/05-requirements/README.md defines requirements inline: "
            + ", ".join(sorted(set(inline_requirements))),
        )
    entries = re.findall(
        r"^- \[([^]]+)\]\(((?:business|functional|quality|rules|user)/"
        r"[^)]+\.md)\)$",
        text,
        flags=re.MULTILINE,
    )
    linked_paths = [INDEX.parent / link for _, link in entries]

    if len(linked_paths) != len(set(linked_paths)):
        fail(
            "docs/05-requirements/README.md contains duplicate requirement "
            "index entries",
        )

    missing = sorted(set(expected) - set(linked_paths))
    unexpected = sorted(set(linked_paths) - set(expected))
    if missing:
        fail(
            "docs/05-requirements/README.md does not link: "
            + ", ".join(str(path.relative_to(ROOT)) for path in missing),
        )
    if unexpected:
        fail(
            "docs/05-requirements/README.md links unexpected files: "
            + ", ".join(str(path.relative_to(ROOT)) for path in unexpected),
        )
    for label, link in entries:
        path = INDEX.parent / link
        if not label.startswith(expected[path]):
            fail(
                f"docs/05-requirements/README.md labels {link} as {label!r}, "
                f"expected {expected[path]}",
            )
        heading = re.search(
            r"^# (.+)$",
            path.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        if heading is None or label != heading.group(1):
            fail(
                "docs/05-requirements/README.md must use the full requirement "
                "title "
                f"from {link}",
            )


def check_requirement_file(path: Path, identifier: str) -> None:
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r"^# (.+)$", text, flags=re.MULTILINE)
    if len(headings) != 1 or not headings[0].startswith(identifier):
        fail(
            f"{path.relative_to(ROOT)} must have one H1 starting with "
            f"{identifier}",
        )
    if not re.fullmatch(
        rf"{re.escape(identifier)}\. \S.+",
        headings[0],
    ):
        fail(
            f"{path.relative_to(ROOT)} must have a meaningful title after "
            f"{identifier}",
        )
    if text.count("## Требование") != 1:
        fail(f"{path.relative_to(ROOT)} must have one requirement section")
    if not re.search(r"^## Требование\n\n\S", text, flags=re.MULTILINE):
        fail(f"{path.relative_to(ROOT)} has an empty requirement section")
    check_sections = re.findall(
        r"^## Проверка(?: требования)?$",
        text,
        flags=re.MULTILINE,
    )
    if len(check_sections) != 1:
        fail(
            f"{path.relative_to(ROOT)} must have one check section named "
            "'Проверка' or 'Проверка требования'",
        )
    if not re.search(
        r"^## Проверка(?: требования)?\n\n\S",
        text,
        flags=re.MULTILINE,
    ):
        fail(f"{path.relative_to(ROOT)} has an empty check section")
    if path.parent.name == "business":
        if "## Проверка требования" in text:
            fail(
                f"{path.relative_to(ROOT)} must name the business requirement "
                "check section 'Проверка'",
            )
        check_body = re.search(
            r"^## Проверка\n\n(?P<body>.*?)(?=^## |\Z)",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        if check_body is None:
            fail(f"{path.relative_to(ROOT)} has no readable check section")
        first_block = check_body.group("body").strip().split("\n\n", 1)[0]
        if not re.match(
            rf"^{re.escape(identifier)} считается выполненным, если\b",
            first_block,
        ):
            fail(
                f"{path.relative_to(ROOT)} must state when the business "
                "requirement is fulfilled before listing evidence",
            )
    if "[К списку требований](../README.md)" not in text:
        fail(f"{path.relative_to(ROOT)} has no link to the requirements index")


def check_tree(expected: dict[Path, str]) -> None:
    actual = {
        path
        for path in REQUIREMENTS_ROOT.rglob("*.md")
        if path != INDEX
    }
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
