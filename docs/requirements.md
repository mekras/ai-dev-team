# Требования к продукту

## Как пользоваться требованиями

Каждое требование хранится в отдельном файле и является источником истины для
своей формулировки, основания, реализации и проверки. Эта страница служит единой
точкой входа и индексом.

Требования разнесены по уровням, каждое имеет идентификатор с понятным
префиксом:

- `БТ` — бизнес-требования (зачем нужен продукт);
- `ПТ` — пользовательские требования (что нужно заказчику);
- `ФТ` — функциональные требования (что делает продукт);
- `КАЧ` — атрибуты качества;
- `ПР` — правила продукта;

У требования могут быть разделы «Основание» (откуда оно следует), «Реализация»
(где оно воплощено) и «Проверка» (как убедиться, что оно выполнено).
Идентификаторы служат для трассировки и анализа влияния; в общении с человеком
используются понятные названия, а не эти коды (см.
[КАЧ-4](requirements/quality/kach-4.md)).

Идентификатор удалённого требования не используется повторно, поэтому в индексе
могут оставаться пропуски.

## Определения

- _Продукт_ — публикуемый пакет APM `ai-dev-team`: роли, навыки, контекст и
  инструкции, которые подключаются к целевому проекту.
- _Проект_ — этот репозиторий по разработке _продукта_.
- _Целевой проект_ — сторонний проект, в котором используется _продукт_.
- _Заказчик_ — человек, управляющий разработкой _целевого проекта_.

## Бизнес-требования

- [БТ-1](requirements/business/bt-1.md)
- [БТ-2](requirements/business/bt-2.md)
- [БТ-3](requirements/business/bt-3.md)

## Пользовательские требования

- [ПТ-1](requirements/user/pt-1.md)
- [ПТ-2](requirements/user/pt-2.md)
- [ПТ-3](requirements/user/pt-3.md)
- [ПТ-4](requirements/user/pt-4.md)
- [ПТ-5. Регистрация гипотез](requirements/user/pt-5.md)
- [ПТ-6. Безопасное использование и разработка ИИ](requirements/user/pt-6.md)
- [ПТ-7. Полная управляемая проверка репозитория](requirements/user/pt-7.md)

## Функциональные требования

- [ФТ-1](requirements/functional/ft-1.md)
- [ФТ-2](requirements/functional/ft-2.md)
- [ФТ-3](requirements/functional/ft-3.md)
- [ФТ-4](requirements/functional/ft-4.md)
- [ФТ-5](requirements/functional/ft-5.md)
- [ФТ-6. Организация структур](requirements/functional/ft-6.md)
- [ФТ-7. Журналы решений](requirements/functional/ft-7.md)
- [ФТ-8](requirements/functional/ft-8.md)
- [ФТ-9. Решение до действия](requirements/functional/ft-9.md)
- [ФТ-10](requirements/functional/ft-10.md)
- [ФТ-11. Выявление требований](requirements/functional/ft-11.md)
- [ФТ-12. Применение The Twelve-Factor App](requirements/functional/ft-12.md)
- [ФТ-13. Реестр гипотез](requirements/functional/ft-13.md)
- [ФТ-14. Жизненный цикл гипотезы](requirements/functional/ft-14.md)
- [ФТ-15. Переход от гипотезы к решению](requirements/functional/ft-15.md)
- [ФТ-16. ИБ использования и разработки ИИ](requirements/functional/ft-16.md)
- [ФТ-17. Схема сообщений коммитов](requirements/functional/ft-17.md)
- [ФТ-18. Профиль проекта и диалог настройки](requirements/functional/ft-18.md)
- [ФТ-19. Реконструируемость проекта](requirements/functional/ft-19.md)
- [ФТ-20. Рефакторинг требований](requirements/functional/ft-20.md)
- [ФТ-21. Динамический охват полной проверки](requirements/functional/ft-21.md)
- [ФТ-22. Поэтапная проверка и исправление](requirements/functional/ft-22.md)

## Атрибуты качества

- [КАЧ-1. Удобство подключения](requirements/quality/kach-1.md)
- [КАЧ-2. Переносимость](requirements/quality/kach-2.md)
- [КАЧ-3. Независимость от внутренней структуры](requirements/quality/kach-3.md)
- [КАЧ-4. Понятность общения](requirements/quality/kach-4.md)
- [КАЧ-5. Лаконичность текстов](requirements/quality/kach-5.md)
- [КАЧ-6. Качество записи решения](requirements/quality/kach-6.md)
- [КАЧ-7. Качество записи гипотезы](requirements/quality/kach-7.md)
- [КАЧ-8. Завершаемость управляемой проверки](requirements/quality/kach-8.md)

## Правила продукта

- [ПР-1](requirements/rules/pr-1.md)
- [ПР-2](requirements/rules/pr-2.md)
- [ПР-3](requirements/rules/pr-3.md)
- [ПР-4](requirements/rules/pr-4.md)
- [ПР-5](requirements/rules/pr-5.md)
- [ПР-6](requirements/rules/pr-6.md)
