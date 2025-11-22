# debug_bootstrap.py - Direct debugpy setup for FastAPI
import os

if os.getenv("DEBUGPY"):
    import debugpy

    debugpy.listen(("127.0.0.1", 5678))
    print("Waiting for debugger to attach...")
    debugpy.wait_for_client()
    print("Debugger attached.")
