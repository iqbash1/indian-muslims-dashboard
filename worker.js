// Byte-range shim for the self-hosted navigation tour video.
//
// Cloudflare Workers Static Assets serves files with HTTP 200 and no
// Accept-Ranges, so <video> playback fails on iOS Safari (which requires
// 206 Partial Content). This Worker runs first ONLY for the video path
// (see "run_worker_first" in wrangler.jsonc) and re-serves it with proper
// range support. Every other route is served directly by Static Assets and
// never invokes this Worker, so the rest of the site is unaffected.

const VIDEO_PATH = '/assets/tour.mp4';
const IMMUTABLE = 'public, max-age=31536000, immutable';

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === VIDEO_PATH && (request.method === 'GET' || request.method === 'HEAD')) {
      return serveVideoWithRange(request, env);
    }
    // Defensive passthrough; with the scoped run_worker_first this is rarely hit.
    return env.ASSETS.fetch(request);
  },
};

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
