// User login-service entry point. Configuration contains paths, never credentials.
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
const config = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const child = spawn(config.python, ['-m', 'dagster', 'dev', '-m', 'market_atlas.orchestration.definitions', '--host', '127.0.0.1', '--port', '3001'], {
  cwd: config.directory, env: {...process.env, ...config.environment}, stdio: 'inherit',
});
let stopping = false;
for (const signal of ['SIGTERM','SIGINT']) process.on(signal, () => {
  if (!stopping) { stopping = true; child.kill(signal); }
});
child.on('error', error => { process.stderr.write(`Dagster start failed (${error.code || error.name}).\n`); process.exit(1); });
child.on('exit', code => process.exit(stopping ? 0 : (code || 1)));
