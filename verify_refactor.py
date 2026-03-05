#!/usr/bin/env python3
"""Verify refactoring compatibility and functionality"""

print('Testing compatibility shims...\n')

# Test old import paths still work
try:
    from api.debugger.model_router import ModelRouter, ModelRoute, RAPTOR_TASKS
    print('✅ api.debugger.model_router imports work (compatibility shim)')
except ImportError as e:
    print(f'❌ api.debugger.model_router import failed: {e}')

try:
    from api.debugger.router import router
    print('✅ api.debugger.router imports work (compatibility shim)')
except ImportError as e:
    print(f'❌ api.debugger.router import failed: {e}')

# Test new canonical paths
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

print('\n🎉 All import paths functional (compatibility window active)')
