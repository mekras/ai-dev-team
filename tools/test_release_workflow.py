import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "packages/ai-dev-team"
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
STEPS = {step["name"]: step for step in WORKFLOW["jobs"]["publish"]["steps"]}


class ReleaseWorkflowTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.remote = self.root / "remote.git"
        self.checkout = self.root / "marketplace"
        self.git_env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1",
                            GIT_CONFIG_GLOBAL=os.devnull)
        self.git(self.root, "init", "--bare", "--initial-branch=master", self.remote)
        self.git(self.root, "clone", self.remote, self.checkout)
        self.git(self.checkout, "config", "user.name", "Test")
        self.git(self.checkout, "config", "user.email", "test@example.invalid")
        self.package = self.checkout / PACKAGE
        self.package.mkdir(parents=True)
        self.manifest = self.package / "apm.yml"
        for version in ("1.3.0", "1.3.1"):
            self.write_version(version)
            self.git(self.checkout, "add", ".")
            self.git(self.checkout, "commit", "-m", version)
            self.git(self.checkout, "tag", f"ai-dev-team--v{version}")
        self.git(self.checkout, "push", "--tags", "origin", "master")

    def git(self, cwd, *args):
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self.git_env, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    def write_version(self, version):
        self.manifest.write_text(f"version: {version}\n", encoding="utf-8")

    def publish(self, version):
        return subprocess.run(
            ["bash", "-c", STEPS["Опубликовать версию пакета"]["run"]],
            cwd=self.checkout, text=True, capture_output=True,
            env=self.git_env | {"PACKAGE_NAME": "ai-dev-team", "RELEASE_VERSION": version},
        )

    def remote_refs(self):
        return self.git(self.remote, "show-ref")

    def test_publishes_new_version(self):
        self.write_version("1.3.2")
        result = self.publish("1.3.2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git(self.remote, "rev-parse", "master"),
                         self.git(self.remote, "rev-parse", "ai-dev-team--v1.3.2^{}"))
        self.assertEqual(self.git(self.remote, "show", f"master:{PACKAGE}/apm.yml"),
                         "version: 1.3.2")

    def test_repeating_old_release_preserves_remote_refs(self):
        before = self.remote_refs()
        self.write_version("1.3.0")
        result = self.publish("1.3.0")
        self.assertEqual(self.remote_refs(), before)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_conflicting_package_for_existing_tag_preserves_remote_refs(self):
        before = self.remote_refs()
        self.write_version("1.3.0")
        (self.package / "README.md").write_text("Changed\n", encoding="utf-8")
        result = self.publish("1.3.0")
        self.assertEqual(self.remote_refs(), before)
        self.assertNotEqual(result.returncode, 0)

    def test_atomic_push_failure_preserves_remote_refs(self):
        before = self.remote_refs()
        self.git(self.remote, "config", "receive.advertiseAtomic", "false")
        self.write_version("1.3.2")
        result = self.publish("1.3.2")
        self.assertEqual(self.remote_refs(), before)
        self.assertNotEqual(result.returncode, 0)


class ReleaseVersionTest(unittest.TestCase):
    def test_documented_tag_examples_pass_release_check(self):
        rules = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        rule = next(line for line in rules.splitlines()
                    if "и не должна иметь приставку" in line)
        versions = re.findall(r"`([0-9][^`]+)`", rule)
        self.assertGreaterEqual(len(versions), 3)
        script = STEPS["Проверить готовность выпуска"]["run"]
        checks = script.removesuffix("APM_PUBLIC_RELEASE=1 apm run tests\n")
        self.assertNotEqual(script, checks)
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for version in versions:
                with self.subTest(version=version):
                    (root / "apm.yml").write_text(f"version: {version}\n")
                    (root / "CHANGELOG.md").write_text(f"## [{version}]\n")
                    result = subprocess.run(
                        ["bash", "-c", checks], cwd=root,
                        env=dict(os.environ, RELEASE_VERSION=version),
                        capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
