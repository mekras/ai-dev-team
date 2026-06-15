#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const PRODUCT_ID = "ai-dev-team";
const DEFAULT_CHANNEL = "stable";
const AVAILABLE_CHANNELS = new Set(["stable", "local", "dev"]);
const SUPPORTED_CLIENTS = new Set(["codex", "claude"]);
const AGENTS_CONNECTION_LINE_PREFIX = "Проект использует `ai-dev-team@";
const AGENTS_CONNECTION_LINE_SUFFIX = "`.\n";
const CODEX_INSTRUCTIONS_BLOCK_START = "# BEGIN ai-dev-team developer_instructions";
const CODEX_INSTRUCTIONS_BLOCK_END = "# END ai-dev-team developer_instructions";
const CLAUDE_INSTRUCTIONS_BLOCK_START = "<!-- BEGIN ai-dev-team CLAUDE.md -->";
const CLAUDE_INSTRUCTIONS_BLOCK_END = "<!-- END ai-dev-team CLAUDE.md -->";

const argv = process.argv.slice(2);

if (argv.includes("--help") || argv.includes("-h") || argv.length === 0) {
  printUsage();
  process.exit(0);
}

run();

function run() {
  const cli = parseCliArgs(argv);

  if (cli.command === "connect") {
    ensureTargetSpecified(cli.client, "connect");
    const channel = normalizeChannel(cli.channel);
    return runConnect(cli.client, channel);
  }

  if (cli.command === "setup") {
    ensureTargetSpecified(cli.client, "setup");
    const channel = normalizeChannel(cli.channel);
    return runSetup(cli.client, channel);
  }

  if (cli.command === "agents") {
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

  if (client === "codex") {
    return configureCodex(channel);
  }

  if (client === "claude") {
    return configureClaude(channel);
  }

  console.error(`Ошибка: не реализовано подключение для ${client}`);
  process.exit(1);
}

function runSetup(client, channel) {
  return runConnect(client, channel);
}

function runAgents(channel) {
  const cwdAgentsPath = path.join(process.cwd(), "AGENTS.md");
  const marker = buildAgentsConnectionLine(channel);

  if (!fs.existsSync(cwdAgentsPath)) {
    fs.writeFileSync(cwdAgentsPath, `${marker}\n`, "utf8");
    console.log(`AGENTS.md создан: ${cwdAgentsPath}`);
    process.exit(0);
  }

  const existing = normalizeLineEndings(fs.readFileSync(cwdAgentsPath, "utf8"));
  const updated = ensureAgentsConnectionAtTop(existing, marker);
  if (existing.trimEnd() === updated) {
    console.log(`AGENTS.md уже содержит подключение: ${cwdAgentsPath}`);
    process.exit(0);
  }

  fs.writeFileSync(cwdAgentsPath, `${updated}\n`, "utf8");
  console.log(`AGENTS.md обновлён: ${cwdAgentsPath}`);
  process.exit(0);
}

function buildAgentsConnectionLine(channel) {
  return `${AGENTS_CONNECTION_LINE_PREFIX}${channel}${AGENTS_CONNECTION_LINE_SUFFIX}`.trim();
}

function isAgentsConnectionLine(line) {
  const normalizedLine = line.trim();
  return (
    normalizedLine.startsWith(AGENTS_CONNECTION_LINE_PREFIX) &&
    normalizedLine.endsWith("`.") &&
    normalizedLine.length > AGENTS_CONNECTION_LINE_PREFIX.length
  );
}

function findAgentsConnectionInsertionIndex(lines) {
  const sectionHeaderIndex = lines.findIndex((line) => line.startsWith("## "));
  if (sectionHeaderIndex !== -1) {
    return sectionHeaderIndex;
  }

  const firstNonEmptyIndex = lines.findIndex((line) => line.trim() !== "");
  return firstNonEmptyIndex === -1 ? 0 : firstNonEmptyIndex;
}

function ensureAgentsConnectionAtTop(content, marker) {
  const normalizedContent = content.trimEnd();
  if (normalizedContent.length === 0) {
    return marker;
  }

  const lines = normalizedContent.split("\n");
  const withoutConnectionLines = lines.filter((line) => !isAgentsConnectionLine(line));
  if (withoutConnectionLines.every((line) => line.trim() === "")) {
    return marker;
  }

  const insertionIndex = findAgentsConnectionInsertionIndex(withoutConnectionLines);
  const before = trimTrailingEmptyLines(withoutConnectionLines.slice(0, insertionIndex));
  const after = trimLeadingEmptyLines(withoutConnectionLines.slice(insertionIndex));
  const nextLines = [...before];

  if (nextLines.length > 0) {
    nextLines.push("");
  }
  nextLines.push(marker);
  if (after.length > 0) {
    nextLines.push("");
  }
  nextLines.push(...after);

  return nextLines.join("\n").trimEnd();
}

function trimLeadingEmptyLines(lines) {
  let start = 0;
  while (start < lines.length && lines[start].trim() === "") {
    start += 1;
  }
  return lines.slice(start);
}

function trimTrailingEmptyLines(lines) {
  let end = lines.length;
  while (end > 0 && lines[end - 1].trim() === "") {
    end -= 1;
  }
  return lines.slice(0, end);
}

function normalizeLineEndings(value) {
  return value.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
}

function configureCodex(channel) {
  const configDir = path.join(os.homedir(), ".codex");
  if (!fs.existsSync(configDir)) {
    console.error("Ошибка: каталог ~/.codex не найден. Сначала запустите Codex хотя бы один раз.");
    process.exit(1);
  }

  const configPath = path.join(configDir, "config.toml");
  const desiredServerSection =
    "[mcp_servers.ai-dev-team]\n" +
    `command = "${PRODUCT_ID}-mcp"\n` +
    `args = ["--channel", "${channel}"]\n`;
  const desiredInstructionsBlock = buildCodexInstructionsBlock();

  const existing = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8") : "";

  const withServer = upsertTomlSection(existing, "mcp_servers.ai-dev-team", desiredServerSection);
  const withInstructions = upsertManagedDeveloperInstructions(
    withServer.text,
    desiredInstructionsBlock,
  );

  fs.writeFileSync(configPath, withInstructions.text);

  if (withServer.changed || withInstructions.changed) {
    const action = existing ? "Подключение Codex обновлено" : "Подключение Codex добавлено";
    console.log(`${action}: ${configPath}`);
    process.exit(0);
  }

  console.log(`Подключение Codex уже настроено: ${configPath}`);
  process.exit(0);
}

function upsertTomlSection(content, sectionName, sectionText) {
  const sectionHeader = `[${sectionName}]`;
  const header = sectionText.split("\n")[0];
  const body = sectionText
    .split("\n")
    .slice(1)
    .filter((line) => line.length > 0);
  const newBlock = [header, ...body];

  if (!content) {
    return { changed: true, text: [...newBlock, ""].join("\n") };
  }

  const lines = content.split(/\r?\n/);
  const start = lines.findIndex((line) => line.trim() === sectionHeader);

  if (start === -1) {
    const separator = lines.length === 0 || lines[lines.length - 1] === "" ? "" : "\n";
    return {
      changed: true,
      text: `${content}${separator}\n${newBlock.join("\n")}\n`,
    };
  }

  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    if (/^\[[^\]]+\]$/.test(lines[index].trim())) {
      end = index;
      break;
    }
  }

  const existingBlock = lines.slice(start, end).map((line) => line.replace(/\s+$/, ""));

  const normalizedExisting = existingBlock.join("\n");
  const normalizedNew = newBlock.join("\n");
  if (normalizedExisting === normalizedNew) {
    return { changed: false, text: content };
  }

  const merged = [...lines.slice(0, start), ...newBlock, ...lines.slice(end)];
  return { changed: true, text: `${merged.join("\n")}\n` };
}

function buildCodexInstructionsBlock() {
  return [
    CODEX_INSTRUCTIONS_BLOCK_START,
    "developer_instructions = '''",
    buildConnectionInstructionsText(),
    "'''",
    CODEX_INSTRUCTIONS_BLOCK_END,
  ].join("\n");
}

function configureClaude(channel) {
  const claudeDir = path.join(os.homedir(), ".claude");
  fs.mkdirSync(claudeDir, { recursive: true });

  const configPath = path.join(os.homedir(), ".claude.json");
  const claudeMdPath = path.join(claudeDir, "CLAUDE.md");

  const existingConfig = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8") : "";
  const withServer = upsertClaudeUserMcpServer(existingConfig, channel);

  const existingClaudeMd = fs.existsSync(claudeMdPath)
    ? normalizeLineEndings(fs.readFileSync(claudeMdPath, "utf8"))
    : "";
  const withInstructions = upsertManagedMarkdownBlock(
    existingClaudeMd,
    buildClaudeInstructionsBlock(),
    CLAUDE_INSTRUCTIONS_BLOCK_START,
    CLAUDE_INSTRUCTIONS_BLOCK_END,
  );

  fs.writeFileSync(configPath, withServer.text);
  fs.writeFileSync(claudeMdPath, withInstructions.text);

  if (withServer.changed || withInstructions.changed) {
    const action =
      existingConfig || existingClaudeMd
        ? "Подключение Claude обновлено"
        : "Подключение Claude добавлено";
    console.log(`${action}: ${configPath}, ${claudeMdPath}`);
    process.exit(0);
  }

  console.log(`Подключение Claude уже настроено: ${configPath}, ${claudeMdPath}`);
  process.exit(0);
}

function upsertClaudeUserMcpServer(content, channel) {
  let parsed;
  if (content.trim().length === 0) {
    parsed = {};
  } else {
    try {
      parsed = JSON.parse(content);
    } catch (error) {
      console.error(
        "Ошибка: ~/.claude.json содержит невалидный JSON. " +
          "Исправьте файл вручную и повторите команду.",
      );
      process.exit(1);
    }
  }

  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    console.error("Ошибка: ~/.claude.json должен содержать JSON-объект.");
    process.exit(1);
  }

  const next = { ...parsed };
  const currentServers =
    next.mcpServers && typeof next.mcpServers === "object" && !Array.isArray(next.mcpServers)
      ? next.mcpServers
      : {};
  const desiredServer = {
    type: "stdio",
    command: `${PRODUCT_ID}-mcp`,
    args: ["--channel", channel],
  };

  next.mcpServers = {
    ...currentServers,
    [PRODUCT_ID]: desiredServer,
  };

  const text = `${JSON.stringify(next, null, 2)}\n`;
  return {
    changed: text !== content,
    text,
  };
}

function buildClaudeInstructionsBlock() {
  const instructions = [
    CLAUDE_INSTRUCTIONS_BLOCK_START,
    buildConnectionInstructionsText(),
    CLAUDE_INSTRUCTIONS_BLOCK_END,
  ];

  return instructions.join("\n");
}

function buildConnectionInstructionsText() {
  return [
    "Если в инструкциях проекта есть строка вида",
    "`Проект использует `ai-dev-team@<канал>`.`,",
    "это означает обязательное подключение продукта `ai-dev-team`.",
    "",
    "Перед предметной работой агент должен:",
    "",
    "- извлечь точный идентификатор подключения из инструкций проекта;",
    "- использовать MCP-инструменты сервера `ai-dev-team`, чтобы получить",
    "  входную точку подключённого продукта;",
    "- применить инструкции входной точки до предметного ответа;",
    "- если сервер `ai-dev-team` или его входная точка недоступны, явно",
    "  сообщить об этом как о блокере и не имитировать применение продукта.",
    "",
    "Работа с корпусом знаний целевого проекта:",
    "",
    "- агент должен искать в машинных инструкциях проекта явное правило о том,",
    "  где хранятся файлы корпуса знаний;",
    "- если для проекта доступны и переносимые, и клиентские инструкции, агент",
    "  должен предпочитать переносимое проектное правило;",
    "- если такое правило найдено, агент должен использовать указанный путь;",
    "- если явное правило не найдено, агент должен считать путём корпуса знаний",
    "  папку `knowledge/` в корне проекта;",
  ].join("\n");
}

function upsertManagedMarkdownBlock(content, blockText, blockStart, blockEnd) {
  const pattern = new RegExp(
    `\\n?${escapeRegExp(blockStart)}[\\s\\S]*?${escapeRegExp(blockEnd)}\\n?`,
  );
  const sanitized = content
    .replace(pattern, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  if (sanitized.length === 0) {
    return {
      changed: content !== `${blockText}\n`,
      text: `${blockText}\n`,
    };
  }

  const text = `${blockText}\n\n${sanitized}\n`;
  return {
    changed: text !== content,
    text,
  };
}

function upsertManagedDeveloperInstructions(content, blockText) {
  const pattern = new RegExp(
    `\\n?${escapeRegExp(CODEX_INSTRUCTIONS_BLOCK_START)}[\\s\\S]*?` +
      `${escapeRegExp(CODEX_INSTRUCTIONS_BLOCK_END)}\\n?`,
  );
  const sanitized = content.replace(pattern, "").replace(/\n{3,}/g, "\n\n");

  if (/^developer_instructions\s*=/m.test(sanitized)) {
    console.error(
      "Ошибка: в ~/.codex/config.toml уже есть ключ developer_instructions вне " +
        "управляемого блока ai-dev-team. Обновите его вручную или удалите " +
        "существующее значение и повторите команду.",
    );
    process.exit(1);
  }

  if (sanitized.length === 0) {
    return {
      changed: content !== `${blockText}\n`,
      text: `${blockText}\n`,
    };
  }

  const lines = sanitized.split(/\r?\n/);
  const firstSectionIndex = lines.findIndex((line) => /^\[[^\]]+\]$/.test(line.trim()));

  if (firstSectionIndex === -1) {
    const separator = sanitized.endsWith("\n\n") ? "" : sanitized.endsWith("\n") ? "\n" : "\n\n";
    const text = `${sanitized}${separator}${blockText}\n`;
    return {
      changed: text !== content,
      text,
    };
  }

  const before = lines.slice(0, firstSectionIndex).join("\n").replace(/\s+$/, "");
  const after = lines.slice(firstSectionIndex).join("\n");
  const prefix = before.length === 0 ? "" : `${before}\n\n`;
  const text = `${prefix}${blockText}\n\n${after}\n`;
  return {
    changed: text !== content,
    text,
  };
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function parseCliArgs(argv) {
  if (!argv.length) {
    console.error("Ошибка: не указана команда или цель подключения.");
    printUsage();
    process.exit(1);
  }

  const parsed = {
    command: argv[0],
    client: argv[1],
    channel: DEFAULT_CHANNEL,
  };

  const startIndex = parsed.command === "agents" ? 1 : 2;
  if (startIndex === 2 && argv.length < 2) {
    ensureTargetSpecified(parsed.client, parsed.command);
  }

  for (let index = startIndex; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      printUsage();
      process.exit(0);
    }

    if (arg.startsWith("--channel=")) {
      parsed.channel = arg.slice("--channel=".length);
      continue;
    }

    if (arg === "--channel") {
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
  agents   добавить или обновить строку подключения в AGENTS.md текущего проекта
  connect  настроить клиент на этой машине
  setup    то же, что и connect

Поддерживаемые клиенты:
  codex
  claude

Параметры:
  --channel  канал подключения. По умолчанию: ${DEFAULT_CHANNEL}
`);
}
