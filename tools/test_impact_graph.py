from __future__ import annotations

import importlib.util
import json
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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


class WorkspaceImpactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="рабочее место ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        fixture = SCRIPT.parents[1] / "evals/script-fixtures/two-repositories"
        shutil.copytree(fixture, self.root, dirs_exist_ok=True)
        self.links = self.root / "workspace-impact.json"

    def change_json(self, path: Path, change) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def run_cli(self, operation: str, *arguments: str, expected: int = 0):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), operation, "--workspace", str(self.links), *arguments],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(completed.returncode, expected, completed.stdout + completed.stderr)
        if completed.stdout:
            return json.loads(completed.stdout)
        self.assertTrue(completed.stderr.startswith("ERROR:"), completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        return completed.stderr

    def test_validate_two_git_repositories_under_unversioned_root(self) -> None:
        for name in ("contracts", "service"):
            subprocess.run(["git", "init", "--quiet", str(self.root / name)], check=True)
        env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(self.root.parent)}
        root_git = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "--show-toplevel"],
            env=env, capture_output=True, check=False,
        )
        self.assertNotEqual(root_git.returncode, 0)
        result = self.run_cli("validate")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["workspace"]["repositories"]), 2)
        self.assertEqual(result["nodes"], 6)

    def test_contract_reaches_other_repository_checks_without_id_collision(self) -> None:
        before = {
            p.relative_to(self.root): p.read_bytes()
            for p in self.root.rglob("*") if p.is_file()
        }
        result = self.run_cli("trace", "--changed-node", "contracts/api", "--facet", "interface")
        affected = {item["id"]: item for item in result["affected"]}
        self.assertEqual(set(affected), {"service/implementation", "service/tests"})
        self.assertEqual(affected["service/tests"]["paths"], [[
            "contracts/api", "service/implementation", "service/tests",
        ]])
        self.assertEqual(affected["service/tests"]["checks"], ["local-test-check"])
        self.assertEqual(affected["service/tests"]["repository"], "service")
        self.assertFalse(result["complete"])
        self.assertEqual(before, {
            p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()
        })

    def test_paths_use_repository_identity_not_physical_directory(self) -> None:
        (self.root / "contracts").rename(self.root / "контракты с пробелами")
        self.change_json(self.links, lambda data: data["repositories"][0].update(
            path="контракты с пробелами",
        ))
        result = self.run_cli(
            "trace", "--changed-path", "contracts/api.json", "--facet", "interface",
        )
        self.assertEqual(result["changed"][0]["id"], "contracts/api")
        self.assertEqual(len(result["affected"]), 2)

    def test_cycle_converges_across_both_repositories(self) -> None:
        self.change_json(self.links, lambda data: data["edges"].append({
            "from": "service/tests", "to": "contracts/api", "relation": "verifies",
            "facets": ["interface"], "rationale": "Проверка совместимости контракта.",
        }))
        result = self.run_cli("trace", "--changed-node", "contracts/api", "--facet", "interface")
        self.assertEqual({entry["id"] for entry in result["affected"]}, {
            "service/implementation", "service/tests",
        })

    def test_inapplicable_facet_does_not_cross_link(self) -> None:
        result = self.run_cli(
            "trace", "--changed-node", "contracts/api", "--facet", "documentation",
        )
        self.assertEqual(result["affected"], [])

    def test_assessment_requires_every_foreign_check(self) -> None:
        arguments = ("--changed-node", "contracts/api", "--facet", "interface")
        result = self.run_cli("assess", *arguments, expected=3)
        self.assertEqual(result["missing_statuses"], ["service/implementation", "service/tests"])
        result = self.run_cli(
            "assess", *arguments, "--status", "service/implementation=updated", expected=3,
        )
        self.assertEqual(result["missing_statuses"], ["service/tests"])
        for blocking in ("blocked", "human_decision"):
            result = self.run_cli(
                "assess", *arguments, "--status", "service/implementation=updated",
                "--status", f"service/tests={blocking}", expected=3,
            )
            self.assertFalse(result["complete"])
        result = self.run_cli(
            "assess", *arguments, "--status", "service/implementation=updated",
            "--status", "service/tests=verified_no_impact",
        )
        self.assertTrue(result["complete"])

    def test_package_source_change_does_not_imply_installed_update(self) -> None:
        source = self.root / "contracts/rules.md"
        installed = self.root / "service/packages/rules.md"
        dependency = json.loads((self.root / "service/dependencies.json").read_text())
        self.assertIn("2", source.read_text())
        self.assertIn(dependency["rules_version"], installed.read_text())
        result = self.run_cli("trace", "--changed-node", "contracts/rules", "--facet", "quality")
        self.assertEqual({entry["id"] for entry in result["affected"]}, {
            "service/installed-rules", "service/implementation", "service/tests",
        })
        self.assertIn("1", installed.read_text())
        self.assertNotIn("2", installed.read_text())
        statuses = [argument for entry in result["affected"]
                    for argument in ("--status", entry["id"] + "=verified_no_impact")]
        assessed = self.run_cli(
            "assess", "--changed-node", "contracts/rules", "--facet", "quality", *statuses,
        )
        self.assertTrue(assessed["complete"])

    def test_trace_identifies_exact_graph_snapshots(self) -> None:
        result = self.run_cli("trace", "--changed-node", "contracts/api", "--facet", "interface")
        snapshot = result["workspace"]
        self.assertEqual(snapshot["scope"], "declared-repositories")
        self.assertEqual(snapshot["sha256"], hashlib.sha256(self.links.read_bytes()).hexdigest())
        for repository in snapshot["repositories"]:
            self.assertEqual(
                repository["sha256"],
                hashlib.sha256(Path(repository["graph"]).read_bytes()).hexdigest(),
            )

    def test_unknown_endpoint_does_not_silently_truncate_scope(self) -> None:
        self.change_json(self.links, lambda data: data["edges"][0].update(to="service/missing"))
        error = self.run_cli("validate", expected=2)
        self.assertIn("unknown node", error)

    def test_missing_graph_blocks_trace(self) -> None:
        (self.root / "service/.ai-dev-team/project-impact.json").unlink()
        error = self.run_cli(
            "trace", "--changed-node", "contracts/api", "--facet", "interface", expected=2,
        )
        self.assertIn("graph unreadable", error)

    def test_repository_aliases_are_rejected(self) -> None:
        self.change_json(
            self.links, lambda data: data["repositories"][1].update(path="contracts/."),
        )
        self.assertIn("повтор корня", self.run_cli("validate", expected=2))

    def test_workspace_paths_cannot_escape_declared_root(self) -> None:
        for path in ("../outside", "/tmp", "C:\\outside", "\\\\host\\share"):
            with self.subTest(path=path):
                self.change_json(self.links, lambda data: data["repositories"][0].update(path=path))
                self.run_cli("validate", expected=2)

    def test_graph_symlink_cannot_escape_repository(self) -> None:
        path = self.root / "service/.ai-dev-team/project-impact.json"
        path.unlink()
        path.symlink_to(self.root / "contracts/.ai-dev-team/project-impact.json")
        self.assertIn("границу", self.run_cli("validate", expected=2))

    def test_file_cannot_be_used_as_repository_root(self) -> None:
        self.change_json(self.links, lambda data: data["repositories"][0].update(
            path="contracts/.ai-dev-team/project-impact.json", graph=".",
        ))
        self.assertIn("каталогом", self.run_cli("validate", expected=2))

    def test_invalid_path_has_controlled_diagnostic(self) -> None:
        self.change_json(self.links, lambda data: data["repositories"][0].update(path="\0"))
        self.assertIn("путь недоступен", self.run_cli("validate", expected=2))

    def test_resolution_failure_is_a_contract_error_on_older_python(self) -> None:
        with mock.patch.object(Path, "resolve", side_effect=RuntimeError("Symlink loop")):
            with self.assertRaisesRegex(impact_graph.ContractError, "путь недоступен"):
                impact_graph.load_workspace(self.links)

    def test_symlink_loop_has_no_traceback(self) -> None:
        loop = self.root / "loop"
        loop.symlink_to(loop)
        self.links = loop
        self.run_cli("validate", expected=2)

    def test_old_graph_is_not_presented_as_semantic_workspace(self) -> None:
        path = self.root / "service/.ai-dev-team/project-impact.json"
        self.change_json(path, lambda data: data.update(schema_version=1))
        self.run_cli("validate", expected=2)

    def test_local_edges_remain_in_local_graph(self) -> None:
        self.change_json(self.links, lambda data: data["edges"][0].update(
            **{"from": "service/implementation", "to": "service/tests"},
        ))
        self.assertIn("местное ребро", self.run_cli("validate", expected=2))

    def test_explicit_facet_is_required(self) -> None:
        self.assertIn("явный --facet", self.run_cli(
            "trace", "--changed-node", "contracts/api", expected=2,
        ))

    def test_unmapped_path_and_unaffected_status_are_rejected(self) -> None:
        self.run_cli(
            "trace", "--changed-path", "contracts/missing", "--facet", "interface", expected=2,
        )
        self.run_cli(
            "assess", "--changed-node", "contracts/api", "--facet", "interface",
            "--status", "service/api=updated", expected=2,
        )


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
    def test_documented_commands_from_project_root(self) -> None:
        skill = SCRIPT.parents[1]
        commands = re.findall(
            r"```shell\n(.*?)```", (skill / "SKILL.md").read_text(), re.DOTALL
        )
        self.assertEqual(len(commands), 6)
        fixture = skill / "evals/script-fixtures/minimal-project"
        for graph_name, config_name in (
            (".ai-dev-team/project-impact.json", ".ai-dev-team/project-verification.json"),
            ("config/impact graph.json", "config/checks config.json"),
        ):
            with self.subTest(graph=graph_name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                installed = repo / "installed skills/impact"
                shutil.copytree(skill / "scripts", installed / "scripts")
                graph = sample_graph()
                graph["schema_version"] = 2
                graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "tests"]
                graph["edges"] = [e for e in graph["edges"] if e["to"] != "tests"]
                graph["graph"]["ignore"] += ["installed skills/**", graph_name, config_name]
                for node in graph["nodes"]:
                    node["semantic_type"] = node["id"]
                    node["authority"] = "canonical"
                config = json.loads(
                    (fixture / ".ai-dev-team/project-verification.json").read_text()
                )
                config["verification"]["impact_graph"] = graph_name
                for field in ("global_inputs", "full_coverage_paths"):
                    config["verification"][field] = [graph_name, config_name]
                files = {
                    graph_name: json.dumps(graph),
                    config_name: json.dumps(config),
                    "docs/concept.md": "Concept\n",
                    "requirements/requirement.md": "Requirement\n",
                    "src/module.py": "# module\n",
                }
                for name, content in files.items():
                    path = repo / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                for args in (
                    ["init", "--quiet"],
                    ["add", "docs", "requirements", "src", graph_name, config_name],
                    ["-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                     "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Fixture"],
                    ["update-ref", "refs/remotes/origin/main", "HEAD"],
                ):
                    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
                (repo / "docs/concept.md").write_text("Changed concept\n")
                variables = {
                    "$impact_skill_dir": str(installed.relative_to(repo)),
                    "$impact_graph_path": graph_name,
                    "$verification_config_path": config_name,
                }
                for block in commands:
                    command = block.replace("<команда Python 3>", shlex.quote(sys.executable))
                    args = shlex.split(command.replace("\\\n", " "))
                    for index, argument in enumerate(args):
                        for variable, value in variables.items():
                            argument = argument.replace(variable, value)
                        args[index] = argument
                    completed = subprocess.run(
                        args, cwd=repo, capture_output=True, text=True, check=False
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    result = json.loads(completed.stdout)
                    if args[2] == "trace":
                        self.assertEqual(
                            {node["id"] for node in result["affected"]},
                            {"requirements", "implementation"},
                        )
                    elif args[2] in {"assess", "coverage"}:
                        self.assertTrue(result["complete"])
                        if args[2] == "coverage":
                            self.assertEqual(result["mapped_paths"], 3)
                    elif args[2] == "run":
                        self.assertEqual(result["status"], "passed")
                        self.assertIn('"status": "executed"', completed.stdout)
                    else:
                        self.assertIn(result["status"], {"ok", "passed"})

    def test_version_two_distinguishes_artifact_from_representation(self) -> None:
        data = sample_graph()
        data["schema_version"] = 2
        for node in data["nodes"]:
            node["semantic_type"] = f"{node['id']} artifact"
            node["authority"] = "canonical"

        graph = impact_graph.validate_graph(data)
        result = impact_graph.trace_result(
            graph,
            [],
            ["docs/concept.md"],
            "semantic",
        )

        self.assertEqual(result["changed"][0]["id"], "concept")
        self.assertEqual(
            next(item for item in result["affected"] if item["id"] == "requirements")
            ["semantic_type"],
            "requirements artifact",
        )

    def test_version_two_rejects_canonical_artifact_without_canonical_view(self) -> None:
        data = sample_graph()
        data["schema_version"] = 2
        for node in data["nodes"]:
            node["semantic_type"] = f"{node['id']} artifact"
            node["authority"] = "canonical"
        data["nodes"][0]["representations"] = [
            {"path": "docs/concept.md", "role": "navigation"},
        ]
        data["nodes"][0].pop("paths")

        with self.assertRaisesRegex(
            impact_graph.ContractError,
            "canonical artifact requires a canonical representation",
        ):
            impact_graph.validate_graph(data)

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

    def test_edge_accepts_optional_basis_boolean(self) -> None:
        data = sample_graph()
        data["edges"][0]["basis"] = True
        data["edges"][1]["basis"] = False

        graph = impact_graph.validate_graph(data)

        self.assertTrue(graph["edges"][0]["basis"])
        self.assertFalse(graph["edges"][1]["basis"])

    def test_edge_rejects_non_boolean_basis(self) -> None:
        data = sample_graph()
        data["edges"][0]["basis"] = "true"

        with self.assertRaisesRegex(
            impact_graph.ContractError,
            "basis: expected boolean",
        ):
            impact_graph.validate_graph(data)

    def test_basis_field_does_not_change_trace_result(self) -> None:
        without_basis = impact_graph.validate_graph(sample_graph())
        result_without_basis = impact_graph.trace_result(
            without_basis,
            [],
            ["docs/concept.md"],
            "semantic",
        )

        with_basis = sample_graph()
        with_basis["edges"][0]["basis"] = False
        with_basis["edges"][1]["basis"] = True
        with_basis = impact_graph.validate_graph(with_basis)
        result_with_basis = impact_graph.trace_result(
            with_basis,
            [],
            ["docs/concept.md"],
            "semantic",
        )

        self.assertEqual(
            [item["id"] for item in result_without_basis["affected"]],
            [item["id"] for item in result_with_basis["affected"]],
        )

    def test_validate_reports_basis_cycle_without_blocking_trace(self) -> None:
        data = sample_graph()
        data["schema_version"] = 2
        for node in data["nodes"]:
            node["semantic_type"] = f"{node['id']} artifact"
            node["authority"] = "canonical"
        data["edges"][0]["basis"] = True
        data["edges"][1]["basis"] = True
        data["edges"].append(
            {
                "from": "implementation",
                "to": "concept",
                "relation": "informs",
                "facets": ["semantic"],
                "rationale": "Implementation feedback reopens the concept.",
                "basis": True,
            },
        )

        graph = impact_graph.validate_graph(data)
        result, exit_code = impact_graph.validation_result(graph)

        self.assertEqual(exit_code, 3)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["semantic_model"])
        self.assertEqual(result["problems"][0]["code"], "basis-cycle")

        trace = impact_graph.trace_result(graph, [], ["docs/concept.md"], "semantic")
        self.assertEqual(
            [item["id"] for item in trace["affected"]],
            ["implementation", "requirements", "tests"],
        )

    def test_find_basis_cycle_ignores_non_basis_edges(self) -> None:
        data = sample_graph()
        data["edges"][0]["basis"] = True
        data["edges"].append(
            {
                "from": "implementation",
                "to": "concept",
                "relation": "informs",
                "facets": ["semantic"],
                "rationale": "Not a basis edge, so no cycle among basis edges.",
                "basis": False,
            },
        )
        graph = impact_graph.validate_graph(data)

        self.assertIsNone(impact_graph.find_basis_cycle(graph))

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

    def test_cli_reports_legacy_graph_as_semantically_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            graph_path = Path(temporary_directory) / ".ai-dev-team/project-impact.json"
            graph_path.parent.mkdir()
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

        self.assertEqual(completed.returncode, 3, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["semantic_model"])
        self.assertEqual(
            result["problems"][0]["code"],
            "semantic-model-unavailable",
        )

    def test_cli_accepts_semantic_graph(self) -> None:
        data = sample_graph()
        data["schema_version"] = 2
        for node in data["nodes"]:
            node["semantic_type"] = f"{node['id']} artifact"
            node["authority"] = "canonical"

        with tempfile.TemporaryDirectory() as temporary_directory:
            graph_path = Path(temporary_directory) / "project-impact.json"
            graph_path.write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(SCRIPT), "validate", "--graph", str(graph_path)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["semantic_model"])


if __name__ == "__main__":
    unittest.main()