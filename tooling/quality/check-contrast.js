#!/usr/bin/env node

// WCAG AA contrast audit.
//
// Token values are read from the stylesheet rather than repeated here. An
// earlier version hard-coded them, and when the palette moved from green to
// amber the audit kept passing against colors that no longer shipped.

const fs = require('node:fs');
const path = require('node:path');

const THEME_CSS = path.resolve(
  __dirname,
  '..',
  '..',
  'apps',
  'web',
  'src',
  'theme',
  'index.css'
);

// Each themed block declares its own full token set.
const THEMES = [
  { name: 'Standard', selector: ':root' },
  { name: 'High contrast', selector: ':root.goblinos-high-contrast' },
  { name: 'Light', selector: ':root.goblinos-light' },
];

// Pairs are named by token, so they follow the palette wherever it goes.
const PAIRS = [
  { fg: 'text', bg: 'bg', minRatio: 4.5, usage: 'Body text' },
  { fg: 'muted', bg: 'bg', minRatio: 4.5, usage: 'Secondary text' },
  { fg: 'text', bg: 'surface', minRatio: 4.5, usage: 'Card text' },
  { fg: 'muted', bg: 'surface', minRatio: 4.5, usage: 'Card secondary' },
  { fg: 'primary', bg: 'bg', minRatio: 3.0, usage: 'Headings/buttons (large text)' },
  { fg: 'danger', bg: 'bg', minRatio: 4.5, usage: 'Error messages' },
  { fg: 'warning', bg: 'bg', minRatio: 4.5, usage: 'Warning messages' },
  { fg: 'info', bg: 'bg', minRatio: 4.5, usage: 'Info messages' },
];

function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

function luminance(r, g, b) {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrastRatio(hex1, hex2) {
  const rgb1 = hexToRgb(hex1);
  const rgb2 = hexToRgb(hex2);
  const lum1 = luminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = luminance(rgb2.r, rgb2.g, rgb2.b);
  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Pull `--name: #hex;` declarations out of one selector's block.
function readTokens(css, selector) {
  const start = css.indexOf(`${selector} {`);
  if (start === -1) {
    return null;
  }
  const end = css.indexOf('\n}', start);
  const block = css.slice(start, end === -1 ? undefined : end);

  const tokens = {};
  const declaration = /--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g;
  let match;
  while ((match = declaration.exec(block)) !== null) {
    tokens[match[1]] = match[2];
  }
  return tokens;
}

if (!fs.existsSync(THEME_CSS)) {
  console.error(`❌ Theme stylesheet not found at ${THEME_CSS}`);
  process.exit(1);
}

const css = fs.readFileSync(THEME_CSS, 'utf8');

console.log('\n========================================');
console.log('   WCAG AA Contrast Audit');
console.log('========================================');
console.log(`Tokens read from ${path.relative(path.resolve(__dirname, '..', '..'), THEME_CSS)}\n`);

const failures = [];

// A theme block overrides only the tokens it redeclares; the rest cascade down
// from :root, so resolve against that base rather than reporting them missing.
const baseTokens = readTokens(css, ':root');

if (!baseTokens) {
  console.error('❌ No :root block found in the theme stylesheet.');
  process.exit(1);
}

for (const theme of THEMES) {
  const declared = readTokens(css, theme.selector);
  const tokens = declared ? { ...baseTokens, ...declared } : null;

  if (!tokens) {
    console.error(`❌ Theme block "${theme.selector}" not found — cannot audit ${theme.name}.`);
    failures.push({ name: `${theme.name}: missing block`, actualRatio: 'n/a', minRatio: 'n/a' });
    continue;
  }

  console.log(`--- ${theme.name} (${theme.selector}) ---\n`);

  for (const pair of PAIRS) {
    const fg = tokens[pair.fg];
    const bg = tokens[pair.bg];
    const label = `--${pair.fg} on --${pair.bg}`;

    if (!fg || !bg) {
      console.error(`❌ MISSING ${label} — token not declared in ${theme.selector}`);
      console.log('');
      failures.push({
        name: `${theme.name}: ${label}`,
        actualRatio: 'undefined token',
        minRatio: pair.minRatio,
      });
      continue;
    }

    const ratio = contrastRatio(fg, bg);
    const pass = ratio >= pair.minRatio;

    console.log(`${pass ? '✅ PASS' : '❌ FAIL'} ${label}`);
    console.log(`   Colors: ${fg} on ${bg}`);
    console.log(`   Ratio: ${ratio.toFixed(2)}:1 (min: ${pair.minRatio}:1)`);
    console.log(`   Usage: ${pair.usage}`);

    if (!pass) {
      failures.push({
        name: `${theme.name}: ${label}`,
        actualRatio: ratio.toFixed(2),
        minRatio: pair.minRatio,
      });
      console.log(`   ⚠️  NEEDS ADJUSTMENT!`);
    }
    console.log('');
  }
}

console.log('========================================');
console.log(failures.length === 0 ? '✅ ALL TESTS PASSED' : '⚠️  SOME TESTS FAILED');
console.log('========================================\n');

if (failures.length > 0) {
  console.log('FAILURES SUMMARY:');
  failures.forEach((f) => {
    console.log(`  - ${f.name}: ${f.actualRatio}:1 (needs ${f.minRatio}:1)`);
  });
  console.log('');
  process.exit(1);
}
