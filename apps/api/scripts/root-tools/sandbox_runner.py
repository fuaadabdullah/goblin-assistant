#!/usr/bin/env python3
"""
Sandbox runner script
Executes user code in a secure, isolated environment inside Docker containers
"""

import os
import sys
import subprocess
import signal
import time
import resource
from typing import List, Optional

def setup_resource_limits():
    """Set resource limits to prevent abuse"""
    # Set CPU time limit (seconds)
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))

    # Set memory limit (bytes) - 256MB
    memory_limit = 256 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))

    # Set file size limit (bytes) - 10MB
    file_limit = 10 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))

    # Limit number of processes
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))

    # Limit number of open files
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))

def get_command_for_language(language: str, runtime_args: List[str]) -> List[str]:
    """Get the appropriate command for executing code in the given language"""

    base_commands = {
        "python": ["python", "/work/main.py"],
        "javascript": ["node", "/work/main.js"],
        "bash": ["bash", "/work/script.sh"]
    }

    if language not in base_commands:
        print(f"Error: Unsupported language '{language}'", file=sys.stderr)
        sys.exit(1)

    command = base_commands[language]
    if runtime_args:
        command.extend(runtime_args)

    return command

def execute_with_timeout(cmd: List[str], timeout: int) -> int:
    """Execute command with timeout and return exit code"""

    def timeout_handler(signum, frame):
        print(f"Execution timed out after {timeout} seconds", file=sys.stderr)
        sys.exit(124)  # Standard timeout exit code

    # Set up signal handler for timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        # Execute the command
        result = subprocess.run(
            cmd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            timeout=timeout + 1,  # Add 1 second buffer
            cwd="/work"
        )
        return result.returncode

    except subprocess.TimeoutExpired:
        print(f"Execution timed out after {timeout} seconds", file=sys.stderr)
        return 124

    except FileNotFoundError:
        print(f"Error: Command not found: {cmd[0]}", file=sys.stderr)
        return 127

    except Exception as e:
        print(f"Error executing command: {str(e)}", file=sys.stderr)
        return 1

    finally:
        # Cancel the alarm
        signal.alarm(0)

def validate_environment():
    """Validate that the execution environment is secure"""

    # Check that we're running as non-root user
    if os.geteuid() == 0:
        print("Error: Running as root user - this should not happen!", file=sys.stderr)
        sys.exit(1)

    # Check that we're in the expected working directory
    if not os.path.exists("/work"):
        print("Error: /work directory not found", file=sys.stderr)
        sys.exit(1)

    # Check that the main file exists
    main_files = ["/work/main.py", "/work/main.js", "/work/script.sh"]
    if not any(os.path.exists(f) for f in main_files):
        print("Error: No executable file found in /work", file=sys.stderr)
        sys.exit(1)

    # Verify we're in a container (check for .dockerenv or container-specific files)
    container_indicators = [
        "/.dockerenv",
        "/proc/1/cgroup"  # Should contain 'docker' or 'containerd'
    ]

    is_container = any(os.path.exists(indicator) for indicator in container_indicators)
    if not is_container:
        print("Warning: Not running in a container environment", file=sys.stderr)

def main():
    """Main execution function"""

    # Validate environment security
    validate_environment()

    # Set up resource limits
    setup_resource_limits()

    # Get execution parameters from environment
    language = os.getenv("SANDBOX_LANGUAGE", "").lower()
    timeout = int(os.getenv("SANDBOX_TIMEOUT", "10"))
    runtime_args = os.getenv("SANDBOX_RUNTIME_ARGS", "")

    if not language:
        print("Error: SANDBOX_LANGUAGE environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Parse runtime arguments
    args_list = runtime_args.split() if runtime_args else []

    # Get the command to execute
    command = get_command_for_language(language, args_list)

    print(f"🏃 Executing {language} code with timeout {timeout}s...")
    print(f"Command: {' '.join(command)}")
    print("-" * 50)

    # Execute the command
    exit_code = execute_with_timeout(command, timeout)

    print("-" * 50)
    print(f"Execution completed with exit code: {exit_code}")

    # Exit with the same code as the executed command
    sys.exit(exit_code)

if __name__ == "__main__":
    main()