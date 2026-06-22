from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from ..metrics_collector import SystemMetrics, metrics_collector


async def start_monitoring(system: Any) -> None:
    system.logger.info("Starting observability alerting system")
    asyncio.create_task(_monitoring_loop(system))


async def _monitoring_loop(system: Any) -> None:
    while True:
        try:
            await check_alerts(system)
            await asyncio.sleep(60)
        except Exception as e:
            system.logger.error("Error in monitoring loop:", error=str(e))
            await asyncio.sleep(60)


async def check_alerts(system: Any) -> None:
    try:
        metrics = await metrics_collector.collect_system_metrics()
        await _check_memory_alerts(system, metrics)
        await _check_retrieval_alerts(system, metrics)
        await _check_context_alerts(system, metrics)
        await _check_decision_alerts(system, metrics)
        await _check_overall_health_alerts(system, metrics)
    except Exception as e:
        system.logger.error("Error checking alerts:", error=str(e))


async def _check_memory_alerts(system: Any, metrics: SystemMetrics) -> None:
    memory_health = metrics.memory_health
    if memory_health.get("score", 0) < 30:
        await create_alert(
            system,
            title="Memory Health Critical",
            description=f"Memory system health score is {memory_health.get('score')}/100",
            metric_name="memory_health_score",
            current_value=memory_health.get("score", 0),
            threshold_value=30,
            severity=system.AlertSeverity.CRITICAL,
            metadata=memory_health,
        )
    if memory_health.get("promotion_rate", 0) < 5:
        await create_alert(
            system,
            title="Low Memory Promotion Rate",
            description=f"Memory promotion rate is {memory_health.get('promotion_rate')}%",
            metric_name="memory_promotion_rate",
            current_value=memory_health.get("promotion_rate", 0),
            threshold_value=5,
            severity=system.AlertSeverity.HIGH,
            metadata=memory_health,
        )
    contradictions = memory_health.get("contradiction_count", 0)
    total_promotions = memory_health.get("total_attempts", 0)
    if contradictions > 5 and total_promotions > 10:
        contradiction_rate = contradictions / total_promotions * 100
        if contradiction_rate > 10:
            await create_alert(
                system,
                title="High Memory Contradiction Rate",
                description=f"Memory contradiction rate is {contradiction_rate:.1f}%",
                metric_name="memory_contradiction_rate",
                current_value=contradiction_rate,
                threshold_value=10,
                severity=system.AlertSeverity.HIGH,
                metadata={"contradictions": contradictions, "total_promotions": total_promotions},
            )


async def _check_retrieval_alerts(system: Any, metrics: SystemMetrics) -> None:
    retrieval_quality = metrics.retrieval_quality
    if retrieval_quality.get("score", 0) < 40:
        await create_alert(
            system,
            title="Retrieval Quality Critical",
            description=f"Retrieval quality score is {retrieval_quality.get('score')}/100",
            metric_name="retrieval_quality_score",
            current_value=retrieval_quality.get("score", 0),
            threshold_value=40,
            severity=system.AlertSeverity.CRITICAL,
            metadata=retrieval_quality,
        )
    if retrieval_quality.get("error_rate", 0) > 10:
        await create_alert(
            system,
            title="High Retrieval Error Rate",
            description=f"Retrieval error rate is {retrieval_quality.get('error_rate')}%",
            metric_name="retrieval_error_rate",
            current_value=retrieval_quality.get("error_rate", 0),
            threshold_value=10,
            severity=system.AlertSeverity.HIGH,
            metadata=retrieval_quality,
        )
    if retrieval_quality.get("avg_relevance", 0) < 0.5:
        await create_alert(
            system,
            title="Low Retrieval Relevance",
            description=f"Average retrieval relevance is {retrieval_quality.get('avg_relevance'):.2f}",
            metric_name="retrieval_avg_relevance",
            current_value=retrieval_quality.get("avg_relevance", 0),
            threshold_value=0.5,
            severity=system.AlertSeverity.MEDIUM,
            metadata=retrieval_quality,
        )


async def _check_context_alerts(system: Any, metrics: SystemMetrics) -> None:
    context_assembly = metrics.context_assembly
    if context_assembly.get("avg_assembly_time", 0) > 1000:
        await create_alert(
            system,
            title="Slow Context Assembly",
            description=f"Context assembly time is {context_assembly.get('avg_assembly_time')}ms",
            metric_name="context_assembly_time",
            current_value=context_assembly.get("avg_assembly_time", 0),
            threshold_value=1000,
            severity=system.AlertSeverity.MEDIUM,
            metadata=context_assembly,
        )
    if context_assembly.get("redaction_rate", 0) > 25:
        await create_alert(
            system,
            title="High Redaction Rate",
            description=f"Redaction rate is {context_assembly.get('redaction_rate')}%",
            metric_name="context_redaction_rate",
            current_value=context_assembly.get("redaction_rate", 0),
            threshold_value=25,
            severity=system.AlertSeverity.MEDIUM,
            metadata=context_assembly,
        )
    if context_assembly.get("error_rate", 0) > 15:
        await create_alert(
            system,
            title="High Context Assembly Error Rate",
            description=f"Context assembly error rate is {context_assembly.get('error_rate')}%",
            metric_name="context_error_rate",
            current_value=context_assembly.get("error_rate", 0),
            threshold_value=15,
            severity=system.AlertSeverity.HIGH,
            metadata=context_assembly,
        )


async def _check_decision_alerts(system: Any, metrics: SystemMetrics) -> None:
    write_time_decisions = metrics.write_time_decisions
    if write_time_decisions.get("avg_confidence", 0) < 0.6:
        await create_alert(
            system,
            title="Low Decision Confidence",
            description=f"Average decision confidence is {write_time_decisions.get('avg_confidence'):.2f}",
            metric_name="decision_confidence",
            current_value=write_time_decisions.get("avg_confidence", 0),
            threshold_value=0.6,
            severity=system.AlertSeverity.MEDIUM,
            metadata=write_time_decisions,
        )


async def _check_overall_health_alerts(system: Any, metrics: SystemMetrics) -> None:
    overall_score = metrics.overall_health_score
    if overall_score < 50:
        await create_alert(
            system,
            title="Overall System Health Critical",
            description=f"Overall health score is {overall_score}/100",
            metric_name="overall_health_score",
            current_value=overall_score,
            threshold_value=50,
            severity=system.AlertSeverity.CRITICAL,
            metadata={"overall_score": overall_score},
        )
    elif overall_score < 70:
        await create_alert(
            system,
            title="Overall System Health Warning",
            description=f"Overall health score is {overall_score}/100",
            metric_name="overall_health_score",
            current_value=overall_score,
            threshold_value=70,
            severity=system.AlertSeverity.MEDIUM,
            metadata={"overall_score": overall_score},
        )


async def create_alert(
    system: Any,
    title: str,
    description: str,
    metric_name: str,
    current_value: float,
    threshold_value: float,
    severity: Any,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    alert_key = f"{metric_name}:{user_id}"
    if alert_key in system._suppressed_alerts or alert_key in system._alerts:
        return

    alert = system.Alert(
        alert_id=alert_key,
        timestamp=datetime.utcnow(),
        severity=severity,
        status=system.AlertStatus.ACTIVE,
        title=title,
        description=description,
        metric_name=metric_name,
        current_value=current_value,
        threshold_value=threshold_value,
        operator="threshold",
        user_id=user_id,
        metadata=metadata or {},
    )

    system._alerts[alert_key] = alert
    await notify_alert(system, alert)
    system.logger.warning(
        "Alert created:",
        alert_id=alert_key,
        severity=severity.value,
        current_value=current_value,
        threshold=threshold_value,
        title=title,
    )


async def notify_alert(system: Any, alert: Any) -> None:
    for callback in system._alert_callbacks:
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(alert)
            else:
                callback(alert)
        except Exception as e:
            system.logger.error("Error notifying alert callback:", error=str(e))


async def resolve_alert(system: Any, alert_id: str) -> None:
    if alert_id in system._alerts:
        alert = system._alerts[alert_id]
        alert.status = system.AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        system.logger.info("Alert resolved:", alert_id=alert_id, title=alert.title)
        asyncio.create_task(cleanup_resolved_alert(system, alert_id))


async def cleanup_resolved_alert(system: Any, alert_id: str, delay_minutes: int = 60) -> None:
    await asyncio.sleep(delay_minutes * 60)
    if alert_id in system._alerts:
        alert = system._alerts[alert_id]
        if alert.status == system.AlertStatus.RESOLVED:
            del system._alerts[alert_id]


def get_active_alerts(system: Any, severity: Optional[Any] = None):
    alerts = [
        alert for alert in system._alerts.values() if alert.status == system.AlertStatus.ACTIVE
    ]
    if severity:
        alerts = [alert for alert in alerts if alert.severity == severity]
    return sorted(alerts, key=lambda x: x.timestamp, reverse=True)


def get_alert_summary(system: Any) -> Dict[str, Any]:
    active_alerts = [
        alert for alert in system._alerts.values() if alert.status == system.AlertStatus.ACTIVE
    ]
    summary = {
        "total_active": len(active_alerts),
        "by_severity": {
            "critical": len(
                [a for a in active_alerts if a.severity == system.AlertSeverity.CRITICAL]
            ),
            "high": len([a for a in active_alerts if a.severity == system.AlertSeverity.HIGH]),
            "medium": len([a for a in active_alerts if a.severity == system.AlertSeverity.MEDIUM]),
            "low": len([a for a in active_alerts if a.severity == system.AlertSeverity.LOW]),
        },
        "by_metric": {},
        "recent_alerts": [],
    }
    for alert in active_alerts:
        summary["by_metric"][alert.metric_name] = summary["by_metric"].get(alert.metric_name, 0) + 1
    for alert in sorted(active_alerts, key=lambda x: x.timestamp, reverse=True)[:10]:
        summary["recent_alerts"].append(
            {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "current_value": alert.current_value,
            }
        )
    return summary
