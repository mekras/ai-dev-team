#!/usr/bin/env python3
"""Создаёт сырые расшифровки для локальных медиа из очереди корпуса."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml


MEDIA_SUFFIXES = {".aac", ".flac", ".m4a", ".mkv", ".mov", ".mp3", ".mp4", ".ogg", ".wav", ".webm"}


def media_file(directory: Path) -> Path | None:
    files = sorted(path for path in directory.iterdir() if path.suffix.lower() in MEDIA_SUFFIXES)
    return files[0] if len(files) == 1 else None


def transcribe(source_file: Path, whisper: str, validator: Path) -> int:
    card = yaml.safe_load(source_file.read_text(encoding="utf-8"))
    if not isinstance(card, dict):
        raise ValueError("карточка источника должна быть YAML-словарём")
    count = 0
    for item in card.get("items", []):
        if not isinstance(item, dict) or item.get("workflow_stage") != "needs_transcript":
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("карточка единицы не задаёт path")
        directory = source_file.parent / path
        transcript = directory / "transcript.txt"
        if transcript.is_file() and transcript.stat().st_size > 0:
            continue
        media = media_file(directory)
        if media is None:
            raise ValueError("единице в очереди нужна ровно одна локальная медиа-запись")
        completed = subprocess.run(
            [whisper, "--model", "turbo", "--output_format", "txt", "--output_dir", str(directory), str(media)],
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(f"whisper завершился с кодом {completed.returncode}")
        produced = directory / f"{media.stem}.txt"
        if not produced.is_file() or produced.stat().st_size == 0:
            raise RuntimeError("whisper не создал непустую расшифровку")
        produced.replace(transcript)
        subprocess.run(["python3", str(validator), str(directory)], check=True)
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", default="knowledge")
    parser.add_argument("--whisper", default="whisper")
    parser.add_argument(
        "--validator",
        default=".agents/skills/kc-transcription/scripts/validate-transcription-result.py",
    )
    args = parser.parse_args(argv)
    count = sum(
        transcribe(path, args.whisper, Path(args.validator))
        for path in sorted(Path(args.corpus_root).glob("data/*/source.yml"))
    )
    print(f"Создано расшифровок: {count}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
