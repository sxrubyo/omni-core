#!/usr/bin/env node

const fs = require("fs");
const os = require("os");
const path = require("path");

const packageRoot = path.resolve(__dirname, "..");
const launcherPath = path.join(packageRoot, "npm", "omni.js");
const nodePath = process.execPath;
const homeDir = os.homedir();
const localBin = path.join(homeDir, ".local", "bin");

function ensureDir(target) {
  fs.mkdirSync(target, { recursive: true });
}

function writeFile(target, contents, mode) {
  ensureDir(path.dirname(target));
  fs.writeFileSync(target, contents, "utf8");
  if (mode) {
    fs.chmodSync(target, mode);
  }
}

function psString(value) {
  return value.replace(/'/g, "''");
}

function cmdString(value) {
  return value.replace(/"/g, '""');
}

function main() {
  ensureDir(localBin);

  const shellWrapper = `#!/usr/bin/env bash
set -euo pipefail
exec "${nodePath}" "${launcherPath}" "$@"
`;
  const cmdWrapper = `@echo off
"${cmdString(nodePath)}" "${cmdString(launcherPath)}" %*
`;
  const psWrapper = `#!/usr/bin/env pwsh
$node = '${psString(nodePath)}'
$launcher = '${psString(launcherPath)}'
& $node $launcher @args
exit $LASTEXITCODE
`;

  writeFile(path.join(localBin, "omni"), shellWrapper, 0o755);
  writeFile(path.join(localBin, "omni.cmd"), cmdWrapper);
  writeFile(path.join(localBin, "omni.ps1"), psWrapper);
}

main();
