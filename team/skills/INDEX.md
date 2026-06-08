# Индекс навыков

Этот файл служит навигацией по переносимым навыкам каркаса.

## Правило применения

Индекс помогает выбрать навык, но не заменяет сам навык. Если задача совпадает с
назначением навыка из списка, агент обязан открыть соответствующий
`team/skills/<skill>/SKILL.md` и применить его правила до исполнения.

Для запросов вида «Настрой проект», «Начни новый проект», «Инициализируй
проект», «Подготовь новый репозиторий» и близких по смыслу запросов применяй
`team/skills/ait-init/SKILL.md`.

## Навыки

- `agents-md-review` — роль: `technical-writer` — проверка `AGENTS.md`.
  Источник: `github.com/mekras/ai-agent-supervisor`,
  `skills/agents-md-review/SKILL.md`.
- `ait-init` — роль: `project-manager` — начало нового проекта и создание
  минимальных стартовых файлов через диалог.
- `analysis` — роль: `analyst` — аналитический разбор.
- `ait-docs-concept` — роль: `technical-writer` — создание и сопровождение
  концепции проекта как главного ориентира проектной документации.
- `documentation-structure-audit` — роль: `technical-writer` — проверка текущей
  структуры документации и безопасные исправления.
- `documentation-structure-design` — роль: `technical-writer` — проектирование
  структуры документации проекта на основании данных и анализа.
- `documentation-structure-rules` — роль: `technical-writer` — фиксация и
  обновление правил, поддерживающих выбранную структуру документации.
- `knowledge-analysis` — роль: `analyst` — анализ корпуса знаний. Источник:
  `github.com/mekras/project-knowlege-corpus`,
  `skills/knowledge-analysis/SKILL.md`.
- `knowledge-corpus-add-source` — роль: `source-inventory` — техническое
  добавление нового источника в корпус знаний. Источник:
  `github.com/mekras/project-knowlege-corpus`,
  `skills/knowledge-corpus-add-source/SKILL.md`.
- `knowledge-corpus-validation` — роль: `source-inventory` — проверка корпуса
  знаний. Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/knowledge-corpus-validation/SKILL.md`.
- `primary-data-intake` — роль: `source-inventory` — приём первичных данных.
  Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/primary-data-intake/SKILL.md`.
- `primary-data-normalization` — роль: `normalizer` — нормализация первичных
  данных. Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/primary-data-normalization/SKILL.md`.
- `primary-data-pipeline` — роль: `cross-role` — координация конвейера первичных
  данных. Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/primary-data-pipeline/SKILL.md`.
- `primary-data-summary` — роль: `source-inventory` — сводка состояния первичных
  данных. Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/primary-data-summary/SKILL.md`.
- `private-project-knowledge` — роль: `source-inventory` — приватный локальный
  слой знаний проекта для агента вне VCS.
- `project-management` — роль: `project-manager` — маршрутизация задачи и выбор
  режима.
- `project-readme` — роль: `technical-writer` — сопровождение проектного
  `README.md`.
- `requirements-analysis` — роль: `requirements-analyst` — анализ и
  моделирование требований.
- `requirements-elicitation` — роль: `requirements-analyst` — выявление
  требований и работа с заинтересованными лицами.
- `requirements-management` — роль: `requirements-analyst` — приоритеты,
  изменения, статусы и связи требований.
- `requirements-specification` — роль: `requirements-analyst` — запись
  требований в проверяемом формате.
- `requirements-validation` — роль: `requirements-analyst` — проверка и
  подготовка требований к утверждению.
- `skill-development` — роль: `cross-role` — разработка навыков агента.
  Источник: `github.com/mekras/ai-agent-supervisor`,
  `skills/skill-development/SKILL.md`.
- `software-architecture` — роль: `software-architect` — архитектура ПО, ADR,
  компонентные границы и управление сложностью системы.
- `source-fact-extraction` — роль: `statement-extractor` — извлечение фактов из
  источников для последующего анализа. Источник:
  `github.com/mekras/project-knowlege-corpus`,
  `skills/source-fact-extraction/SKILL.md`.
- `source-impact-audit` — роль: `analyst` — анализ влияния источников на
  производные материалы. Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/source-impact-audit/SKILL.md`.
- `source-inventory` — роль: `source-inventory` — учёт и техническая
  синхронизация источников. Источник:
  `github.com/mekras/project-knowlege-corpus`,
  `skills/source-inventory/SKILL.md`.
- `statement-extraction` — роль: `statement-extractor` — извлечение утверждений
  из данных. Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/statement-extraction/SKILL.md`.
- `subagent-model-routing` — роль: `cross-role` — маршрутизация подагентов по
  моделям, стоимости, риску, качеству и правилам эскалации. Источник:
  `github.com/mekras/ai-agent-supervisor`,
  `skills/subagent-model-routing/SKILL.md`.
- `technical-writing` — роль: `technical-writer` — техническое письмо.
- `transcript-analysis` — роль: `technical-writer` — разбор и очистка
  стенограмм. Источник: `github.com/mekras/project-knowlege-corpus`,
  `skills/transcript-analysis/SKILL.md`.

## Правило размещения

Каждый навык хранится в собственном каталоге рядом с `references/`, `assets/` и
`evals/`, если они нужны этому навыку.
