#!/usr/bin/env python3
"""Проверить доступность внешних адресов источников корпуса знаний.

Паспорт источника хранит публичные адреса в полях `url`, `locator` и
`public_reference`. Скрипт обращается к каждому такому адресу по одному разу и
фиксирует код ответа, переадресацию и недоступность. Массовая выгрузка
содержимого не выполняется: тело ответа не сохраняется.

Скрипт ничего не меняет в корпусе. Отчёт описывает конкретный запуск и
записывается вне Git.
"""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
DEFAULT_REPORT = (
    ROOT / ".ai-dev-team" / "local" / "reports" / "corpus-source-check.md"
)

LOCATOR_FIELDS = ("url", "locator", "public_reference")
USER_AGENT = "ai-dev-team-corpus-source-check/1"
STALE_AFTER_DAYS = 180


class Target:
    def __init__(self, source_id: str, slug: str, field: str, url: str) -> None:
        self.source_id = source_id
        self.slug = slug
        self.field = field
        self.url = url
        self.state = "unknown"
        self.detail = ""

    @property
    def label(self) -> str:
        return f"{self.source_id} ({self.field})"


def collect_targets(data_dir: Path) -> tuple[list[Target], list[str]]:
    targets: list[Target] = []
    skipped: list[str] = []

    for source_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        card_path = source_dir / "source.yml"
        if not card_path.exists():
            skipped.append(f"{source_dir.name}: нет паспорта источника source.yml")
            continue
        card = yaml.safe_load(card_path.read_text(encoding="utf-8")) or {}
        source_id = str(card.get("id") or source_dir.name.upper())
        slug = str(card.get("slug") or source_dir.name)

        seen: set[str] = set()
        network_found = False
        for field in LOCATOR_FIELDS:
            value = card.get(field)
            if not isinstance(value, str):
                continue
            if not value.startswith(("http://", "https://")):
                continue
            network_found = True
            if value in seen:
                continue
            seen.add(value)
            targets.append(Target(source_id, slug, field, value))

        if not network_found:
            skipped.append(f"{source_id}: нет публичного сетевого адреса")

    return targets, skipped


def check(target: Target, timeout: float) -> Target:
    request = urllib.request.Request(
        target.url,
        method="HEAD",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            target.state = "ok"
            target.detail = f"код {response.status}"
            if response.url != target.url:
                target.state = "redirect"
                target.detail = f"код {response.status}, переадресация на {response.url}"
    except urllib.error.HTTPError as error:
        if error.code in (403, 405, 429, 501):
            return check_with_get(target, timeout)
        target.state = "failed"
        target.detail = f"код {error.code}"
    except urllib.error.URLError as error:
        target.state = "unreachable"
        target.detail = f"нет соединения: {error.reason}"
    except (TimeoutError, OSError) as error:
        target.state = "unreachable"
        target.detail = f"ошибка обращения: {error}"
    return target


def check_with_get(target: Target, timeout: float) -> Target:
    request = urllib.request.Request(
        target.url,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)
            target.state = "ok"
            target.detail = f"код {response.status}"
            if response.url != target.url:
                target.state = "redirect"
                target.detail = f"код {response.status}, переадресация на {response.url}"
    except urllib.error.HTTPError as error:
        if error.code in (403, 429):
            target.state = "restricted"
            target.detail = (
                f"код {error.code}: адрес отвечает, но отказывает автоматическому "
                "обращению; проверять вручную"
            )
        else:
            target.state = "failed"
            target.detail = f"код {error.code}"
    except urllib.error.URLError as error:
        target.state = "unreachable"
        target.detail = f"нет соединения: {error.reason}"
    except (TimeoutError, OSError) as error:
        target.state = "unreachable"
        target.detail = f"ошибка обращения: {error}"
    return target


def stale_sources(data_dir: Path, today: date) -> list[str]:
    stale: list[str] = []
    for source_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        card_path = source_dir / "source.yml"
        if not card_path.exists():
            continue
        card = yaml.safe_load(card_path.read_text(encoding="utf-8")) or {}
        checked = card.get("last_checked_at")
        if isinstance(checked, str):
            try:
                checked = date.fromisoformat(checked)
            except ValueError:
                continue
        if not isinstance(checked, date):
            continue
        age = (today - checked).days
        if age > STALE_AFTER_DAYS:
            stale.append(f"{card.get('id', source_dir.name)}: проверен {age} дн. назад")
    return stale


def render_report(
    targets: list[Target],
    skipped: list[str],
    stale: list[str],
    today: date,
) -> str:
    groups: dict[str, list[Target]] = {}
    for target in targets:
        groups.setdefault(target.state, []).append(target)

    titles = {
        "failed": "Отвечают ошибкой",
        "unreachable": "Недоступны",
        "restricted": "Отказывают автоматическому обращению",
        "redirect": "Отвечают переадресацией",
        "ok": "Доступны",
        "unknown": "Не проверены",
    }

    lines = [
        "# Проверка адресов источников корпуса знаний",
        "",
        f"Дата запуска: {today.isoformat()}.",
        f"Проверено адресов: {len(targets)}.",
        "",
    ]

    for state in ("failed", "unreachable", "restricted", "redirect", "ok", "unknown"):
        group = groups.get(state)
        if not group:
            continue
        lines.append(f"## {titles[state]} ({len(group)})")
        lines.append("")
        for target in sorted(group, key=lambda item: item.source_id):
            lines.append(f"- {target.label}: {target.url} — {target.detail}")
        lines.append("")

    if stale:
        lines.append(f"## Давно не проверялись вручную ({len(stale)})")
        lines.append("")
        lines.extend(f"- {entry}" for entry in stale)
        lines.append("")

    if skipped:
        lines.append(f"## Без сетевого адреса ({len(skipped)})")
        lines.append("")
        lines.extend(f"- {entry}" for entry in skipped)
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Проверить доступность внешних адресов источников корпуса.",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=KNOWLEDGE,
        help="корень корпуса знаний (по умолчанию knowledge)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="путь отчёта о запуске (по умолчанию .ai-dev-team/local/reports)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="таймаут одного обращения в секундах",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="число одновременных обращений",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="только показать проверяемые адреса, без обращений к сети",
    )
    args = parser.parse_args(argv)

    data_dir = args.corpus_root / "data"
    if not data_dir.is_dir():
        print(f"ERROR: не найден отслеживаемый слой данных корпуса: {data_dir}")
        return 2

    targets, skipped = collect_targets(data_dir)

    if args.list:
        for target in targets:
            print(f"{target.label}\t{target.url}")
        print(f"Всего адресов: {len(targets)}; источников без адреса: {len(skipped)}.")
        return 0

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        targets = list(pool.map(lambda item: check(item, args.timeout), targets))

    today = date.today()
    report = render_report(targets, skipped, stale_sources(data_dir, today), today)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")

    broken = [t for t in targets if t.state in ("failed", "unreachable")]
    restricted = [t for t in targets if t.state == "restricted"]
    redirected = [t for t in targets if t.state == "redirect"]
    print(
        f"Проверка источников: {len(targets)} адресов, "
        f"недоступных {len(broken)}, с отказом автоматическому обращению "
        f"{len(restricted)}, с переадресацией {len(redirected)}."
    )
    print(f"Отчёт: {args.report}")

    for target in broken:
        print(f"ERROR: {target.label}: {target.url} — {target.detail}")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
