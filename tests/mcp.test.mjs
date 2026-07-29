// Unit tests for the /mcp handler in worker.js. Zero dependencies: plain
// `node --test tests/mcp.test.mjs` (node 18+ has node:test and the fetch
// globals). env.ASSETS is stubbed from the committed docs/api/ files, so the
// tests exercise the same data the deployed worker serves.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { handleMcp } from '../worker.js';

const DOCS = join(dirname(fileURLToPath(import.meta.url)), '..', 'docs');

const env = {
  ASSETS: {
    fetch: async (req) => {
      const path = new URL(req.url).pathname;
      const file = join(DOCS, path);
      if (!existsSync(file)) return new Response('not found', { status: 404 });
      return new Response(readFileSync(file), { status: 200 });
    },
  },
};

function post(bodyObj, headers = {}) {
  return new Request('https://muslimdata.in/mcp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(bodyObj),
  });
}

function rpc(method, params, id = 1) {
  return { jsonrpc: '2.0', id, method, ...(params ? { params } : {}) };
}

test('OPTIONS preflight returns 204 with CORS', async () => {
  const res = await handleMcp(new Request('https://muslimdata.in/mcp', { method: 'OPTIONS' }), env);
  assert.equal(res.status, 204);
  assert.equal(res.headers.get('access-control-allow-origin'), '*');
});

test('GET returns 405 with Allow', async () => {
  const res = await handleMcp(new Request('https://muslimdata.in/mcp', { method: 'GET' }), env);
  assert.equal(res.status, 405);
  assert.equal(res.headers.get('allow'), 'POST, OPTIONS');
});

test('legacy initialize echoes a supported version, no session header', async () => {
  const res = await handleMcp(post(rpc('initialize', {
    protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '0' },
  })), env);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('mcp-session-id'), null);
  const j = await res.json();
  assert.equal(j.result.protocolVersion, '2025-06-18');
  assert.ok(j.result.capabilities.tools);
  assert.ok(j.result.serverInfo.name);
  assert.ok(j.result.instructions.includes('muslimdata.in'));
});

test('initialize with an unknown version falls back to 2025-06-18', async () => {
  const res = await handleMcp(post(rpc('initialize', { protocolVersion: '1900-01-01' })), env);
  const j = await res.json();
  assert.equal(j.result.protocolVersion, '2025-06-18');
});

test('notifications/initialized returns 202 with empty body', async () => {
  const res = await handleMcp(post({ jsonrpc: '2.0', method: 'notifications/initialized' }), env);
  assert.equal(res.status, 202);
  assert.equal(await res.text(), '');
});

test('ping returns empty result', async () => {
  const res = await handleMcp(post(rpc('ping')), env);
  const j = await res.json();
  assert.deepEqual(j.result, {});
});

test('tools/list returns the 3 read-only tools with schemas', async () => {
  const res = await handleMcp(post(rpc('tools/list')), env);
  const j = await res.json();
  const names = j.result.tools.map((t) => t.name);
  assert.deepEqual(names, ['list_metrics', 'get_metric', 'compare']);
  for (const t of j.result.tools) {
    assert.ok(t.inputSchema, `${t.name} has inputSchema`);
    assert.equal(t.annotations.readOnlyHint, true);
  }
});

test('every POST response carries no-store, nosniff and CORS', async () => {
  const res = await handleMcp(post(rpc('ping')), env);
  assert.equal(res.headers.get('cache-control'), 'no-store');
  assert.equal(res.headers.get('x-content-type-options'), 'nosniff');
  assert.equal(res.headers.get('access-control-allow-origin'), '*');
});

test('tools/call list_metrics lists 23 metrics with page URLs', async () => {
  const res = await handleMcp(post(rpc('tools/call', { name: 'list_metrics', arguments: {} })), env);
  const j = await res.json();
  const text = j.result.content[0].text;
  assert.ok(text.includes('id: lit-7plus'));
  assert.ok(text.includes('https://muslimdata.in/m/lit-7plus/'));
  assert.equal((text.match(/- /g) || []).length, 23);
});

test('tools/call compare carries the landing URL and Cite as line', async () => {
  const res = await handleMcp(post(rpc('tools/call', { name: 'compare', arguments: { id: 'lit-7plus' } })), env);
  const j = await res.json();
  const text = j.result.content[0].text;
  assert.ok(!j.result.isError);
  assert.ok(text.includes('https://muslimdata.in/m/lit-7plus/'));
  assert.ok(text.includes('Cite as:'));
  assert.ok(text.includes('Muslim'));
});

test('tools/call get_metric filters by religion and state', async () => {
  const res = await handleMcp(post(rpc('tools/call', {
    name: 'get_metric',
    arguments: { id: 'lit-7plus', religion: 'muslim', state: 'Kerala' },
  })), env);
  const j = await res.json();
  const text = j.result.content[0].text;
  assert.ok(text.includes('Kerala'));
  assert.ok(!text.includes('Hindu  '), 'religion filter applied to series rows');
  assert.ok(text.includes('Cite as:'));
});

test('traversal-shaped id is rejected as a tool error, no throw', async () => {
  const res = await handleMcp(post(rpc('tools/call', { name: 'get_metric', arguments: { id: '../etc' } })), env);
  assert.equal(res.status, 200);
  const j = await res.json();
  assert.equal(j.result.isError, true);
  assert.ok(j.result.content[0].text.includes('Valid ids:'));
});

test('unknown tool name is a tool error listing the tools', async () => {
  const res = await handleMcp(post(rpc('tools/call', { name: 'drop_tables', arguments: {} })), env);
  const j = await res.json();
  assert.equal(j.result.isError, true);
  assert.ok(j.result.content[0].text.includes('list_metrics'));
});

test('unknown method (legacy) returns 200 with -32601', async () => {
  const res = await handleMcp(post(rpc('resources/list')), env);
  assert.equal(res.status, 200);
  const j = await res.json();
  assert.equal(j.error.code, -32601);
});

test('batch bodies are rejected with -32600', async () => {
  const res = await handleMcp(post([rpc('ping', undefined, 1), rpc('ping', undefined, 2)]), env);
  assert.equal(res.status, 400);
  const j = await res.json();
  assert.equal(j.error.code, -32600);
});

// ---- modern era (2026-07-28) ----

const MODERN_META = { 'io.modelcontextprotocol/protocolVersion': '2026-07-28' };

test('server/discover returns supportedVersions incl 2026-07-28', async () => {
  const res = await handleMcp(post(rpc('server/discover', { _meta: MODERN_META }),
    { 'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': 'server/discover' }), env);
  assert.equal(res.status, 200);
  const j = await res.json();
  assert.equal(j.result.resultType, 'complete');
  assert.ok(j.result.supportedVersions.includes('2026-07-28'));
  assert.ok(j.result.supportedVersions.includes('2025-03-26'));
  assert.ok(j.result._meta['io.modelcontextprotocol/serverInfo'].name);
});

test('modern request with mismatched Mcp-Method is 400 / -32020', async () => {
  const res = await handleMcp(post(
    { jsonrpc: '2.0', id: 1, method: 'tools/list', params: { _meta: MODERN_META } },
    { 'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': 'tools/call' }), env);
  assert.equal(res.status, 400);
  const j = await res.json();
  assert.equal(j.error.code, -32020);
});

test('modern tools/call validates Mcp-Name against params.name', async () => {
  const ok = await handleMcp(post(
    { jsonrpc: '2.0', id: 1, method: 'tools/call', params: { _meta: MODERN_META, name: 'compare', arguments: { id: 'lit-7plus' } } },
    { 'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': 'tools/call', 'Mcp-Name': 'compare' }), env);
  assert.equal(ok.status, 200);
  const bad = await handleMcp(post(
    { jsonrpc: '2.0', id: 1, method: 'tools/call', params: { _meta: MODERN_META, name: 'compare', arguments: { id: 'lit-7plus' } } },
    { 'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': 'tools/call', 'Mcp-Name': 'other' }), env);
  assert.equal(bad.status, 400);
});

test('unsupported protocol version is 400 / -32022 with supported list', async () => {
  const res = await handleMcp(post(rpc('tools/list', {
    _meta: { 'io.modelcontextprotocol/protocolVersion': '1900-01-01' },
  }), { 'MCP-Protocol-Version': '1900-01-01', 'Mcp-Method': 'tools/list' }), env);
  assert.equal(res.status, 400);
  const j = await res.json();
  assert.equal(j.error.code, -32022);
  assert.ok(j.error.data.supported.includes('2026-07-28'));
});

test('unknown method (modern) returns 404 with -32601', async () => {
  const res = await handleMcp(post(rpc('subscriptions/listen', { _meta: MODERN_META }),
    { 'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': 'subscriptions/listen' }), env);
  assert.equal(res.status, 404);
  const j = await res.json();
  assert.equal(j.error.code, -32601);
});

test('header/body protocol version mismatch is 400 / -32020', async () => {
  const res = await handleMcp(post(rpc('tools/list', { _meta: MODERN_META }),
    { 'MCP-Protocol-Version': '2025-06-18', 'Mcp-Method': 'tools/list' }), env);
  assert.equal(res.status, 400);
  const j = await res.json();
  assert.equal(j.error.code, -32020);
});
