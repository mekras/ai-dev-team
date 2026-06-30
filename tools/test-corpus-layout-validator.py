#!/usr/bin/env python3
"""Regression tests for the portable corpus layout validator."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / ".apm" / "skills" / "kc-inventory" / "scripts" / "validate-corpus-layout.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip(), encoding="utf-8")


def write_minimal_corpus(root: Path, corpus_yml: str | None = None) -> None:
    write_text(
        root / "corpus.yml",
        corpus_yml
        or """
        contract_version: 1
        tracked_data:
          root: data
          source_pattern: data/<source>/source.yml
          source_unit_pattern: data/<source>/<units>/<unit>/item.yml
          statement_pattern: data/<source>/<units>/<unit>/statements.yml
        local_data:
          raw: .local/raw
          private: .local/private
          cache: .local/cache
          temporary_file_pattern: "*.tmp.*"
        source_units:
          document:
            unit: file_or_section
            path_pattern: data/<source>/documents/<slug>
        workflow_stages:
          - indexed
          - blocked
        """,
    )
    write_text(
        root / "catalog.yml",
        """
        sources:
          - id: TEST
            title: "Test source"
            path: data/test-source
        """,
    )
    write_text(
        root / "data" / "test-source" / "source.yml",
        """
        id: TEST
        slug: test-source
        title: "Test source"
        access:
          default: "Open test fixture."
        status: active
        carrier_type: document
        source_kind: reference
        adapter: manual
        reliability: test fixture
        refresh_policy: manual
        """,
    )
    write_text(
        root / "data" / "test-source" / "items.yml",
        """
        items:
          - id: TEST-ITEM-001
            title: "Test item"
            access: "Same as source."
            status: active
            workflow_stage: indexed
        """,
    )


def write_external_corpus_source(root: Path, with_items: bool = False) -> None:
    write_text(
        root / "catalog.yml",
        """
        sources:
          - id: TEST
            title: "Test source"
            path: data/test-source
          - id: EXT
            title: "External corpus"
            path: data/external-corpus
        """,
    )
    write_text(
        root / "data" / "external-corpus" / "source.yml",
        """
        id: EXT
        slug: external-corpus
        title: "External corpus"
        access:
          default: "Access follows the connected project or local checkout."
        status: active
        carrier_type: repository
        source_kind: knowledge_corpus
        adapter: builtin.git
        reliability: working
        refresh_policy: manual
        locator: "ssh://git@example.org/team/corpus.git#knowledge"
        external_corpus:
          contract: portable_v1
          use_as: peer
          local_checkout: .local/external-corpora/external-corpus
        """,
    )
    if with_items:
        write_text(
            root / "data" / "external-corpus" / "items.yml",
            """
            items:
              - id: EXT-CATALOG
                title: "External catalog"
                access: "Same as source."
                status: active
                workflow_stage: indexed
            """,
        )


def write_statement(
    root: Path,
    status: str = "ready_for_review",
    kind: str | None = None,
    text: str = "Fact.",
    excerpt: str = "Fact.",
    artifact_text: str = "Fact.",
    scope: str = "{}",
) -> None:
    kind_line = f"kind: {kind}\n            " if kind is not None else ""
    write_text(root / "data" / "test-source" / "documents" / "item-001" / "artifact.md", artifact_text)
    write_text(
        root / "data" / "test-source" / "documents" / "item-001" / "item.yml",
        """
        id: TEST-ITEM-001
        title: "Test item"
        access: "Same as source."
        status: active
        workflow_stage: indexed
        """,
    )
    write_text(
        root / "data" / "test-source" / "documents" / "item-001" / "statements.yml",
        f"""
        source_id: TEST
        item_id: TEST-ITEM-001
        statements:
          - id: TEST-001
            source_id: TEST
            item_id: TEST-ITEM-001
            status: {status}
            {kind_line}text: "{text}"
            excerpt: "{excerpt}"
            artifact: artifact.md
            checked_at: 2026-06-30
            scope: {scope}
            open_questions: []
        """,
    )


def run_validator(root: Path, *, strict_statements: bool = False) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(VALIDATOR)]
    if strict_statements:
        command.append("--strict-statements")
    command.append(str(root))
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def assert_passes(root: Path) -> None:
    result = run_validator(root)
    if result.returncode != 0:
        raise AssertionError(f"expected validator to pass, got:\n{result.stdout}")


def assert_fails_with(root: Path, expected: str, *, strict_statements: bool = False) -> None:
    result = run_validator(root, strict_statements=strict_statements)
    if result.returncode == 0:
        raise AssertionError("expected validator to fail")
    if expected not in result.stdout:
        raise AssertionError(f"expected {expected!r} in output:\n{result.stdout}")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        assert_passes(root)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root)
        assert_passes(root)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root)
        assert_fails_with(root, "missing kind in strict statement validation", strict_statements=True)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(
            root,
            kind="fact",
            text="The validator should not accept copied statement text as evidence.",
            excerpt="The validator should not accept copied statement text as evidence.",
            artifact_text="The source contains the original evidence.",
        )
        assert_fails_with(root, "excerpt duplicates statement text", strict_statements=True)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(
            root,
            kind="fact",
            text="The source says the corpus needs traceable excerpts.",
            excerpt="traceable excerpt missing from artifact",
            artifact_text="The source says another fragment.",
        )
        assert_fails_with(
            root,
            "excerpt is not found in referenced text artifact",
            strict_statements=True,
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(
            root,
            kind="fact",
            text="The source says section metadata must stay useful.",
            excerpt="section metadata",
            artifact_text="The source says section metadata must stay useful.",
            scope="{section_title: ''}",
        )
        assert_fails_with(root, "scope.section_title must be non-empty", strict_statements=True)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="invalid_kind")
        assert_fails_with(root, "kind must be one of:")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, status="fact")
        assert_fails_with(root, "status contains statement kind fact")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_external_corpus_source(root)
        assert_passes(root)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_text(
            root / "catalog.yml",
            """
            sources:
              - id: EXT
                title: "External corpus"
                path: data/external-corpus
            """,
        )
        write_text(
            root / "data" / "external-corpus" / "source.yml",
            """
            id: EXT
            slug: external-corpus
            title: "External corpus"
            access:
              default: "Access follows the connected project."
            status: active
            carrier_type: repository
            source_kind: knowledge_corpus
            adapter: builtin.git
            reliability: working
            refresh_policy: manual
            locator: "ssh://git@example.org/team/corpus.git#knowledge"
            """,
        )
        assert_fails_with(root, "knowledge_corpus source requires external_corpus block")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        (root / "inventory").mkdir()
        assert_fails_with(root, "inventory/: legacy corpus layer remains outside data/")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(
            root,
            """
            contract_version: 1
            tracked_data:
              root: data
              layers:
                registry: data
                legacy_inventory: knowledge/inventory
            local_data:
              raw: .local/raw
            source_units:
              document:
                unit: file_or_section
                path_pattern: data/<source>/documents/<slug>
            """,
        )
        assert_fails_with(root, "corpus.yml: legacy layer remains active outside portable layout")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
