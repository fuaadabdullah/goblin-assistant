---
title: "VISUAL TESTING"
description: "Visual Regression Testing - Quick Reference"
---

# Visual Regression Testing - Quick Reference

## Start Storybook

```bash
# From monorepo root
npx storybook dev -p 6006 --config-dir apps/goblin-assistant/.storybook
```

Visit: http://localhost:6006

## Run Visual Tests

```bash

cd apps/goblin-assistant
export CHROMATIC_PROJECT_TOKEN=your_token
npm run chromatic
```

## Add New Story

```typescript
// MyComponent.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import MyComponent from './MyComponent';

const meta = {
  title: 'UI/MyComponent',
  component: MyComponent,
  tags: ['autodocs'],
} satisfies Meta<typeof MyComponent>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    children: 'Hello',
  },
};
```

## Test Commands

```bash

# Unit tests
npm test

# Unit tests (run once)
npm run test:run

# Storybook (from root)
npx storybook dev -p 6006 --config-dir apps/goblin-assistant/.storybook

# Visual regression (requires token)
npm run chromatic
```

## Files Created

- `.storybook/main.ts` - Storybook config
- `.storybook/preview.tsx` - Global decorators
- `src/**/*.stories.tsx` - Component stories (68 total)
- `.github/workflows/visual-regression.yml` - CI/CD workflow

## Coverage

- ✅ 69 unit tests passing
- ✅ 68 visual stories
- ✅ 150+ component states documented
- ✅ Accessibility checks enabled
- ✅ CI/CD ready

## Need Help?

See: `docs/VISUAL_REGRESSION_COMPLETE.md`
