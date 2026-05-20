"""
Background service for cleaning up expired sandbox artifacts
Runs periodically to enforce TTL and prevent storage bloat
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional
import structlog

from .artifact_service import artifact_service
from .sandbox_metrics import record_cleanup_run

logger = structlog.get_logger()


class ArtifactCleanupService:
    """Service for cleaning up expired artifacts"""

    def __init__(self):
        self.cleanup_interval_hours = int(os.getenv("ARTIFACT_CLEANUP_INTERVAL_HOURS", "24"))
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the cleanup service"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Artifact cleanup service started", interval_hours=self.cleanup_interval_hours)

    async def stop(self):
        """Stop the cleanup service"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Artifact cleanup service stopped")

    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while self._running:
            try:
                # Run cleanup
                deleted_count = artifact_service.delete_expired_artifacts()

                # Record cleanup metrics
                record_cleanup_run(True, deleted_count)

                if deleted_count > 0:
                    logger.info("Artifact cleanup completed", artifacts_removed=deleted_count)
                else:
                    logger.info("Artifact cleanup completed", artifacts_removed=0, detail="no expired artifacts found")

            except Exception as e:
                # Record failed cleanup
                record_cleanup_run(False, 0)
                logger.error("Error during artifact cleanup", error=str(e))

            # Wait for next cleanup cycle
            await asyncio.sleep(self.cleanup_interval_hours * 60 * 60)

    async def run_once(self) -> int:
        """Run cleanup once (for manual triggering)"""
        try:
            deleted_count = artifact_service.delete_expired_artifacts()

            # Record cleanup metrics
            record_cleanup_run(True, deleted_count)

            logger.info("Manual artifact cleanup completed", artifacts_removed=deleted_count)
            return deleted_count
        except Exception as e:
            # Record failed cleanup
            record_cleanup_run(False, 0)
            logger.error("Error during manual artifact cleanup", error=str(e))
            return 0


# Global instance
artifact_cleanup_service = ArtifactCleanupService()


# For running as a standalone script
if __name__ == "__main__":
    import asyncio

    async def main():
        logger.info("Running manual artifact cleanup")
        deleted = await artifact_cleanup_service.run_once()
        logger.info("Cleanup complete", artifacts_removed=deleted)

    asyncio.run(main())