#!/usr/bin/env python3
"""
LLM Exporter for Datadog

Monitors local LLM processes (llama.cpp, Ollama) and exports metrics to Datadog.
Runs as a sidecar process to collect resource usage and performance metrics.

Usage:
    python llm_exporter.py --provider llama_cpp --process-name "llama-server"
    python llm_exporter.py --provider ollama --process-name "ollama"
"""

import argparse
import time
import psutil
import subprocess
import json
import os
import signal
import sys
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

# Add the fastapi directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi'))

from metrics import metrics

@dataclass
class ProcessMetrics:
    """Metrics collected from a process."""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    num_threads: int
    num_fds: Optional[int] = None
    io_read_bytes: Optional[int] = None
    io_write_bytes: Optional[int] = None

class LLMExporter:
    """Exporter for LLM process metrics."""

    def __init__(self, provider: str, process_name: str, interval: int = 10):
        self.provider = provider
        self.process_name = process_name
        self.interval = interval
        self.process: Optional[psutil.Process] = None
        self.running = True

        # Metrics tracking
        self.request_count = 0
        self.last_io_counters = None

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"Received signal {signum}, shutting down...")
        self.running = False

    def find_process(self) -> Optional[psutil.Process]:
        """Find the LLM process by name."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if self.process_name.lower() in proc.info['name'].lower():
                    return psutil.Process(proc.info['pid'])
                # Also check command line for more specific matching
                if proc.info['cmdline']:
                    cmdline_str = ' '.join(proc.info['cmdline'])
                    if self.process_name.lower() in cmdline_str.lower():
                        return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def get_process_metrics(self, process: psutil.Process) -> ProcessMetrics:
        """Collect metrics from a process."""
        try:
            cpu_percent = process.cpu_percent(interval=1.0)

            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            memory_percent = process.memory_percent()

            num_threads = process.num_threads()

            # File descriptors (Unix only)
            num_fds = None
            try:
                num_fds = len(process.open_files())
            except (psutil.AccessDenied, AttributeError):
                pass

            # IO counters
            io_read_bytes = None
            io_write_bytes = None
            try:
                io_counters = process.io_counters()
                if io_counters:
                    io_read_bytes = io_counters.read_bytes
                    io_write_bytes = io_counters.write_bytes

                    # Calculate delta from last measurement
                    if self.last_io_counters:
                        io_read_bytes -= self.last_io_counters.read_bytes
                        io_write_bytes -= self.last_io_counters.write_bytes

                    self.last_io_counters = io_counters
            except (psutil.AccessDenied, AttributeError):
                pass

            return ProcessMetrics(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                num_threads=num_threads,
                num_fds=num_fds,
                io_read_bytes=io_read_bytes,
                io_write_bytes=io_write_bytes,
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Error collecting metrics from process: {e}")
            return None

    def get_llama_cpp_metrics(self) -> Dict[str, any]:
        """Get additional metrics specific to llama.cpp."""
        metrics_data = {}

        try:
            # Try to get metrics from llama.cpp's metrics endpoint if available
            # This would require llama.cpp to expose a metrics endpoint
            # For now, we'll use process metrics only
            pass
        except Exception as e:
            print(f"Error getting llama.cpp specific metrics: {e}")

        return metrics_data

    def get_ollama_metrics(self) -> Dict[str, any]:
        """Get additional metrics specific to Ollama."""
        metrics_data = {}

        try:
            # Try to get metrics from Ollama API
            result = subprocess.run(
                ['curl', '-s', 'http://localhost:11434/api/tags'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                metrics_data['models_loaded'] = len(data.get('models', []))
                metrics_data['ollama_api_available'] = True
            else:
                metrics_data['ollama_api_available'] = False

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error getting Ollama metrics: {e}")
            metrics_data['ollama_api_available'] = False

        return metrics_data

    def emit_metrics(self, process_metrics: ProcessMetrics, extra_metrics: Dict[str, any]):
        """Emit all metrics to Datadog."""
        tags = {"provider": self.provider}

        # Process metrics
        metrics.gauge("llm.cpu_usage", process_metrics.cpu_percent, tags=tags)
        metrics.gauge("llm.memory_mb", process_metrics.memory_mb, tags=tags)
        metrics.gauge("llm.memory_percent", process_metrics.memory_percent, tags=tags)
        metrics.gauge("llm.threads", process_metrics.num_threads, tags=tags)

        if process_metrics.num_fds is not None:
            metrics.gauge("llm.open_files", process_metrics.num_fds, tags=tags)

        if process_metrics.io_read_bytes is not None:
            metrics.gauge("llm.io_read_bytes_per_interval", process_metrics.io_read_bytes, tags=tags)

        if process_metrics.io_write_bytes is not None:
            metrics.gauge("llm.io_write_bytes_per_interval", process_metrics.io_write_bytes, tags=tags)

        # Provider-specific metrics
        for key, value in extra_metrics.items():
            if isinstance(value, (int, float)):
                metrics.gauge(f"llm.{key}", value, tags=tags)
            elif isinstance(value, bool):
                metrics.gauge(f"llm.{key}", 1 if value else 0, tags=tags)

        # Health check
        metrics.gauge("llm.process_healthy", 1, tags=tags)

    def run(self):
        """Main monitoring loop."""
        print(f"Starting LLM exporter for {self.provider} (process: {self.process_name})")
        print(f"Collection interval: {self.interval}s")

        while self.running:
            try:
                # Find or refresh process reference
                if not self.process or not self.process.is_running():
                    self.process = self.find_process()
                    if not self.process:
                        print(f"Process '{self.process_name}' not found, waiting...")
                        metrics.gauge("llm.process_healthy", 0, tags={"provider": self.provider})
                        time.sleep(self.interval)
                        continue

                # Collect metrics
                process_metrics = self.get_process_metrics(self.process)
                if not process_metrics:
                    print("Failed to collect process metrics")
                    continue

                # Get provider-specific metrics
                extra_metrics = {}
                if self.provider == "llama_cpp":
                    extra_metrics = self.get_llama_cpp_metrics()
                elif self.provider == "ollama":
                    extra_metrics = self.get_ollama_metrics()

                # Emit to Datadog
                self.emit_metrics(process_metrics, extra_metrics)

                print(f"[{datetime.now().isoformat()}] Metrics emitted - CPU: {process_metrics.cpu_percent:.1f}%, "
                      f"Memory: {process_metrics.memory_mb:.1f}MB")

            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                metrics.increment_counter("llm.exporter_errors", tags={"provider": self.provider})

            time.sleep(self.interval)

        print("LLM exporter stopped")

def main():
    parser = argparse.ArgumentParser(description="LLM Metrics Exporter for Datadog")
    parser.add_argument("--provider", required=True, choices=["llama_cpp", "ollama"],
                       help="LLM provider type")
    parser.add_argument("--process-name", required=True,
                       help="Process name to monitor (e.g., 'llama-server', 'ollama')")
    parser.add_argument("--interval", type=int, default=10,
                       help="Metrics collection interval in seconds (default: 10)")

    args = parser.parse_args()

    exporter = LLMExporter(
        provider=args.provider,
        process_name=args.process_name,
        interval=args.interval
    )

    exporter.run()

if __name__ == "__main__":
    main()
