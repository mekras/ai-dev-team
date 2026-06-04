#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PRODUCT_ID = 'ai-dev-team';
const DEFAULT_CHANNEL = 'stable';
const AVAILABLE_CHANNELS = new Set(['stable', 'local', 'dev']);
const SUPPORTED_CLIENTS = new Set(['codex']);
const AGENTS_CONNECTION_LINE_PREFIX = 'Проект использует `ai-dev-team@';
const AGENTS_CONNECTION_LINE_SUFFIX = '`.\n';

const argv = process.argv.slice(2);

if (argv.includes('--help') || argv.includes('-h') || argv.length === 0) {
  printUsage();
  process.exit(0);
}

run();

function run() {
  const cli = parseCliArgs(argv);

  if (cli.command === 'connect') {
    ensureTargetSpecified(cli.client, 'connect');
    const channel = normalizeChannel(cli.channel);
    return runConnect(cli.client, channel);
  }

  if (cli.command === 'setup') {
    ensureTargetSpecified(cli.client, 'setup');
    const channel = normalizeChannel(cli.channel);
    return runSetup(cli.client, channel);
  }

  if (cli.command === 'agents') {
    const channel = normalizeChannel(cli.channel);
    return runAgents(channel);
  }

  console.error(`Ошибка: неизвестная команда ${cli.command}`);
  printUsage();
  process.exit(1);
}

function runConnect(client, channel) {
  if (!SUPPORTED_CLIENTS.has(client)) {
    console.error(`Ошибка: неподдерживаемый клиент ${client}`);
    process.exit(1);
  }

  if (client === 'codex') {
    return configureCodex(channel);
  }

  console.error(`Ошибка: не реализовано подключение для ${client}`);
  process.exit(1);
}

function runSetup(client, channel) {
  return runConnect(client, channel);
}

function runAgents(channel) {
  const cwdAgentsPath = path.join(process.cwd(), 'AGENTS.md');
  const marker = `${AGENTS_CONNECTION_LINE_PREFIX}${channel}${AGENTS_CONNECTION_LINE_SUFFIX}`;

  if (!fs.existsSync(cwdAgentsPath)) {
    fs.writeFileSync(cwdAgentsPath, marker, 'utf8');
    console.log(`AGENTS.md создан: ${cwdAgentsPath}`);
    process.exit(0);
  }

  const existing = fs.readFileSync(cwdAgentsPath, 'utf8');
  if (existing.includes(marker)) {
    console.log(`AGENTS.md уже содержит подключение: ${cwdAgentsPath}`);
    process.exit(0);
  }

  const normalized = existing.trim().length === 0
    ? marker
    : `${existing.replace(/\n*$/, '')}\n\n${marker}`;

  fs.writeFileSync(cwdAgentsPath, normalized, 'utf8');
  console.log(`AGENTS.md обновлён: ${cwdAgentsPath}`);
  process.exit(0);
}

function configureCodex(channel) {
  const configDir = path.join(os.homedir(), '.codex');
  if (!fs.existsSync(configDir)) {
    console.error(
      'Ошибка: каталог ~/.codex не найден. Сначала запустите Codex хотя бы один раз.'
    );
    process.exit(1);
  }

  const configPath = path.join(configDir, 'config.toml');
  const desiredSection =
    '[mcp_servers.ai-dev-team]\n'
    + `command = "${PRODUCT_ID}-mcp"\n`
    + `args = ["--channel", "${channel}"]\n`;

  const existing = fs.existsSync(configPath)
    ? fs.readFileSync(configPath, 'utf8')
    : '';

  const result = upsertTomlSection(existing, 'mcp_servers.ai-dev-team',
    desiredSection);

  fs.writeFileSync(configPath, result.text);

  if (result.changed) {
    const action = existing
      ? 'Подключение Codex обновлено'
      : 'Подключение Codex добавлено';
    console.log(`${action}: ${configPath}`);
    process.exit(0);
  }

  console.log(`Подключение Codex уже настроено: ${configPath}`);
  process.exit(0);
}

function upsertTomlSection(content, sectionName, sectionText) {
  const sectionHeader = `[${sectionName}]`;
  const header = sectionText.split('\n')[0];
  const body = sectionText
    .split('\n')
    .slice(1)
    .filter((line) => line.length > 0);
  const newBlock = [header, ...body];

  if (!content) {
    return { changed: true, text: [...newBlock, ''].join('\n') };
  }

  const lines = content.split(/\r?\n/);
  const start = lines.findIndex(
    (line) => line.trim() === sectionHeader
  );

  if (start === -1) {
    const separator = lines.length === 0 || lines[lines.length - 1] === ''
      ? ''
      : '\n';
    return {
      changed: true,
      text: `${content}${separator}\n${newBlock.join('\n')}\n`,
    };
  }

  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    if (/^\[[^\]]+\]$/.test(lines[index].trim())) {
      end = index;
      break;
    }
  }

  const existingBlock = lines
    .slice(start, end)
    .map((line) => line.replace(/\s+$/, ''));

  const normalizedExisting = existingBlock.join('\n');
  const normalizedNew = newBlock.join('\n');
  if (normalizedExisting === normalizedNew) {
    return { changed: false, text: content };
  }

  const merged = [
    ...lines.slice(0, start),
    ...newBlock,
    ...lines.slice(end),
  ];
  return { changed: true, text: `${merged.join('\n')}\n` };
}

function parseCliArgs(argv) {
  if (!argv.length) {
    console.error('Ошибка: не указана команда или цель подключения.');
    printUsage();
    process.exit(1);
  }

  const parsed = {
    command: argv[0],
    client: argv[1],
    channel: DEFAULT_CHANNEL,
  };

  const startIndex = parsed.command === 'agents' ? 1 : 2;
  if (startIndex === 2 && argv.length < 2) {
    ensureTargetSpecified(parsed.client, parsed.command);
  }

  for (let index = startIndex; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--help' || arg === '-h') {
      printUsage();
      process.exit(0);
    }

    if (arg.startsWith('--channel=')) {
      parsed.channel = arg.slice('--channel='.length);
      continue;
    }

    if (arg === '--channel') {
      parsed.channel = argv[index + 1];
      index += 1;
      continue;
    }
  }

  return parsed;
}

function ensureTargetSpecified(client, commandName) {
  if (!client) {
    console.error(`Ошибка: нужно указать клиент после ${commandName}.`);
    printUsage();
    process.exit(1);
  }
}

function normalizeChannel(value) {
  const next = (value || DEFAULT_CHANNEL).trim();
  if (!AVAILABLE_CHANNELS.has(next)) {
    console.error(`Ошибка: неизвестный канал ${next}`);
    process.exit(1);
  }
  return next;
}

function printUsage() {
  console.log(`Использование:
  ai-dev-team connect|setup <client> [--channel stable|local|dev]
  ai-dev-team agents [--channel stable|local|dev]

Команды:
  agents   добавить или обновить строку подключения в AGENTS.md
  connect  добавить или обновить подключение клиента
  setup    то же, что и connect

Поддерживаемые клиенты:
  codex

Параметры:
  --channel  канал подключения. По умолчанию: ${DEFAULT_CHANNEL}
`);
}
