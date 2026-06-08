SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

APM ?= apm
NPM ?= npm
NPX ?= npx
FILES ?=

.PHONY: deps install lint-md format apm-install apm-update

.PHONY: help
help:
	@printf '%s\n' \
		'Доступные цели:' \
		'  make deps                                  Установить или обновить зависимости' \
		'  make lint-md                               Проверить Markdown-файлы' \
		"  make format FILES='путь1 путь 2'           Отформатировать выбранные файлы" \
		'  make apm-install                           Установить APM-зависимости проекта' \
		'  make apm-update                            Обновить APM-зависимости проекта'

deps: apm-install install

install:
	$(NPM) install

apm-install:
	$(APM) install --target agent-skills --frozen

apm-update:
	$(APM) deps update --target agent-skills

lint-md:
	$(NPM) run lint:md

format:
	@test -n "$(FILES)" || { \
		echo "Задай FILES, например: make format FILES='AGENTS.md'"; \
		exit 2; \
	}
	$(NPX) prettier --write $(FILES)
