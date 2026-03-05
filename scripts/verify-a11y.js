#!/usr/bin/env node

/**
 * Quick Accessibility Verification Script
 *
 * Checks key accessibility features are in place:
 * 1. High-contrast CSS tokens exist
 * 2. prefers-reduced-motion media query exists
 * 3. Focus indicators defined
 * 4. Skip link styles defined
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const cssPath = path.join(__dirname, '../src/index.css');
const css = fs.readFileSync(cssPath, 'utf8');

console.log('\n========================================');
console.log('   Accessibility Feature Check');
console.log('========================================\n');

const checks = [
  {
    name: 'High-Contrast Mode CSS',
    pattern: /\.goblinos-high-contrast/,
    description: 'CSS variables for high-contrast mode',
  },
  {
    name: 'Reduced Motion Support',
    pattern: /@media \(prefers-reduced-motion: reduce\)/,
    description: 'Media query for motion sensitivity',
  },
  {
    name: 'Focus Indicators',
    pattern: /:focus-visible/,
    description: 'Keyboard navigation focus styles',
  },
  {
    name: 'Skip Link',
    pattern: /\.skip-link/,
    description: 'Skip to main content link',
  },
  {
    name: 'Enhanced Button Focus',
    pattern: /button:focus-visible/,
    description: 'Button-specific focus enhancement',
  },
  {
    name: 'Enhanced Input Focus',
    pattern: /input:focus-visible/,
    description: 'Input-specific focus enhancement',
  },
  {
    name: 'Scanlines Effect',
    pattern: /\.scanlines::after/,
    description: 'CRT scanline overlay effect',
  },
];

let allPassed = true;

checks.forEach((check) => {
  const found = check.pattern.test(css);
  const status = found ? '✅ FOUND' : '❌ MISSING';

  if (!found) allPassed = false;

  console.log(`${status} ${check.name}`);
  console.log(`   ${check.description}`);
  console.log('');
});

console.log('========================================');
console.log(allPassed ? '✅ ALL FEATURES PRESENT' : '⚠️  SOME FEATURES MISSING');
console.log('========================================\n');

// Check component files exist
const componentsToCheck = [
  '../src/hooks/useContrastMode.tsx',
  '../src/components/ContrastModeToggle.tsx',
];

console.log('Component Files:\n');

componentsToCheck.forEach((filePath) => {
  const fullPath = path.join(__dirname, filePath);
  const exists = fs.existsSync(fullPath);
  const status = exists ? '✅ EXISTS' : '❌ MISSING';
  console.log(`${status} ${path.basename(filePath)}`);
});

console.log('\n========================================\n');

if (!allPassed) {
  console.error('ERROR: Some accessibility features are missing!');
  process.exit(1);
}

console.log('✅ All accessibility features verified!\n');
console.log('Next steps:');
console.log('1. Open http://localhost:3000 in browser');
console.log('2. Check for contrast toggle in navigation');
console.log('3. Run Lighthouse audit for full verification\n');

process.exit(0);
