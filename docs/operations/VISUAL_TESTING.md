---
title: "VISUAL TESTING"
description: "Visual Regression Testing - Quick Reference"
---

# Visual Regression Testing - Quick Reference

## Start Storybook

```bash
# From monorepo root
pnpm --filter @goblin/web storybook
```

Visit: http://localhost:6006

## Run Visual Tests

```bash

export CHROMATIC_PROJECT_TOKEN=your_token
pnpm --filter @goblin/web chromatic
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
pnpm --filter @goblin/web test:ci

# Storybook (from root)
pnpm --filter @goblin/web storybook

# Static Storybook build
pnpm --filter @goblin/web build-storybook

# Visual regression (requires token)
pnpm --filter @goblin/web chromatic
```

## Files Created

- `apps/web/.storybook/main.ts` - Storybook config
- `apps/web/.storybook/preview.tsx` - Global decorators
- `apps/web/src/**/*.stories.tsx` - Component stories
- `.github/workflows/ci.yml` - Chromatic PR job

## Coverage

- ✅ 69 unit tests passing
- ✅ 68 visual stories
- ✅ 150+ component states documented
- ✅ Accessibility checks enabled
- ✅ CI/CD ready

## Need Help?

Chromatic runs on pull requests when `CHROMATIC_PROJECT_TOKEN` is configured and the
repository variable `CHROMATIC_ENABLED` is set to `true`.
