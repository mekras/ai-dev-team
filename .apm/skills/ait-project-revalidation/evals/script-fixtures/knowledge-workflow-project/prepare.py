#!/usr/bin/env python3
"""Готовит состояние через публичный CLI для сценариев проверки корпуса."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


script = sys.argv[1]
repo = Path(sys.argv[2])


def call(*arguments: str) -> None:
    subprocess.run(
        [sys.executable, script, *arguments, "--repo", str(repo)],
        check=True,
        cwd=repo,
    )


shutil.move(
    repo / ".agents/skills/ait-docs-concept/SKILL.md.fixture",
    repo / ".agents/skills/ait-docs-concept/SKILL.md",
)
subprocess.run(["git", "init", str(repo)], check=True)
subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
subprocess.run(
    [
        "git", "-C", str(repo), "-c", "user.email=contract@example.invalid",
        "-c", "user.name=Contract", "commit", "-m", "init",
    ],
    check=True,
)
call("init", "--mode", "manual")
call(
    "record-concept", "--result", "found", "--instructions", "AGENTS.md",
    "--concept", "docs/concept.md", "--evidence", "AGENTS.md указывает концепцию",
)
call(
    "classify", "--id", "rule:AGENTS", "--participation", "not_applicable",
    "--applicable", "no", "--reason", "Правило не является отдельной проверкой",
)
call(
    "start-application", "--id", "concept-check", "--stage", "requirements",
    "--capability", "skill:ait-docs-concept", "--method", "review",
    "--surface", "docs/concept.md", "--action", "Проверить концепцию",
    "--priority-rationale", "Концепция задаёт основание проверки",
    "--subject", "docs/concept.md",
)
for criterion, note in (
    ("problem-goal-method-result", "Четыре элемента согласованы"),
    ("essential-frames", "Рамки не противоречат замыслу"),
    ("meaning-and-modality", "Смысловых противоречий нет"),
):
    call(
        "record-observation", "--application", "concept-check",
        "--artifact", "docs/concept.md", "--start-line", "1", "--end-line", "3",
        "--criterion-id", criterion, "--result", "supports", "--note", note,
    )
call(
    "finish-application", "--application", "concept-check", "--outcome", "passed",
    "--decision", "accept", "--evidence", "observation-001", "--evidence",
    "observation-002", "--evidence", "observation-003", "--artifact",
    "docs/concept.md", "--coverage", "Критерии проверены по концепции",
    "--claim", "Концепция содержит основание проекта", "--claim-support",
    "observation-001", "--challenge", "Есть ли скрытое противоречие",
    "--challenge-outcome", "refuted", "--challenge-support", "observation-001",
)
mode = sys.argv[3] if len(sys.argv) > 3 else None
if mode in {"knowledge", "technical", "semantic", "complete"}:
    call(
        "record-knowledge", "--result", "found", "--root", "knowledge",
        "--evidence", "Корпус находится в knowledge",
    )
if mode in {"technical", "semantic", "complete"}:
    call(
        "start-application", "--id", "knowledge-technical", "--stage",
        "repository", "--capability", "skill:kc-validation", "--method",
        "validation", "--surface", "knowledge/index.md", "--action",
        "Проверить структуру корпуса", "--priority-rationale",
        "Корпус обязателен после концепции", "--knowledge-phase", "technical",
        "--subject-index", "knowledge/index.md",
    )
    for artifact, end_line, note in (
        ("knowledge/index.md", "3", "Индекс ссылается на доступное утверждение."),
        ("knowledge/statement.md", "3", "Утверждение доступно из индекса."),
    ):
        call(
            "record-observation", "--application", "knowledge-technical",
            "--artifact", artifact, "--start-line", "1", "--end-line", end_line,
            "--criterion-id", "corpus-admission", "--criterion",
            "Материал корпуса доступен для проверки.", "--result", "supports",
            "--note", note,
        )
    call(
        "finish-application", "--application", "knowledge-technical", "--outcome",
        "passed", "--decision", "accept", "--evidence", "technical-evidence",
        "--artifact", "knowledge/index.md", "--artifact", "knowledge/statement.md",
        "--coverage", "Корпус проверен", "--claim", "Корпус структурно пригоден",
        "--claim-support", "observation-001", "--challenge",
        "Есть ли недоступный материал корпуса", "--challenge-outcome", "refuted",
        "--challenge-support", "observation-001", "--command", "true",
    )
if mode in {"semantic", "complete"}:
    call(
        "start-application", "--id", "knowledge-semantic", "--stage",
        "repository", "--capability", "skill:kc-validation", "--method", "review",
        "--surface", "knowledge/index.md", "--action", "Проверить смысл корпуса",
        "--priority-rationale", "Смысл корпуса определяет основания решений",
        "--knowledge-phase", "semantic", "--subject-index", "knowledge/index.md",
    )
    for artifact, criterion, note in (
        ("knowledge/index.md", "source-concept-fit", "Индекс раскрывает состав корпуса."),
        ("knowledge/statement.md", "statement-consistency", "Утверждение относится к корпусу."),
        ("knowledge/index.md", "coverage-gaps", "Ограничения охвата названы."),
        ("knowledge/index.md", "decision-value", "Утверждение пригодно для решения."),
    ):
        call(
            "record-observation", "--application", "knowledge-semantic",
            "--artifact", artifact, "--start-line", "1", "--end-line", "3",
            "--criterion-id", criterion, "--result", "supports",
            "--note", note,
        )
    call(
        "finish-application", "--application", "knowledge-semantic", "--outcome",
        "passed", "--decision", "accept", "--evidence", "semantic-evidence",
        "--artifact", "knowledge/index.md", "--artifact", "knowledge/statement.md",
        "--coverage", "Смысл корпуса проверен", "--claim",
        "Корпус содержит проверяемое утверждение", "--claim-support",
        "observation-001", "--challenge", "Есть ли разрыв между индексом и утверждением",
        "--challenge-outcome", "refuted", "--challenge-support", "observation-001",
    )
if mode == "complete":
    call(
        "start-application", "--id", "requirements-check", "--stage",
        "requirements", "--capability", "skill:ait-req-revalidation", "--method",
        "review", "--surface", "docs/concept.md", "--action",
        "Проверить требования", "--priority-rationale",
        "Требования определяют последующую работу", "--subject-pattern", "docs/*.md",
    )
    for criterion, note in (
        ("level-and-solution-boundary", "Уровень зафиксирован."),
        ("source-and-necessity", "Основание связано с концепцией."),
        ("clarity-and-verifiability", "Формулировка проверяема."),
        ("set-consistency-and-traceability", "Связь с концепцией сохранена."),
    ):
        call(
            "record-observation", "--application", "requirements-check",
            "--artifact", "docs/concept.md", "--start-line", "1", "--end-line", "3",
            "--criterion-id", criterion, "--result", "supports", "--note", note,
        )
    call(
        "finish-application", "--application", "requirements-check", "--outcome",
        "passed", "--decision", "accept", "--evidence", "requirements-evidence",
        "--artifact", "docs/concept.md", "--coverage", "Требования проверены",
        "--claim", "Требования согласованы с концепцией", "--claim-support",
        "observation-001", "--challenge", "Есть ли разрыв с концепцией",
        "--challenge-outcome", "refuted", "--challenge-support", "observation-001",
    )
    for stage in ("repository", "requirements", "design", "code", "tests", "assurance", "impact"):
        call("stage", "--name", stage, "--status", "running")
        call("stage", "--name", stage, "--status", "complete")
