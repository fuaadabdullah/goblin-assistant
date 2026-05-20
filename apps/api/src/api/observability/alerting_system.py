"""\nAlerting System\nImplements monitoring and alerting for system health issues\n"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio
import os
import structlog

from .metrics_collector import metrics_collector, SystemMetrics
from .decision_logger import decision_logger
from .memory_logger import memory_promotion_logger
from .retrieval_tracer import retrieval_tracer
from .context_snapshotter import context_snapshotter
from ..config.system_config import get_system_config

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert definition"""
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    metric_name: str
    current_value: float
    threshold_value: float
    operator: str
    user_id: Optional[str]
    metadata: Dict[str, Any]
    resolved_at: Optional[datetime] = None


class AlertingSystem:
    """System for monitoring and alerting on observability metrics"""
    
    def __init__(self):
        self.config = get_system_config()
        self._alerts: Dict[str, Alert] = {}
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        self._suppressed_alerts: set = set()
        
        # Default alert thresholds
        self._default_thresholds = {
            "memory_promotion_rate": {"operator": "<", "value": 5, "severity": AlertSeverity.HIGH},
            "retrieval_error_rate": {"operator": ">", "value": 10, "severity": AlertSeverity.HIGH},
            "retrieval_avg_relevance": {"operator": "<", "value": 0.5, "severity": AlertSeverity.MEDIUM},
            "context_assembly_time": {"operator": ">", "value": 1000, "severity": AlertSeverity.MEDIUM},
            "decision_confidence": {"operator": "<", "value": 0.6, "severity": AlertSeverity.MEDIUM},
            "overall_health_score": {"operator": "<", "value": 50, "severity": AlertSeverity.CRITICAL}
        }
    
    async def start_monitoring(self):
        """Start the alerting monitoring loop"""
        logger.info("Starting observability alerting system")
        
        # Start monitoring tasks
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await self._check_alerts()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_alerts(self):
        """Check all metrics against alert thresholds"""
        try:
            # Get current system metrics
            metrics = await metrics_collector.collect_system_metrics()
            
            # Check memory health alerts
            await self._check_memory_alerts(metrics)
            
            # Check retrieval quality alerts
            await self._check_retrieval_alerts(metrics)
            
            # Check context assembly alerts
            await self._check_context_alerts(metrics)
            
            # Check decision system alerts
            await self._check_decision_alerts(metrics)
            
            # Check overall health alerts
            await self._check_overall_health_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _check_memory_alerts(self, metrics: SystemMetrics):
        """Check memory system alerts"""
        memory_health = metrics.memory_health
        
        if memory_health.get("score", 0) < 30:
            await self._create_alert(
                title="Memory Health Critical",
                description=f"Memory system health score is {memory_health.get('score')}/100",
                metric_name="memory_health_score",
                current_value=memory_health.get("score", 0),
                threshold_value=30,
                severity=AlertSeverity.CRITICAL,
                metadata=memory_health
            )
        
        if memory_health.get("promotion_rate", 0) < 5:
            await self._create_alert(
                title="Low Memory Promotion Rate",
                description=f"Memory promotion rate is {memory_health.get('promotion_rate')}%",
                metric_name="memory_promotion_rate",
                current_value=memory_health.get("promotion_rate", 0),
                threshold_value=5,
                severity=AlertSeverity.HIGH,
                metadata=memory_health
            )
        
        # Check for contradiction spikes
        contradictions = memory_health.get("contradiction_count", 0)
        total_promotions = memory_health.get("total_attempts", 0)
        if contradictions > 5 and total_promotions > 10:
            contradiction_rate = contradictions / total_promotions * 100
            if contradiction_rate > 10:
                await self._create_alert(
                    title="High Memory Contradiction Rate",
                    description=f"Memory contradiction rate is {contradiction_rate:.1f}%",
                    metric_name="memory_contradiction_rate",
                    current_value=contradiction_rate,
                    threshold_value=10,
                    severity=AlertSeverity.HIGH,
                    metadata={"contradictions": contradictions, "total_promotions": total_promotions}
                )
    
    async def _check_retrieval_alerts(self, metrics: SystemMetrics):
        """Check retrieval system alerts"""
        retrieval_quality = metrics.retrieval_quality
        
        if retrieval_quality.get("score", 0) < 40:
            await self._create_alert(
                title="Retrieval Quality Critical",
                description=f"Retrieval quality score is {retrieval_quality.get('score')}/100",
                metric_name="retrieval_quality_score",
                current_value=retrieval_quality.get("score", 0),
                threshold_value=40,
                severity=AlertSeverity.CRITICAL,
                metadata=retrieval_quality
            )
        
        if retrieval_quality.get("error_rate", 0) > 10:
            await self._create_alert(
                title="High Retrieval Error Rate",
                description=f"Retrieval error rate is {retrieval_quality.get('error_rate')}%",
                metric_name="retrieval_error_rate",
                current_value=retrieval_quality.get("error_rate", 0),
                threshold_value=10,
                severity=AlertSeverity.HIGH,
                metadata=retrieval_quality
            )
        
        if retrieval_quality.get("avg_relevance", 0) < 0.5:
            await self._create_alert(
                title="Low Retrieval Relevance",
                description=f"Average retrieval relevance is {retrieval_quality.get('avg_relevance'):.2f}",
                metric_name="retrieval_avg_relevance",
                current_value=retrieval_quality.get("avg_relevance", 0),
                threshold_value=0.5,
                severity=AlertSeverity.MEDIUM,
                metadata=retrieval_quality
            )
    
    async def _check_context_alerts(self, metrics: SystemMetrics):
        """Check context assembly alerts"""
        context_assembly = metrics.context_assembly
        
        if context_assembly.get("avg_assembly_time", 0) > 1000:
            await self._create_alert(
                title="Slow Context Assembly",
                description=f"Context assembly time is {context_assembly.get('avg_assembly_time')}ms",
                metric_name="context_assembly_time",
                current_value=context_assembly.get("avg_assembly_time", 0),
                threshold_value=1000,
                severity=AlertSeverity.MEDIUM,
                metadata=context_assembly
            )
        
        if context_assembly.get("redaction_rate", 0) > 25:
            await self._create_alert(
                title="High Redaction Rate",
                description=f"Redaction rate is {context_assembly.get('redaction_rate')}%",
                metric_name="context_redaction_rate",
                current_value=context_assembly.get("redaction_rate", 0),
                threshold_value=25,
                severity=AlertSeverity.MEDIUM,
                metadata=context_assembly
            )
        
        if context_assembly.get("error_rate", 0) > 15:
            await self._create_alert(
                title="High Context Assembly Error Rate",
                description=f"Context assembly error rate is {context_assembly.get('error_rate')}%",
                metric_name="context_error_rate",
                current_value=context_assembly.get("error_rate", 0),
                threshold_value=15,
                severity=AlertSeverity.HIGH,
                metadata=context_assembly
            )
    
    async def _check_decision_alerts(self, metrics: SystemMetrics):
        """Check decision system alerts"""
        write_time_decisions = metrics.write_time_decisions
        
        if write_time_decisions.get("avg_confidence", 0) < 0.6:
            await self._create_alert(
                title="Low Decision Confidence",
                description=f"Average decision confidence is {write_time_decisions.get('avg_confidence'):.2f}",
                metric_name="decision_confidence",
                current_value=write_time_decisions.get("avg_confidence", 0),
                threshold_value=0.6,
                severity=AlertSeverity.MEDIUM,
                metadata=write_time_decisions
            )
    
    async def _check_overall_health_alerts(self, metrics: SystemMetrics):
        """Check overall system health alerts"""
        overall_score = metrics.overall_health_score
        
        if overall_score < 50:
            await self._create_alert(
                title="Overall System Health Critical",
                description=f"Overall health score is {overall_score}/100",
                metric_name="overall_health_score",
                current_value=overall_score,
                threshold_value=50,
                severity=AlertSeverity.CRITICAL,
                metadata={"overall_score": overall_score}
            )
        elif overall_score < 70:
            await self._create_alert(
                title="Overall System Health Warning",
                description=f"Overall health score is {overall_score}/100",
                metric_name="overall_health_score",
                current_value=overall_score,
                threshold_value=70,
                severity=AlertSeverity.MEDIUM,
                metadata={"overall_score": overall_score}
            )
    
    async def _create_alert(
        self,
        title: str,
        description: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        severity: AlertSeverity,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create a new alert if it doesn't already exist"""
        
        alert_key = f"{metric_name}:{user_id}"
        
        # Skip if alert is already suppressed or exists
        if alert_key in self._suppressed_alerts or alert_key in self._alerts:
            return
        
        # Create alert
        alert = Alert(
            alert_id=alert_key,
            timestamp=datetime.utcnow(),
            severity=severity,
            status=AlertStatus.ACTIVE,
            title=title,
            description=description,
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            operator="threshold",
            user_id=user_id,
            metadata=metadata or {}
        )
        
        # Store alert
        self._alerts[alert_key] = alert
        
        # Notify callbacks
        await self._notify_alert(alert)
        
        logger.warning(
            f"Alert created: {title}",
            alert_id=alert_key,
            severity=severity.value,
            current_value=current_value,
            threshold=threshold_value
        )
    
    async def _notify_alert(self, alert: Alert):
        """Notify all registered callbacks about the alert"""
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error notifying alert callback: {e}")
    
    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """Register a callback to be notified when alerts are created"""
        self._alert_callbacks.append(callback)
    
    async def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            
            logger.info(f"Alert resolved: {alert.title}", alert_id=alert_id)
            
            # Remove from active alerts after a delay
            asyncio.create_task(self._cleanup_resolved_alert(alert_id))
    
    async def _cleanup_resolved_alert(self, alert_id: str, delay_minutes: int = 60):
        """Clean up resolved alerts after a delay"""
        await asyncio.sleep(delay_minutes * 60)
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            if alert.status == AlertStatus.RESOLVED:
                del self._alerts[alert_id]
    
    def suppress_alert(self, alert_id: str):
        """Suppress an alert to prevent it from being recreated"""
        self._suppressed_alerts.add(alert_id)
        logger.info(f"Alert suppressed: {alert_id}")
    
    def unsuppress_alert(self, alert_id: str):
        """Unsuppress an alert"""
        self._suppressed_alerts.discard(alert_id)
        logger.info(f"Alert unsuppressed: {alert_id}")
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get all active alerts, optionally filtered by severity"""
        alerts = [alert for alert in self._alerts.values() if alert.status == AlertStatus.ACTIVE]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alert status"""
        active_alerts = [alert for alert in self._alerts.values() if alert.status == AlertStatus.ACTIVE]
        
        summary = {
            "total_active": len(active_alerts),
            "by_severity": {
                "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "high": len([a for a in active_alerts if a.severity == AlertSeverity.HIGH]),
                "medium": len([a for a in active_alerts if a.severity == AlertSeverity.MEDIUM]),
                "low": len([a for a in active_alerts if a.severity == AlertSeverity.LOW])
            },
            "by_metric": {},
            "recent_alerts": []
        }
        
        # Group by metric
        for alert in active_alerts:
            if alert.metric_name not in summary["by_metric"]:
                summary["by_metric"][alert.metric_name] = 0
            summary["by_metric"][alert.metric_name] += 1
        
        # Recent alerts (last 10)
        recent_alerts = sorted(active_alerts, key=lambda x: x.timestamp, reverse=True)[:10]
        for alert in recent_alerts:
            summary["recent_alerts"].append({
                "alert_id": alert.alert_id,
                "title": alert.title,
                "severity": alert.severity.value,
                "timestamp": alert.timestamp.isoformat(),
                "current_value": alert.current_value
            })
        
        return summary


# Global alerting system instance
alerting_system = AlertingSystem()


# Example alert handlers
async def log_alert_handler(alert: Alert):
    """Log alerts to structured logger"""
    logger.warning(
        f"ALERT: {alert.title}",
        alert_id=alert.alert_id,
        severity=alert.severity.value,
        description=alert.description,
        metric_name=alert.metric_name,
        current_value=alert.current_value,
        threshold_value=alert.threshold_value
    )


async def email_alert_handler(alert: Alert):
    """Send email alerts via SMTP for CRITICAL and HIGH severity alerts."""
    if alert.severity not in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
        return

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    email_from = os.environ.get("ALERT_EMAIL_FROM", smtp_user)
    email_to = os.environ.get("ALERT_EMAIL_TO")

    if not all([smtp_host, smtp_user, smtp_pass, email_to]):
        logger.warning("Email alert skipped: SMTP env vars not configured", alert_id=alert.alert_id)
        return

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    def _send():
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
        msg["From"] = email_from
        msg["To"] = email_to
        body = (
            f"Alert: {alert.title}\n"
            f"Severity: {alert.severity.value}\n"
            f"Description: {alert.description}\n"
            f"Metric: {alert.metric_name} = {alert.current_value} (threshold: {alert.threshold_value})\n"
            f"Time: {alert.timestamp.isoformat()}\n"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(email_from, email_to, msg.as_string())

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send)
        logger.info("Email alert sent", alert_id=alert.alert_id, to=email_to)
    except Exception as exc:
        logger.error("Failed to send email alert", alert_id=alert.alert_id, error=str(exc))


async def webhook_alert_handler(alert: Alert):
    """Send webhook alerts via HTTP POST for CRITICAL severity alerts."""
    if alert.severity != AlertSeverity.CRITICAL:
        return

    webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("Webhook alert skipped: ALERT_WEBHOOK_URL not configured", alert_id=alert.alert_id)
        return

    import httpx

    payload = {
        "alert_id": alert.alert_id,
        "title": alert.title,
        "severity": alert.severity.value,
        "description": alert.description,
        "metric_name": alert.metric_name,
        "current_value": alert.current_value,
        "threshold_value": alert.threshold_value,
        "timestamp": alert.timestamp.isoformat(),
        "metadata": alert.metadata,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        logger.info("Webhook alert sent", alert_id=alert.alert_id, status=response.status_code)
    except Exception as exc:
        logger.error("Failed to send webhook alert", alert_id=alert.alert_id, error=str(exc))


# Register default alert handlers
alerting_system.register_alert_callback(log_alert_handler)
alerting_system.register_alert_callback(email_alert_handler)
alerting_system.register_alert_callback(webhook_alert_handler)