"""Default alert handlers (log/email/webhook/slack).

Split out of alerting_system.py; registration happens there.
"""

import asyncio
import os

import structlog

# Imported at the bottom of alerting_system.py, after Alert/AlertSeverity are
# defined there — so this circular import is safe at runtime.
from .alerting_system import Alert, AlertSeverity

logger = structlog.get_logger()


async def log_alert_handler(alert: Alert):
    """Log alerts to structured logger"""
    logger.warning(
        "ALERT:",
        alert_id=alert.alert_id,
        severity=alert.severity.value,
        description=alert.description,
        metric_name=alert.metric_name,
        current_value=alert.current_value,
        threshold_value=alert.threshold_value,
        title=alert.title,
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
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

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
        logger.warning(
            "Webhook alert skipped: ALERT_WEBHOOK_URL not configured",
            alert_id=alert.alert_id,
        )
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


async def slack_alert_handler(alert: Alert):
    """Post alert to Slack for all severity levels."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        return

    import httpx

    _emoji = {
        AlertSeverity.CRITICAL: "🚨",
        AlertSeverity.HIGH: "⚠️",
        AlertSeverity.MEDIUM: "📊",
        AlertSeverity.LOW: "ℹ️",
    }
    emoji = _emoji.get(alert.severity, "📢")
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *[{alert.severity.value.upper()}] {alert.title}*\n"
                        f"{alert.description}\n"
                        f"`{alert.metric_name}` = {alert.current_value} "
                        f"(threshold: {alert.threshold_value})"
                    ),
                },
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("Slack alert sent", alert_id=alert.alert_id)
    except Exception as exc:
        logger.error("Failed to send Slack alert", alert_id=alert.alert_id, error=str(exc))
