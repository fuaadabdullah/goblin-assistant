try {
  require('@testing-library/jest-dom');
} catch {
  // Keep tests runnable in constrained environments where this optional
  // matcher package may be missing from node_modules.
}

// Set React ACT environment
global.IS_REACT_ACT_ENVIRONMENT = true;
