#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..', '..');
const targetDirs = ['apps/web/src'];
const validExtensions = new Set(['.ts', '.tsx', '.js', '.jsx']);
const ignoredDirs = new Set(['node_modules', '.next', 'dist', 'coverage', '.git']);
const ignoredPathSegments = new Set(['__tests__', 'test']);
const ignoredFilePatterns = [/\.test\.[jt]sx?$/, /\.spec\.[jt]sx?$/];

const findings = [];

const walk = (dirPath) => {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    const relativePath = path.relative(repoRoot, fullPath);

    if (entry.isDirectory()) {
      if (ignoredDirs.has(entry.name) || ignoredPathSegments.has(entry.name)) {
        continue;
      }
      walk(fullPath);
      continue;
    }

    if (ignoredFilePatterns.some((pattern) => pattern.test(entry.name))) {
      continue;
    }

    const ext = path.extname(entry.name);
    if (!validExtensions.has(ext)) {
      continue;
    }

    const content = fs.readFileSync(fullPath, 'utf8');
    const lines = content.split(/\r?\n/);

    lines.forEach((line, index) => {
      const trimmed = line.trim();

      if (trimmed.startsWith('//') || trimmed.startsWith('*') || trimmed.startsWith('/*')) {
        return;
      }

      if (line.includes('/v1/')) {
        findings.push({
          file: relativePath,
          line: index + 1,
          value: line.trim(),
        });
      }
    });
  }
};

for (const target of targetDirs) {
  const fullTarget = path.join(repoRoot, target);
  if (fs.existsSync(fullTarget)) {
    walk(fullTarget);
  }
}

if (findings.length > 0) {
  console.error('❌ Frontend /v1 path guard failed. Use internal app routes instead of provider-style /v1 endpoints.');
  findings.forEach((finding) => {
    console.error(`  - ${finding.file}:${finding.line} -> ${finding.value}`);
  });
  process.exit(1);
}

console.log('✅ Frontend /v1 path guard passed.');
