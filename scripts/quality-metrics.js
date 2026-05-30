#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const scriptPath = path.resolve(__dirname, "..", "tooling", "quality", "quality-metrics.js");
const result = spawnSync(process.execPath, [scriptPath, ...process.argv.slice(2)], {
  stdio: "inherit",
});
process.exit(result.status ?? 1);
