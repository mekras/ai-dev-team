#!/usr/bin/env python3
"""Получает явно разрешённые фрагменты из очереди корпуса знаний."""

from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import yaml


MAX_FRAGMENT_BYTES = 5 * 1024 * 1024
ALLOWED_COPY_POLICIES = {"fragments_only", "metadata_only"}


def eligible(item: dict[str, object]) -> bool:
    stage = item.get("workflow_stage")
    return stage == "needs_fetch" or (
        stage == "indexed"
        and item.get("processing_scope")
        in {"selected_fragments", "full", "full_redacted"}
    )


def item_directory(source_dir: Path, item: dict[str, object]) -> Path:
    path = item.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("карточка единицы не задаёт path")
    directory = (source_dir / path).resolve()
    if source_dir.resolve() not in directory.parents:
        raise ValueError("path единицы выходит за пределы источника")
    return directory


def download_fragment(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("fetch_url должен быть публичным HTTP(S)-адресом")

    request = urllib.request.Request(url, headers={"User-Agent": "ai-dev-team-corpus/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        length = response.headers.get("Content-Length")
        if length is not None and int(length) > MAX_FRAGMENT_BYTES:
            raise ValueError("фрагмент превышает разрешённый размер 5 МиБ")
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            try:
                shutil.copyfileobj(response, handle, length=64 * 1024)
                if handle.tell() > MAX_FRAGMENT_BYTES:
                    raise ValueError("фрагмент превышает разрешённый размер 5 МиБ")
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
    temporary.replace(destination)


def fetch_source(source_file: Path) -> int:
    card = yaml.safe_load(source_file.read_text(encoding="utf-8"))
    if not isinstance(card, dict):
        raise ValueError("карточка источника должна быть YAML-словарём")
    policy = card.get("copy_policy")
    if policy not in ALLOWED_COPY_POLICIES:
        return 0
    items = card.get("items", [])
    if not isinstance(items, list):
        raise ValueError("поле items должно быть списком")

    changed = False
    for item in items:
        if not isinstance(item, dict) or not eligible(item):
            continue
        url = item.get("fetch_url")
        if not isinstance(url, str) or not url:
            raise ValueError(
                "выбранная единица должна задавать fetch_url для точечного получения"
            )
        directory = item_directory(source_file.parent, item)
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / "fragment.html"
        download_fragment(url, destination)
        item["workflow_stage"] = "fetched"
        changed = True

    if changed:
        source_file.write_text(
            yaml.safe_dump(card, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    return int(changed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", default="knowledge")
    args = parser.parse_args(argv)
    root = Path(args.corpus_root)
    changed = sum(fetch_source(path) for path in sorted(root.glob("data/*/source.yml")))
    print(f"Получено фрагментов: {changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
