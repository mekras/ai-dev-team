from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import runpy
import tempfile
import unittest


check = runpy.run_path(
    str(Path(__file__).with_name("check-subagent-role-routes.py"))
)["check"]


class CheckSubagentRoleRoutesTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.agents = self.root / ".apm/agents"
        self.agents.mkdir(parents=True)
        self.config = self.root / ".ai-dev-team/local/subagents.local.toml"
        self.config.parent.mkdir(parents=True)

    def add_product_role(self, name):
        (self.agents / f"{name}.agent.md").touch()

    def run_check(self, policy=None):
        if policy is not None:
            self.config.write_text(policy, encoding="utf-8")

        output = StringIO()
        errors = StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = check(self.root)

        if policy is not None:
            self.assertEqual(self.config.read_bytes(), policy.encode("utf-8"))
        return status, output.getvalue(), errors.getvalue()

    def test_aligned_routes_exclude_root_and_local_roles(self):
        self.add_product_role("project-manager")
        self.add_product_role("analyst")
        status, output, errors = self.run_check(
            '[[policy_runtime.routes]]\nrole = "analyst"\n'
            '[[policy_runtime.routes]]\nrole = "tester"\n'
            '[[policy_runtime.routes]]\nexecution_class = "deep_review"\n'
            '[roles.analyst]\n[roles.tester]\nlocal_only = true\n'
        )
        self.assertEqual(status, 0)
        self.assertEqual(errors, "")
        self.assertIn("соответствуют составу ролей", output)

    def test_reports_new_and_removed_roles_as_separate_findings(self):
        self.add_product_role("new-role")
        status, output, errors = self.run_check(
            '[[policy_runtime.routes]]\nrole = "old-role"\n[roles.old-role]\n'
        )
        self.assertEqual(status, 0)
        self.assertEqual(errors, "")
        self.assertIn("Предметные роли без настроенного маршрута: new-role.", output)
        self.assertIn("Маршруты к ролям, которых нет в продукте: old-role.", output)

    def test_role_without_assignment_does_not_count_as_configured(self):
        self.add_product_role("analyst")
        status, output, _ = self.run_check(
            '[[policy_runtime.routes]]\nrole = "analyst"\n'
        )
        self.assertEqual(status, 0)
        self.assertIn("Именованные маршруты без назначения: analyst.", output)
        self.assertNotIn("Маршруты к ролям, которых нет в продукте", output)

    def test_skips_checkout_without_local_policy(self):
        status, output, errors = self.run_check()
        self.assertEqual(status, 0)
        self.assertIn("локальной настройки нет", output)
        self.assertEqual(errors, "")
        self.assertFalse(self.config.exists())

    def test_invalid_toml_is_not_a_successful_check(self):
        status, output, errors = self.run_check("[roles")
        self.assertEqual(status, 1)
        self.assertEqual(output, "")
        self.assertIn("Не удалось сверить маршруты подагентов", errors)
