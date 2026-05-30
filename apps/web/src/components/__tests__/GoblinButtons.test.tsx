import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// GoblinButtons re-exports; test the source of truth
describe('GoblinButtons barrel', () => {
  it('re-exports GoblinButton, GhostButton, IconButton', async () => {
    // Just verify the barrel module exists and exports are accessible
    const mod = await import('../GoblinButtons');
    expect(mod.GoblinButton).toBeDefined();
    expect(mod.GhostButton).toBeDefined();
    expect(mod.IconButton).toBeDefined();
  });
});
