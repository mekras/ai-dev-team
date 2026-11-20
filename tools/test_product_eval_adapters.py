import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_adapter(filename, module_name):
    path = ROOT / "tools" / "product-eval-adapters" / f"{filename}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CODEX = load_adapter("codex", "product_eval_codex")
CLAUDE = load_adapter("claude", "product_eval_claude")


class ProductEvalAdapterTest(unittest.TestCase):
    def test_codex_collects_all_visible_agent_messages(self):
        events = [
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Маршрут"},
            },
            {
                "type": "item.completed",
                "item": {"type": "command_execution", "text": "не ответ"},
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Итог"},
            },
        ]
        self.assertEqual(
            "Маршрут\n\nИтог",
            CODEX.extract_answer(events, "последний ответ"),
        )

    def test_codex_uses_fallback_without_agent_messages(self):
        self.assertEqual("итог", CODEX.extract_answer([], "итог"))

    def test_claude_collects_text_blocks_from_all_assistant_messages(self):
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "План"},
                        {"type": "tool_use", "name": "Bash"},
                    ],
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Итог"}],
                },
            },
        ]
        self.assertEqual(
            "План\n\nИтог",
            CLAUDE.extract_answer(events, "последний ответ"),
        )

    def test_claude_trace_order_finds_first_routing_message_and_change(self):
        def assistant(*blocks):
            return {"type": "assistant", "message": {"content": list(blocks)}}

        events = [
            {"type": "system"},
            assistant({
                "type": "tool_use",
                "name": "Read",
                "input": {"file_path": ".agents/skills/ait-routing/SKILL.md"},
            }),
            assistant({"type": "text", "text": "План работы"}),
            assistant({
                "type": "tool_use",
                "name": "Edit",
                "input": {"file_path": "catalog.py"},
            }),
            assistant({"type": "text", "text": "Итог"}),
        ]
        self.assertEqual(
            {"routing_read": 0, "first_message": 1, "first_change": 2},
            CLAUDE.trace_order(events),
        )

    def test_claude_trace_order_reports_late_routing_read(self):
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Ответ"},
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {
                                "command": "cat .claude/skills/ait-routing/SKILL.md",
                            },
                        },
                    ],
                },
            },
        ]
        self.assertEqual(
            {"routing_read": 1, "first_message": 0, "first_change": None},
            CLAUDE.trace_order(events),
        )

    def test_codex_trace_order_finds_first_routing_message_and_change(self):
        events = [
            {"type": "thread.started", "thread_id": "t"},
            {
                "type": "item.started",
                "item": {
                    "type": "command_execution",
                    "command": "sed -n 1,200p .agents/skills/ait-routing/SKILL.md",
                },
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Вопрос"},
            },
            {"type": "item.completed", "item": {"type": "file_change"}},
        ]
        self.assertEqual(
            {"routing_read": 1, "first_message": 2, "first_change": 3},
            CODEX.trace_order(events),
        )

    def test_checksum_comparison_counts_as_routing_access(self):
        command = (
            "sha256sum .agents/skills/ait-routing/SKILL.md "
            ".agents/skills/ai-human-communication/SKILL.md"
        )
        codex_events = [
            {
                "type": "item.started",
                "item": {"type": "command_execution", "command": command},
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Ответ"},
            },
        ]
        claude_events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": command},
                        },
                        {"type": "text", "text": "Ответ"},
                    ],
                },
            },
        ]
        expected = {"routing_read": 0, "first_message": 1, "first_change": None}
        self.assertEqual(expected, CODEX.trace_order(codex_events))
        self.assertEqual(expected, CLAUDE.trace_order(claude_events))

    def test_codex_trace_order_without_routing_read(self):
        events = [
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Ответ"},
            },
        ]
        self.assertEqual(
            {"routing_read": None, "first_message": 0, "first_change": None},
            CODEX.trace_order(events),
        )

    def test_claude_uses_result_as_fallback(self):
        self.assertEqual("итог", CLAUDE.extract_answer([], "итог"))


if __name__ == "__main__":
    unittest.main()
