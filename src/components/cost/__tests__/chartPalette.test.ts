import * as fs from 'node:fs';
import * as path from 'node:path';
import { CHART_COLOR_PALETTE, getChartPaletteColor } from '../chartPalette';

const legacyHexPalette = ['#7c3aed', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#a78bfa'];

describe('chart palette regression', () => {
  it('exports a shared theme-token palette', () => {
    expect(CHART_COLOR_PALETTE.length).toBeGreaterThan(0);
    CHART_COLOR_PALETTE.forEach((color) => {
      expect(color.startsWith('var(--')).toBe(true);
    });
    expect(getChartPaletteColor(CHART_COLOR_PALETTE.length)).toBe(CHART_COLOR_PALETTE[0]);
  });

  it('keeps Dashboard and ProviderUsageChart on the shared palette', () => {
    const dashboardSource = fs.readFileSync(
      path.join(process.cwd(), 'src/screens/Dashboard.tsx'),
      'utf8'
    );
    const providerUsageSource = fs.readFileSync(
      path.join(process.cwd(), 'src/components/cost/ProviderUsageChart.tsx'),
      'utf8'
    );

    expect(dashboardSource).toContain('getChartPaletteColor');
    expect(providerUsageSource).toContain('getChartPaletteColor');
    expect(dashboardSource).not.toMatch(/const colors = \[/);
    expect(providerUsageSource).not.toMatch(/const colors = \[/);
    expect(dashboardSource).not.toContain('Math.round((cost as number) * 10)');
    expect(providerUsageSource).not.toContain('Approximated');

    legacyHexPalette.forEach((color) => {
      expect(dashboardSource).not.toContain(color);
      expect(providerUsageSource).not.toContain(color);
    });
  });
});
