import * as fs from 'node:fs';
import * as path from 'node:path';

const srcDir = path.join(process.cwd(), 'src');
const rawConsolePattern = /console\.(log|warn|error|info|debug)\s*\(/;

const isRuntimeSourceFile = (filePath: string) => {
  if (!filePath.endsWith('.ts') && !filePath.endsWith('.tsx')) {
    return false;
  }

  return !(
    filePath.includes(`${path.sep}__tests__${path.sep}`) ||
    filePath.includes(`${path.sep}pages${path.sep}api${path.sep}`) ||
    filePath.endsWith('.stories.ts') ||
    filePath.endsWith('.stories.tsx') ||
    filePath.endsWith('.test.ts') ||
    filePath.endsWith('.test.tsx') ||
    filePath.startsWith('._')
  );
};

const collectRuntimeFiles = (directory: string): string[] =>
  fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const resolvedPath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      return collectRuntimeFiles(resolvedPath);
    }

    return isRuntimeSourceFile(resolvedPath) ? [resolvedPath] : [];
  });

describe('console audit', () => {
  it('does not use raw console logging in shipped frontend runtime files', () => {
    const offenders = collectRuntimeFiles(srcDir)
      .filter((filePath) => path.relative(srcDir, filePath) !== 'utils/dev-log.ts')
      .filter((filePath) => rawConsolePattern.test(fs.readFileSync(filePath, 'utf8')))
      .map((filePath) => path.relative(srcDir, filePath));

    expect(offenders).toEqual([]);
  });
});
