import * as fs from 'node:fs';
import * as path from 'node:path';

const rawPrecisionPattern = /\.toFixed\((2|4|6)\)/;

const files = [
  'src/hooks/useCostClipboard.ts',
  'src/screens/GoblinDemo.tsx',
  'src/features/chat/components/ChatComposer.tsx',
  'src/features/chat/components/ChatMessageList.tsx',
  'src/components/cost/CostDisplay.tsx',
  'src/components/cost/CostSummary.tsx',
  'src/components/cost/CostPanel.tsx',
  'src/components/cost/CostBreakdownChart.tsx',
  'src/components/dashboard/CostOverviewBanner.tsx',
];

describe('cost format audit', () => {
  it('uses formatCost instead of raw toFixed precision in cost display files', () => {
    const offenders = files.filter((filePath) => {
      const source = fs.readFileSync(path.join(process.cwd(), filePath), 'utf8');
      return rawPrecisionPattern.test(source);
    });

    expect(offenders).toEqual([]);
  });
});
