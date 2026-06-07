# Извлечённые утверждения: `REUS`

## Основание

- Источник учёта: `knowledge/inventory/REUS.md`
- Первичный источник: `knowledge/primary/REUS/source.md`
- Индекс первичных страниц: `knowledge/primary/REUS/page-index.tsv`
- Нормализованный слой: `knowledge/normalized/REUS/source.md`
- Атрибуция и правовой статус: `knowledge/source-attribution.md`
- Дата извлечения: `2026-06-05`

## Назначение

Фиксация первых проверяемых наблюдений по REUSE.

## Утверждения

### REUS-001

- Статус: `ready_for_review`
- Утверждение: REUSE связывает выбор лицензии проекта с использованием SPDX
  License List и хранением текстов лицензий в каталоге `LICENSES/`.
- Фрагмент источника: разделы FAQ про шаг `Choose and provide licenses`.
- Область применения: организация лицензий в репозитории.
- Опора в артефактах:
  - `knowledge/primary/REUS/pages/faq/index.html`
  - `knowledge/normalized/REUS/source.md`

### REUS-002

- Статус: `ready_for_review`
- Утверждение: REUSE уделяет отдельное внимание лицензионной информации в
  заголовках файлов и объясняет, зачем она нужна даже при наличии VCS.
- Фрагмент источника: FAQ про `copyright`, `license headers` и причины их
  сохранения.
- Область применения: разметка файлов и проверка полноты сведений.
- Опора в артефактах:
  - `knowledge/primary/REUS/pages/faq/index.html`
  - `knowledge/normalized/REUS/source.md`

### REUS-003

- Статус: `ready_for_review`
- Утверждение: FAQ REUSE рассматривает лицензии зависимостей, нестандартные
  лицензии и исключения как отдельные практические случаи, требующие явной
  обработки.
- Фрагмент источника: вопросы `dependencies licenses`, `custom license` и
  `custom exception`.
- Область применения: работа со смешанными и нестандартными сценариями.
- Опора в артефактах:
  - `knowledge/primary/REUS/pages/faq/index.html`
  - `knowledge/normalized/REUS/source.md`

### REUS-004

- Статус: `ready_for_review`
- Утверждение: REUSE не предлагает создавать custom exception отдельно, а
  советует оформлять такой случай как custom license, встраивающую исключение.
- Фрагмент источника: вопрос `custom exception`.
- Область применения: обработка нетиповых лицензионных исключений.
- Опора в артефактах:
  - `knowledge/primary/REUS/pages/faq/index.html`
  - `knowledge/normalized/REUS/source.md`

### REUS-005

- Статус: `ready_for_review`
- Утверждение: FAQ REUSE отдельно объясняет, почему история VCS не считается
  заменой файловых сведений о copyright и лицензии.
- Фрагмент источника: вопросы `why-care` и `vcs-copyright`.
- Область применения: обоснование сохранения лицензионных заголовков в файлах.
- Опора в артефактах:
  - `knowledge/primary/REUS/pages/faq/index.html`
  - `knowledge/normalized/REUS/source.md`
