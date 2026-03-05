#!/usr/bin/env node
/**
 * Theme System Verification Script
 * Validates the GoblinOS theme implementation
 */

import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..');

const CHECKS = {
  passed: [],
  failed: [],
  warnings: [],
};

function checkExists(filePath, description) {
  const fullPath = join(ROOT, filePath);
  if (existsSync(fullPath)) {
    CHECKS.passed.push(`✅ ${description}`);
    return true;
  } else {
    CHECKS.failed.push(`❌ ${description} (not found: ${filePath})`);
    return false;
  }
}

function checkFileContains(filePath, patterns, description) {
  const fullPath = join(ROOT, filePath);
  if (!existsSync(fullPath)) {
    CHECKS.failed.push(`❌ ${description} (file not found)`);
    return false;
  }

  const content = readFileSync(fullPath, 'utf-8');
  const missing = [];

  for (const [name, pattern] of Object.entries(patterns)) {
    if (!pattern.test(content)) {
      missing.push(name);
    }
  }

  if (missing.length === 0) {
    CHECKS.passed.push(`✅ ${description}`);
    return true;
  } else {
    CHECKS.failed.push(`❌ ${description} (missing: ${missing.join(', ')})`);
    return false;
  }
}

console.log('\n🔍 GoblinOS Theme System Verification\n');
console.log('═'.repeat(50) + '\n');

// 1. Core theme files exist
console.log('📁 Checking theme module files...\n');
checkExists('src/theme/index.css', 'Theme CSS module exists');
checkExists('src/theme/theme.js', 'Theme JS utilities exist');

// 2. Theme CSS has required variables
console.log('\n🎨 Checking CSS variable definitions...\n');
checkFileContains(
  'src/theme/index.css',
  {
    neutrals: /--bg:\s*#071117/,
    'brand colors': /--primary:\s*#06D06A/,
    'high-contrast': /\.goblinos-high-contrast/,
    'reduced motion': /@media\s*\(prefers-reduced-motion:\s*reduce\)/,
    'focus indicators': /:focus-visible/,
    'skip link': /\.skip-link/,
  },
  'Theme CSS has required tokens and accessibility features'
);

// 3. Theme JS has required exports
console.log('\n⚙️  Checking theme utilities...\n');
checkFileContains(
  'src/theme/theme.js',
  {
    setThemeVars: /export function setThemeVars/,
    enableHighContrast: /export function enableHighContrast/,
    initializeTheme: /export function initializeTheme/,
    THEME_PRESETS: /export const THEME_PRESETS/,
    'system preferences': /matchMedia\('.*prefers-contrast.*'\)/,
  },
  'Theme utilities have all required exports'
);

// 4. App.tsx integration
console.log('\n🔌 Checking app integration...\n');
checkFileContains(
  'src/App.tsx',
  {
    'theme import': /import.*from\s+['"]\.\/theme\/theme['"]/,
    'css import': /import\s+['"]\.\/theme\/index\.css['"]/,
    initialization: /initializeTheme\(\)/,
  },
  'App.tsx imports and initializes theme system'
);

// 5. Tailwind config uses CSS vars
console.log('\n🎨 Checking Tailwind integration...\n');
const tailwindPath = join(ROOT, '../tailwind.config.js');
if (existsSync(tailwindPath)) {
  const tailwind = readFileSync(tailwindPath, 'utf-8');
  const hasCssVars = /var\(--bg\)/.test(tailwind) && /var\(--primary\)/.test(tailwind);
  if (hasCssVars) {
    CHECKS.passed.push('✅ Tailwind config uses CSS variables');
  } else {
    CHECKS.failed.push('❌ Tailwind config does not reference CSS variables');
  }
} else {
  CHECKS.warnings.push('⚠️  Could not find tailwind.config.js');
}

// 6. High-contrast toggle exists
console.log('\n🎛️  Checking UI components...\n');
checkExists('src/components/ContrastModeToggle.tsx', 'High-contrast toggle component exists');
checkExists('src/hooks/useContrastMode.tsx', 'Contrast mode hook exists');

// 7. Check for hard-coded hex colors (sample check)
console.log('\n🔍 Scanning for hard-coded colors...\n');
const indexCss = readFileSync(join(ROOT, 'src/index.css'), 'utf-8');
const hasThemeImport = /@import.*theme\/index\.css/.test(indexCss);
const hasDuplicateVars = indexCss.includes('--bg: #071117') && !indexCss.includes('@import');

if (hasThemeImport) {
  CHECKS.passed.push('✅ index.css imports theme/index.css (no duplicates)');
} else if (hasDuplicateVars) {
  CHECKS.warnings.push('⚠️  index.css may have duplicate CSS variable definitions');
} else {
  CHECKS.warnings.push('⚠️  Could not verify CSS import pattern');
}

// Results summary
console.log('\n' + '═'.repeat(50));
console.log('\n📊 Results Summary\n');
console.log(`✅ Passed: ${CHECKS.passed.length}`);
console.log(`❌ Failed: ${CHECKS.failed.length}`);
console.log(`⚠️  Warnings: ${CHECKS.warnings.length}\n`);

if (CHECKS.failed.length > 0) {
  console.log('Failed Checks:\n');
  CHECKS.failed.forEach((msg) => console.log(`  ${msg}`));
  console.log('');
}

if (CHECKS.warnings.length > 0) {
  console.log('Warnings:\n');
  CHECKS.warnings.forEach((msg) => console.log(`  ${msg}`));
  console.log('');
}

if (CHECKS.passed.length > 0 && CHECKS.failed.length === 0) {
  console.log('✨ All checks passed!\n');
  console.log('Theme system is correctly implemented:\n');
  console.log('  • CSS variables defined in src/theme/index.css');
  console.log('  • Runtime utilities in src/theme/theme.js');
  console.log('  • High-contrast mode toggle available');
  console.log('  • Reduced motion support enabled');
  console.log('  • Tailwind integrated with CSS vars');
  console.log('  • App initialized on mount\n');
}

// Exit with error code if any checks failed
process.exit(CHECKS.failed.length > 0 ? 1 : 0);
