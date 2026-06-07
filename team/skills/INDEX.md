# Индекс навыков

Этот файл служит навигацией по переносимым навыкам каркаса.

## Навыки

- `agents-md-review` — роль: `technical-writer` — проверка `AGENTS.md`.
  Источник: `vendor/ai-agent-supervisor/skills/agents-md-review/SKILL.md`.
- `analysis` — роль: `analyst` — аналитический разбор.
- `knowledge-analysis` — роль: `analyst` — анализ корпуса знаний. Источник:
  `vendor/project-knowlege-corpus/skills/knowledge-analysis/SKILL.md`.
- `knowledge-corpus-add-source` — роль: `source-inventory` — техническое
  добавление нового источника в корпус знаний. Источник:
  `vendor/project-knowlege-corpus/skills/knowledge-corpus-add-source/SKILL.md`.
- `knowledge-corpus-validation` — роль: `source-inventory` — проверка корпуса
  знаний. Источник:
  `vendor/project-knowlege-corpus/skills/knowledge-corpus-validation/SKILL.md`.
- `primary-data-intake` — роль: `source-inventory` — приём первичных данных.
  Источник:
  `vendor/project-knowlege-corpus/skills/primary-data-intake/SKILL.md`.
- `primary-data-normalization` — роль: `normalizer` — нормализация первичных
  данных. Источник:
  `vendor/project-knowlege-corpus/skills/primary-data-normalization/SKILL.md`.
- `primary-data-pipeline` — роль: `cross-role` — координация конвейера первичных
  данных. Источник:
  `vendor/project-knowlege-corpus/skills/primary-data-pipeline/SKILL.md`.
- `primary-data-summary` — роль: `source-inventory` — сводка состояния первичных
  данных. Источник:
  `vendor/project-knowlege-corpus/skills/primary-data-summary/SKILL.md`.
- `project-management` — роль: `project-manager` — маршрутизация задачи и выбор
  режима.
- `project-readme` — роль: `technical-writer` — сопровождение проектного
  `README.md`.
- `skill-development` — роль: `cross-role` — разработка навыков агента.
  Источник: `vendor/ai-agent-supervisor/skills/skill-development/SKILL.md`.
- `source-fact-extraction` — роль: `statement-extractor` — извлечение фактов из
  источников для последующего анализа. Источник:
  `vendor/project-knowlege-corpus/skills/source-fact-extraction/SKILL.md`.
- `source-impact-audit` — роль: `analyst` — анализ влияния источников на
  производные материалы. Источник:
  `vendor/project-knowlege-corpus/skills/source-impact-audit/SKILL.md`.
- `source-inventory` — роль: `source-inventory` — учёт и техническая
  синхронизация источников. Источник:
  `vendor/project-knowlege-corpus/skills/source-inventory/SKILL.md`.
- `statement-extraction` — роль: `statement-extractor` — извлечение утверждений
  из данных. Источник:
  `vendor/project-knowlege-corpus/skills/statement-extraction/SKILL.md`.
- `technical-writing` — роль: `technical-writer` — техническое письмо.
- `transcript-analysis` — роль: `technical-writer` — разбор и очистка
  стенограмм. Источник:
  `vendor/project-knowlege-corpus/skills/transcript-analysis/SKILL.md`.

## Правило размещения

Каждый навык хранится в собственном каталоге рядом с `references/`, `assets/` и
`evals/`, если они нужны этому навыку.
