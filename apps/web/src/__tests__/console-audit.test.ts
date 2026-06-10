import * as fs from 'node:fs';
import * as path from 'node:path';

const srcDir = path.join(process.cwd(), 'src');
const appDir = path.join(process.cwd(), 'app');
// Only console.warn and console.error are permitted in runtime code.
// console.warn calls are stripped in production builds via next.config.ts compiler.removeConsole.
// console.error is preserved for production error reporting.
const rawConsolePattern = /console\.(log|info|debug|trace|dir)\s*\(/;

const isRuntimeSourceFile = (filePath: string) => {
  if (!filePath.endsWith('.ts') && !filePath.endsWith('.tsx')) {
    return false;
  }

  return !(
    filePath.includes(`${path.sep}__tests__${path.sep}`) ||
    filePath.includes(`${path.sep}pages${path.sep}api${path.sep}`) ||
    filePath.includes(`${path.sep}e2e${path.sep}`) ||
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
  it('does not use banned console methods (log, info, debug, trace, dir) in shipped runtime files', () => {
    const srcOffenders = collectRuntimeFiles(srcDir)
      .filter((filePath) => path.relative(srcDir, filePath) !== 'utils/dev-log.ts')
      .filter((filePath) => rawConsolePattern.test(fs.readFileSync(filePath, 'utf8')))
      .map((filePath) => path.relative(srcDir, filePath));

    const srcMessages = srcOffenders.map((f) => `  src/${f}`);

    const appOffenders: string[] = [];
    if (fs.existsSync(appDir)) {
      const files = collectRuntimeFiles(appDir)
        .filter((filePath) => rawConsolePattern.test(fs.readFileSync(filePath, 'utf8')))
        .map((filePath) => path.relative(appDir, filePath));
      appOffenders.push(...files);
    }

    const appMessages = appOffenders.map((f) => `  app/${f}`);

    const allOffenders = [...srcMessages, ...appMessages];

    expect(allOffenders).toEqual([]);
  });
});
