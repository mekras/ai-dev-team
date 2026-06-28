#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import os
import re
import shutil
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
DATA = KNOWLEDGE / "data"
PRIMARY = KNOWLEDGE / "primary"
NORMALIZED = KNOWLEDGE / "normalized"
STATEMENTS = KNOWLEDGE / "statements"
INDEX = KNOWLEDGE / "index"
FALLBACK_DATE = "2026-06-28"


def rel_from_data(source_slug: str, target: Path) -> str:
    source_dir = DATA / source_slug
    if target.is_relative_to(source_dir):
        return target.relative_to(ROOT).as_posix()
    return Path(os.path.relpath(target, start=source_dir)).as_posix()


def stage_for(source_id: str) -> str:
    normalized_exists = (NORMALIZED / source_id).exists()
    statements_exists = (STATEMENTS / f"{source_id}.md").exists()
    if statements_exists:
        return "statements_extracted"
    if normalized_exists:
        return "normalized"
    return "fetched"


def default_access(source_id: str) -> str:
    return (
        f"Смотри паспорт источника в knowledge/primary/{source_id}/source.md "
        "и ограничения использования в knowledge/source-attribution.md."
    )


def artifact_title(source_id: str, row: dict[str, str]) -> str:
    notes = (row.get("notes") or "").strip()
    if notes:
        return notes
    artifact = (
        row.get("artifact_path")
        or row.get("html_path")
        or row.get("body_path")
        or row.get("extracted_path")
        or ""
    ).strip()
    name = Path(artifact).name
    if name:
        return f"{source_id}: {name}"
    return f"{source_id}: {row.get('id', 'artifact')}"


def page_title(source_id: str, row: dict[str, str]) -> str:
    title = (row.get("title") or "").strip()
    if title:
        return html.unescape(title)
    raw_id = (row.get("id") or "").strip()
    if raw_id:
        return f"{source_id}: {raw_id}"
    return artifact_title(source_id, row)


def item_id_from_raw(source_id: str, raw_id: str, seen: set[str], artifact_path: Path | None) -> str:
    base = f"{source_id}-{raw_id.replace('/', '-')}"
    candidate = base
    if candidate not in seen:
        seen.add(candidate)
        return candidate

    if artifact_path is not None and artifact_path.suffix:
        candidate = f"{base}-{artifact_path.suffix.lstrip('.')}"
        if candidate not in seen:
            seen.add(candidate)
            return candidate

    index = 2
    while True:
        candidate = f"{base}-{index}"
        if candidate not in seen:
            seen.add(candidate)
            return candidate
        index += 1


def unit_slug(item_id: str, source_id: str) -> str:
    prefix = f"{source_id}-"
    base = item_id[len(prefix) :] if item_id.startswith(prefix) else item_id
    slug = re.sub(r"[^a-z0-9._-]+", "-", base.lower()).strip("-")
    return slug or "unit"


def unwrap_value(value: str) -> str:
    return value.strip().strip("`")


def parse_statements_file(source_id: str) -> tuple[str, Path | None, list[dict[str, object]]]:
    path = STATEMENTS / f"{source_id}.md"
    if not path.exists():
        return FALLBACK_DATE, None, []

    text = path.read_text(encoding="utf-8")
    checked_at_match = re.search(r"Дата извлечения:\s*`?(\d{4}-\d{2}-\d{2})`?", text)
    checked_at = checked_at_match.group(1) if checked_at_match else FALLBACK_DATE
    default_artifact = None
    candidate_paths: list[Path] = []
    for match in re.finditer(
        rf"`(knowledge/(?:primary|normalized)/{re.escape(source_id)}/[^`]+)`",
        text,
    ):
        candidate = ROOT / match.group(1)
        if candidate.exists():
            candidate_paths.append(candidate)

    def candidate_score(path: Path) -> tuple[int, int]:
        rel = path.relative_to(ROOT).as_posix()
        if "/files/" in rel and path.suffix == ".txt":
            return (5, len(rel))
        if "/files/" in rel:
            return (4, len(rel))
        if "/pages/" in rel:
            return (3, len(rel))
        if rel.endswith("/source.md"):
            return (1, len(rel))
        return (2, len(rel))

    if candidate_paths:
        default_artifact = max(candidate_paths, key=candidate_score)

    default_status = "ready_for_review"
    status_match = re.search(r"Статус\s+[—-]\s+`?([^`\n.]+)`?", text)
    if status_match:
        default_status = unwrap_value(status_match.group(1))

    headings = list(re.finditer(r"^###\s+(.+)$", text, flags=re.M))
    statements: list[dict[str, object]] = []

    for index, match in enumerate(headings):
        heading = match.group(1).strip()
        statement_id_match = re.match(r"([A-Z0-9]+-\d{3})(?:\.\s*(.+))?$", heading)
        if not statement_id_match:
            continue
        statement_id = statement_id_match.group(1)
        statement_title = (statement_id_match.group(2) or "").strip()
        body_start = match.end()
        body_end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[body_start:body_end].strip()
        lines = body.splitlines()

        paragraph_lines: list[str] = []
        fields: dict[str, str] = {}
        artifacts: list[str] = []
        current: str | None = None

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                if current in {"status", "assertion", "fragment", "area"}:
                    current = None
                continue

            if line.startswith("- Статус:"):
                current = "status"
                fields[current] = unwrap_value(line.split(":", 1)[1])
                continue
            if line.startswith("- Утверждение:"):
                current = "assertion"
                fields[current] = unwrap_value(line.split(":", 1)[1])
                continue
            if line.startswith("- Фрагмент источника:"):
                current = "fragment"
                fields[current] = unwrap_value(line.split(":", 1)[1])
                continue
            if line.startswith("- Область применения:"):
                current = "area"
                fields[current] = unwrap_value(line.split(":", 1)[1])
                continue
            if line.startswith("- Основание:") or line.startswith("- Опора в артефактах:"):
                current = "artifacts"
                continue
            if line.startswith("  - ") and current == "artifacts":
                artifacts.append(unwrap_value(line[4:]))
                continue
            if current == "artifacts" and artifacts and line.startswith("    "):
                artifacts[-1] = f"{artifacts[-1]} {unwrap_value(stripped)}".strip()
                continue
            if line.startswith("  ") and current in {"status", "assertion", "fragment", "area"}:
                fields[current] = f"{fields[current]} {unwrap_value(stripped)}".strip()
                continue
            if line.startswith("- "):
                current = None
                continue
            if current is None:
                paragraph_lines.append(stripped)

        statement_text = fields.get("assertion") or " ".join(paragraph_lines).strip()
        artifact_path = None
        for artifact in artifacts:
            candidate = ROOT / artifact
            if candidate.exists():
                artifact_path = candidate
                break
        if artifact_path is None:
            artifact_path = default_artifact or path

        statements.append(
            {
                "id": statement_id,
                "source_id": source_id,
                "status": fields.get("status", default_status),
                "text": statement_text,
                "excerpt": fields.get("fragment", statement_title or statement_text),
                "artifact_path": artifact_path,
                "checked_at": checked_at,
                "scope": {
                    "section_title": statement_title,
                    "application": fields.get("area", ""),
                },
                "open_questions": [],
            }
        )

    return checked_at, default_artifact, statements


def map_statement_to_item(
    source_id: str,
    items: list[dict[str, str]],
    artifact_path: Path,
    default_artifact: Path | None = None,
) -> str:
    source_item_id = f"{source_id}-source"
    source_dir = DATA / source_id.lower()
    artifact_resolved = artifact_path.resolve()

    for item in items:
        item_path = item.get("path")
        if not item_path:
            continue
        target_path = (source_dir / item_path).resolve()
        if target_path == artifact_resolved:
            return item["id"]

    parts = artifact_path.parts
    if source_id in parts and "pages" in parts:
        page_index = parts.index("pages")
        page_parts = list(parts[page_index + 1 : -1])
        if page_parts:
            page_slug = "-".join(page_parts)
            candidate = f"{source_id}-{page_slug}"
            if any(item["id"] == candidate for item in items):
                return candidate

    if default_artifact is not None and artifact_resolved == default_artifact.resolve():
        preferred_suffixes = (".txt", ".md", ".epub", ".pdf", ".djvu", ".html")
        for suffix in preferred_suffixes:
            for item in items:
                item_path = item.get("path", "")
                if item["id"] != source_item_id and item_path.endswith(suffix):
                    return item["id"]

    return source_item_id


def build_items_for_source(source_id: str) -> list[dict[str, str]]:
    slug = source_id.lower()
    source_primary = PRIMARY / source_id
    page_index = source_primary / "page-index.tsv"
    access = default_access(source_id)
    stage = stage_for(source_id)
    items: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    items.append(
        {
            "id": item_id_from_raw(source_id, "source", seen_ids, source_primary / "source.md"),
            "source_id": source_id,
            "title": f"{source_id}: обзор источника",
            "access": access,
            "status": "approved",
            "workflow_stage": stage,
            "path": rel_from_data(slug, source_primary / "source.md"),
        }
    )

    if page_index.exists():
        lines = page_index.read_text(encoding="utf-8").splitlines()
        if lines:
            header = lines[0]
            if "\t" in header and header.startswith("id\t"):
                reader = csv.DictReader(lines, delimiter="\t")
                for row in reader:
                    raw_id = row["id"].strip()
                    artifact_field = next(
                        (
                            key
                            for key in (
                                "artifact_path",
                                "html_path",
                                "body_path",
                                "extracted_path",
                            )
                            if (row.get(key) or "").strip()
                        ),
                        None,
                    )
                    artifact_path = None
                    if artifact_field:
                        raw_artifact_path = Path(row[artifact_field].strip())
                        artifact_path = (
                            ROOT / raw_artifact_path
                            if raw_artifact_path.parts[:1] == ("knowledge",)
                            else source_primary / raw_artifact_path
                        )
                    item: dict[str, str] = {
                        "id": item_id_from_raw(source_id, raw_id, seen_ids, artifact_path),
                        "source_id": source_id,
                        "title": page_title(source_id, row),
                        "access": access,
                        "status": "approved",
                        "workflow_stage": stage,
                    }
                    url = (row.get("url") or row.get("source_url") or "").strip()
                    if url:
                        item["url"] = url
                    if artifact_path is not None:
                        item["path"] = rel_from_data(slug, artifact_path)
                    items.append(item)
                return items

            if header.startswith("https://"):
                for line in lines:
                    url, raw_id, title = line.split("\t", 2)
                    artifact_path = source_primary / "pages" / raw_id / "index.html"
                    items.append(
                        {
                            "id": item_id_from_raw(
                                source_id, raw_id, seen_ids, artifact_path
                            ),
                            "source_id": source_id,
                            "title": html.unescape(title.strip()),
                            "url": url.strip(),
                            "access": access,
                            "status": "approved",
                            "workflow_stage": stage,
                            "path": rel_from_data(slug, artifact_path),
                        }
                    )
                return items

    pages_dir = source_primary / "pages"
    if pages_dir.exists():
        for page in sorted(p for p in pages_dir.rglob("index.html")):
            rel_page = page.relative_to(pages_dir).parent.as_posix()
            items.append(
                {
                    "id": item_id_from_raw(source_id, rel_page, seen_ids, page),
                    "source_id": source_id,
                    "title": f"{source_id}: {rel_page}",
                    "access": access,
                    "status": "approved",
                    "workflow_stage": stage,
                    "path": rel_from_data(slug, page),
                }
            )
        if items:
            return items

    return items


def ensure_statement_artifact_items(
    source_id: str,
    items: list[dict[str, str]],
    statements: list[dict[str, object]],
) -> list[dict[str, str]]:
    slug = source_id.lower()
    source_dir = DATA / slug
    seen_ids = {item["id"] for item in items}
    known_targets = {}
    for item in items:
        item_path = item.get("path")
        if item_path:
            known_targets[(source_dir / item_path).resolve()] = item["id"]

    extra_items: list[dict[str, str]] = []
    for statement in statements:
        artifact_path = Path(statement["artifact_path"]).resolve()
        if artifact_path in known_targets:
            continue
        try:
            rel = artifact_path.relative_to(ROOT).as_posix()
        except ValueError:
            continue

        if not rel.startswith("knowledge/"):
            continue

        raw_id = rel.removeprefix("knowledge/").replace("/", "-")
        item_id = item_id_from_raw(source_id, raw_id, seen_ids, artifact_path)
        title = f"{source_id}: {artifact_path.name or artifact_path.parent.name}"
        extra_items.append(
            {
                "id": item_id,
                "source_id": source_id,
                "title": title,
                "access": default_access(source_id),
                "status": "approved",
                "workflow_stage": stage_for(source_id),
                "path": rel_from_data(slug, artifact_path),
            }
        )
        known_targets[artifact_path] = item_id

    return items + extra_items


def write_yaml(path: Path, payload: object) -> None:
    text = yaml.safe_dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        width=80,
    )
    path.write_text(text, encoding="utf-8")


def materialize_units(
    source_dir: Path,
    source_id: str,
    items: list[dict[str, str]],
    statements_checked_at: str,
    default_artifact: Path | None,
    source_statements: list[dict[str, object]],
) -> None:
    units_root = source_dir / "items"
    shutil.rmtree(units_root, ignore_errors=True)
    units_root.mkdir(parents=True, exist_ok=True)

    statements_by_item: dict[str, list[dict[str, object]]] = {}
    for statement in source_statements:
        item_id = map_statement_to_item(
            source_id,
            items,
            Path(statement["artifact_path"]),
            default_artifact,
        )
        statements_by_item.setdefault(item_id, []).append(statement)

    for item in items:
        unit_dir = units_root / unit_slug(item["id"], source_id)
        unit_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "id": item["id"],
            "source_id": source_id,
            "title": item["title"],
            "access": item["access"],
            "status": item["status"],
            "workflow_stage": item["workflow_stage"],
        }
        if "url" in item:
            payload["url"] = item["url"]
        if "path" in item:
            tracked_path = (source_dir / item["path"]).resolve()
            payload["files"] = {
                "tracked": [Path(os.path.relpath(tracked_path, start=unit_dir)).as_posix()]
        }
        write_yaml(unit_dir / "item.yml", payload)

        unit_statements = statements_by_item.get(item["id"])
        if not unit_statements:
            continue

        statements_payload = {"statements": []}
        for statement in unit_statements:
            artifact_path = Path(statement["artifact_path"])
            statements_payload["statements"].append(
                {
                    "id": statement["id"],
                    "source_id": source_id,
                    "item_id": item["id"],
                    "status": statement["status"],
                    "text": statement["text"],
                    "excerpt": statement["excerpt"],
                    "artifact": Path(
                        os.path.relpath(artifact_path, start=unit_dir)
                    ).as_posix(),
                    "checked_at": statements_checked_at,
                    "scope": statement["scope"],
                    "open_questions": statement["open_questions"],
                }
            )
        write_yaml(unit_dir / "statements.yml", statements_payload)


def main() -> int:
    INDEX.mkdir(parents=True, exist_ok=True)
    global_items: list[dict[str, str]] = []

    for source_dir in sorted(p for p in DATA.iterdir() if p.is_dir()):
        source_card = yaml.safe_load((source_dir / "source.yml").read_text(encoding="utf-8"))
        source_id = source_card["id"]
        statements_checked_at, default_artifact, source_statements = parse_statements_file(
            source_id
        )
        items = build_items_for_source(source_id)
        items = ensure_statement_artifact_items(source_id, items, source_statements)
        write_yaml(source_dir / "items.yml", {"items": items})
        materialize_units(
            source_dir,
            source_id,
            items,
            statements_checked_at,
            default_artifact,
            source_statements,
        )

        for item in items:
            global_item = {
                "id": item["id"],
                "source_id": source_id,
                "title": item["title"],
                "workflow_stage": item["workflow_stage"],
                "access": item["access"],
            }
            if "path" in item:
                global_item["path"] = (
                    source_dir / item["path"]
                ).relative_to(KNOWLEDGE).as_posix()
            global_items.append(global_item)

    write_yaml(INDEX / "items.yml", {"items": global_items})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
