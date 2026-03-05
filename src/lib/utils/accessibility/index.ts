
'use client';

// Re-export all accessibility utilities
export { aria } from './aria';
export { focusManager } from './focus';
export { screenReader } from './screen-reader';
export { keyboard } from './keyboard';
export { colorContrast } from './color-contrast';
export { semantic } from './semantic';
export { motion } from './motion';
export { textScaling } from './text-scaling';
export { highContrast } from './high-contrast';
export { a11yTest } from './testing';

// Export combined object for backward compatibility
import { aria } from './aria';
import { focusManager } from './focus';
import { screenReader } from './screen-reader';
import { keyboard } from './keyboard';
import { colorContrast } from './color-contrast';
import { semantic } from './semantic';
import { motion } from './motion';
import { textScaling } from './text-scaling';
import { highContrast } from './high-contrast';
import { a11yTest } from './testing';

export const accessibility = {
  aria,
  focusManager,
  screenReader,
  keyboard,
  colorContrast,
  semantic,
  motion,
  textScaling,
  highContrast,
  a11yTest,
};
