SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

NPM ?= npm
NPX ?= npx
FILES ?=

AI_AGENT_SUPERVISOR_REMOTE ?= ai-agent-supervisor
AI_AGENT_SUPERVISOR_BRANCH ?= master
AI_AGENT_SUPERVISOR_PREFIX ?= vendor/ai-agent-supervisor

PROJECT_KNOWLEGE_CORPUS_REMOTE ?= project-knowlege-corpus
PROJECT_KNOWLEGE_CORPUS_BRANCH ?= master
PROJECT_KNOWLEGE_CORPUS_PREFIX ?= vendor/project-knowlege-corpus

.PHONY: install lint-md format subtree-update \
	subtree-update-ai-agent-supervisor \
	subtree-update-project-knowlege-corpus

.PHONY: help
help:
	@printf '%s\n' \
		'Доступные цели:' \
		'  make deps                                  Установить или обновить зависимости' \
		'  make lint-md                               Проверить Markdown-файлы' \
		"  make format FILES='путь1 путь 2'           Отформатировать выбранные файлы" \
		'  make subtree-update-ai-agent-supervisor    Обновить vendor/ai-agent-supervisor' \
		'  make subtree-update-project-knowlege-corpus Обновить vendor/project-knowlege-corpus'

.PHOYNY: deps
deps: subtree-update install

install:
	$(NPM) install

lint-md:
	$(NPM) run lint:md

format:
	@test -n "$(FILES)" || { \
		echo "Задай FILES, например: make format FILES='AGENTS.md'"; \
		exit 2; \
	}
	$(NPX) prettier --write $(FILES)

subtree-update: subtree-update-ai-agent-supervisor \
	subtree-update-project-knowlege-corpus

subtree-update-ai-agent-supervisor:
	git remote get-url $(AI_AGENT_SUPERVISOR_REMOTE) >/dev/null
	git fetch $(AI_AGENT_SUPERVISOR_REMOTE)
	git subtree pull --prefix=$(AI_AGENT_SUPERVISOR_PREFIX) \
		$(AI_AGENT_SUPERVISOR_REMOTE) \
		$(AI_AGENT_SUPERVISOR_BRANCH) \
		--squash

subtree-update-project-knowlege-corpus:
	git remote get-url $(PROJECT_KNOWLEGE_CORPUS_REMOTE) >/dev/null
	git fetch $(PROJECT_KNOWLEGE_CORPUS_REMOTE)
	git subtree pull --prefix=$(PROJECT_KNOWLEGE_CORPUS_PREFIX) \
		$(PROJECT_KNOWLEGE_CORPUS_REMOTE) \
		$(PROJECT_KNOWLEGE_CORPUS_BRANCH) \
		--squash
