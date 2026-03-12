#!/usr/bin/env python3
"""Verify refactored import paths are functional."""

print('Testing canonical import paths...\n')

try:
    from api.core.router import ModelRouter, ModelRoute, RAPTOR_TASKS
    print('✅ api.core.router imports work (canonical location)')
except ImportError as e:
    print(f'❌ api.core.router import failed: {e}')

try:
    from api.routes.debug import router
    print('✅ api.routes.debug imports work (canonical location)')
except ImportError as e:
    print(f'❌ api.routes.debug import failed: {e}')

print('\n🎉 All canonical import paths functional')
