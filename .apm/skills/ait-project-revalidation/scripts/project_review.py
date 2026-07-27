#!/usr/bin/env python3
"""Инвентаризация и локальное состояние полной проверки проекта."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
TERMINAL_STATES = {"complete", "complete_with_accepted_risks"}
PROCESS_STATES = {
    "running",
    "waiting_decision",
    "blocked",
    "interrupted",
    *TERMINAL_STATES,
}
STAGE_STATUSES = {"pending", "running", "complete"}
PARTICIPATION = {
    "check",
    "constraint",
    "preparation",
    "correction",
    "not_applicable",
}
TRANSITIONS = {
    "running": PROCESS_STATES,
    "waiting_decision": {"running", "blocked", "interrupted"},
    "blocked": {"running", "interrupted"},
    "interrupted": {"running", "blocked"},
    "complete": set(),
    "complete_with_accepted_risks": set(),
}
CLASSIFICATION = (
    Path(__file__).resolve().parents[1] / "references" / "capabilities.json"
)


class ReviewError(RuntimeError):
    """Нарушен договор полной проверки."""


def now() -> str:
    return datetime.now(UTC).isoformat()


def run_git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewError(f"git {' '.join(arguments)}: {detail}")
    return completed.stdout


def repository_root(start: Path) -> Path:
    output = run_git(start.resolve(), "rev-parse", "--show-toplevel")
    return Path(output.decode().strip()).resolve()


def state_path(repo: Path) -> Path:
    relative = run_git(
        repo,
        "rev-parse",
        "--git-path",
        "ai-dev-team/project-review-state.json",
    ).decode().strip()
    path = Path(relative)
    if not path.is_absolute():
        path = repo / path
    return path.resolve()


def file_hash(path: Path) -> str:
    if path.is_symlink():
        payload = os.readlink(path).encode("utf-8", errors="surrogateescape")
    else:
        payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def repository_snapshot(repo: Path) -> dict[str, Any]:
    output = run_git(
        repo,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    )
    files: dict[str, str] = {}
    for raw_name in output.split(b"\0"):
        if not raw_name:
            continue
        name = raw_name.decode("utf-8", errors="surrogateescape")
        parts = Path(name).parts
        if ".git" in parts:
            continue
        path = repo / name
        if path.is_file() or path.is_symlink():
            files[name] = file_hash(path)
    digest = stable_hash(files)
    return {"id": digest, "files": files}


def stable_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReviewError(f"не найден файл {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReviewError(f"ошибка JSON в {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReviewError(f"корень {path} должен быть объектом")
    return value


def classification_name(entry: dict[str, Any]) -> str:
    path = Path(entry["path"])
    if entry["kind"] == "skill":
        return path.name
    if entry["kind"] == "role":
        return path.name.removesuffix(".agent.md")
    return path.name.removesuffix(".instructions.md")


def load_core_classification(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = CLASSIFICATION
    data = load_json(path)
    if data.get("version") != SCHEMA_VERSION:
        raise ReviewError("неподдерживаемая версия классификации")
    return data


def dependency_owners(lock_path: Path) -> dict[str, str]:
    if not lock_path.is_file():
        return {}
    owners: dict[str, str] = {}
    owner: str | None = None
    in_files = False
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if line.startswith("- repo_url:"):
            owner = stripped.split(":", 1)[1].strip().strip("'\"")
            in_files = False
        elif stripped == "deployed_files:":
            in_files = True
        elif stripped == "deployed_file_hashes:":
            in_files = False
        elif in_files and stripped.startswith("- ") and owner:
            owners[stripped[2:].strip().strip("'\"")] = owner
    return owners


def frontmatter_description(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    header = text[4:end]
    lines = header.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value and value not in {">", "|"}:
            return value.strip("'\"")
        continuation: list[str] = []
        for nested in lines[index + 1 :]:
            if nested and not nested.startswith((" ", "\t")):
                break
            if nested.strip():
                continuation.append(nested.strip())
        return " ".join(continuation) or None
    return None


def first_paragraph(text: str) -> str | None:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end >= 0:
            text = text[end + 4 :]
    paragraphs = re.split(r"\n\s*\n", text)
    for paragraph in paragraphs:
        value = " ".join(
            line.strip()
            for line in paragraph.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "---"))
        )
        if value:
            return value
    return None


def component_description(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if path.suffix == ".toml":
        try:
            value = tomllib.loads(text).get("description")
        except tomllib.TOMLDecodeError:
            value = None
        return value if isinstance(value, str) and value.strip() else None
    return frontmatter_description(text) or first_paragraph(text)


def candidate_components(repo: Path) -> list[tuple[str, str, Path]]:
    candidates: list[tuple[str, str, Path]] = []
    for base in (".agents/skills", ".claude/skills", ".codex/skills"):
        for path in sorted((repo / base).glob("*/SKILL.md")):
            candidates.append(("skill", path.parent.name, path))
    for path in sorted((repo / ".claude/agents").glob("*.md")):
        candidates.append(("role", path.stem, path))
    for path in sorted((repo / ".codex/agents").glob("*.toml")):
        candidates.append(("role", path.stem, path))
    for path in sorted((repo / ".agents/agents").glob("*.md")):
        candidates.append(("role", path.stem, path))
    for path in sorted((repo / ".claude/rules").glob("*.md")):
        candidates.append(("rule", path.stem, path))
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = repo / name
        if path.is_file():
            candidates.append(("rule", path.stem, path))
    return candidates


def inventory(
    repo: Path,
    classification: Path | None = None,
) -> dict[str, Any]:
    core = load_core_classification(classification)
    core_by_key = {
        (entry["kind"], classification_name(entry)): entry
        for entry in core["capabilities"]
    }
    owners = dependency_owners(repo / "apm.lock.yaml")
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for kind, name, path in candidate_components(repo):
        key = (kind, name)
        relative = path.relative_to(repo).as_posix()
        item = merged.setdefault(
            key,
            {
                "id": f"{kind}:{name}",
                "kind": kind,
                "name": name,
                "paths": [],
                "origins": [],
                "descriptions": [],
                "input_hashes": {},
            },
        )
        item["paths"].append(relative)
        item["input_hashes"][relative] = file_hash(path)
        description = component_description(path)
        if description and description not in item["descriptions"]:
            item["descriptions"].append(description)
        if key in core_by_key:
            origin = "core"
        elif relative in owners:
            origin = f"dependency:{owners[relative]}"
        else:
            origin = "project"
        if origin not in item["origins"]:
            item["origins"].append(origin)

    result: list[dict[str, Any]] = []
    for key, item in sorted(merged.items()):
        core_entry = core_by_key.get(key)
        item["paths"].sort()
        item["origins"].sort()
        item["descriptions"].sort()
        item["input_hash"] = stable_hash(item.pop("input_hashes"))
        if core_entry:
            item["origin"] = "core"
            item["classification"] = {
                "status": "classified",
                "capability_id": core_entry["id"],
                "participation": core_entry["participation"],
                "stage": core_entry.get("stage"),
                "applicability": core_entry["applicability"],
                "purpose": core_entry["purpose"],
            }
        else:
            dependency_origins = [
                value for value in item["origins"] if value.startswith("dependency:")
            ]
            item["origin"] = dependency_origins[0] if dependency_origins else "project"
            item["classification"] = {
                "status": "unclassified" if item["descriptions"] else "unknown",
                "capability_id": None,
                "participation": None,
                "stage": None,
                "applicability": None,
                "purpose": item["descriptions"][0] if item["descriptions"] else None,
            }
        result.append(item)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "classification_version": core["version"],
        "capabilities": result,
    }
    payload["fingerprint"] = stable_hash(payload)
    return payload


def workspace_id(repo: Path) -> str:
    git_dir = run_git(repo, "rev-parse", "--absolute-git-dir").decode().strip()
    return stable_hash({"repo": str(repo), "git_dir": git_dir})


def initial_capability_decisions(
    capability_inventory: dict[str, Any],
) -> dict[str, Any]:
    decisions: dict[str, Any] = {}
    for item in capability_inventory["capabilities"]:
        classification = item["classification"]
        decisions[item["id"]] = {
            "input_hash": item["input_hash"],
            "origin": item["origin"],
            "status": classification["status"],
            "participation": classification["participation"],
            "stage": classification["stage"],
            "applicable": (
                True if classification.get("applicability") == "always" else None
            ),
            "reason": (
                "Поставляемая классификация требует применения."
                if classification.get("applicability") == "always"
                else None
            ),
        }
    return decisions


def new_state(
    repo: Path,
    mode: str,
    controller: str | None,
    controller_proven: bool,
) -> dict[str, Any]:
    if mode == "managed" and not controller_proven:
        raise ReviewError(
            "управляемый режим требует доказанного контроллера продолжения",
        )
    capability_inventory = inventory(repo)
    stages = load_core_classification()["stages"]
    timestamp = now()
    state = {
        "schema_version": SCHEMA_VERSION,
        "workspace_id": workspace_id(repo),
        "repo": str(repo),
        "mode": mode,
        "controller": {
            "name": controller,
            "proven": controller_proven,
        },
        "status": "running",
        "current_stage": stages[0],
        "next_action": "Классифицировать внешние возможности.",
        "snapshot": repository_snapshot(repo),
        "capability_inventory": capability_inventory,
        "capability_decisions": initial_capability_decisions(capability_inventory),
        "stages": {
            stage: {
                "status": "running" if index == 0 else "pending",
                "input_snapshot": None,
                "capabilities": [],
            }
            for index, stage in enumerate(stages)
        },
        "findings": {},
        "checks": {},
        "history": [
            {
                "at": timestamp,
                "event": "initialized",
                "status": "running",
            },
        ],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    return state


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value["updated_at"] = now()
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_state(repo: Path) -> tuple[Path, dict[str, Any]]:
    path = state_path(repo)
    state = load_json(path)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ReviewError("неподдерживаемая версия состояния")
    if state.get("workspace_id") != workspace_id(repo):
        raise ReviewError("состояние относится к другому рабочему каталогу")
    return path, state


def add_history(state: dict[str, Any], event: str, **details: Any) -> None:
    state["history"].append({"at": now(), "event": event, **details})


def set_next(state: dict[str, Any], action: str) -> None:
    if state["status"] in TERMINAL_STATES:
        raise ReviewError("конечное состояние не принимает следующее действие")
    state["next_action"] = action
    add_history(state, "next_action", action=action)


def classify_capability(state: dict[str, Any], args: argparse.Namespace) -> None:
    if args.id not in state["capability_decisions"]:
        raise ReviewError(f"неизвестная возможность {args.id}")
    if args.participation not in PARTICIPATION:
        raise ReviewError(f"неизвестный вид участия {args.participation}")
    if args.stage and args.stage not in state["stages"]:
        raise ReviewError(f"неизвестный этап {args.stage}")
    if args.participation == "not_applicable" and args.applicable != "no":
        raise ReviewError("not_applicable требует applicable no")
    decision = state["capability_decisions"][args.id]
    decision.update(
        {
            "status": "classified",
            "participation": args.participation,
            "stage": args.stage,
            "applicable": args.applicable == "yes",
            "reason": args.reason,
        },
    )
    if args.applicable == "unknown":
        decision["status"] = "unknown"
        decision["applicable"] = None
    if decision["applicable"] and args.stage:
        capabilities = state["stages"][args.stage]["capabilities"]
        if args.id not in capabilities:
            capabilities.append(args.id)
            capabilities.sort()
    add_history(state, "capability_classified", capability=args.id)


def record_finding(state: dict[str, Any], args: argparse.Namespace) -> None:
    if args.id in state["findings"]:
        raise ReviewError(f"проблема {args.id} уже существует")
    if args.stage not in state["stages"]:
        raise ReviewError(f"неизвестный этап {args.stage}")
    state["findings"][args.id] = {
        "stage": args.stage,
        "summary": args.summary,
        "blocking": args.blocking,
        "evidence": args.evidence,
        "group": args.group,
        "allowed_paths": sorted(set(args.allowed_path)),
        "verification": args.verification,
        "status": "open",
        "decision": None,
    }
    if args.blocking:
        state["status"] = "waiting_decision"
        state["next_action"] = f"Получить решение по проблеме {args.id}."
    add_history(state, "finding_recorded", finding=args.id)


def record_decision(state: dict[str, Any], args: argparse.Namespace) -> None:
    finding = state["findings"].get(args.finding)
    if not finding:
        raise ReviewError(f"неизвестная проблема {args.finding}")
    group = finding.get("group")
    targets = {
        identifier: value
        for identifier, value in state["findings"].items()
        if identifier == args.finding or (group and value.get("group") == group)
    }
    if args.decision in {"accept", "defer"} and any(
        value["blocking"] for value in targets.values()
    ):
        raise ReviewError("блокирующую проблему нельзя принять или отложить")
    if args.decision in {"accept", "defer"} and (
        not args.reason or not args.revisit_condition
    ):
        raise ReviewError(
            "принятие риска требует причины и условия пересмотра",
        )
    if args.decision == "fix" and any(
        not value["allowed_paths"] or not value["verification"]
        for value in targets.values()
    ):
        raise ReviewError(
            "исправление требует разрешённых путей и способа проверки",
        )
    if args.decision == "not_applicable" and not args.reason:
        raise ReviewError("неприменимость требует причины")
    for value in targets.values():
        value["decision"] = {
            "value": args.decision,
            "reason": args.reason,
            "revisit_condition": args.revisit_condition,
            "at": now(),
        }
        if args.decision == "fix":
            value["status"] = "approved"
        elif args.decision in {"accept", "defer"}:
            value["status"] = "accepted"
        else:
            value["status"] = "not_applicable"
    if args.decision == "fix":
        state["status"] = "running"
        state["next_action"] = (
            f"Исправить группу {group}."
            if group
            else f"Исправить проблему {args.finding}."
        )
    elif args.decision in {"accept", "defer"}:
        state["status"] = "running"
    else:
        state["status"] = "running"
    add_history(
        state,
        "decision_recorded",
        finding=args.finding,
        group=group,
        targets=sorted(targets),
        decision=args.decision,
    )


def record_check(state: dict[str, Any], args: argparse.Namespace) -> None:
    if not args.capability and not args.finding:
        raise ReviewError("проверка должна ссылаться на возможность или проблему")
    if args.capability and args.capability not in state["capability_decisions"]:
        raise ReviewError(f"неизвестная возможность {args.capability}")
    if args.finding and args.finding not in state["findings"]:
        raise ReviewError(f"неизвестная проблема {args.finding}")
    if args.stage not in state["stages"]:
        raise ReviewError(f"неизвестный этап {args.stage}")
    state["checks"][args.id] = {
        "stage": args.stage,
        "capability": args.capability,
        "finding": args.finding,
        "status": args.status,
        "evidence": args.evidence,
        "input_snapshot": state["snapshot"]["id"],
    }
    if args.finding and args.status == "passed":
        state["findings"][args.finding]["status"] = "resolved"
    add_history(state, "check_recorded", check=args.id, status=args.status)


def validate_completion(state: dict[str, Any], target: str) -> None:
    incomplete_stages = [
        name
        for name, value in state["stages"].items()
        if value["status"] != "complete"
    ]
    if incomplete_stages:
        raise ReviewError(
            "не завершены этапы: " + ", ".join(incomplete_stages),
        )
    unknown = [
        name
        for name, value in state["capability_decisions"].items()
        if value["status"] != "classified" or value["applicable"] is None
    ]
    if unknown:
        raise ReviewError(
            "не классифицированы возможности: " + ", ".join(unknown),
        )
    checked_capabilities = {
        check["capability"]
        for check in state["checks"].values()
        if check["status"] in {"passed", "not_applicable"}
    }
    unchecked = [
        name
        for name, value in state["capability_decisions"].items()
        if value["applicable"]
        and value["participation"] == "check"
        and name not in checked_capabilities
    ]
    if unchecked:
        raise ReviewError(
            "нет результата применимых проверок: " + ", ".join(unchecked),
        )
    unresolved = [
        name
        for name, value in state["findings"].items()
        if value["status"] not in {"resolved", "not_applicable", "accepted"}
    ]
    if unresolved:
        raise ReviewError("не закрыты проблемы: " + ", ".join(unresolved))
    failed = [
        name
        for name, value in state["checks"].items()
        if value["status"] not in {"passed", "not_applicable"}
    ]
    if failed:
        raise ReviewError("не пройдены проверки: " + ", ".join(failed))
    accepted = [
        name
        for name, value in state["findings"].items()
        if value["status"] == "accepted"
    ]
    if target == "complete" and accepted:
        raise ReviewError(
            "complete не допускает принятые риски: " + ", ".join(accepted),
        )
    if target == "complete_with_accepted_risks" and not accepted:
        raise ReviewError("нет принятого риска для выбранного конечного статуса")


def transition(state: dict[str, Any], target: str, action: str | None) -> None:
    source = state["status"]
    if target not in PROCESS_STATES:
        raise ReviewError(f"неизвестное состояние {target}")
    if target not in TRANSITIONS[source]:
        raise ReviewError(f"недопустимый переход {source} → {target}")
    if target in TERMINAL_STATES:
        validate_completion(state, target)
        state["next_action"] = None
    elif action:
        state["next_action"] = action
    state["status"] = target
    add_history(state, "transition", source=source, target=target)


def set_stage(state: dict[str, Any], name: str, status: str) -> None:
    if name not in state["stages"]:
        raise ReviewError(f"неизвестный этап {name}")
    if status not in STAGE_STATUSES:
        raise ReviewError(f"неизвестное состояние этапа {status}")
    if status == "complete":
        unresolved = [
            identifier
            for identifier, finding in state["findings"].items()
            if finding["stage"] == name
            and finding["status"] not in {"resolved", "not_applicable", "accepted"}
        ]
        if unresolved:
            raise ReviewError(
                "этап содержит нерешённые проблемы: " + ", ".join(unresolved),
            )
        undecided = [
            identifier
            for identifier, decision in state["capability_decisions"].items()
            if decision.get("stage") == name
            and (
                decision["status"] != "classified"
                or decision["applicable"] is None
            )
        ]
        if undecided:
            raise ReviewError(
                "этап содержит неклассифицированные возможности: "
                + ", ".join(undecided),
            )
        checked = {
            check["capability"]
            for check in state["checks"].values()
            if check["stage"] == name
            and check["status"] in {"passed", "not_applicable"}
        }
        unchecked = [
            identifier
            for identifier, decision in state["capability_decisions"].items()
            if decision.get("stage") == name
            and decision["applicable"]
            and decision["participation"] == "check"
            and identifier not in checked
        ]
        if unchecked:
            raise ReviewError(
                "этап не применил проверки: " + ", ".join(unchecked),
            )
        state["stages"][name]["input_snapshot"] = state["snapshot"]["id"]
    state["stages"][name]["status"] = status
    if status == "running":
        state["current_stage"] = name
    add_history(state, "stage_status", stage=name, status=status)


def changed_paths(old: dict[str, str], new: dict[str, str]) -> list[str]:
    return sorted(
        name
        for name in set(old) | set(new)
        if old.get(name) != new.get(name)
    )


def approved_paths(state: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for finding in state["findings"].values():
        if finding["status"] == "approved":
            result.update(finding["allowed_paths"])
    return result


def refresh(state: dict[str, Any], repo: Path) -> None:
    new_snapshot = repository_snapshot(repo)
    changed = changed_paths(
        state["snapshot"]["files"],
        new_snapshot["files"],
    )
    allowed = approved_paths(state)
    external = [name for name in changed if name not in allowed]
    if external:
        state["pending_snapshot"] = new_snapshot
        state["status"] = "interrupted"
        state["next_action"] = "Разобрать внешние изменения области Git."
        add_history(state, "external_change", paths=external)
        return
    state["snapshot"] = new_snapshot

    old_inventory = state["capability_inventory"]
    new_inventory = inventory(repo)
    if old_inventory["fingerprint"] == new_inventory["fingerprint"]:
        add_history(state, "refreshed", changed_paths=changed)
        return

    old_decisions = state["capability_decisions"]
    state["capability_inventory"] = new_inventory
    state["capability_decisions"] = initial_capability_decisions(new_inventory)
    for identifier, decision in state["capability_decisions"].items():
        previous = old_decisions.get(identifier)
        if previous and previous["input_hash"] == decision["input_hash"]:
            state["capability_decisions"][identifier] = previous

    changed_capabilities = [
        identifier
        for identifier, decision in state["capability_decisions"].items()
        if identifier not in old_decisions
        or old_decisions[identifier]["input_hash"] != decision["input_hash"]
    ]
    unknown = [
        identifier
        for identifier in changed_capabilities
        if state["capability_decisions"][identifier]["status"] != "classified"
    ]
    for identifier in changed_capabilities:
        decision = state["capability_decisions"][identifier]
        stage = decision.get("stage")
        if stage and stage in state["stages"]:
            state["stages"][stage]["status"] = "pending"
    if unknown:
        state["status"] = "blocked"
        state["next_action"] = "Классифицировать изменившиеся возможности."
    else:
        state["status"] = "running"
        state["next_action"] = "Повторить открытые изменением этапы."
    add_history(
        state,
        "capabilities_changed",
        capabilities=changed_capabilities,
    )


def validate_state(state: dict[str, Any]) -> None:
    if state.get("status") not in PROCESS_STATES:
        raise ReviewError("состояние процесса неизвестно")
    if state["status"] in TERMINAL_STATES:
        validate_completion(state, state["status"])
    elif not state.get("next_action"):
        raise ReviewError("активное состояние требует next_action")


def add_common_repo(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", type=Path, default=Path.cwd())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    inventory_parser = commands.add_parser("inventory")
    add_common_repo(inventory_parser)
    inventory_parser.add_argument("--classification", type=Path, default=CLASSIFICATION)

    init_parser = commands.add_parser("init")
    add_common_repo(init_parser)
    init_parser.add_argument("--mode", choices=("managed", "manual"), required=True)
    init_parser.add_argument("--controller")
    init_parser.add_argument("--controller-proven", action="store_true")

    for name in ("show", "validate", "refresh"):
        subparser = commands.add_parser(name)
        add_common_repo(subparser)

    next_parser = commands.add_parser("next")
    add_common_repo(next_parser)
    next_parser.add_argument("--action", required=True)

    transition_parser = commands.add_parser("transition")
    add_common_repo(transition_parser)
    transition_parser.add_argument("--to", required=True)
    transition_parser.add_argument("--next-action")

    stage_parser = commands.add_parser("stage")
    add_common_repo(stage_parser)
    stage_parser.add_argument("--name", required=True)
    stage_parser.add_argument("--status", required=True)

    classify_parser = commands.add_parser("classify")
    add_common_repo(classify_parser)
    classify_parser.add_argument("--id", required=True)
    classify_parser.add_argument("--participation", required=True)
    classify_parser.add_argument("--stage")
    classify_parser.add_argument(
        "--applicable",
        choices=("yes", "no", "unknown"),
        required=True,
    )
    classify_parser.add_argument("--reason", required=True)

    finding_parser = commands.add_parser("record-finding")
    add_common_repo(finding_parser)
    finding_parser.add_argument("--id", required=True)
    finding_parser.add_argument("--stage", required=True)
    finding_parser.add_argument("--summary", required=True)
    finding_parser.add_argument("--blocking", action="store_true")
    finding_parser.add_argument("--evidence", action="append", default=[])
    finding_parser.add_argument("--group")
    finding_parser.add_argument("--allowed-path", action="append", default=[])
    finding_parser.add_argument("--verification")

    decision_parser = commands.add_parser("record-decision")
    add_common_repo(decision_parser)
    decision_parser.add_argument("--finding", required=True)
    decision_parser.add_argument(
        "--decision",
        choices=("fix", "accept", "defer", "not_applicable"),
        required=True,
    )
    decision_parser.add_argument("--reason")
    decision_parser.add_argument("--revisit-condition")

    check_parser = commands.add_parser("record-check")
    add_common_repo(check_parser)
    check_parser.add_argument("--id", required=True)
    check_parser.add_argument("--stage", required=True)
    check_parser.add_argument("--capability")
    check_parser.add_argument("--finding")
    check_parser.add_argument(
        "--status",
        choices=("passed", "failed", "not_applicable"),
        required=True,
    )
    check_parser.add_argument("--evidence", action="append", default=[])
    return parser


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> None:
    args = build_parser().parse_args()
    try:
        repo = repository_root(args.repo)
        if args.command == "inventory":
            print_json(inventory(repo, args.classification.resolve()))
            return
        path = state_path(repo)
        if args.command == "init":
            if path.exists():
                raise ReviewError(f"состояние уже существует: {path}")
            state = new_state(
                repo,
                args.mode,
                args.controller,
                args.controller_proven,
            )
            atomic_write(path, state)
            print_json({"state_path": str(path), "state": state})
            return

        path, state = load_state(repo)
        if args.command == "show":
            print_json(state)
            return
        if args.command == "validate":
            validate_state(state)
            print("Project review state OK")
            return
        if args.command == "refresh":
            refresh(state, repo)
        elif args.command == "next":
            set_next(state, args.action)
        elif args.command == "transition":
            transition(state, args.to, args.next_action)
        elif args.command == "stage":
            set_stage(state, args.name, args.status)
        elif args.command == "classify":
            classify_capability(state, args)
        elif args.command == "record-finding":
            record_finding(state, args)
        elif args.command == "record-decision":
            record_decision(state, args)
        elif args.command == "record-check":
            record_check(state, args)
        validate_state(state)
        atomic_write(path, state)
        print_json({"state_path": str(path), "status": state["status"]})
    except ReviewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
