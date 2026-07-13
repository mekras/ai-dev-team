#!/usr/bin/env python3
"""Проверить сценарии результата с текущей раскладкой корпуса знаний."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = (
    ROOT
    / ".agents/skills/ai-setup-apm/scripts/eval-tools"
    / "validate-skill-result-evals.py"
)

spec = importlib.util.spec_from_file_location("_upstream_result_validator", UPSTREAM)
if spec is None or spec.loader is None:
    raise SystemExit(f"Не удалось загрузить средство проверки: {UPSTREAM}")

validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)

# Корпус версии 0.14 хранит единицы источников в items, а прежний договор
# средства проверки допускал только pages. Оба варианта являются переносимыми.
validator.PORTABLE_STATEMENT_PATH_RE = re.compile(
    r"^knowledge/data/[a-z0-9][a-z0-9-]*/(?:pages|items)/.+/statements\.yml$"
)

raise SystemExit(validator.main())
