from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / ".apm"
    / "skills"
    / "ait-session-analysis"
    / "scripts"
    / "session_analysis.py"
)


def load_session_module():
    spec = importlib.util.spec_from_file_location("session_analysis_tested", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load session analysis module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SessionAnalysisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "Проект с пробелом"
        self.codex = self.root / "codex"
        self.claude = self.root / "claude"
        self.local = (
            self.project / ".ai-dev-team" / "local" / "session-analysis"
        )
        self.project.mkdir()
        self.codex.mkdir()
        self.claude.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_jsonl(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

    def write_sessions(self, codex_text: str = "Repeated validation") -> None:
        self.write_jsonl(
            self.codex / "session.jsonl",
            [
                {
                    "timestamp": "2026-08-25T10:00:00Z",
                    "type": "session_meta",
                    "payload": {"id": "codex-one", "cwd": str(self.project)},
                },
                {
                    "timestamp": "2026-08-25T10:01:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": (
                            "token=synthetic-secret-value "
                            "Authorization: Basic dXNlcjpwYXNz "
                            "Cookie=session-cookie-value "
                            "credential=free-text-credential "
                            "passwd=free-text-password "
                            "private_key=free-text-private-key "
                            "session_key=free-text-session-key "
                            "person@example.test +7 999 123-45-67 "
                            "AKIAABCDEFGHIJKLMNOP "
                            "eyJabc.def.ghi https://user:pass@example.test"
                        ),
                    },
                },
                {
                    "timestamp": "2026-08-25T10:02:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": "turn-one",
                        "last_agent_message": codex_text,
                    },
                },
            ],
        )
        self.write_jsonl(
            self.claude / "session.jsonl",
            [
                {
                    "type": "user",
                    "sessionId": "claude-one",
                    "uuid": "user-one",
                    "cwd": str(self.project),
                    "timestamp": "2026-08-25T11:00:00Z",
                    "message": {"role": "user", "content": "Review"},
                },
                {
                    "type": "assistant",
                    "sessionId": "claude-one",
                    "uuid": "answer-one",
                    "cwd": str(self.project),
                    "timestamp": "2026-08-25T11:01:00Z",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "A check was skipped"},
                            {
                                "type": "tool_use",
                                "name": "synthetic",
                                "input": {
                                    "password": "json-secret-value",
                                    "client_secret": "client-secret-value",
                                    "id_token": "id-token-value",
                                    "nested": {
                                        "authorization": "Bearer nested-secret"
                                    },
                                },
                            },
                        ],
                        "stop_reason": "end_turn",
                    },
                },
            ],
        )

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *arguments],
            check=False,
            cwd=self.root,
            text=True,
            capture_output=True,
        )

    def prepare(self, candidate_name: str) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            "prepare",
            "--project-root",
            str(self.project),
            "--state",
            str(self.local / "state.json"),
            "--candidate",
            str(self.local / candidate_name),
            "--codex-root",
            str(self.codex),
            "--claude-root",
            str(self.claude),
        )

    def commit(self, candidate_name: str) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            "commit",
            "--state",
            str(self.local / "state.json"),
            "--candidate",
            str(self.local / candidate_name),
        )

    def test_prepare_redacts_and_commit_keeps_only_metadata(self) -> None:
        self.write_sessions()

        prepared = self.prepare("candidate-first.json")

        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        result = json.loads(prepared.stdout)
        self.assertEqual(result["coverage"]["selected_parts"], 2)
        self.assertIn("[REDACTED]", prepared.stdout)
        self.assertNotIn("synthetic-secret-value", prepared.stdout)
        self.assertNotIn("person@example.test", prepared.stdout)
        self.assertNotIn("999 123-45-67", prepared.stdout)
        self.assertNotIn("json-secret-value", prepared.stdout)
        self.assertNotIn("nested-secret", prepared.stdout)
        self.assertNotIn("client-secret-value", prepared.stdout)
        self.assertNotIn("id-token-value", prepared.stdout)
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", prepared.stdout)
        self.assertNotIn("eyJabc.def.ghi", prepared.stdout)
        self.assertNotIn("user:pass", prepared.stdout)
        self.assertNotIn("dXNlcjpwYXNz", prepared.stdout)
        self.assertNotIn("session-cookie-value", prepared.stdout)
        self.assertNotIn("free-text-credential", prepared.stdout)
        self.assertNotIn("free-text-password", prepared.stdout)
        self.assertNotIn("free-text-private-key", prepared.stdout)
        self.assertNotIn("free-text-session-key", prepared.stdout)

        committed = self.commit("candidate-first.json")

        self.assertEqual(committed.returncode, 0, committed.stderr)
        state_text = (self.local / "state.json").read_text(encoding="utf-8")
        self.assertNotIn("Repeated validation", state_text)
        self.assertNotIn("synthetic-secret-value", state_text)
        if os.name == "posix":
            self.assertEqual((self.local / "state.json").stat().st_mode & 0o777, 0o600)

    def test_repeat_selects_nothing_but_changed_content_reappears(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-first.json").returncode, 0)
        self.assertEqual(self.commit("candidate-first.json").returncode, 0)

        repeated = self.prepare("candidate-second.json")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(json.loads(repeated.stdout)["coverage"]["selected_parts"], 0)

        self.write_sessions(codex_text="Changed completed content")
        changed = self.prepare("candidate-third.json")
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertEqual(json.loads(changed.stdout)["coverage"]["selected_parts"], 1)

    def test_replayed_candidate_is_rejected(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-first.json").returncode, 0)
        self.assertEqual(self.commit("candidate-first.json").returncode, 0)

        replayed = self.commit("candidate-first.json")

        self.assertEqual(replayed.returncode, 2)
        self.assertIn("недоступен", replayed.stderr)

    def test_committed_candidate_is_rejected_after_state_loss(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-first.json").returncode, 0)
        saved = (self.local / "candidate-first.json").read_text(encoding="utf-8")
        self.assertEqual(self.commit("candidate-first.json").returncode, 0)
        (self.local / "state.json").unlink()
        replay = self.local / "candidate-replay.json"
        replay.write_text(saved, encoding="utf-8")
        if os.name == "posix":
            replay.chmod(0o600)

        committed = self.commit("candidate-replay.json")

        self.assertEqual(committed.returncode, 2)
        self.assertIn("Целостность", committed.stderr)

    def test_state_write_failure_after_key_rotation_is_fail_closed(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-failed-state.json").returncode, 0)
        module = load_session_module()
        original_atomic_json = module.atomic_json
        calls = 0

        def fail_second_write(path, value):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise module.SessionError("synthetic state write failure")
            return original_atomic_json(path, value)

        arguments = type(
            "Arguments",
            (),
            {
                "state": str(self.local / "state.json"),
                "candidate": str(self.local / "candidate-failed-state.json"),
            },
        )()
        with mock.patch.object(module, "atomic_json", side_effect=fail_second_write):
            with self.assertRaises(module.SessionError):
                module.commit(arguments)

        self.assertFalse((self.local / "state.json").exists())
        repeated = self.commit("candidate-failed-state.json")
        self.assertEqual(repeated.returncode, 2)
        self.assertIn("Целостность", repeated.stderr)

    def test_reset_invalidates_old_candidate(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-first.json").returncode, 0)
        old_candidate = (self.local / "candidate-first.json").read_text(
            encoding="utf-8"
        )
        self.assertEqual(self.commit("candidate-first.json").returncode, 0)
        reset = self.run_script(
            "reset",
            "--state",
            str(self.local / "state.json"),
        )
        self.assertEqual(reset.returncode, 0, reset.stderr)

        replay_path = self.local / "candidate-replay.json"
        replay_path.write_text(old_candidate, encoding="utf-8")
        if os.name == "posix":
            replay_path.chmod(0o600)

        replayed = self.commit("candidate-replay.json")

        self.assertEqual(replayed.returncode, 2)
        self.assertTrue(replayed.stderr.strip())

    def test_reset_before_first_commit_invalidates_candidate(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-before-reset.json").returncode, 0)

        reset = self.run_script(
            "reset",
            "--state",
            str(self.local / "state.json"),
        )
        committed = self.commit("candidate-before-reset.json")

        self.assertEqual(reset.returncode, 0, reset.stderr)
        self.assertEqual(committed.returncode, 2)
        self.assertTrue(committed.stderr.strip())

    def test_candidate_cannot_be_overwritten(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-once.json").returncode, 0)

        repeated = self.prepare("candidate-once.json")

        self.assertEqual(repeated.returncode, 2)
        self.assertIn("уже существует", repeated.stderr)

    def test_tampered_candidate_is_rejected(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-tampered.json").returncode, 0)
        candidate_path = self.local / "candidate-tampered.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["baseline_at"] = candidate["snapshot_at"]
        candidate["handled"]["a" * 64] = "b" * 64
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        if os.name == "posix":
            candidate_path.chmod(0o600)

        committed = self.commit("candidate-tampered.json")

        self.assertEqual(committed.returncode, 2)
        self.assertIn("Целостность", committed.stderr)

    def test_concurrent_commit_lock_is_rejected(self) -> None:
        self.write_sessions()
        self.assertEqual(self.prepare("candidate-locked.json").returncode, 0)
        lock = self.local / "state.json.lock"
        lock.write_text("locked", encoding="utf-8")
        if os.name == "posix":
            lock.chmod(0o600)

        committed = self.commit("candidate-locked.json")

        self.assertEqual(committed.returncode, 2)
        self.assertIn("уже выполняется", committed.stderr)

    def test_total_size_limit_stops_commit(self) -> None:
        self.write_sessions()

        prepared = self.run_script(
            "prepare",
            "--project-root",
            str(self.project),
            "--state",
            str(self.local / "state.json"),
            "--candidate",
            str(self.local / "candidate-limited.json"),
            "--max-total-bytes",
            "1",
            "--codex-root",
            str(self.codex),
            "--claude-root",
            str(self.claude),
        )

        self.assertEqual(prepared.returncode, 2)
        result = json.loads(prepared.stdout)
        self.assertFalse(result["commit_allowed_after_successful_report"])

    def test_foreign_large_log_does_not_block_project(self) -> None:
        self.write_sessions()
        foreign = self.codex / "foreign.jsonl"
        foreign.write_text(
            json.dumps(
                {
                    "type": "session_meta",
                    "payload": {"id": "foreign", "cwd": str(self.root / "other")},
                }
            )
            + "\n"
            + ("x" * 100_000),
            encoding="utf-8",
        )

        prepared = self.run_script(
            "prepare",
            "--project-root",
            str(self.project),
            "--state",
            str(self.local / "state.json"),
            "--candidate",
            str(self.local / "candidate-foreign.json"),
            "--max-file-bytes",
            "1000",
            "--codex-root",
            str(self.codex),
            "--claude-root",
            str(self.claude),
        )

        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout)["coverage"]["selected_parts"], 2)

    def test_replaced_journal_after_snapshot_is_rejected(self) -> None:
        self.write_sessions()
        module = load_session_module()
        path = self.codex / "session.jsonl"
        snapshot = module.file_snapshot(path)
        replacement = self.codex / "replacement.jsonl"
        replacement.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        os.replace(replacement, path)

        with self.assertRaises(module.SessionError):
            module.codex_units(snapshot, self.project.resolve(), 1_000_000)

    def test_same_size_journal_change_after_snapshot_is_rejected(self) -> None:
        self.write_sessions()
        module = load_session_module()
        path = self.codex / "session.jsonl"
        snapshot = module.file_snapshot(path)
        digest = module.snapshot_digest(snapshot)
        original = path.read_bytes()
        changed = original.replace(b"Repeated validation", b"Altered validation!")
        self.assertEqual(len(changed), len(original))
        path.write_bytes(changed)

        with self.assertRaises(module.SessionError):
            module.codex_units(
                snapshot,
                self.project.resolve(),
                1_000_000,
                digest,
            )

    def test_malformed_allowed_codex_record_stops_selection(self) -> None:
        self.write_jsonl(
            self.codex / "malformed.jsonl",
            [
                {
                    "type": "session_meta",
                    "payload": {"id": "bad", "cwd": str(self.project)},
                },
                {"type": "event_msg", "payload": "untrusted"},
            ],
        )

        prepared = self.prepare("candidate-malformed-codex.json")

        self.assertEqual(prepared.returncode, 2)
        self.assertFalse(
            json.loads(prepared.stdout)["commit_allowed_after_successful_report"]
        )
        self.assertNotIn("untrusted", prepared.stdout + prepared.stderr)

    def test_malformed_allowed_claude_record_stops_selection(self) -> None:
        self.write_jsonl(
            self.claude / "malformed.jsonl",
            [
                {
                    "type": "user",
                    "cwd": str(self.project),
                    "message": {"role": "user", "content": "valid"},
                },
                {
                    "type": "assistant",
                    "cwd": str(self.project),
                    "message": "untrusted",
                },
            ],
        )

        prepared = self.prepare("candidate-malformed-claude.json")

        self.assertEqual(prepared.returncode, 2)
        self.assertFalse(
            json.loads(prepared.stdout)["commit_allowed_after_successful_report"]
        )
        self.assertNotIn("untrusted", prepared.stdout + prepared.stderr)

    def test_claude_message_without_content_stops_selection(self) -> None:
        self.write_jsonl(
            self.claude / "missing-content.jsonl",
            [
                {
                    "type": "user",
                    "cwd": str(self.project),
                    "message": {"role": "user"},
                }
            ],
        )

        prepared = self.prepare("candidate-missing-content.json")

        self.assertEqual(prepared.returncode, 2)
        self.assertNotIn("Traceback", prepared.stderr)

    def test_first_run_does_not_read_unbounded_matching_history(self) -> None:
        for number in range(32):
            path = self.codex / f"recent-{number:02d}.jsonl"
            self.write_jsonl(
                path,
                [
                    {
                        "type": "session_meta",
                        "payload": {
                            "id": f"recent-{number}",
                            "cwd": str(self.project),
                        },
                    },
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "task_complete",
                            "turn_id": f"turn-{number}",
                            "last_agent_message": "done",
                        },
                    },
                ],
            )
            os.utime(path, (2_000 + number, 2_000 + number))
        oldest = self.codex / "old-malformed.jsonl"
        self.write_jsonl(
            oldest,
            [
                {
                    "type": "session_meta",
                    "payload": {"id": "old", "cwd": str(self.project)},
                },
                {"type": "event_msg", "payload": "must-not-be-read"},
            ],
        )
        os.utime(oldest, (1_000, 1_000))

        prepared = self.prepare("candidate-bounded-first.json")

        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        result = json.loads(prepared.stdout)
        self.assertTrue(result["coverage"]["history_files_not_read"])
        self.assertNotIn("must-not-be-read", prepared.stdout + prepared.stderr)

    def test_first_run_does_not_commit_empty_bounded_window(self) -> None:
        for number in range(32):
            path = self.codex / f"incomplete-{number:02d}.jsonl"
            self.write_jsonl(
                path,
                [
                    {
                        "type": "session_meta",
                        "payload": {
                            "id": f"incomplete-{number}",
                            "cwd": str(self.project),
                        },
                    },
                    {
                        "type": "event_msg",
                        "payload": {
                            "type": "user_message",
                            "message": "unfinished",
                        },
                    },
                ],
            )
            os.utime(path, (2_000 + number, 2_000 + number))
        old = self.codex / "old-completed.jsonl"
        self.write_jsonl(
            old,
            [
                {
                    "type": "session_meta",
                    "payload": {"id": "old", "cwd": str(self.project)},
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": "old-turn",
                        "last_agent_message": "older completed work",
                    },
                },
            ],
        )
        os.utime(old, (1_000, 1_000))

        prepared = self.prepare("candidate-empty-window.json")

        self.assertEqual(prepared.returncode, 2)
        result = json.loads(prepared.stdout)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["commit_allowed_after_successful_report"])

    def test_unknown_matching_format_does_not_create_state(self) -> None:
        self.write_jsonl(
            self.codex / "unknown.jsonl",
            [
                {
                    "type": "session_meta",
                    "payload": {"id": "unknown", "cwd": str(self.project)},
                },
                {"type": "future_event", "payload": {"answer": 42}},
            ],
        )

        prepared = self.prepare("candidate-unknown.json")

        self.assertEqual(prepared.returncode, 2)
        result = json.loads(prepared.stdout)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["commit_allowed_after_successful_report"])
        self.assertFalse((self.local / "state.json").exists())

    def test_nested_git_project_is_excluded(self) -> None:
        self.write_sessions()
        (self.project / ".git").mkdir()
        nested = self.project / "nested"
        (nested / ".git").mkdir(parents=True)
        self.write_jsonl(
            self.codex / "nested.jsonl",
            [
                {
                    "type": "session_meta",
                    "payload": {"id": "nested", "cwd": str(nested)},
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": "nested-turn",
                        "last_agent_message": "Must not be selected",
                    },
                },
            ],
        )

        prepared = self.prepare("candidate-nested.json")

        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout)["coverage"]["selected_parts"], 2)
        self.assertNotIn("Must not be selected", prepared.stdout)

    def test_all_mode_is_paginated_without_committing(self) -> None:
        self.write_sessions()
        common = (
            "prepare",
            "--project-root",
            str(self.project),
            "--state",
            str(self.local / "state.json"),
            "--mode",
            "all",
            "--limit",
            "1",
            "--codex-root",
            str(self.codex),
            "--claude-root",
            str(self.claude),
        )

        first = self.run_script(
            *common,
            "--candidate",
            str(self.local / "candidate-all-one.json"),
        )
        second = self.run_script(
            *common,
            "--offset",
            "1",
            "--candidate",
            str(self.local / "candidate-all-two.json"),
        )

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        first_result = json.loads(first.stdout)
        second_result = json.loads(second.stdout)
        self.assertTrue(first_result["coverage"]["more_parts_available"])
        self.assertEqual(first_result["coverage"]["next_offset"], 1)
        self.assertFalse(second_result["coverage"]["more_parts_available"])
        self.assertFalse(first_result["commit_allowed_after_successful_report"])
        self.assertFalse((self.local / "state.json").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink is unavailable")
    def test_symlink_state_is_rejected(self) -> None:
        self.write_sessions()
        self.local.mkdir(parents=True)
        external = self.root / "external-state.json"
        external.write_text("{}", encoding="utf-8")
        os.symlink(external, self.local / "state.json")

        prepared = self.prepare("candidate-symlink.json")

        self.assertEqual(prepared.returncode, 2)
        self.assertIn("символ", prepared.stderr.lower())


if __name__ == "__main__":
    unittest.main()
