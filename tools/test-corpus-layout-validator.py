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


def indented_yaml_fragment(text: str) -> str:
    return "\n".join(f"        {line}" if line else "" for line in dedent(text).lstrip().splitlines())


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
          - normalized
          - statements_extracted
          - source_checked
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


def write_long_source(root: Path, *, stage: str = "normalized") -> None:
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
        source_kind: book
        long_source: true
        adapter: manual
        storage_strategy: local_only
        copy_policy: metadata_only
        reliability: test fixture
        refresh_policy: manual
        extraction_status: normalized_fragments_ready
        """,
    )
    write_text(
        root / "data" / "test-source" / "items.yml",
        f"""
        items:
          - id: TEST-ITEM-001
            title: "Chapter 1"
            access: "Same as source."
            status: active
            workflow_stage: {stage}
        """,
    )


def write_long_source_item(root: Path, *, stage: str = "normalized") -> None:
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
        long_source: false
        adapter: manual
        storage_strategy: local_only
        copy_policy: metadata_only
        reliability: test fixture
        refresh_policy: manual
        """,
    )
    write_text(
        root / "data" / "test-source" / "items.yml",
        f"""
        items:
          - id: TEST-ITEM-001
            title: "Long appendix"
            access: "Same as source."
            status: active
            workflow_stage: {stage}
            long_source: true
        """,
    )


def write_source_map(root: Path, *, coverage: str | None = None, extra: str = "") -> None:
    coverage_text = indented_yaml_fragment(
        coverage if coverage is not None else "coverage_absence_reason: Not started."
    )
    extra_text = indented_yaml_fragment(extra) if extra else ""
    write_text(
        root / "data" / "test-source" / "source-map.yml",
        f"""
        source_map_version: 1
        source_id: TEST
        long_source: true
        extraction_passport:
          format: pdf
          file_size_bytes: 123
          content_hash_absence_reason: "Test fixture has no source file."
          metadata_source: manual
          extraction_tool: manual
          extraction_status: normalized_fragments_ready
        structure:
          units:
            - id: chapter-1
              title: "Chapter 1"
              order: 1
{coverage_text}
{extra_text}
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


def write_derived_statement(
    root: Path,
    *,
    analysis_id: str = "NIGHT",
    statement_id: str = "DRV-NIGHT-001",
    kind: str = "observation",
    status: str = "candidate",
    statement_ids: str = "[TEST-001]",
    item_ids: str = "[]",
    artifacts: str = "[]",
    external_references: str = "[]",
    derivation_type: str = "aggregation",
    derivation_artifact: str | None = "analysis/night-starts/calculate.sql",
    checked_by: str = "",
) -> None:
    write_text(
        root / "analysis" / "night-starts" / "calculate.sql",
        "SELECT COUNT(*) FROM searches;\n",
    )
    artifact_line = (
        f'artifact: "{derivation_artifact}"' if derivation_artifact is not None else ""
    )
    write_text(
        root / "analysis" / "night-starts" / "derived-statements.yml",
        f"""
        analysis_id: {analysis_id}
        title: "Night search starts"
        derived_statements:
          - id: {statement_id}
            kind: {kind}
            status: {status}
            text: "Most headquarters in the sample started at night."
            derived_from:
              statement_ids: {statement_ids}
              item_ids: {item_ids}
              artifacts: {artifacts}
              external_references: {external_references}
            derivation:
              type: {derivation_type}
              method: "Count starts between 22:00 and 06:00."
              {artifact_line}
              parameters:
                night_interval: "22:00-06:00"
            checked_at: 2026-07-10
            checked_by: "{checked_by}"
            scope:
              applies_to: ["test sample"]
              does_not_apply_to: []
            limitations:
              - "Start time does not describe search duration."
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
        write_statement(root, kind="fact")
        write_derived_statement(root)
        assert_passes(root)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, kind="fact")
        assert_fails_with(root, "fact is direct only")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, statement_id="NIGHT-001")
        assert_fails_with(root, "id must match DRV-NIGHT-NNN")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, statement_ids="[]")
        assert_fails_with(root, "derived_from must contain at least one input")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, statement_ids="[MISSING-001]")
        assert_fails_with(root, "derived statement input is missing in corpus: MISSING-001")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, statement_ids="[DRV-NIGHT-001]")
        assert_fails_with(root, "derived statements must use direct inputs")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_external_corpus_source(root)
        write_statement(root, kind="fact")
        write_derived_statement(
            root,
            statement_ids="[]",
            external_references=(
                "[{corpus_source_id: EXT, statement_id: EXT-001, revision: v1}]"
            ),
        )
        assert_passes(root)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(
            root,
            statement_ids="[]",
            external_references=(
                "[{corpus_source_id: MISSING, statement_id: EXT-001, revision: v1}]"
            ),
        )
        assert_fails_with(root, "corpus source is missing: MISSING")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_external_corpus_source(root)
        write_statement(root, kind="fact")
        write_derived_statement(
            root,
            statement_ids="[]",
            external_references="[{corpus_source_id: EXT, statement_id: EXT-001}]",
        )
        assert_fails_with(root, "revision or revision_absence_reason is required")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, derivation_artifact=None)
        assert_fails_with(root, "aggregation derivation requires artifact")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, derivation_artifact="../calculate.sql")
        assert_fails_with(root, "derivation.artifact must be repository-relative")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(root, status="confirmed")
        assert_fails_with(root, "confirmed statement requires checked_by")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_statement(root, kind="fact")
        write_derived_statement(
            root,
            status="confirmed",
            checked_by="Reviewer",
            statement_ids="[]",
            artifacts=(
                "[{path: data/test-source/searches.local.csv, "
                "content_hash_absence_reason: 'Test fixture'}]"
            ),
        )
        assert_fails_with(root, "confirmed statement input requires content_hash")

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

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_long_source(root)
        assert_fails_with(root, "long source reached normalization or statements without source-map.yml")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_long_source_item(root)
        assert_fails_with(root, "long source reached normalization or statements without source-map.yml")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_long_source(root)
        write_source_map(root)
        assert_passes(root)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_long_source(root, stage="statements_extracted")
        write_source_map(
            root,
            coverage="""
            coverage:
              units:
                - unit_id: chapter-1
            """,
        )
        assert_fails_with(root, "status must be non-empty text")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_minimal_corpus(root)
        write_long_source(root)
        write_source_map(root, extra='full_text: "Complete tracked text is not allowed."')
        assert_fails_with(root, "source-map.yml contains full-text-like fields")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
