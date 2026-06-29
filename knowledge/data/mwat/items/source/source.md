# Источник: `MWAT`

## Статус

Источник принят в корпус знаний как `external_reference` и объединяет две
связанные таксономии MITRE: `CWE` (слабости) и `CAPEC` (шаблоны атак). Корпус
хранит локатор, условия лицензии, нормализованный обзор и краткие утверждения,
но не хранит копию каталогов. Это живые каталоги; материал получается из
первоисточника по запросу.

## Происхождение

- Названия: `CWE` (Common Weakness Enumeration), `CAPEC` (Common Attack Pattern
  Enumeration and Classification)
- Издатель: The MITRE Corporation (при поддержке CISA/DHS)
- Канонические адреса: `https://cwe.mitre.org/`, `https://capec.mitre.org/`
- Тип источника: таксономии слабостей ПО (CWE) и шаблонов атак (CAPEC)
- Дата включения в корпус: `2026-06-25`

## Стратегия источника

- `storage_strategy: external_reference`
- `retrieval_mode: on_demand` (получать релевантную запись CWE/CAPEC по запросу)
- `copy_policy: external_reference`
- `requires_access_check: true` (соблюдать условия использования MITRE и
  товарные знаки при переносе)

## Что сохранено в корпусе

- паспорт: `knowledge/data/mwat/items/source/source.md`
- нормализованный обзор:
  `knowledge/data/mwat/items/normalized-mwat-source.md/source.md`
- утверждения:
  `knowledge/data/mwat/items/normalized-mwat-source.md/statements.yml`
- учёт: `knowledge/data/mwat/source.yml`
- локальная копия не хранится

## Условия использования

- Лицензионный статус: CWE и CAPEC свободны для использования с воспроизведением
  условий MITRE; `CWE` и `CAPEC` — товарные знаки MITRE.
- URL условий: `https://cwe.mitre.org/about/termsofuse.html`
- Уровень уверенности: высокий.
- Допустимое использование: использование с атрибуцией MITRE.
- Атрибуция: `knowledge/source-attribution.md`.

## Ограничения

- Каталоги велики и регулярно обновляются (версии); указывать версию и сверяться
  с актуальной.
- В корпус переносятся краткие сведения и идентификаторы (например, `CWE-79`),
  без массового копирования описаний.

## Назначение в проекте

Источник используется как таксономия слабостей и атак: `CWE` связывает
требования `ASVS` со слабостями и помогает классифицировать находки
`security-audit`; `CAPEC` дополняет `security-threat-modeling` (шаблоны атак,
библиотеки атак).
