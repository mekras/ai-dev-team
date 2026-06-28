# Извлечённые утверждения: `SPDX`

## Основание

- Источник учёта: `knowledge/inventory/SPDX.md`
- Первичный источник: `knowledge/primary/SPDX/source.md`
- Индекс первичных страниц: `knowledge/primary/SPDX/page-index.tsv`
- Нормализованный слой: `knowledge/normalized/SPDX/source.md`
- Атрибуция и правовой статус: `knowledge/source-attribution.md`
- Дата извлечения: `2026-06-05`

## Назначение

Фиксация первых наблюдений по справочному набору SPDX.

## Утверждения

### SPDX-001

- Статус: `ready_for_review`
- Утверждение: SPDX License List является частью спецификации SPDX и содержит
  короткий идентификатор, полное имя, текст лицензии и постоянный URL для каждой
  лицензии и исключения.
- Фрагмент источника: страница `licenses`.
- Область применения: выбор канонических идентификаторов лицензий.
- Опора в артефактах:
  - `knowledge/primary/SPDX/pages/licenses/index.html`
  - `knowledge/normalized/SPDX/source.md`

### SPDX-002

- Статус: `ready_for_review`
- Утверждение: исключения SPDX рассматриваются как отдельный справочный слой и
  используются в SPDX-выражениях через оператор `WITH`.
- Фрагмент источника: страницы `licenses`, `exceptions-index` и
  `license-expressions`.
- Область применения: запись исключений и составных лицензионных выражений.
- Опора в артефактах:
  - `knowledge/primary/SPDX/page-index.tsv`
  - `knowledge/normalized/SPDX/source.md`

### SPDX-003

- Статус: `ready_for_review`
- Утверждение: экосистема SPDX выделяет отдельные правила matching для
  определения того, когда текст можно считать совпадающим с лицензией или
  исключением из списка.
- Фрагмент источника: страница `matching-guidelines`.
- Область применения: проверка текстов лицензий и автоматизация сопоставления.
- Опора в артефактах:
  - `knowledge/primary/SPDX/pages/matching-guidelines/index.html`
  - `knowledge/normalized/SPDX/source.md`

### SPDX-004

- Статус: `ready_for_review`
- Утверждение: правила matching SPDX выделяют omitable и replaceable фрагменты
  текста лицензии как часть механики сопоставления.
- Фрагмент источника: пояснение на странице `licenses` о matching guidelines.
- Область применения: автоматическая проверка совпадения текстов лицензий.
- Опора в артефактах:
  - `knowledge/primary/SPDX/pages/licenses/index.html`
  - `knowledge/normalized/SPDX/source.md`
