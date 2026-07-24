#!/usr/bin/env python3
"""Регрессионные проверки средств оценки доступности знаний."""

from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / ".apm" / "skills" / "kc-retrieval-evaluation" / "scripts"
VALIDATOR = SCRIPTS / "validate-evaluation-suite.py"
SAMPLER = SCRIPTS / "sample-source-sections.py"
RUNNER = SCRIPTS / "run-evaluation-suite.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8")


def run(*command: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd or REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def source_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_corpus(root: Path) -> str:
    artifact = root / "data" / "example" / "documents" / "guide" / "normalized.md"
    write_text(
        artifact,
        """
        # Введение

        Этот раздел содержит только вводные сведения.

        # Правило обновления

        После изменения договора нужно повторно проверить зависящие документы.
        Проверка относится только к документам, которые используют изменённый договор.

        # Другой раздел

        Здесь описано другое самостоятельное правило.
        """,
    )
    write_text(
        root / "data" / "example" / "documents" / "guide" / "statements.yml",
        """
        statements:
          - id: EX-001
            text: "После изменения договора нужно перепроверить зависящие документы."
        """,
    )
    lines = artifact.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[4:8])


def approved_suite(evidence: str) -> dict:
    return {
        "suite_version": 1,
        "id": "example-suite",
        "description": "Проверка правила обновления.",
        "cases": [
            {
                "id": "example-001",
                "status": "approved",
                "source": {
                    "artifact": "data/example/documents/guide/normalized.md",
                    "line_start": 5,
                    "line_end": 8,
                    "sha256": source_digest(evidence),
                },
                "target": {
                    "text": (
                        "После изменения договора нужно повторно проверить "
                        "зависящие документы."
                    ),
                    "importance_class": "rule",
                    "importance_rationale": "Правило определяет порядок сопровождения.",
                    "limitations": [
                        "Требование относится только к зависящим документам."
                    ],
                },
                "acceptable_answers": [
                    "Перепроверить документы, которые зависят от договора."
                ],
                "must_not_claim": ["Переписать все документы проекта."],
                "corpus_expectation": {
                    "representation": "present",
                    "statement_ids": ["EX-001"],
                },
                "questions": [
                    {
                        "id": "example-001-direct",
                        "type": "direct",
                        "text": "Что сделать после изменения договора?",
                    },
                    {
                        "id": "example-001-paraphrase",
                        "type": "paraphrase",
                        "text": (
                            "Как поступить со связанными материалами после "
                            "пересмотра соглашения?"
                        ),
                    },
                ],
                "provenance": {"target_author": "author/session-1"},
                "review": {
                    "target_entailment": "confirmed",
                    "target_reviewer": "reviewer/session-2",
                    "question_answerability": "confirmed",
                    "question_reviewer": "question-reviewer/session-3",
                },
                "access_review": {
                    "source_evidence_to_judge": "approved",
                    "reviewed_by": "owner/session-4",
                    "rationale": "Тестовый публичный фрагмент разрешён.",
                },
            }
        ],
    }


def write_mock_adapter(path: Path) -> None:
    write_text(
        path,
        r'''
        #!/usr/bin/env python3
        import json
        import os
        import sys

        _model = sys.argv[1]
        prompt = sys.stdin.read()
        access = os.environ.get("KC_EVALUATION_ACCESS")
        assert os.environ.get("KC_EVALUATION_READ_ONLY") == "1"

        if access == "statements":
            assert not any(path.name == "normalized.md" for path in __import__("pathlib").Path.cwd().rglob("*"))
            result = {
                "representation": "present",
                "statement_ids": ["EX-001"],
                "paths": ["data/example/documents/guide/statements.yml"],
                "rationale": "Целевой смысл представлен.",
            }
        elif access == "corpus":
            result = {
                "answer": "Нужно перепроверить зависящие документы.",
                "abstained": False,
                "evidence": [{
                    "path": "data/example/documents/guide/statements.yml",
                    "statement_id": "EX-001",
                    "locator": "EX-001",
                }],
            }
        elif access == "closed_book":
            result = {
                "answer": "Без корпуса ответ неизвестен.",
                "abstained": True,
                "evidence": [],
            }
        elif access == "judge":
            passed = "Нужно перепроверить зависящие документы." in prompt
            result = {
                "correctness": "pass" if passed else "fail",
                "groundedness": "pass" if passed else "fail",
                "target_expressed": passed,
                "forbidden_claim_detected": False,
                "rationale": "Сравнение с опорным фрагментом.",
            }
        else:
            raise SystemExit("unsupported access mode")

        print(json.dumps(result, ensure_ascii=False))
        ''',
    )
    path.chmod(0o755)


def assert_validator_and_hashes(root: Path, suite_path: Path, suite: dict) -> None:
    suite_path.write_text(
        yaml.safe_dump(suite, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    result = run(
        sys.executable,
        str(VALIDATOR),
        str(suite_path),
        "--corpus-root",
        str(root),
    )
    if result.returncode != 0:
        raise AssertionError(f"ожидалось прохождение проверки:\n{result.stdout}")

    suite["cases"][0]["source"]["sha256"] = "0" * 64
    suite_path.write_text(
        yaml.safe_dump(suite, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    result = run(
        sys.executable,
        str(VALIDATOR),
        str(suite_path),
        "--corpus-root",
        str(root),
    )
    if result.returncode == 0 or "source.sha256" not in result.stdout:
        raise AssertionError(f"не выявлен изменённый источник:\n{result.stdout}")


def assert_independent_review(root: Path, suite_path: Path, evidence: str) -> None:
    suite = approved_suite(evidence)
    suite["cases"][0]["review"]["target_reviewer"] = "author/session-1"
    suite_path.write_text(
        yaml.safe_dump(suite, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    result = run(
        sys.executable,
        str(VALIDATOR),
        str(suite_path),
        "--corpus-root",
        str(root),
    )
    if (
        result.returncode == 0
        or "target author and target reviewer must differ" not in result.stdout
    ):
        raise AssertionError(f"не выявлено отсутствие независимой проверки:\n{result.stdout}")


def assert_sampler(root: Path, output: Path) -> None:
    command = (
        sys.executable,
        str(SAMPLER),
        str(root),
        "--source",
        "data/example/documents/guide/normalized.md",
        "--count",
        "2",
        "--seed",
        "17",
        "--suite-id",
        "sample-suite",
        "--output",
        str(output),
    )
    first = run(*command)
    if first.returncode != 0:
        raise AssertionError(f"выборка не создана:\n{first.stdout}")
    first_text = output.read_text(encoding="utf-8")
    second = run(*command, "--force")
    if second.returncode != 0 or output.read_text(encoding="utf-8") != first_text:
        raise AssertionError("выборка с одинаковым seed не воспроизводится")
    sampled = yaml.safe_load(first_text)
    if len(sampled["cases"]) != 2:
        raise AssertionError("создано неправильное число кандидатов")
    if any(case["status"] != "candidate" for case in sampled["cases"]):
        raise AssertionError("выборка должна создавать только кандидаты")


def assert_runner(root: Path, suite_path: Path, evidence: str, temp: Path) -> None:
    suite = approved_suite(evidence)
    suite_path.write_text(
        yaml.safe_dump(suite, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    adapter = temp / "mock-adapter"
    write_mock_adapter(adapter)
    config = temp / "config.local.yml"
    write_text(
        config,
        f"""
        adapters:
          mock: "{adapter}"
        models:
          inspector: mock:inspector
          answerer: mock:answerer
          judge: mock:judge
        timeout: 30
        closed_book: true
        permissions:
          corpus_access_approved: true
          source_evidence_to_judge_approved: true
        """,
    )
    output = temp / "results.local.json"
    result = run(
        sys.executable,
        str(RUNNER),
        str(suite_path),
        "--config",
        str(config),
        "--corpus-root",
        str(root),
        "--output",
        str(output),
    )
    if result.returncode != 0:
        raise AssertionError(f"модельный прогон не завершён:\n{result.stdout}")
    report = json.loads(output.read_text(encoding="utf-8"))
    summary = report["summary"]
    assert summary["representation"] == {"present": 1}
    assert summary["corpus_correctness"] == {"pass": 2}
    assert summary["closed_book_correctness"] == {"fail": 2}
    assert summary["corpus_lift"] == 1.0
    assert summary["paired_questions"] == 2
    assert summary["evidence_self_reported"]["rate"] == 1.0

    denied_config = temp / "denied-config.local.yml"
    denied_text = config.read_text(encoding="utf-8").replace(
        "corpus_access_approved: true",
        "corpus_access_approved: false",
    )
    denied_config.write_text(denied_text, encoding="utf-8")
    denied_output = temp / "denied.local.json"
    denied = run(
        sys.executable,
        str(RUNNER),
        str(suite_path),
        "--config",
        str(denied_config),
        "--corpus-root",
        str(root),
        "--output",
        str(denied_output),
    )
    if (
        denied.returncode == 0
        or "permissions.corpus_access_approved должен быть true" not in denied.stdout
    ):
        raise AssertionError("прогон не остановлен без разрешения доступа")

    inside_suite = root / "leaking-suite.local.yml"
    inside_suite.write_text(suite_path.read_text(encoding="utf-8"), encoding="utf-8")
    leaking_output = temp / "leaking.local.json"
    leaking = run(
        sys.executable,
        str(RUNNER),
        str(inside_suite),
        "--config",
        str(config),
        "--corpus-root",
        str(root),
        "--output",
        str(leaking_output),
    )
    if leaking.returncode == 0 or "должен находиться вне корня корпуса" not in leaking.stdout:
        raise AssertionError("прогон не остановлен при доступном модели эталоне")


def assert_report_contracts(root: Path) -> None:
    sys.path.insert(0, str(SCRIPTS))
    try:
        runner = runpy.run_path(str(RUNNER))
    finally:
        sys.path.pop(0)

    corpus_prompt = runner["answer_prompt"]("Вопрос?", corpus_access=True)
    closed_book_prompt = runner["answer_prompt"]("Вопрос?", corpus_access=False)
    judge_contract_prompt = runner["judge_prompt"](
        {"target": {}, "acceptable_answers": [], "must_not_claim": []},
        {"text": "Вопрос?"},
        {"answer": "Ответ.", "evidence": []},
        "Опорный фрагмент.",
    )
    assert "locator вида lines:N-M" in corpus_prompt
    assert '"evidence": []' in closed_book_prompt
    assert '"path":' not in closed_book_prompt
    assert "target_expressed равно false" in judge_contract_prompt
    assert "correctness и groundedness должны быть" in judge_contract_prompt

    statements_root = root / "statements-only"
    write_text(
        statements_root / "data" / "example" / "statements.yml",
        """
        statements:
          - id: EX-001
            text: "Проверяемое утверждение."
        """,
    )
    runner["validate_inspection"](
        {
            "representation": "present",
            "statement_ids": ["EX-001"],
            "paths": ["data/example/statements.yml"],
            "rationale": "Смысл представлен.",
        },
        statements_root,
    )
    for bad_inspection in (
        {
            "representation": "present",
            "statement_ids": [],
            "paths": [],
            "rationale": "Пустой самоотчёт.",
        },
        {
            "representation": "present",
            "statement_ids": ["MISSING-001"],
            "paths": ["data/example/statements.yml"],
            "rationale": "Вымышленный идентификатор.",
        },
    ):
        try:
            runner["validate_inspection"](bad_inspection, statements_root)
        except ValueError:
            pass
        else:
            raise AssertionError("принят недоказанный инспекторский вердикт")

    try:
        runner["validate_answer"](
            {
                "answer": "Ответ.",
                "abstained": False,
                "evidence": [{"path": "", "statement_id": "", "locator": ""}],
            },
            corpus_root=root,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("принят пустой объект основания")

    write_text(
        root / "data" / "example" / "statements.yml",
        """
        statements:
          - id: EX-001
            text: "Проверяемое утверждение."
        """,
    )
    try:
        runner["validate_answer"](
            {
                "answer": "Ответ.",
                "abstained": False,
                "evidence": [
                    {
                        "path": "data/example/statements.yml",
                        "statement_id": "",
                        "locator": "произвольное место",
                    }
                ],
            },
            corpus_root=root,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("принят statements.yml без statement_id")

    evidence_file = root / "data" / "example" / "normalized.md"
    write_text(
        evidence_file,
        """
        # Раздел

        Проверяемое утверждение.
        """,
    )
    runner["validate_answer"](
        {
            "answer": "Ответ.",
            "abstained": False,
            "evidence": [
                {
                    "path": "data/example/normalized.md",
                    "statement_id": "",
                    "locator": "lines:1-3",
                }
            ],
        },
        corpus_root=root,
    )
    try:
        runner["validate_answer"](
            {
                "answer": "Ответ.",
                "abstained": False,
                "evidence": [
                    {
                        "path": "data/example/normalized.md",
                        "statement_id": "",
                        "locator": "выдуманный раздел",
                    }
                ],
            },
            corpus_root=root,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("принят непроверяемый locator основания")

    try:
        runner["validate_judgement"](
            {
                "correctness": "pass",
                "groundedness": "pass",
                "target_expressed": False,
                "forbidden_claim_detected": True,
            }
        )
    except ValueError:
        pass
    else:
        raise AssertionError("принят противоречивый вердикт судьи")

    asymmetric_results = [
        {
            "id": "case-1",
            "importance_class": "rule",
            "expected_representation": "unknown",
            "inspection": None,
            "errors": [],
            "questions": [
                {
                    "id": "q-corpus",
                    "type": "direct",
                    "errors": ["closed_book: transport"],
                    "corpus": {
                        "answer": {"evidence": []},
                        "judgement": {"correctness": "pass", "groundedness": "pass"},
                    },
                    "closed_book": None,
                },
                {
                    "id": "q-closed",
                    "type": "paraphrase",
                    "errors": ["corpus: transport"],
                    "corpus": None,
                    "closed_book": {
                        "answer": {"evidence": []},
                        "judgement": {"correctness": "fail", "groundedness": "fail"},
                    },
                },
            ],
        }
    ]
    summary = runner["summarize"](asymmetric_results, True)
    assert summary["paired_questions"] == 0
    assert summary["corpus_lift"] is None


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        corpus_root = temp / "knowledge"
        evidence = write_corpus(corpus_root)
        suite_path = temp / "suite.local.yml"

        assert_validator_and_hashes(corpus_root, suite_path, approved_suite(evidence))
        assert_independent_review(corpus_root, suite_path, evidence)
        assert_sampler(corpus_root, temp / "sample.local.yml")
        assert_runner(corpus_root, suite_path, evidence, temp)
        assert_report_contracts(temp)

    print("Проверки средств оценки доступности знаний пройдены.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
