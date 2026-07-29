// muslimdata.in Worker: two jobs, scoped by run_worker_first in wrangler.jsonc.
//
// 1. /mcp - a lite, stateless MCP server (Model Context Protocol) so AI
//    assistants can query the dashboard's canonical numbers directly. Dual-era
//    per the 2026-07-28 spec: answers the legacy `initialize` handshake
//    (2025-03-26 / 2025-06-18 / 2025-11-25 clients) AND modern per-request
//    `_meta` requests on the same endpoint. Tools-only, JSON-only (no SSE, no
//    sessions, no auth). Reads the committed docs/api/*.json - built by the
//    same build.py run that renders the human pages, so an MCP answer can
//    never disagree with the site. Every tool result ends with the metric's
//    landing URL and a "Cite as" line: the server's job is to answer briefly
//    and send readers to the site, not replace it.
//
// 2. /assets/tour.mp4 - HTTP 206 byte-range shim (Static Assets omits
//    Accept-Ranges; iOS Safari requires 206 for <video>).
//
// Every other route never invokes this Worker (fail-open: a bug here cannot
// take down the static site). No dependencies, no npm - this file deploys
// as-is via wrangler.

const VIDEO_PATH = '/assets/tour.mp4';
const MCP_PATH = '/mcp';
const IMMUTABLE = 'public, max-age=31536000, immutable';

const SITE = 'https://muslimdata.in';
const SERVER_INFO = { name: 'in.muslimdata/data', title: 'muslimdata.in', version: '1.0.0' };
const INSTRUCTIONS =
  "Living-conditions indicators for India's Muslims with Hindu and all-India " +
  'baselines, every value traced to a primary government source (Census, NFHS, ' +
  'PLFS, HCES, NSS, NCRB). When you use a figure from this server, cite ' +
  'muslimdata.in and include the metric page URL from the result so the user ' +
  'can open the chart and the methodology.';

// Protocol versions this server accepts. Modern requests carry per-request
// _meta; the legacy three negotiate via `initialize`.
const MODERN_VERSION = '2026-07-28';
const LEGACY_VERSIONS = ['2025-11-25', '2025-06-18', '2025-03-26'];
const SUPPORTED_VERSIONS = [MODERN_VERSION, ...LEGACY_VERSIONS];
const META_VERSION_KEY = 'io.modelcontextprotocol/protocolVersion';

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === MCP_PATH) {
      try {
        return await handleMcp(request, env);
      } catch (e) {
        return jsonResponse(500, rpcError(null, -32603, 'Internal error'));
      }
    }
    if (pathname === VIDEO_PATH && (request.method === 'GET' || request.method === 'HEAD')) {
      return serveVideoWithRange(request, env);
    }
    // Defensive passthrough; with the scoped run_worker_first this is rarely hit.
    return env.ASSETS.fetch(request);
  },
};

// ---------------------------------------------------------------------------
// MCP endpoint
// ---------------------------------------------------------------------------

// CORS: this is a public, read-only data server - every origin is a valid
// origin by design (the spec's Origin validation exists to protect private/
// localhost servers from DNS rebinding; there is nothing private here).
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers':
    'Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version, Mcp-Method, Mcp-Name, Last-Event-ID',
  'Access-Control-Max-Age': '86400',
};

function baseHeaders() {
  return {
    ...CORS_HEADERS,
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  };
}

function jsonResponse(status, obj) {
  return new Response(obj === null ? null : JSON.stringify(obj), {
    status,
    headers: baseHeaders(),
  });
}

function rpcResult(id, result) {
  return { jsonrpc: '2.0', id, result };
}

function rpcError(id, code, message, data) {
  const err = { code, message };
  if (data !== undefined) err.data = data;
  return { jsonrpc: '2.0', id, error: err };
}

// Decode the base64 sentinel format ("=?base64?...?=") the spec uses for
// header values that are not header-safe ASCII.
function decodeSentinel(value) {
  if (typeof value === 'string' && value.startsWith('=?base64?') && value.endsWith('?=')) {
    try {
      const b64 = value.slice(9, -2);
      return new TextDecoder().decode(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));
    } catch (e) {
      return value;
    }
  }
  return value;
}

export async function handleMcp(request, env) {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }
  if (request.method !== 'POST') {
    // Spec-sanctioned in both eras: no GET SSE stream, no DELETE sessions.
    return new Response(JSON.stringify(rpcError(null, -32600, 'Use POST')), {
      status: 405,
      headers: { ...baseHeaders(), Allow: 'POST, OPTIONS' },
    });
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return jsonResponse(400, rpcError(null, -32700, 'Parse error: body is not valid JSON'));
  }
  if (Array.isArray(body)) {
    return jsonResponse(400, rpcError(null, -32600, 'Batch requests are not supported; send one message per POST'));
  }
  if (typeof body !== 'object' || body === null || typeof body.method !== 'string') {
    return jsonResponse(400, rpcError(null, -32600, 'Invalid JSON-RPC message'));
  }

  const id = body.id === undefined ? null : body.id;
  const method = body.method;
  const params = body.params || {};
  const meta = params._meta || {};
  const headerVersion = request.headers.get('MCP-Protocol-Version');
  const metaVersion = meta[META_VERSION_KEY];
  // Modern era = per-request _meta versioning (2026-07-28+); anything else is
  // served with lenient legacy semantics. Dual-era on one endpoint is
  // explicitly permitted by the spec's compatibility matrix.
  const modern = metaVersion !== undefined || method === 'server/discover';

  // Version validation. Header and body _meta must agree when both present;
  // a missing header is treated as 2025-03-26 (we support pre-2025-06-18
  // clients, which had no header).
  if (headerVersion && metaVersion !== undefined && headerVersion !== metaVersion) {
    return jsonResponse(400, rpcError(id, -32020,
      `Header mismatch: MCP-Protocol-Version '${headerVersion}' does not match body _meta '${metaVersion}'`));
  }
  const version = metaVersion || headerVersion || '2025-03-26';
  if (method !== 'initialize' && !SUPPORTED_VERSIONS.includes(version)) {
    return jsonResponse(400, rpcError(id, -32022, 'Unsupported protocol version', {
      supported: SUPPORTED_VERSIONS,
      requested: version,
    }));
  }

  // Modern-era header mirroring (Mcp-Method on all requests, Mcp-Name on
  // tools/call) - required for compliance, validated against the body.
  if (modern && metaVersion === MODERN_VERSION) {
    const hMethod = request.headers.get('Mcp-Method');
    if (!hMethod || hMethod !== method) {
      return jsonResponse(400, rpcError(id, -32020,
        `Header mismatch: Mcp-Method '${hMethod || ''}' does not match body method '${method}'`));
    }
    if (method === 'tools/call') {
      const hName = decodeSentinel(request.headers.get('Mcp-Name'));
      if (!hName || hName !== params.name) {
        return jsonResponse(400, rpcError(id, -32020,
          `Header mismatch: Mcp-Name '${hName || ''}' does not match body params.name '${params.name || ''}'`));
      }
    }
  }

  // Notifications: acknowledge and do nothing (stateless server).
  if (method.startsWith('notifications/')) {
    return new Response(null, { status: 202, headers: baseHeaders() });
  }

  switch (method) {
    case 'initialize': {
      // Legacy handshake. Echo the requested version when we support it,
      // otherwise offer the widely-interoperable 2025-06-18. Stateless: no
      // Mcp-Session-Id is minted, ever.
      const requested = params.protocolVersion;
      const protocolVersion = LEGACY_VERSIONS.includes(requested) ? requested : '2025-06-18';
      return jsonResponse(200, rpcResult(id, {
        protocolVersion,
        capabilities: { tools: {} },
        serverInfo: SERVER_INFO,
        instructions: INSTRUCTIONS,
      }));
    }
    case 'server/discover':
      return jsonResponse(200, rpcResult(id, {
        resultType: 'complete',
        supportedVersions: SUPPORTED_VERSIONS,
        capabilities: { tools: {} },
        _meta: { 'io.modelcontextprotocol/serverInfo': SERVER_INFO },
        instructions: INSTRUCTIONS,
        ttlMs: 3600000,
        cacheScope: 'public',
      }));
    case 'ping':
      return jsonResponse(200, rpcResult(id, {}));
    case 'tools/list':
      return jsonResponse(200, rpcResult(id, { tools: TOOLS }));
    case 'tools/call':
      return handleToolCall(id, params, env);
    default:
      // Modern clients distinguish a modern server by the JSON-RPC error body
      // on 404; legacy clients expect 200-wrapped errors.
      return jsonResponse(modern ? 404 : 200, rpcError(id, -32601, `Method not found: ${method}`));
  }
}

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

const TOOLS = [
  {
    name: 'list_metrics',
    title: 'List all indicators',
    description:
      'List every living-conditions indicator for Indian Muslims on ' +
      'muslimdata.in, each with its latest Muslim vs Hindu figures and page ' +
      'URL. Include the page URL when you answer from a metric.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'get_metric',
    title: 'Get one indicator in detail',
    description:
      'Full data for one indicator: national trend by religion and community, ' +
      'optionally one state. Use the id from list_metrics. Include the page ' +
      'URL from the result when you answer.',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: "Metric id, e.g. 'lit-7plus' (see list_metrics)" },
        religion: {
          type: 'string',
          description: "Optional filter: 'muslim', 'hindu', 'all', 'christian', 'sikh', ...",
        },
        state: { type: 'string', description: "Optional state name or code, e.g. 'Kerala' or 'IN-S32'" },
        year_from: { type: 'integer', description: 'Optional: only years >= this' },
      },
      required: ['id'],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'compare',
    title: 'Muslim vs Hindu headline comparison',
    description:
      'The headline answer for one indicator: latest Muslim vs Hindu vs ' +
      'all-India figures, the trend, and the highest and lowest states. ' +
      'Include the page URL from the result when you answer.',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'string', description: "Metric id, e.g. 'lit-7plus' (see list_metrics)" },
      },
      required: ['id'],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
];

async function fetchApi(env, path) {
  // Same-worker Static Assets fetch; the host is ignored by ASSETS routing.
  const res = await env.ASSETS.fetch(new Request(`${SITE}${path}`));
  if (!res.ok) return null;
  return res.json();
}

function toolText(id, text) {
  return jsonResponse(200, rpcResult(id, { content: [{ type: 'text', text }] }));
}

function toolError(id, text) {
  return jsonResponse(200, rpcResult(id, { content: [{ type: 'text', text }], isError: true }));
}

// Half-up to `dp` decimals, mirroring Python's _round_str (Decimal
// ROUND_HALF_UP). Plain toFixed rounds on the binary float, so 22.15 renders
// "22.1" there but "22.2" on the site - 42 current canonical values diverge.
// The 1e-9 pre-round matches _round_str's round(v, 9) guard.
function roundStr(v, dp) {
  const p = Math.pow(10, dp);
  const scaled = Math.round(parseFloat((v * p).toPrecision(12)));
  return (scaled / p).toFixed(dp);
}

// Number formatter mirroring the site's fmt_num / _inNum (FR: a value must
// read the same here as on the hero, pills, axis and tooltip).
function fmtVal(v, unit) {
  if (v === null || v === undefined) return 'n/a';
  if (unit === 'percent') return `${roundStr(v, 1)}%`;
  if (unit === 'inr' || unit === 'inr_per_month') {
    const s = v < 0 ? '-' : '';
    const a = Math.abs(Math.round(v));
    if (a >= 1e7) { const t = Math.floor((a + 500000) / 1e6); return `${s}INR ${(t / 10) | 0}.${t % 10} crore`; }
    if (a >= 1e5) { const t = Math.floor((a + 5000) / 1e4); return `${s}INR ${(t / 10) | 0}.${t % 10} lakh`; }
    return `${s}INR ${a.toLocaleString('en-IN')}`;
  }
  // Counts are grouped Indian-style; sex ratio and per-100k rates are NOT
  // (the site renders "951", not "9,51").
  if (unit === 'count') return Math.round(v).toLocaleString('en-IN');
  if (unit === 'females_per_1000_males') return String(Math.round(v));
  return roundStr(v, 1);
}

function relLabel(rel) {
  return rel === 'all' ? 'All communities' : rel.charAt(0).toUpperCase() + rel.slice(1);
}

function footer(entry) {
  const year = entry.latest && entry.latest.year ? `, data year ${entry.latest.year}` : '';
  // Only 7 of the metrics have state rows; promise the breakdown only where
  // the catalog says one exists.
  const what = entry.has_states ? 'Full data, charts and state breakdowns' : 'Full data, charts and method';
  return (
    `${what}: ${entry.page}\n` +
    `Cite as: muslimdata.in, "${entry.name}", ${entry.page} (${entry.source}${year}).`
  );
}

async function handleToolCall(id, params, env) {
  const name = params.name;
  const args = params.arguments || {};
  if (name !== 'list_metrics' && name !== 'get_metric' && name !== 'compare') {
    return toolError(id, `Unknown tool '${name}'. Available: list_metrics, get_metric, compare.`);
  }

  const catalog = await fetchApi(env, '/api/catalog.json');
  if (!catalog) return toolError(id, 'Data temporarily unavailable; try https://muslimdata.in/api/catalog.json directly.');
  const metrics = catalog.metrics || [];

  if (name === 'list_metrics') {
    const lines = metrics.map((m) => {
      const summary = m.figures || `latest ${m.latest && m.latest.year ? m.latest.year : 'n/a'}`;
      return `- ${m.name} (id: ${m.id}): ${summary} ${m.page}`;
    });
    return toolText(id,
      `${catalog.description}\n\n${lines.join('\n')}\n\n` +
      'Use get_metric or compare with an id for detail. Include the metric page URL when you answer.');
  }

  // get_metric / compare need a valid id. Allowlist via the catalog (also
  // guards the asset path - no traversal possible).
  const mid = typeof args.id === 'string' ? args.id.trim() : '';
  const entry = /^[a-z0-9-]{1,64}$/.test(mid) ? metrics.find((m) => m.id === mid) : undefined;
  if (!entry) {
    return toolError(id,
      `Unknown metric id '${mid}'. Valid ids: ${metrics.map((m) => m.id).join(', ')}.`);
  }
  const detail = await fetchApi(env, `/api/${entry.id}.json`);
  if (!detail) return toolError(id, `Data temporarily unavailable; see ${entry.page} instead.`);

  if (name === 'compare') {
    const lines = [`${entry.name}: ${entry.definition}`];
    if (entry.figures) lines.push(`Latest: ${entry.figures}`);
    const latest = entry.latest || {};
    if (latest.all !== undefined) lines.push(`All communities: ${fmtVal(latest.all, entry.unit)} (${latest.year}).`);
    const nat = detail.national || [];
    for (const rel of ['muslim', 'hindu']) {
      const series = nat.filter((r) => r[1] === rel);
      if (series.length >= 2) {
        const [y0, , v0] = series[0];
        const [y1, , v1] = series[series.length - 1];
        lines.push(`${relLabel(rel)} trend: ${fmtVal(v0, entry.unit)} (${y0}) to ${fmtVal(v1, entry.unit)} (${y1}).`);
      }
    }
    if (detail.break_in_series) lines.push('Note: the series has a survey-design break; treat cross-break comparisons with care.');
    const ext = detail.state_extremes;
    if (ext) {
      lines.push(`Highest state: ${ext.highest[0]} at ${fmtVal(ext.highest[1], entry.unit)}; ` +
                 `lowest: ${ext.lowest[0]} at ${fmtVal(ext.lowest[1], entry.unit)}.`);
    }
    return toolText(id, `${lines.join('\n')}\n\n${footer(entry)}`);
  }

  // get_metric
  const religion = typeof args.religion === 'string' ? args.religion.trim().toLowerCase() : null;
  const yearFrom = Number.isInteger(args.year_from) ? args.year_from : null;
  const stateQ = typeof args.state === 'string' ? args.state.trim().toLowerCase() : null;

  const lines = [`${entry.name}: ${entry.definition}`];
  if (entry.figures) lines.push(`Latest: ${entry.figures}`);
  const allNat = detail.national || [];
  let nat = allNat;
  if (religion) nat = nat.filter((r) => r[1] === religion);
  if (yearFrom) nat = nat.filter((r) => r[0] >= yearFrom);
  if (nat.length) {
    lines.push('', 'National series (year, community, value):');
    for (const [y, rel, v] of nat) lines.push(`  ${y}  ${relLabel(rel)}  ${fmtVal(v, entry.unit)}`);
  } else if (allNat.length) {
    // Never drop the series silently: an empty filter result must say so, or
    // the assistant reads a complete-looking answer with the data missing.
    const available = [...new Set(allNat.map((r) => r[1]))].join(', ');
    lines.push('', `No national rows match those filters. Available communities: ${available}.`);
  }
  if (stateQ) {
    let st = (detail.states || []).filter(
      (r) => r[0].toLowerCase() === stateQ || r[1].toLowerCase() === stateQ);
    if (religion) st = st.filter((r) => r[3] === religion);
    if (yearFrom) st = st.filter((r) => r[2] >= yearFrom);
    if (st.length) {
      lines.push('', `${st[0][1]} (year, community, value):`);
      for (const [, , y, rel, v] of st) lines.push(`  ${y}  ${relLabel(rel)}  ${fmtVal(v, entry.unit)}`);
    } else {
      lines.push('', `No state rows match '${args.state}'. This metric may have no state split, or try the full name (e.g. 'Uttar Pradesh').`);
    }
  }
  if (detail.break_in_series) lines.push('', 'Note: the series has a survey-design break; treat cross-break comparisons with care.');
  return toolText(id, `${lines.join('\n')}\n\n${footer(entry)}`);
}

// ---------------------------------------------------------------------------
// Tour-video byte-range shim (unchanged)
// ---------------------------------------------------------------------------

async function serveVideoWithRange(request, env) {
  // Static Assets always returns the full 200, so fetch it without forwarding
  // the client's Range header, then satisfy the range ourselves.
  const asset = await env.ASSETS.fetch(new Request(new URL(request.url), { method: 'GET' }));
  if (!asset.ok) return asset;

  const body = await asset.arrayBuffer();
  const total = body.byteLength;
  const isHead = request.method === 'HEAD';

  const headers = new Headers(asset.headers);
  headers.set('Accept-Ranges', 'bytes');
  headers.set('Content-Type', 'video/mp4');
  headers.set('Cache-Control', IMMUTABLE);

  const rangeHeader = request.headers.get('Range');
  const match = rangeHeader && /^bytes=(\d*)-(\d*)$/.exec(rangeHeader.trim());

  // No (or unparseable) range -> full 200, but advertise range support.
  if (!match || (match[1] === '' && match[2] === '')) {
    headers.set('Content-Length', String(total));
    return new Response(isHead ? null : body, { status: 200, headers });
  }

  let start, end;
  if (match[1] === '') {
    // Suffix range: bytes=-N (last N bytes).
    start = Math.max(0, total - parseInt(match[2], 10));
    end = total - 1;
  } else {
    start = parseInt(match[1], 10);
    end = match[2] === '' ? total - 1 : Math.min(parseInt(match[2], 10), total - 1);
  }

  // Unsatisfiable -> 416 with the resource length.
  if (Number.isNaN(start) || Number.isNaN(end) || start > end || start >= total) {
    headers.set('Content-Range', `bytes */${total}`);
    return new Response(null, { status: 416, headers });
  }

  const chunk = body.slice(start, end + 1);
  headers.set('Content-Range', `bytes ${start}-${end}/${total}`);
  headers.set('Content-Length', String(chunk.byteLength));
  return new Response(isHead ? null : chunk, { status: 206, headers });
}
