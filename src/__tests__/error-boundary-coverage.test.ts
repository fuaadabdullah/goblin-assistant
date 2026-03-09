import * as fs from 'node:fs';
import * as path from 'node:path';

const pagesDir = path.join(process.cwd(), 'src/pages');

const collectPageFiles = (dir: string): string[] =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const resolvedPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      if (entry.name === 'api') {
        return [];
      }

      return collectPageFiles(resolvedPath);
    }

    return entry.name.endsWith('.tsx') && !entry.name.startsWith('._') ? [resolvedPath] : [];
  });

describe('error boundary route coverage audit', () => {
  it('wraps every renderable page with withRouteErrorBoundary or explicitly excludes it', () => {
    const excludedPages = new Set(['_app.tsx', '_document.tsx', 'onboarding.tsx']);
    const pageFiles = collectPageFiles(pagesDir);

    const uncoveredPages = pageFiles
      .filter(filePath => {
        const relativePath = path.relative(pagesDir, filePath);

        return !excludedPages.has(relativePath);
      })
      .filter(filePath => {
        const contents = fs.readFileSync(filePath, 'utf8');
        return !contents.includes('withRouteErrorBoundary');
      })
      .map(filePath => path.relative(pagesDir, filePath));

    expect(uncoveredPages).toEqual([]);
  });
});
