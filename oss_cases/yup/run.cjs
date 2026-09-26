// Original Bug Squad runner; upstream sources remain unmodified.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const esbuild = require('esbuild');

const bug = process.argv[2];
if (!/^bug0[123]$/.test(bug || '')) {
  console.error('Usage: node oss_cases/yup/run.cjs bug01|bug02|bug03');
  process.exit(2);
}

const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'bug-squad-yup-'));
try {
  const output = path.join(temporary, 'reproduce.cjs');
  esbuild.buildSync({
    entryPoints: [path.join(__dirname, bug, 'reproduce.js')],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    target: 'node18',
    outfile: output,
    logLevel: 'warning',
  });
  const result = spawnSync(process.execPath, [output], { stdio: 'inherit' });
  if (result.error) throw result.error;
  process.exitCode = result.status ?? 1;
} finally {
  fs.rmSync(temporary, { recursive: true, force: true });
}
