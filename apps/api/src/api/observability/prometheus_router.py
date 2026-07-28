"""Global Prometheus metrics endpoint."""

from fastapi import APIRouter, Response

from .telemetry import get_prometheus_content_type, get_prometheus_metrics_text

router = APIRouter(tags=["observability"])


@router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=get_prometheus_metrics_text(),
        media_type=get_prometheus_content_type(),
    )
