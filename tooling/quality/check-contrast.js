#!/usr/bin/env node

// WCAG AA Contrast Ratio Calculator
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

// Critical token combinations
const tests = [
  { name: '--text on --bg', fg: '#E6F2F1', bg: '#071117', minRatio: 4.5, usage: 'Body text' },
  { name: '--muted on --bg', fg: '#9AA5A8', bg: '#071117', minRatio: 4.5, usage: 'Secondary text' },
  { name: '--text on --surface', fg: '#E6F2F1', bg: '#0b1617', minRatio: 4.5, usage: 'Card text' },
  {
    name: '--muted on --surface',
    fg: '#9AA5A8',
    bg: '#0b1617',
    minRatio: 4.5,
    usage: 'Card secondary',
  },
  {
    name: '--primary on --bg (large)',
    fg: '#06D06A',
    bg: '#071117',
    minRatio: 3.0,
    usage: 'Headings/buttons (large text)',
  },
  {
    name: '--danger on --bg',
    fg: '#ff4757',
    bg: '#071117',
    minRatio: 4.5,
    usage: 'Error messages',
  },
  {
    name: '--warning on --bg',
    fg: '#ffa502',
    bg: '#071117',
    minRatio: 4.5,
    usage: 'Warning messages',
  },
  { name: '--info on --bg', fg: '#3498db', bg: '#071117', minRatio: 4.5, usage: 'Info messages' },
];

console.log('\n========================================');
console.log('   WCAG AA Contrast Audit');
console.log('========================================\n');

let allPass = true;
const failures = [];

tests.forEach((test) => {
  const ratio = contrastRatio(test.fg, test.bg);
  const pass = ratio >= test.minRatio;
  const status = pass ? '✅ PASS' : '❌ FAIL';
  allPass = allPass && pass;

  console.log(`${status} ${test.name}`);
  console.log(`   Colors: ${test.fg} on ${test.bg}`);
  console.log(`   Ratio: ${ratio.toFixed(2)}:1 (min: ${test.minRatio}:1)`);
  console.log(`   Usage: ${test.usage}`);

  if (!pass) {
    failures.push({ ...test, actualRatio: ratio.toFixed(2) });
    console.log(`   ⚠️  NEEDS ADJUSTMENT!`);
  }
  console.log('');
});

console.log('========================================');
console.log(allPass ? '✅ ALL TESTS PASSED' : '⚠️  SOME TESTS FAILED');
console.log('========================================\n');

if (failures.length > 0) {
  console.log('FAILURES SUMMARY:');
  failures.forEach((f) => {
    console.log(`  • ${f.name}: ${f.actualRatio}:1 (need ${f.minRatio}:1)`);
  });
  console.log('');
}

process.exit(allPass ? 0 : 1);
