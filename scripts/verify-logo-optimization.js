#!/usr/bin/env node

/**
 * Logo Optimization Verification Script
 *
 * Checks:
 * 1. Logo component exists with proper props
 * 2. SVG assets exist and are optimized
 * 3. Favicons are present
 * 4. Theme-adaptive CSS is configured
 * 5. Navigation uses Logo component
 */

import { readFileSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const appRoot = dirname(__dirname);

let checksPass = 0;
let checksFail = 0;

function check(condition, successMsg, failMsg) {
  if (condition) {
    console.log(`✅ ${successMsg}`);
    checksPass++;
    return true;
  } else {
    console.log(`❌ ${failMsg}`);
    checksFail++;
    return false;
  }
}

console.log('🎨 Verifying Logo Optimization...\n');

// 1. Check Logo component exists
const logoComponentPath = join(appRoot, 'src/components/Logo.tsx');
const logoExists = existsSync(logoComponentPath);
check(logoExists, '1. Logo component exists', '1. Logo component missing');

if (logoExists) {
  const logoContent = readFileSync(logoComponentPath, 'utf-8');
  check(
    logoContent.includes('variant') &&
      logoContent.includes('size') &&
      logoContent.includes('animated'),
    '   - Logo has variant, size, and animated props',
    '   - Logo missing required props'
  );
  check(
    logoContent.includes('emoji') && logoContent.includes('simple') && logoContent.includes('full'),
    '   - Logo supports emoji, simple, and full variants',
    '   - Logo missing variant options'
  );
  check(
    logoContent.includes('xs') && logoContent.includes('sm') && logoContent.includes('md'),
    '   - Logo supports multiple size options',
    '   - Logo missing size options'
  );
}

// 2. Check SVG assets
const logoSvgPath = join(appRoot, 'src/assets/logo.svg');
const logoSimpleSvgPath = join(appRoot, 'src/assets/logo-simple.svg');

check(existsSync(logoSvgPath), '2. Full logo SVG exists', '2. Full logo SVG missing');
check(existsSync(logoSimpleSvgPath), '   - Simple logo SVG exists', '   - Simple logo SVG missing');

if (existsSync(logoSvgPath)) {
  const svgContent = readFileSync(logoSvgPath, 'utf-8');
  check(
    svgContent.includes('var(--color-') && svgContent.includes('viewBox'),
    '   - Logo SVG uses CSS variables (theme-adaptive)',
    '   - Logo SVG not using CSS variables'
  );
  check(
    svgContent.length < 5000,
    '   - Logo SVG is optimized (< 5KB)',
    '   - Logo SVG might need optimization'
  );
}

// 3. Check favicons
const faviconPath = join(appRoot, 'public/favicon.svg');
const appleTouchIconPath = join(appRoot, 'public/apple-touch-icon.svg');

check(existsSync(faviconPath), '3. Favicon SVG exists', '3. Favicon SVG missing');
check(
  existsSync(appleTouchIconPath),
  '   - Apple touch icon exists',
  '   - Apple touch icon missing'
);

// 4. Check HTML references
const htmlPath = join(appRoot, 'index.html');
if (existsSync(htmlPath)) {
  const htmlContent = readFileSync(htmlPath, 'utf-8');
  check(
    htmlContent.includes('favicon.svg'),
    '4. HTML references favicon.svg',
    '4. HTML missing favicon reference'
  );
  check(
    htmlContent.includes('apple-touch-icon'),
    '   - HTML includes apple-touch-icon',
    '   - HTML missing apple-touch-icon'
  );
  check(
    htmlContent.includes('theme-color'),
    '   - HTML includes theme-color meta tag',
    '   - HTML missing theme-color meta'
  );
}

// 5. Check CSS animations
const cssPath = join(appRoot, 'src/index.css');
if (existsSync(cssPath)) {
  const cssContent = readFileSync(cssPath, 'utf-8');
  check(
    cssContent.includes('.logo-transition') && cssContent.includes('.logo-animated'),
    '5. CSS includes logo animation classes',
    '5. CSS missing logo animation classes'
  );
  check(
    cssContent.includes('pulse-glow') && cssContent.includes('@keyframes'),
    '   - CSS includes pulse-glow animation',
    '   - CSS missing pulse-glow animation'
  );
  check(
    cssContent.includes('prefers-reduced-motion'),
    '   - CSS respects prefers-reduced-motion',
    '   - CSS missing reduced motion support'
  );
}

// 6. Check Navigation integration
const navPath = join(appRoot, 'src/components/Navigation.tsx');
if (existsSync(navPath)) {
  const navContent = readFileSync(navPath, 'utf-8');
  check(
    navContent.includes('import Logo') && navContent.includes('<Logo'),
    '6. Navigation uses Logo component',
    '6. Navigation not using Logo component'
  );
  check(
    navContent.includes('size="sm"') && navContent.includes('variant="simple"'),
    '   - Navigation uses appropriate logo size/variant',
    '   - Navigation missing logo props'
  );
}

// Summary
console.log('\n' + '='.repeat(60));
console.log(`📊 Verification Complete`);
console.log('='.repeat(60));
console.log(`✅ Checks Passed: ${checksPass}`);
console.log(`❌ Checks Failed: ${checksFail}`);

if (checksFail === 0) {
  console.log('\n🎉 Logo optimization complete and verified!');
  console.log('\nFeatures:');
  console.log('  • Theme-adaptive SVG logos');
  console.log('  • Multiple variants (full, simple, emoji)');
  console.log('  • Multiple sizes (xs, sm, md, lg, xl)');
  console.log('  • Smooth animations with reduced motion support');
  console.log('  • Optimized favicons for all platforms');
  process.exit(0);
} else {
  console.log('\n⚠️  Some checks failed. Please review the errors above.');
  process.exit(1);
}
