import http from 'node:http';
import { createHash, timingSafeEqual } from 'node:crypto';

const MAX_BODY = 4096 + 64; // Relay adds its authenticated device identity.
const MAX_RESPONSE = 4096;
const messages = {
  400: 'Invalid request', 401: 'Unauthorized', 404: 'Not found', 408: 'Request timed out',
  413: 'Request too large', 415: 'Unsupported content type', 500: 'Host operation failed',
  503: 'Host unavailable', 504: 'Operation timed out; inspect status before retrying',
};
const hash = value => createHash('sha256').update(value).digest();
const timeout = value => Number.isInteger(value) && value > 0 && value <= 60000;

// This host has no public/browser API. The authenticated local relay owns the
// device identity; the existing device API owns all sessions and mutations.
export function createTerminalServer({ token, dispatch, headerTimeoutMs = 10000,
  bodyTimeoutMs = 10000, operationTimeoutMs = 30000, shutdownTimeoutMs = 30000 } = {}) {
  if (typeof token !== 'string' || token.length < 32 || token.length > 4096 || /[^\x21-\x7e]/u.test(token))
    throw new Error('A bounded private bridge token is required');
  if (typeof dispatch !== 'function' || ![headerTimeoutMs, bodyTimeoutMs, operationTimeoutMs, shutdownTimeoutMs].every(timeout))
    throw new Error('Invalid host configuration');
  const expected = hash('Bearer ' + token), sockets = new Map(), usedSockets = new WeakSet(), work = new Set();
  let stopping = false, closing;
  function reply(res, status, value = { error: messages[status] }) {
    if (res.destroyed || res.writableEnded) return;
    let body;
    try { body = Buffer.from(JSON.stringify(value)); } catch { status = 500; }
    if (!body || body.length > MAX_RESPONSE) { status = 500; body = Buffer.from(JSON.stringify({ error: messages[500] })); }
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': body.length,
      'Cache-Control': 'no-store', 'Connection': 'close', 'X-Content-Type-Options': 'nosniff' });
    res.end(body);
  }
  function uniqueHeaders(req) {
    const names = new Set();
    for (let i = 0; i < req.rawHeaders.length; i += 2) {
      const name = req.rawHeaders[i].toLowerCase();
      if (names.has(name)) return false;
      names.add(name);
    }
    return true;
  }
  const server = http.createServer({ maxHeaderSize: 8192, headersTimeout: Math.min(headerTimeoutMs, bodyTimeoutMs),
    requestTimeout: bodyTimeoutMs, connectionsCheckingInterval: 1000 }, (req, res) => {
    clearTimeout(sockets.get(req.socket));
    if (usedSockets.has(req.socket)) { req.socket.destroy(); return; }
    usedSockets.add(req.socket);
    const reject = status => { reply(res, status); req.resume(); };
    if (stopping || work.size >= 4) { reject(503); return; }
    if (!uniqueHeaders(req) || Object.hasOwn(req.headers, 'origin') || req.headers.expect || req.headers.upgrade ||
        req.headers['transfer-encoding'] || req.headers['content-encoding']) { reject(400); return; }
    const auth = req.headers.authorization;
    if (typeof auth !== 'string' || auth.length > 4103 || !timingSafeEqual(hash(auth), expected)) { reject(401); return; }
    if (req.method === 'GET' && req.url === '/healthz' && !req.headers['content-length']) {
      reply(res, 200, { service: 'hardwareone-g2-terminal-bridge', schema: 1 }); return;
    }
    if (req.method !== 'POST' || req.url !== '/api/hardwareone') { reject(404); return; }
    if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/iu.test(req.headers['content-type'] || '')) { reject(415); return; }
    const length = req.headers['content-length'];
    if (typeof length !== 'string' || !/^[1-9][0-9]*$/u.test(length)) { reject(400); return; }
    if (Number(length) > MAX_BODY) { reject(413); return; }
    const parts = []; let received = 0, abandoned = false;
    const bodyTimer = setTimeout(() => { abandoned = true; reply(res, 408); req.resume(); }, bodyTimeoutMs);
    const abandon = () => { abandoned = true; clearTimeout(bodyTimer); };
    req.on('aborted', abandon); req.on('error', abandon);
    req.on('data', chunk => {
      if (abandoned) return;
      received += chunk.length;
      if (received > MAX_BODY || received > Number(length)) { abandon(); reply(res, 413); return; }
      parts.push(chunk);
    });
    req.on('end', () => {
      clearTimeout(bodyTimer);
      if (abandoned || res.destroyed) return;
      let value;
      try {
        if (received !== Number(length)) throw new Error();
        value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(parts)));
        if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
      } catch { reply(res, 400); return; }
      if (stopping || work.size >= 4) { reply(res, 503); return; }
      // A lost client/HTTP timeout never cancels or repeats an admitted action.
      // Device request IDs retain their outcome in the existing API cache.
      const timer = setTimeout(() => reply(res, 504), operationTimeoutMs);
      const task = Promise.resolve().then(() => dispatch(value)).then(
        result => reply(res, 200, result), () => reply(res, 500),
      ).finally(() => { clearTimeout(timer); work.delete(task); });
      work.add(task);
    });
  });
  server.maxConnections = 8;
  server.maxRequestsPerSocket = 1;
  server.on('connection', socket => {
    const timer = setTimeout(() => socket.destroy(), headerTimeoutMs);
    sockets.set(socket, timer);
    socket.on('error', () => {});
    socket.on('close', () => { clearTimeout(timer); sockets.delete(socket); });
  });
  const badSocket = socket => {
    if (!socket.destroyed && socket.writable) socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 0\r\n\r\n');
  };
  server.on('clientError', (_error, socket) => badSocket(socket));
  server.on('upgrade', (_req, socket) => badSocket(socket));
  server.on('connect', (_req, socket) => badSocket(socket));
  server.on('checkContinue', (req, res) => { reply(res, 400); req.resume(); });
  server.on('checkExpectation', (req, res) => { reply(res, 400); req.resume(); });
  return {
    address: () => server.address(),
    listen(port = 3457) {
      if (!Number.isInteger(port) || port < 0 || port > 65535 || stopping) return Promise.reject(new Error('Invalid listen request'));
      return new Promise((resolve, reject) => {
        const failed = error => { server.off('listening', ready); reject(error); };
        const ready = () => { server.off('error', failed); resolve(server.address()); };
        server.once('error', failed); server.once('listening', ready);
        server.listen({ host: '127.0.0.1', port });
      });
    },
    close() {
      if (closing) return closing;
      stopping = true;
      closing = (async () => {
        const drained = new Promise(resolve => server.close(() => resolve()));
        let timer;
        await Promise.race([Promise.all([drained, Promise.allSettled([...work])]),
          new Promise(resolve => { timer = setTimeout(resolve, shutdownTimeoutMs); })]);
        clearTimeout(timer);
        for (const socket of sockets.keys()) socket.destroy();
        await drained;
      })();
      return closing;
    },
  };
}
