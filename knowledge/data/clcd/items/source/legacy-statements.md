# Извлечённые утверждения: `CLCD`

## Основание

- Источник учёта: `knowledge/inventory/CLCD.md`
- Первичный источник: `knowledge/primary/CLCD/source.md`
- Индекс первичных артефактов: `knowledge/primary/CLCD/page-index.tsv`
- Нормализованный слой: `knowledge/normalized/CLCD/source.md`
- Дата извлечения: `2026-06-25`

## Ограничения

- Утверждения извлечены из локальной текстовой выгрузки PDF.
- Текстовая выгрузка может содержать дефекты извлечения, переносов и примеров
  кода; спорные места требуют сверки с PDF.
- Полный текст книги, крупные дословные фрагменты и большие примеры кода не
  публикуются в Git.

## Утверждения

### CLCD-001

Чистота кода влияет на скорость развития продукта: работающий, но грязный код
постепенно повышает стоимость изменений и сопровождения.

- Статус: вывод источника
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-002

Профессиональная обязанность программиста включает сопротивление давлению,
которое ведёт к ухудшению кода ради краткосрочной скорости.

- Статус: вывод источника
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-003

Код следует оставлять чище, чем он был до изменения; небольшие локальные
улучшения являются частью нормальной работы с кодом.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-004

Имена должны передавать намерение, избегать дезинформации, быть удобными для
поиска и использовать одно слово для одной концепции.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-005

Функция должна быть компактной, выполнять одну операцию, работать на одном
уровне абстракции и иметь содержательное имя.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-006

Большое число аргументов, аргументы-флаги и смешение команд с запросами ухудшают
понятность функции и повышают риск ошибки.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-007

Комментарии не должны компенсировать плохой код; если смысл можно выразить
именем, функцией или структурой, предпочтительно улучшить код.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-008

Полезный комментарий объясняет намерение, предупреждает о последствиях или
фиксирует контекст, который нельзя ясно выразить самим кодом.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-009

Форматирование кода должно помогать чтению: связанные элементы должны быть
близко, уровни вложенности видимы, а структура файла предсказуема.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-010

Объекты и структуры данных имеют разные цели: объект скрывает данные за
поведением, а структура данных открывает данные без значимого поведения.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-011

Обработка ошибок должна сохранять основной путь выполнения читаемым, передавать
контекст исключения и избегать возврата или передачи `null`.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-012

Границы со сторонним кодом нужно изолировать так, чтобы детали чужого API не
распространялись по системе.

- Статус: вывод источника
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-013

Учебные тесты помогают проверить понимание стороннего API и защитить проект от
изменений этого API.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-014

Модульные тесты должны быть читаемыми, быстрыми, независимыми, повторяемыми и
достаточно точными, чтобы поддерживать безопасный рефакторинг.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-015

Класс должен быть небольшим по ответственности, иметь высокую связность и
понятную причину для изменения.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-016

Система должна отделять создание объектов и связывание зависимостей от
прикладной логики.

- Статус: вывод источника
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-017

Архитектуру и систему нужно развивать через разделение уровней абстракции,
модульность и контролируемые границы.

- Статус: вывод источника
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-018

Многопоточный код требует отдельной осторожности: нужно разделять
многопоточность и прикладную логику, ограничивать общие данные и проверять
сценарии выполнения.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-019

Последовательное очищение кода должно идти маленькими проверяемыми шагами, где
каждое улучшение сохраняет работоспособность.

- Статус: наблюдение
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-020

Запахи кода и эвристические правила нужны как практический список сигналов при
чтении, анализе и рефакторинге, а не как механическая замена инженерного
суждения.

- Статус: вывод источника
- Основание:
  - `knowledge/primary/CLCD/files/clean-code-martin-ru.txt`
  - `knowledge/normalized/CLCD/source.md`

### CLCD-021

Примеры кода из книги являются учебным материалом, но перенос крупных фрагментов
в публичный корпус недопустим без отдельного правового основания.

- Статус: ограничение публикации
- Основание:
  - `knowledge/primary/CLCD/source.md`
  - `knowledge/source-attribution.md`
