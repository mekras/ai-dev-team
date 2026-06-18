---
description:
  Connects a project to ai-dev-team through generated agent instructions.
applyTo: "**/*"
---

# Подключение ai-dev-team

Проект использует `ai-dev-team`.

## Каталог ai-dev-team

Используй первый установленный каталог `ai-dev-team` с обязательными файлами:

- `apm_modules/mekras/ai-dev-team`;
- `apm_modules/_local/ai-dev-team`.

Каталог подходит, если в нём есть файлы:

- `team/skills/project-management/SKILL.md`;
- `team/skills/INDEX.md`.

Если ни один каталог не подходит, остановись и сообщи о блокере.

## Маршрут задачи

Перед предметной работой открой `team/skills/project-management/SKILL.md` из
каталога `ai-dev-team`, выбери режим и покажи маршрут:

```text
Режим менеджера: лёгкий|полный.
Причина: ...
Маршрут: ...
```

Если маршрут выбирает навык из `team/skills/INDEX.md` найденного каталога
`ai-dev-team`, до исполнения открой соответствующий
`team/skills/<skill>/SKILL.md` и применяй его правила. Одного упоминания навыка
в маршруте недостаточно.

Для запросов вида «Настрой проект», «Перенастрой проект», «Начни новый проект»,
«Инициализируй проект», «Подготовь новый репозиторий» и близких по смыслу
запросов обязательно применяй `team/skills/ait-setup/SKILL.md` из каталога
`ai-dev-team`.
