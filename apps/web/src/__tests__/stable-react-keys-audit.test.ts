import * as fs from 'node:fs';
import * as path from 'node:path';

const srcDir = path.join(process.cwd(), 'src');
const rawIndexKeyPattern = /key=\{(?:idx|index|i)\}/;

const isRuntimeTsxFile = (filePath: string) => {
  if (!filePath.endsWith('.tsx')) {
    return false;
  }

  return !(
    filePath.includes(`${path.sep}__tests__${path.sep}`) ||
    filePath.endsWith('.stories.tsx') ||
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

    return isRuntimeTsxFile(resolvedPath) ? [resolvedPath] : [];
  });

describe('stable react key audit', () => {
  it('does not use raw index keys in runtime TSX files', () => {
    const offenders = collectRuntimeFiles(srcDir)
      .filter((filePath) => rawIndexKeyPattern.test(fs.readFileSync(filePath, 'utf8')))
      .map((filePath) => path.relative(srcDir, filePath));

    expect(offenders).toEqual([]);
  });
});
