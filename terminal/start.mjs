import { existsSync, lstatSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { randomBytes } from 'node:crypto';
import { createIdentity, readPrivateToken, Gateway } from './gateway.mjs';
import { createOpenClawProvider } from './provider.mjs';
import { createDeviceApi } from './device-api.mjs';
import { createTerminalServer } from './server.mjs';

export function readConfiguration(root) {
  const path = join(root, 'hardwareone.json'), info = lstatSync(path);
  if (!info.isFile() || info.size > 8192 || info.mode & 0o077 || info.uid !== process.getuid())
    throw new Error('Host configuration must be a private regular file');
  const c = JSON.parse(readFileSync(path, 'utf8'));
  const names = ['port', 'gatewayPort', 'gatewayTokenFile', 'identityFile', 'bridgeTokenFile', 'approvals'];
  if (!c || typeof c !== 'object' || Array.isArray(c) || Object.keys(c).some(name => !names.includes(name)) ||
      !Number.isInteger(c.port) || c.port < 1024 || c.port > 65535 ||
      !Number.isInteger(c.gatewayPort) || c.gatewayPort < 1 || c.gatewayPort > 65535 || c.port === c.gatewayPort ||
      typeof c.approvals !== 'boolean' || names.slice(2, 5).some(name =>
        typeof c[name] !== 'string' || !isAbsolute(c[name]) || c[name].includes('\0')))
    throw new Error('Invalid local host configuration');
  return c;
}

export async function main(args = process.argv.slice(2), root = dirname(fileURLToPath(import.meta.url))) {
  process.umask(0o077);
  if (args.length > 1 || args.some(a => !['--init', '--check'].includes(a)))
    throw new Error('Usage: node start.mjs [--init|--check]');
  const configPath = join(root, 'hardwareone.json');
  if (args.includes('--init')) {
    if (existsSync(configPath)) throw new Error('Configuration exists; refusing to overwrite');
    const identityFile = join(root, 'gateway-identity.pem'), bridgeTokenFile = join(root, 'bridge-token.txt');
    if (!existsSync(identityFile)) createIdentity(identityFile);
    if (!existsSync(bridgeTokenFile)) writeFileSync(bridgeTokenFile, randomBytes(32).toString('hex') + '\n', { flag: 'wx', mode: 0o600 });
    writeFileSync(configPath, JSON.stringify({ port: 3457, gatewayPort: 18789,
      gatewayTokenFile: join(homedir(), '.openclaw/hardwareone-relay/gateway-token.txt'),
      identityFile, bridgeTokenFile, approvals: true }, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
    console.log('Created private host configuration. Review paths, then run node start.mjs --check to check pairing.');
    return;
  }
  const c = readConfiguration(root), token = readPrivateToken(c.bridgeTokenFile);
  const gateway = new Gateway({ tokenFile: c.gatewayTokenFile, identityFile: c.identityFile, approvals: c.approvals, port: c.gatewayPort });
  if (args.includes('--check')) {
    if (gateway.identity) console.log(`Hardware One Terminal device ID: ${gateway.identity.id}`);
    try {
      const hello = await gateway.connect();
      console.log(`Gateway ${hello.server.version} connected. Granted scopes: ${(hello.auth?.scopes || []).join(', ')}`);
    } catch {
      console.error('Gateway connection check failed. Inspect local Gateway status and pairing.');
      console.error('If pairing is required: run openclaw devices list, verify this device ID and requested scopes, then approve its exact request ID.');
      process.exitCode = 1;
    } finally { gateway.close(); }
    return;
  }
  const provider = createOpenClawProvider(() => {}, { client: gateway });
  const server = createTerminalServer({ token, dispatch: createDeviceApi(provider) });
  try { await server.listen(c.port); } catch (error) { gateway.close(); throw error; }
  console.log(`HardwareOne G2 Terminal Bridge listening on http://127.0.0.1:${c.port}`);
  let closing = false;
  const shutdown = async () => {
    if (closing) return;
    closing = true;
    await server.close();
    gateway.close();
  };
  process.once('SIGINT', shutdown); process.once('SIGTERM', shutdown);
  return { server, gateway, shutdown };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await main(); }
  catch { console.error('Terminal host could not start. Check its private configuration, files and local port.'); process.exitCode = 1; }
}
