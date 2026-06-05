#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PRODUCT_ID = 'ai-dev-team';
const PRODUCT_VERSION = '0.1.0';
const DEFAULT_CHANNEL = 'stable';
const AVAILABLE_CHANNELS = new Set(['stable', 'local', 'dev']);
const MCP_URI_PREFIX = 'ai-dev-team://';

const PRODUCT_ROOT = path.resolve(__dirname, '..');
const TEAM_ROOT = path.join(PRODUCT_ROOT, 'team');
const AI_CONTROL_RESOURCES = [
  {
    path: 'team/ai-control/README.md',
    source: 'vendor/ai-agent-supervisor/knowledge/ai-control-layer.md',
  },
  {
    path: 'team/ai-control/ai-application-check.md',
    source:
      'vendor/ai-agent-supervisor/skills/ai-application-check/references/application-check.md',
  },
  {
    path: 'team/ai-control/ai-application-check-template.md',
    source:
      'vendor/ai-agent-supervisor/skills/ai-application-check/assets/application-check-template.md',
  },
  {
    path: 'team/ai-control/ai-work-control.md',
    source:
      'vendor/ai-agent-supervisor/skills/ai-work-control/references/work-control.md',
  },
  {
    path: 'team/ai-control/ai-work-result-evaluation.md',
    source:
      'vendor/ai-agent-supervisor/skills/ai-work-result-evaluation/references/work-result-evaluation.md',
  },
  {
    path: 'team/ai-control/ai-work-result-evaluation-case-template.md',
    source:
      'vendor/ai-agent-supervisor/skills/ai-work-result-evaluation/assets/work-result-evaluation-case-template.md',
  },
  {
    path: 'team/ai-control/data-collection-procedure.md',
    source:
      'vendor/ai-agent-supervisor/skills/ai-data-collection/references/data-collection-procedure.md',
  },
];
const AI_CONTROL_RESOURCE_MAP = Object.fromEntries(
  AI_CONTROL_RESOURCES.map((entry) => [entry.path, entry.source])
);
const CLI_OPTIONS = parseCliArgs(process.argv.slice(2));
const SERVER_CHANNEL = normalizeChannel(CLI_OPTIONS.channel);

if (CLI_OPTIONS.help) {
  printUsage();
  process.exit(0);
}

if (CLI_OPTIONS.check) {
  runSelfCheck();
  process.exit(0);
}

const baseTools = [
  {
    name: 'resolve_product',
    description:
      'Возвращает сведения о продукте и канале подключения.',
    inputSchema: {
      type: 'object',
      properties: {
        product_id: {
          type: 'string',
          description: 'Идентификатор подключения, например ai-dev-team@stable',
        },
      },
      required: ['product_id'],
      additionalProperties: false,
    },
  },
  {
    name: 'get_entrypoint',
    description:
      'Возвращает текст корневой точки входа FRAMEWORK.md для продукта.',
    inputSchema: {
      type: 'object',
      properties: {
        product_id: {
          type: 'string',
          description: 'Идентификатор подключения, например ai-dev-team@stable',
        },
      },
      required: ['product_id'],
      additionalProperties: false,
    },
  },
  {
    name: 'list_resources',
    description:
      'Возвращает список доступных ресурсов для заданного продукта.',
    inputSchema: {
      type: 'object',
      properties: {
        product_id: {
          type: 'string',
          description: 'Идентификатор подключения, например ai-dev-team@stable',
        },
      },
      required: ['product_id'],
      additionalProperties: false,
    },
  },
  {
    name: 'get_resource',
    description:
      'Возвращает текст одного ресурса по логическому пути.',
    inputSchema: {
      type: 'object',
      properties: {
        product_id: {
          type: 'string',
          description: 'Идентификатор подключения, например ai-dev-team@stable',
        },
        resource_path: {
          type: 'string',
          description:
            'Логический путь ресурса, например team/roles/project-manager.md',
        },
      },
      required: ['product_id', 'resource_path'],
      additionalProperties: false,
    },
  },
];

const protocolError = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,
};

function printUsage() {
  console.log(`Использование:
  ai-dev-team-mcp [--channel stable|local|dev] [--product id] [--check]

Параметры:
  --channel   канал подключения, по умолчанию stable
  --product   идентификатор продукта, по умолчанию ${PRODUCT_ID}@stable
  --check     выполнить локальную самопроверку и завершить работу
  --help      показать эту справку
`);
}

function parseCliArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--help' || arg === '-h') {
      result.help = true;
      continue;
    }
    if (arg.startsWith('--channel=')) {
      result.channel = arg.slice('--channel='.length);
      continue;
    }
    if (arg === '--channel') {
      result.channel = argv[index + 1];
      index += 1;
      continue;
    }
    if (arg.startsWith('--product=')) {
      result.product = arg.slice('--product='.length);
      continue;
    }
    if (arg === '--product') {
      result.product = argv[index + 1];
      index += 1;
      continue;
    }
    if (arg === '--check') {
      result.check = true;
    }
  }
  return result;
}

function normalizeChannel(value) {
  const next = value || DEFAULT_CHANNEL;
  if (!AVAILABLE_CHANNELS.has(next)) {
    process.stderr.write(`Ошибка: неизвестный канал "${next}"`);
    process.exit(1);
  }
  return next;
}

function parseProductId(productId) {
  const raw = String(productId || `${PRODUCT_ID}@${SERVER_CHANNEL}`).trim();
  const at = raw.lastIndexOf('@');
  if (at <= 0 || at === raw.length - 1) {
    return { product: raw, channel: SERVER_CHANNEL };
  }
  return {
    product: raw.slice(0, at),
    channel: raw.slice(at + 1),
  };
}

function parseRequestProduct(productId) {
  const parsed = parseProductId(productId);
  if (parsed.product !== PRODUCT_ID) {
    const error = new Error(`Неизвестный продукт: ${parsed.product}`);
    error.code = 'UNKNOWN_PRODUCT';
    throw error;
  }
  if (!AVAILABLE_CHANNELS.has(parsed.channel)) {
    const error = new Error(`Неизвестный канал: ${parsed.channel}`);
    error.code = 'UNKNOWN_CHANNEL';
    throw error;
  }
  return {
    product_id: `${parsed.product}@${parsed.channel}`,
    channel: parsed.channel,
  };
}

function safeJoinResourcePath(resourcePath) {
  const normalized = path
    .normalize(resourcePath)
    .replace(/\\+/g, '/')
    .replace(/^\/+/, '');
  if (normalized.startsWith('..')) {
    const error = new Error('Недопустимый путь ресурса');
    error.code = 'INVALID_RESOURCE_PATH';
    throw error;
  }
  const full = path.join(PRODUCT_ROOT, normalized);
  if (!full.startsWith(PRODUCT_ROOT)) {
    const error = new Error('Недопустимый путь ресурса');
    error.code = 'INVALID_RESOURCE_PATH';
    throw error;
  }
  return { normalized, full };
}

function collectRoleResources() {
  const roleDir = path.join(TEAM_ROOT, 'roles');
  return fs
    .readdirSync(roleDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.md'))
    .map((entry) => buildResourceEntry(`team/roles/${entry.name}`));
}

function collectSkillResources() {
  const result = [];
  const skillsIndex = buildResourceEntry('team/skills/INDEX.md');
  const skillRoot = path.join(TEAM_ROOT, 'skills');
  const entries = fs.readdirSync(skillRoot, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const skillManifest = path.join(skillRoot, entry.name, 'SKILL.md');
    if (!fs.existsSync(skillManifest)) continue;
    result.push(buildResourceEntry(`team/skills/${entry.name}/SKILL.md`));
  }

  return [skillsIndex, ...result];
}

function buildResourceEntry(relativePath) {
  return {
    uri: `${MCP_URI_PREFIX}${relativePath}`,
    path: relativePath,
    name: path.basename(relativePath),
    mimeType: 'text/markdown',
    description: `Файл ${relativePath}`,
  };
}

function collectAiControlResources() {
  return AI_CONTROL_RESOURCES
    .map((entry) => buildResourceEntry(entry.path))
    .sort((a, b) => a.path.localeCompare(b.path));
}

function getStableResources() {
  return [
    buildResourceEntry('FRAMEWORK.md'),
    buildResourceEntry('team/templates/project-AGENTS.md'),
    ...collectRoleResources(),
    ...collectSkillResources(),
    ...collectAiControlResources(),
  ].sort((a, b) => a.path.localeCompare(b.path));
}

function getLocalResources() {
  return [...getStableResources()];
}

function getDevResources() {
  return [...getLocalResources()];
}

function getResources(channel) {
  if (channel === 'dev') {
    return getDevResources();
  }
  if (channel === 'local') {
    return getLocalResources();
  }
  return getStableResources();
}

function resolveProduct(args) {
  const product = parseRequestProduct(args.product_id || `${PRODUCT_ID}@${SERVER_CHANNEL}`);
  return {
    product_id: product.product_id,
    product: PRODUCT_ID,
    channel: product.channel,
    transport: 'mcp',
    mode: 'read-only',
    entrypoint: `${MCP_URI_PREFIX}FRAMEWORK.md`,
    version: PRODUCT_VERSION,
  };
}

function getEntrypoint(args) {
  const product = parseRequestProduct(args.product_id || `${PRODUCT_ID}@${SERVER_CHANNEL}`);
  const resources = getResources(product.channel);
  const entrypoint = resources.find((resource) => resource.path === 'FRAMEWORK.md');
  if (!entrypoint) {
    const error = new Error('ENTRYPOINT_NOT_FOUND');
    error.code = 'ENTRYPOINT_NOT_FOUND';
    throw error;
  }
  const data = fs.readFileSync(
    path.join(PRODUCT_ROOT, entrypoint.path),
    'utf8'
  );
  return {
    product_id: product.product_id,
    entrypoint: entrypoint.path,
    uri: entrypoint.uri,
    text: data,
  };
}

function listResources(args) {
  const product = parseRequestProduct(args.product_id || `${PRODUCT_ID}@${SERVER_CHANNEL}`);
  return {
    product_id: product.product_id,
    resources: getResources(product.channel).map((entry) => ({
      uri: entry.uri,
      name: entry.name,
      description: entry.description,
      mimeType: entry.mimeType,
    })),
  };
}

function getResource(args) {
  const product = parseRequestProduct(args.product_id || `${PRODUCT_ID}@${SERVER_CHANNEL}`);
  const resourcePath = sanitizeResourcePath(args.resource_path);
  const normalizedResources = getResources(product.channel).map((entry) => entry.path);
  if (!normalizedResources.includes(resourcePath)) {
    const error = new Error('RESOURCE_NOT_AVAILABLE_FOR_CHANNEL');
    error.code = 'RESOURCE_NOT_AVAILABLE_FOR_CHANNEL';
    throw error;
  }

  return {
    product_id: product.product_id,
    uri: `${MCP_URI_PREFIX}${resourcePath}`,
    path: resourcePath,
    text: fs.readFileSync(resolveResourceFile(resourcePath), 'utf8'),
  };
}

function sanitizeResourcePath(resourcePath) {
  if (typeof resourcePath !== 'string' || !resourcePath.trim()) {
    const error = new Error('resource_path обязателен');
    error.code = 'INVALID_RESOURCE_PATH';
    throw error;
  }
  const normalized = path
    .normalize(resourcePath)
    .replace(/\\+/g, '/')
    .replace(/^\/+/, '');
  if (normalized.startsWith('..')) {
    const error = new Error('Недопустимый путь ресурса');
    error.code = 'INVALID_RESOURCE_PATH';
    throw error;
  }
  return normalized;
}

function resolveResourceFile(resourcePath) {
  const mappedPath = AI_CONTROL_RESOURCE_MAP[resourcePath];
  if (mappedPath) {
    const { full } = safeJoinResourcePath(mappedPath);
    return full;
  }
  const { full } = safeJoinResourcePath(resourcePath);
  return full;
}

function listTools() {
  return baseTools;
}

function handleToolsCall(name, args) {
  if (name === 'resolve_product') return resolveProduct(args);
  if (name === 'get_entrypoint') return getEntrypoint(args);
  if (name === 'list_resources') return listResources(args);
  if (name === 'get_resource') return getResource(args);
  const error = new Error(`Unknown tool: ${name}`);
  error.code = 'TOOL_NOT_FOUND';
  throw error;
}

function createToolResult(text) {
  const payload = typeof text === 'string' ? text : JSON.stringify(text, null, 2);
  return {
    content: [
      {
        type: 'text',
        text: payload,
      },
    ],
  };
}

function handleResourcesList() {
  return {
    resources: getResources(SERVER_CHANNEL),
    nextCursor: null,
  };
}

function readResourceByUri(uri) {
  if (typeof uri !== 'string' || !uri.startsWith(MCP_URI_PREFIX)) {
    const error = new Error('Недопустимый URI ресурса');
    error.code = 'INVALID_RESOURCE_URI';
    throw error;
  }
  const resourcePath = uri.slice(MCP_URI_PREFIX.length);
  const item = getResources(SERVER_CHANNEL).find(
    (resource) => resource.uri === uri || resource.path === resourcePath
  );
  if (!item) {
    const error = new Error('Ресурс недоступен');
    error.code = 'RESOURCE_NOT_AVAILABLE_FOR_CHANNEL';
    throw error;
  }
  const data = fs.readFileSync(resolveResourceFile(item.path), 'utf8');
  return {
    contents: [
      {
        uri: item.uri,
        mimeType: item.mimeType,
        text: data,
      },
    ],
  };
}

function handleMessage(raw) {
  let request;
  try {
    request = JSON.parse(raw);
  } catch (error) {
    writeResponse({
      jsonrpc: '2.0',
      error: {
        code: protocolError.PARSE_ERROR,
        message: 'Невалидный JSON',
      },
    });
    return;
  }

  if (!request || request.jsonrpc !== '2.0' || typeof request.method !== 'string') {
    if (request && Object.prototype.hasOwnProperty.call(request, 'id')) {
      writeError(request.id, protocolError.INVALID_REQUEST, 'Невалидный запрос');
    }
    return;
  }
  if (!Object.prototype.hasOwnProperty.call(request, 'id')) {
    return;
  }

  try {
    const method = request.method;
    const params = request.params || {};

    if (method === 'initialize') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: { listChanged: false },
            resources: { listChanged: false },
          },
          serverInfo: {
            name: 'ai-dev-team-mcp',
            version: PRODUCT_VERSION,
          },
        },
      });
      return;
    }

    if (method === 'tools/list') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: {
          tools: listTools(),
        },
      });
      return;
    }

    if (method === 'tools/call') {
      const called = handleToolsCall(params.name, params.arguments || {});
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: createToolResult(called),
      });
      return;
    }

    if (method === 'resources/list') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: handleResourcesList(),
      });
      return;
    }

    if (method === 'resources/read') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: readResourceByUri(params.uri),
      });
      return;
    }

    if (method === 'resolve_product') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: resolveProduct(params),
      });
      return;
    }

    if (method === 'get_entrypoint') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: getEntrypoint(params),
      });
      return;
    }

    if (method === 'list_resources') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: listResources(params),
      });
      return;
    }

    if (method === 'get_resource') {
      writeResponse({
        jsonrpc: '2.0',
        id: request.id,
        result: getResource(params),
      });
      return;
    }

    writeError(request.id, protocolError.METHOD_NOT_FOUND, `Unknown method: ${method}`);
  } catch (error) {
    writeError(request.id, codeToJsonRpc(error), error.message, {
      code: error.code || 'UNKNOWN_ERROR',
      channel: SERVER_CHANNEL,
    });
  }
}

function codeToJsonRpc(error) {
  if (error.code === 'UNKNOWN_PRODUCT') return protocolError.INVALID_REQUEST;
  if (error.code === 'UNKNOWN_CHANNEL') return protocolError.INVALID_PARAMS;
  if (
    error.code === 'INVALID_RESOURCE_PATH' ||
    error.code === 'INVALID_RESOURCE_URI'
  ) {
    return protocolError.INVALID_PARAMS;
  }
  if (
    error.code === 'RESOURCE_NOT_AVAILABLE_FOR_CHANNEL' ||
    error.code === 'ENTRYPOINT_NOT_FOUND'
  ) {
    return protocolError.INVALID_REQUEST;
  }
  if (error.code === 'TOOL_NOT_FOUND') {
    return protocolError.INVALID_PARAMS;
  }
  return protocolError.INTERNAL_ERROR;
}

function runSelfCheck() {
  try {
    const productId = CLI_OPTIONS.product || `${PRODUCT_ID}@${SERVER_CHANNEL}`;
    const resolved = resolveProduct({ product_id: productId });
    const entrypoint = getEntrypoint({ product_id: productId });
    const resources = listResources({ product_id: productId });

    process.stdout.write(`${JSON.stringify({
      ok: true,
      product_id: resolved.product_id,
      channel: resolved.channel,
      entrypoint: entrypoint.entrypoint,
      resource_count: resources.resources.length,
    }, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`Ошибка самопроверки: ${error.message}\n`);
    process.exit(1);
  }
}

let transportMode = null;

function writeResponse(response) {
  const payload = JSON.stringify(response);
  if (transportMode === 'json-line') {
    process.stdout.write(`${payload}\n`);
    return;
  }

  const frame =
    `Content-Length: ${Buffer.byteLength(payload, 'utf8')}\r\n\r\n${payload}`;
  process.stdout.write(frame);
}

function writeError(id, code, message, data) {
  writeResponse({
    jsonrpc: '2.0',
    id,
    error: {
      code,
      message,
      data,
    },
  });
}

function parseContentLength(headerBlock) {
  const lines = headerBlock.split('\r\n');
  for (const rawLine of lines) {
    const idx = rawLine.indexOf(':');
    if (idx < 0) {
      continue;
    }
    const name = rawLine.slice(0, idx).trim().toLowerCase();
    if (name !== 'content-length') {
      continue;
    }
    const value = rawLine.slice(idx + 1).trim();
    if (!value) {
      return null;
    }
    const length = Number.parseInt(value, 10);
    if (!Number.isFinite(length) || length < 0) {
      return null;
    }
    return length;
  }
  return null;
}

function extractFrameFromBuffer(buffer) {
  const separator = '\r\n\r\n';
  const headerEnd = buffer.indexOf(separator);
  if (headerEnd < 0) {
    return null;
  }

  const headerBlock = buffer.slice(0, headerEnd).toString('utf8');
  const contentLength = parseContentLength(headerBlock);
  if (contentLength === null) {
    return { raw: null, rest: buffer.slice(headerEnd + separator.length) };
  }

  const bodyStart = headerEnd + separator.length;
  const bodyEnd = bodyStart + contentLength;
  if (buffer.length < bodyEnd) {
    return null;
  }

  return {
    raw: buffer.slice(bodyStart, bodyEnd).toString('utf8'),
    rest: buffer.slice(bodyEnd),
  };
}

function detectTransportMode(buffer) {
  const trimmed = buffer.toString('utf8').trimStart();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith('Content-Length:')) {
    return 'mcp-framed';
  }
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    return 'json-line';
  }
  return null;
}

function extractJsonLineFromBuffer(buffer) {
  const newlineIndex = buffer.indexOf('\n');
  if (newlineIndex < 0) {
    return null;
  }

  return {
    raw: buffer.slice(0, newlineIndex).toString('utf8').trim(),
    rest: buffer.slice(newlineIndex + 1),
  };
}

function run() {
  if (process.stdin.isTTY && process.stderr.isTTY) {
    process.stderr.write(
      `ai-dev-team-mcp: канал=${SERVER_CHANNEL}, транспорт=stdio, ожидание клиента\n`
    );
  }

  let buffer = Buffer.alloc(0);
  process.stdin.on('data', (chunk) => {
    const next = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    buffer = Buffer.concat([buffer, next]);

    if (!transportMode) {
      transportMode = detectTransportMode(buffer);
      if (!transportMode) {
        return;
      }
    }

    while (true) {
      const frame =
        transportMode === 'json-line'
          ? extractJsonLineFromBuffer(buffer)
          : extractFrameFromBuffer(buffer);
      if (!frame) {
        break;
      }

      if (frame.raw === null) {
        writeResponse({
          jsonrpc: '2.0',
          id: null,
          error: {
            code: protocolError.PARSE_ERROR,
            message:
              transportMode === 'json-line'
                ? 'Невалидное JSON-сообщение'
                : 'Невалидный заголовок MCP',
          },
        });
        buffer = frame.rest;
        continue;
      }

      if (frame.raw) {
        handleMessage(frame.raw);
      }
      buffer = frame.rest;
    }
  });

  process.stdin.on('end', () => {
    if (buffer.length !== 0) {
      writeResponse({
        jsonrpc: '2.0',
        id: null,
        error: {
          code: protocolError.PARSE_ERROR,
          message:
            transportMode === 'json-line'
              ? 'Незавершённое JSON-сообщение'
              : 'Незавершённое MCP-сообщение',
        },
      });
    }
  });

  process.stdin.resume();
}

run();
