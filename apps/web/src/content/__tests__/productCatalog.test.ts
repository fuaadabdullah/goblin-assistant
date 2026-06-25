import { describe, expect, it } from 'vitest';
import { getProductForDepartment, getProductInfo, listFeaturedProducts } from '@goblin/shared';

describe('product catalog', () => {
  it('exposes the featured product experiences', () => {
    const featured = listFeaturedProducts().map((product) => product.name);
    expect(featured).toEqual([
      'Research Goblin',
      'Coding Goblin',
      'Finance Goblin',
      'Strategy Goblin',
      'Operations Goblin',
    ]);
  });

  it('maps product ids to internal departments', () => {
    expect(getProductInfo('finance')?.departmentId).toBe('reasoning');
    expect(getProductInfo('operations')?.departmentId).toBe('tool_use');
    expect(getProductInfo('research')?.departmentId).toBe('research');
  });

  it('provides a deterministic department fallback surface', () => {
    expect(getProductForDepartment('research')?.name).toBe('Research Goblin');
    expect(getProductForDepartment('reasoning')?.departmentId).toBe('reasoning');
  });
});
