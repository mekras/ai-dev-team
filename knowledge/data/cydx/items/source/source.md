# Источник: `CYDX`

## Статус

Источник принят в корпус знаний как `external_reference`: корпус хранит локатор,
лицензию, нормализованный обзор и краткие утверждения, но не хранит копию
спецификации. `CycloneDX` — развивающийся стандарт; материал получается из
первоисточника по запросу.

## Происхождение

- Название: `OWASP CycloneDX` (стандарт Bill of Materials)
- Издатель: OWASP Foundation; стандартизирован Ecma International
- Версия на дату включения: `1.7` (релиз `2025-10-21`)
- Стандарт: `ECMA-424` (публикация `2025-12-10`)
- Канонический адрес: `https://cyclonedx.org/specification/overview/`
- Репозиторий: `https://github.com/CycloneDX/specification`
- Тип источника: открытый стандарт состава ПО (SBOM и смежные BOM)
- Дата включения в корпус: `2026-06-25`

## Стратегия источника

- `storage_strategy: external_reference`
- `retrieval_mode: on_demand`
- `copy_policy: external_reference`
- `requires_access_check: false`

## Что сохранено в корпусе

- паспорт: `knowledge/primary/CYDX/source.md`
- нормализованный обзор: `knowledge/normalized/CYDX/source.md`
- утверждения: `knowledge/statements/CYDX.md`
- учёт: `knowledge/inventory/CYDX.md`
- локальная копия не хранится

## Условия использования

- Лицензия: схемы CycloneDX доступны под `Apache License 2.0`; стандарт
  опубликован как `ECMA-424` с royalty-free патентной политикой.
- URL лицензии: `https://www.apache.org/licenses/LICENSE-2.0`
- Уровень уверенности: высокий.
- Допустимое использование: свободное при соблюдении условий Apache 2.0.
- Атрибуция: `knowledge/source-attribution.md`.

## Ограничения

- Стандарт развивается (версия растёт); указывать версию и сверяться с
  актуальной.
- Дополняет уже учтённый в корпусе `SPDX` (другой стандарт SBOM); это не замена.

## Назначение в проекте

Источник используется как основание навыка `security-tooling` (SCA и SBOM:
состав ПО, зависимости, уязвимости, VEX) и связи с управлением компонентами
(практика SSDF `PW.4`).
