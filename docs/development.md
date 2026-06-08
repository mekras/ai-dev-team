# Разработка продукта

## Установка и обновление зависимостей

```shell
make deps
```

Эта команда:

- ставит APM-зависимости проекта через
  `apm install --target agent-skills --frozen`;
- ставит Node.js-зависимости через `npm install`.

Чтобы обновить закреплённые версии APM-зависимостей и lockfile, выполните:

```shell
make apm-update
```
