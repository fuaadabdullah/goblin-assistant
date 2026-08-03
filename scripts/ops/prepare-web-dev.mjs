#!/usr/bin/env node

import { execFileSync } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const PORT = 3000;
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

function run(command, args) {
  try {
    return execFileSync(command, args, {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      windowsHide: true,
    }).trim();
  } catch {
    return '';
  }
}

function listeningPid(port) {
  if (process.platform === 'win32') {
    const command = [
      `$connection = Get-NetTCPConnection -State Listen -LocalPort ${port}`,
      '  | Select-Object -First 1 -ExpandProperty OwningProcess;',
      'if ($connection) { Write-Output $connection }',
    ].join(' ');
    const output = run('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', command]);
    const pid = Number.parseInt(output, 10);
    return Number.isInteger(pid) && pid > 0 ? pid : null;
  }

  const output = run('lsof', [`-tiTCP:${port}`, '-sTCP:LISTEN']);
  const pid = Number.parseInt(output.split(/\s+/)[0] ?? '', 10);
  return Number.isInteger(pid) && pid > 0 ? pid : null;
}

function processCommand(pid) {
  if (process.platform === 'win32') {
    const command = [
      `$process = Get-CimInstance Win32_Process -Filter \"ProcessId = ${pid}\";`,
      'if ($process) { Write-Output $process.CommandLine }',
    ].join(' ');
    return run('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', command]);
  }
  return run('ps', ['-p', String(pid), '-o', 'command=']);
}

function isOwnedNextDev(commandLine) {
  const normalizedCommand = commandLine.replaceAll('\\', '/').toLowerCase();
  const normalizedRepoRoot = REPO_ROOT.replaceAll('\\', '/').toLowerCase();
  const nextRuntime =
    /(?:^|[\/\s])next(?:\.cmd|\.exe)?(?:[\/\s]|$)/i.test(commandLine) ||
    normalizedCommand.includes('/next/dist/server/lib/start-server.js');
  return normalizedCommand.includes(normalizedRepoRoot) && nextRuntime;
}

function stopProcess(pid) {
  if (process.platform === 'win32') {
    execFileSync('taskkill.exe', ['/PID', String(pid), '/T', '/F'], {
      stdio: 'ignore',
      windowsHide: true,
    });
    return;
  }
  process.kill(pid, 'SIGTERM');
}

function waitForPortRelease(port, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (listeningPid(port) === null) return true;
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100);
  }
  return listeningPid(port) === null;
}

const ownerPid = listeningPid(PORT);
if (ownerPid === null) {
  console.log(`==> Port ${PORT} is available.`);
  process.exit(0);
}

const commandLine = processCommand(ownerPid);
if (!isOwnedNextDev(commandLine)) {
  console.error(`Port ${PORT} is already in use by PID ${ownerPid}.`);
  console.error(
    `Refusing to kill a process not owned by this checkout: ${commandLine || 'command unavailable'}`
  );
  process.exit(1);
}

console.log(`==> Stopping orphaned Next.js dev server on port ${PORT} (PID ${ownerPid})...`);
try {
  stopProcess(ownerPid);
} catch (error) {
  console.error(`Unable to stop PID ${ownerPid}: ${error instanceof Error ? error.message : error}`);
  process.exit(1);
}

if (!waitForPortRelease(PORT)) {
  console.error(`Port ${PORT} is still occupied after stopping PID ${ownerPid}.`);
  process.exit(1);
}

console.log(`==> Port ${PORT} is available.`);
