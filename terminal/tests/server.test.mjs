import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import net from 'node:net';
import { mkdtempSync, readFileSync, rmSync, chmodSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createTerminalServer } from '../server.mjs';
import { createDeviceApi } from '../device-api.mjs';
import { createOpenClawProvider } from '../provider.mjs';
import { main, readConfiguration } from '../start.mjs';

const TOKEN = 'synthetic-bridge-token-'.repeat(3);
async function fixture(t, dispatch = async body => ({ ok: true, body }), limits = {}) {
  const server = createTerminalServer({ token: TOKEN, dispatch, ...limits });
  const address = await server.listen(0);
  assert.equal(address.address, '127.0.0.1');
  t.after(() => server.close());
  const request = (value = {}, options = {}) => new Promise((resolve, reject) => {
    const body = Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(value));
    const req = http.request({ host: '127.0.0.1', port: address.port, method: 'POST', path: '/api/hardwareone',
      ...options, headers: { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json',
        'Content-Length': body.length, ...options.headers }, agent: false }, res => {
      const parts = [];
      res.on('data', part => parts.push(part));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, raw: Buffer.concat(parts).toString(),
        body: parts.length ? JSON.parse(Buffer.concat(parts)) : null }));
      res.on('error', reject);
    });
    req.on('error', reject); req.end(body);
  });
  const raw = value => new Promise((resolve, reject) => {
    const socket = net.createConnection(address.port, '127.0.0.1'); let result = '';
    socket.setEncoding('utf8'); socket.on('connect', () => socket.write(value));
    socket.on('data', part => result += part); socket.on('end', () => resolve(result));
    socket.on('error', error => error.code === 'ECONNRESET' ? resolve(result) : reject(error));
  });
  return { server, address, request, raw };
}

test('authenticated loopback host preserves API objects and exposes only its safe health identity', async t => {
  const calls = [], f = await fixture(t, async body => { calls.push(body); return { schema: 1, ok: true, requestId: body.requestId, text: '🌲' }; });
  const input = { schema: 1, op: 'list', requestId: 'a'.repeat(32), deviceId: 'fixture', offset: 0, limit: 2 };
  const response = await f.request(input);
  assert.equal(response.status, 200); assert.equal(response.body.text, '🌲'); assert.deepEqual(calls, [input]);
  assert.equal(Number(response.headers['content-length']), Buffer.byteLength(response.raw));
  assert.equal(response.headers['cache-control'], 'no-store'); assert.equal(response.headers.connection, 'close');
  const health = await f.raw(`GET /healthz HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer ${TOKEN}\r\n\r\n`);
  assert.match(health, /200 OK/); assert.match(health, /"service":"hardwareone-g2-terminal-bridge"/);
  assert(!health.includes(TOKEN)); assert.equal(calls.length, 1);
});

test('unauthorized, browser, duplicate header and non-API requests never reach the provider', async t => {
  let calls = 0; const f = await fixture(t, async () => { calls++; return {}; });
  for (const auth of ['', 'Bearer wrong', 'bearer ' + TOKEN, TOKEN])
    assert.equal((await f.request({}, { headers: { Authorization: auth } })).status, 401);
  assert.equal((await f.request({}, { headers: { Origin: 'https://example.invalid' } })).status, 400);
  for (const path of ['/api/hardwareone?token=' + TOKEN, '/api/hardwareone/', '/api/sessions', '/api/chat', '/api/events', '/debug', '/healthz?x=1'])
    assert.equal((await f.request({}, { path })).status, 404);
  for (const method of ['PUT', 'OPTIONS', 'GET']) assert.equal((await f.request({}, { method })).status, 404);
  const duplicated = await f.raw(`POST /api/hardwareone HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer ${TOKEN}\r\nauthorization: Bearer ${TOKEN}\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}`);
  assert.match(duplicated, /400 Bad Request/);
  const unauthHealth = await f.raw('GET /healthz HTTP/1.1\r\nHost: localhost\r\n\r\n');
  assert.match(unauthHealth, /401 Unauthorized/); assert.equal(calls, 0);
});

test('framing, body, UTF-8 and output limits fail with fixed errors and no payload leaks', async t => {
  let calls = 0; const f = await fixture(t, async body => { calls++; return body.mode === 'large' ? { text: 'X'.repeat(4096) } : { ok: true }; });
  for (const headers of [{ 'Content-Type': 'text/plain' }, { 'Content-Encoding': 'gzip' }, { Expect: '100-continue' }])
    assert.notEqual((await f.request({}, { headers })).status, 200);
  const upper = await f.request({ text: 'a'.repeat(4149) }); // 4160 bytes including JSON framing.
  assert.equal(upper.status, 200);
  assert.equal((await f.request({ text: 'a'.repeat(4150) })).status, 413);
  for (const input of ['{"private":"DO_NOT_ECHO",', '[]', 'null']) {
    const r = await f.request(Buffer.from(input)); assert.equal(r.status, 400); assert(!r.raw.includes('DO_NOT_ECHO'));
  }
  assert.equal((await f.request(Buffer.from([0x7b, 0x22, 0x78, 0x22, 0x3a, 0x22, 0xff, 0x22, 0x7d]))).status, 400);
  const large = await f.request({ mode: 'large' }); assert.equal(large.status, 500); assert(Buffer.byteLength(large.raw) <= 4096);
  const chunked = await f.raw(`POST /api/hardwareone HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer ${TOKEN}\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\n\r\n`);
  assert.match(chunked, /400 Bad Request/);
  const largeHeader = await f.raw(`GET /healthz HTTP/1.1\r\nHost: localhost\r\nX-Long: ${'a'.repeat(9000)}\r\n\r\n`);
  assert.match(largeHeader, /400 Bad Request/); assert.equal(calls, 2);
});

test('provider exceptions are sanitized; HTTP timeout neither repeats nor cancels admitted work', async t => {
  let resolveWork, calls = 0;
  const f = await fixture(t, body => {
    calls++;
    if (body.throw) throw Error('PRIVATE_PROVIDER_DETAIL');
    return new Promise(resolve => resolveWork = resolve);
  }, { operationTimeoutMs: 30 });
  const failed = await f.request({ throw: true }); assert.equal(failed.status, 500); assert(!failed.raw.includes('PRIVATE'));
  const timed = await f.request({ action: true }); assert.equal(timed.status, 504); assert.equal(calls, 2);
  resolveWork({ accepted: true }); await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 2);
});

test('slow headers/body and stalled shutdown are bounded; normal close drains admitted work', async t => {
  const f = await fixture(t, async () => ({}), { headerTimeoutMs: 30, bodyTimeoutMs: 30 });
  assert.equal(await f.raw('POST /api/hardwareone HTTP/1.1\r\n'), '');
  const partial = await f.raw(`POST /api/hardwareone HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer ${TOKEN}\r\nContent-Type: application/json\r\nContent-Length: 8\r\n\r\n{`);
  assert.match(partial, /408 Request Timeout/);
  let release, started;
  const admitted = new Promise(resolve => started = resolve);
  const g = await fixture(t, () => { started(); return new Promise(resolve => release = resolve); });
  const response = g.request({}); await admitted;
  let closed = false; const closing = g.server.close().then(() => closed = true);
  await new Promise(resolve => setImmediate(resolve)); assert.equal(closed, false);
  release({ accepted: true }); assert.equal((await response).body.accepted, true); await closing;
  const h = await fixture(t, () => new Promise(() => {}), { operationTimeoutMs: 30, shutdownTimeoutMs: 30 });
  const pending = h.request({}).catch(() => null); await new Promise(resolve => setTimeout(resolve, 10));
  await h.server.close(); await pending;
});

test('concurrent admitted work is bounded and a disconnected client does not trigger a retry', async t => {
  const releases = []; let admitted = 0;
  const f = await fixture(t, () => { admitted++; return new Promise(resolve => releases.push(resolve)); });
  const requests = Array.from({ length: 4 }, () => f.request({}));
  while (admitted < 4) await new Promise(resolve => setImmediate(resolve));
  assert.equal((await f.request({})).status, 503); assert.equal(admitted, 4);
  for (const release of releases) release({ accepted: true });
  assert((await Promise.all(requests)).every(r => r.body.accepted));
  let accepted, finish;
  const started = new Promise(resolve => accepted = resolve);
  const g = await fixture(t, () => { accepted(); return new Promise(resolve => finish = resolve); });
  const socket = net.createConnection(g.address.port, '127.0.0.1');
  socket.on('error', () => {});
  await new Promise(resolve => socket.once('connect', resolve));
  socket.write(`POST /api/hardwareone HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer ${TOKEN}\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}`);
  await started; socket.destroy();
  let closed = false; const closing = g.server.close().then(() => closed = true);
  await new Promise(resolve => setImmediate(resolve)); assert.equal(closed, false);
  finish({ accepted: true }); await closing; assert.equal(closed, true);
});

test('real provider/device API through HTTP preserves question receipt, retry and next user turn', async t => {
  let onEvent, sessionKey, runId, number = 0;
  const calls = [];
  const client = { onEvent(fn) { onEvent = fn; }, onDisconnect() {},
    async connect() { return { auth: { scopes: ['operator.questions'] }, features: { methods: ['question.list'] } }; },
    async request(method, params) {
      calls.push({ method, params });
      switch (method) {
        case 'sessions.subscribe': return {};
        case 'sessions.messages.subscribe': sessionKey = params.key; return { subscribed: true, key: sessionKey };
        case 'question.list': return { questions: [] };
        case 'chat.history': return { messages: [] };
        case 'chat.send': runId = params.idempotencyKey; return { runId };
        case 'question.resolve': return { status: 'answered' };
        default: throw Error('Unexpected fake method');
      }
    },
  };
  const provider = createOpenClawProvider(() => {}, { client });
  const f = await fixture(t, createDeviceApi(provider));
  const request = (op, extra = {}, requestId = (++number).toString(16).padStart(32, '0')) =>
    f.request({ schema: 1, op, deviceId: 'fixture', requestId, ...extra }).then(r => { assert.equal(r.status, 200); assert(r.body.ok); return r.body; });
  const view = await request('new'), selected = { view: view.view, instance: view.instance }; let cursor = 0;
  async function drain() {
    const events = [];
    for (let i = 0; i < 100; i++) {
      const response = await request('poll', { ...selected, after: cursor });
      cursor = response.cursor; events.push(...response.events); if (!response.more) return { events, state: response.state };
    }
    throw Error('View did not drain');
  }
  await drain(); await request('prompt', { ...selected, text: 'Keep chatting' }); await drain();
  onEvent({ event: 'question.requested', payload: { id: 'question', agentId: 'main', sessionKey, status: 'pending', expiresAtMs: Date.now() + 60000,
    questions: [{ questionId: 'choice', question: 'Choose one', options: [{ label: 'One' }, { label: 'Two' }] }] } });
  const card = (await drain()).events.find(e => e.type === 'query'); assert(card);
  const answer = { ...selected, pendingId: card.pendingId, questionId: card.questionId, optionIds: ['o1'] };
  const first = await request('question', answer, 'f'.repeat(32)); assert(first.applied);
  assert.deepEqual(await request('question', answer, 'f'.repeat(32)), first);
  const received = await drain(); assert(received.events.some(e => e.kind === 5 && e.text === 'Choose one\nYou: Two'));
  assert.equal(calls.filter(c => c.method === 'question.resolve').length, 1);
  onEvent({ event: 'chat', payload: { sessionKey, runId, seq: 1, state: 'final', message: { content: 'Let’s talk about Two.' } } });
  const final = await drain(); assert.equal(final.state, 'idle'); assert(final.events.some(e => e.kind === 2 && e.text === 'Let’s talk about Two.'));
  assert((await request('prompt', { ...selected, text: 'Tell me more' })).accepted);
  assert.equal(calls.filter(c => c.method === 'chat.send').length, 2);
});

test('initialization uses flat first-party files, preserves identity and refuses configuration overwrite', async () => {
  const root = mkdtempSync(join(tmpdir(), 'hardwareone-first-party-'));
  const previousUmask = process.umask(), log = console.log;
  try {
    console.log = () => {};
    await main(['--init'], root);
    const c = readConfiguration(root), identity = readFileSync(c.identityFile), token = readFileSync(c.bridgeTokenFile);
    assert.equal(c.port, 3457); assert(c.approvals); assert.equal(token.toString().trim().length, 64);
    await assert.rejects(main(['--init'], root), /Configuration exists/);
    assert.deepEqual(readFileSync(c.identityFile), identity); assert.deepEqual(readFileSync(c.bridgeTokenFile), token);
    writeFileSync(join(root, 'hardwareone.json'), JSON.stringify({ ...c, port: c.gatewayPort }));
    assert.throws(() => readConfiguration(root), /Invalid local/);
    writeFileSync(join(root, 'hardwareone.json'), JSON.stringify(c)); chmodSync(join(root, 'hardwareone.json'), 0o644);
    assert.throws(() => readConfiguration(root), /private regular/);
  } finally { console.log = log; process.umask(previousUmask); rmSync(root, { recursive: true, force: true }); }
});
