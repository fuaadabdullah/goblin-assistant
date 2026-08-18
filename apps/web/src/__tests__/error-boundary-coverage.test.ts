import * as fs from 'node:fs';
import * as path from 'node:path';

const appDir = path.join(process.cwd(), 'app');

const collectPageFiles = (dir: string): string[] => {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const resolvedPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      // Skip api routes, __tests__, and node_modules
      if (entry.name === 'api' || entry.name === '__tests__' || entry.name === 'node_modules') {
        return [];
      }

      return collectPageFiles(resolvedPath);
    }

    // Only collect page.tsx files
    return entry.name === 'page.tsx' && !entry.name.startsWith('._') ? [resolvedPath] : [];
  });
};

describe('error boundary route coverage audit', () => {
  it('wraps every page.tsx with withRouteErrorBoundary or has a corresponding error.tsx', () => {
    const pageFiles = collectPageFiles(appDir);

    const uncoveredPages = pageFiles
      .filter((filePath) => {
        const contents = fs.readFileSync(filePath, 'utf8');

        // Check if page itself uses withRouteErrorBoundary
        const hasRouteBoundary = contents.includes('withRouteErrorBoundary');

        // Check if there's a sibling error.tsx for layout-level protection
        const dir = path.dirname(filePath);
        const siblingErrorTsx = path.join(dir, 'error.tsx');
        const hasSiblingError = fs.existsSync(siblingErrorTsx);

        return !hasRouteBoundary && !hasSiblingError;
      })
      .map((filePath) => path.relative(appDir, filePath));

    expect(uncoveredPages).toEqual([]);
  });

  it('creates global-error.tsx at the root', () => {
    const globalErrorPath = path.join(appDir, 'global-error.tsx');
    expect(fs.existsSync(globalErrorPath)).toBe(true);

    const contents = fs.readFileSync(globalErrorPath, 'utf8');
    expect(contents).toContain('reset');
  });

  it('verifies error.tsx files exist for critical feature routes', () => {
    const criticalRoutes = ['chat', 'admin', 'settings'];
    const missingErrorFiles = criticalRoutes.filter((route) => {
      const errorPath = path.join(appDir, route, 'error.tsx');
      return !fs.existsSync(errorPath);
    });

    expect(missingErrorFiles).toEqual([]);
  });
});
