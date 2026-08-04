from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / ".apm"
    / "skills"
    / "ait-impact-analysis"
    / "scripts"
    / "impact_graph.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("impact_graph", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load impact graph module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


impact_graph = load_module()


def sample_graph() -> dict:
    return {
        "schema_version": 1,
        "graph": {
            "name": "test",
            "description": "Test graph.",
            "default_facet": "semantic",
            "unmapped_paths": "block",
            "ignore": [".git/**"],
        },
        "nodes": [
            {
                "id": "concept",
                "title": "Concept",
                "kind": "concept",
                "paths": ["docs/concept.md"],
                "checks": ["concept-check"],
            },
            {
                "id": "requirements",
                "title": "Requirements",
                "kind": "requirements",
                "paths": ["requirements/**"],
                "checks": ["requirements-check"],
                "review_stages": ["requirements"],
            },
            {
                "id": "implementation",
                "title": "Implementation",
                "kind": "implementation",
                "paths": ["src/**"],
                "checks": ["code-check"],
                "review_stages": ["code"],
            },
            {
                "id": "tests",
                "title": "Tests",
                "kind": "test",
                "paths": ["tests/**"],
                "checks": ["test-check"],
                "review_stages": ["tests"],
            },
        ],
        "edges": [
            {
                "from": "concept",
                "to": "requirements",
                "relation": "constrains",
                "facets": ["semantic"],
                "rationale": "Requirements refine the concept.",
            },
            {
                "from": "requirements",
                "to": "implementation",
                "relation": "realizes",
                "facets": ["semantic", "interface"],
                "rationale": "Implementation realizes requirements.",
            },
            {
                "from": "implementation",
                "to": "tests",
                "relation": "verifies",
                "facets": ["any"],
                "rationale": "Tests verify implementation.",
            },
        ],
    }


class ImpactGraphTests(unittest.TestCase):
    def test_trace_reaches_full_depth_and_reports_paths(self) -> None:
        graph = impact_graph.validate_graph(sample_graph())
        result = impact_graph.trace_result(
            graph,
            [],
            ["docs/concept.md"],
            "semantic",
        )

        self.assertEqual(
            [item["id"] for item in result["affected"]],
            ["implementation", "requirements", "tests"],
        )
        tests = next(item for item in result["affected"] if item["id"] == "tests")
        self.assertEqual(
            tests["paths"],
            [["concept", "requirements", "implementation", "tests"]],
        )
        self.assertEqual(
            result["review_stages"],
            ["code", "requirements", "tests"],
        )

    def test_facet_stops_edges_that_do_not_apply(self) -> None:
        graph = impact_graph.validate_graph(sample_graph())
        result = impact_graph.trace_result(
            graph,
            [],
            ["docs/concept.md"],
            "documentation",
        )

        self.assertEqual(result["affected"], [])
        self.assertTrue(result["complete"])

    def test_new_facet_can_be_added_to_same_input_set(self) -> None:
        graph = impact_graph.validate_graph(sample_graph())
        result = impact_graph.trace_result(
            graph,
            ["concept:documentation", "requirements:interface"],
            [],
            None,
        )

        self.assertEqual(
            [item["id"] for item in result["affected"]],
            ["implementation", "tests"],
        )

    def test_cycle_terminates_at_fixed_point(self) -> None:
        data = sample_graph()
        data["edges"].append(
            {
                "from": "tests",
                "to": "requirements",
                "relation": "informs",
                "facets": ["semantic"],
                "rationale": "A failed test can reveal a requirement defect.",
            },
        )
        graph = impact_graph.validate_graph(data)
        result = impact_graph.trace_result(
            graph,
            ["concept:semantic"],
            [],
            None,
        )

        self.assertEqual(len(result["affected"]), 3)

    def test_unmapped_changed_path_blocks_trace(self) -> None:
        graph = impact_graph.validate_graph(sample_graph())

        with self.assertRaisesRegex(
            impact_graph.ContractError,
            "unmapped changed paths",
        ):
            impact_graph.trace_result(
                graph,
                [],
                ["unknown/file.txt"],
                "semantic",
            )

    def test_assess_requires_every_affected_node(self) -> None:
        graph = impact_graph.validate_graph(sample_graph())
        result = impact_graph.trace_result(
            graph,
            ["concept"],
            [],
            None,
        )

        assessed, exit_code = impact_graph.assess_result(
            result,
            [
                "requirements=updated",
                "implementation=verified_no_impact",
            ],
        )

        self.assertEqual(exit_code, 3)
        self.assertEqual(assessed["missing_statuses"], ["tests"])
        self.assertFalse(assessed["complete"])

    def test_assess_rejects_blocking_status(self) -> None:
        graph = impact_graph.validate_graph(sample_graph())
        result = impact_graph.trace_result(
            graph,
            ["concept"],
            [],
            None,
        )

        assessed, exit_code = impact_graph.assess_result(
            result,
            [
                "requirements=updated",
                "implementation=verified_no_impact",
                "tests=human_decision",
            ],
        )

        self.assertEqual(exit_code, 3)
        self.assertEqual(assessed["blocking_statuses"], ["tests"])

    def test_legacy_owner_decision_status_is_rejected(self) -> None:
        with self.assertRaisesRegex(impact_graph.ContractError, "unsupported status"):
            impact_graph.parse_statuses(["tests=owner_decision"])

    def test_invalid_edge_target_is_rejected(self) -> None:
        data = sample_graph()
        data["edges"][0]["to"] = "missing"

        with self.assertRaisesRegex(
            impact_graph.ContractError,
            "unknown node",
        ):
            impact_graph.validate_graph(data)

    def test_coverage_rejects_missing_repository(self) -> None:
        graph = impact_graph.validate_graph(sample_graph())

        with self.assertRaisesRegex(
            impact_graph.ContractError,
            "repository directory not found",
        ):
            impact_graph.coverage_result(
                graph,
                ROOT / "missing-impact-graph-test-repository",
            )

    def test_coverage_handles_git_paths_verbatim(self) -> None:
        data = sample_graph()
        data["nodes"].append(
            {
                "id": "localized-docs",
                "title": "Localized documentation",
                "kind": "documentation",
                "paths": ["документы/**"],
                "checks": ["documentation-check"],
            },
        )
        graph = impact_graph.validate_graph(data)

        with tempfile.TemporaryDirectory() as temporary_directory:
            repo = Path(temporary_directory)
            subprocess.run(
                ["git", "init", "--quiet", str(repo)],
                check=True,
            )
            paths = [
                repo / "документы" / "требования.md",
                repo / "документы" / "строка\nпереноса.md",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "add",
                    "документы/требования.md",
                ],
                check=True,
            )

            result, exit_code = impact_graph.coverage_result(graph, repo)

        self.assertEqual(exit_code, 0)
        self.assertTrue(result["complete"])
        self.assertEqual(result["mapped_paths"], 2)
        self.assertEqual(result["unmapped_paths"], [])

    def test_cli_uses_only_json_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            graph_path = Path(temporary_directory) / "project-impact.json"
            graph_path.write_text(
                json.dumps(sample_graph()),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "validate",
                    "--graph",
                    str(graph_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
