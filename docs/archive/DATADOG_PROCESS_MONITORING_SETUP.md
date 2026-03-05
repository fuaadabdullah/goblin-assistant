# Datadog Process Monitoring Setup Complete

## 📋 Summary

Successfully configured comprehensive Datadog process monitoring for the Goblin Assistant backend with I/O stats collection, sensitive data scrubbing, and optimized performance.

## 🎯 What Was Implemented

### 1. Configuration Files

Created in `goblin-infra/projects/goblin-assistant/infra/observability/datadog/`:

| File                         | Purpose                                                                 |
| ---------------------------- | ----------------------------------------------------------------------- |
| `datadog-agent.yaml`         | Main agent configuration with process collection, tagging, integrations |
| `system-probe.yaml`          | System probe config for I/O stats and network monitoring                |
| `docker-compose-datadog.yml` | Docker Compose deployment with all required capabilities                |
| `k8s-datadog-agent.yaml`     | Kubernetes DaemonSet with RBAC and service account                      |
| `setup-datadog-processes.sh` | Automated setup script for Linux hosts                                  |
| `verify-setup.sh`            | Verification script to check installation                               |
| `setup-env.sh`               | Environment-specific configuration (prod/staging/dev)                   |
| `README.md`                  | Complete documentation (700+ lines)                                     |
| `QUICKSTART.md`              | Quick reference guide                                                   |

### 2. Features Enabled

- ✅ **Process Discovery**: Automatic detection of Python/Gunicorn/Uvicorn processes
- ✅ **Process Metrics**: CPU, memory, I/O, network, file descriptors
- ✅ **I/O Statistics**: Read/write bytes and operations via system-probe
- ✅ **Optimized Collection**: Runs in core agent (v7.53.0+) for reduced footprint
- ✅ **Sensitive Data Scrubbing**: Hides API keys, tokens, passwords from process args
- ✅ **Container Awareness**: Docker and Kubernetes process tagging
- ✅ **APM Integration**: Link processes with distributed traces
- ✅ **Custom Metrics**: DogStatsD integration for app-specific metrics

### 3. Security Measures

**Sensitive Word Scrubbing** - Configured to hide:

- `api_key`, `apikey`, `*_key`
- `token`, `auth_token`, `access_token`, `bearer`, `jwt`
- `password`, `passwd`
- `secret`, `*_secret`
- `credential`
- Provider-specific keys (`openai_api_key`, `anthropic_api_key`, `groq_api_key`)

**Permissions**:

- Agent runs as dedicated `dd-agent` user
- System-probe requires elevated privileges (CAP_SYS_ADMIN, CAP_SYS_PTRACE)
- Proper file permissions (0640) on config files

### 4. Deployment Options

#### Option A: Linux Host (Recommended for VMs)

```bash
# 1. Install agent
DD_API_KEY=<YOUR_KEY> DD_SITE="datadoghq.com" \
bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"

# 2. Setup process monitoring
cd goblin-infra/projects/goblin-assistant/infra/observability/datadog
sudo ./setup-datadog-processes.sh

# 3. Verify
./verify-setup.sh
```

#### Option B: Docker Compose (For Containers)

```bash

# 1. Set environment
cd goblin-infra/projects/goblin-assistant/infra/observability/datadog
./setup-env.sh production

# 2. Start agent
docker-compose -f docker-compose-datadog.yml --env-file .env.datadog up -d

# 3. Check logs
docker logs datadog-agent
```

#### Option C: Kubernetes (For K8s Clusters)

```bash
# 1. Create secret
kubectl create secret generic datadog-secret \
  --from-literal=api-key=<YOUR_KEY> \
  -n goblin-assistant

# 2. Deploy DaemonSet
kubectl apply -f k8s-datadog-agent.yaml

# 3. Verify
kubectl get pods -n goblin-assistant -l app=datadog-agent
```

## 📊 Monitoring Capabilities

### Available Metrics

```python

# CPU usage by process
system.processes.cpu.pct{service:goblin-assistant}

# Memory usage (RSS)
system.processes.mem.rss{service:goblin-assistant}

# I/O operations
system.processes.io.read_bytes{service:goblin-assistant}
system.processes.io.write_bytes{service:goblin-assistant}

# Network traffic
system.processes.net.bytes_sent{service:goblin-assistant}
system.processes.net.bytes_rcvd{service:goblin-assistant}

# Open files
system.processes.open_file_descriptors{service:goblin-assistant}

# Process count
system.processes.number{service:goblin-assistant}
```

### Datadog UI Access

- **Process Explorer**: <https://app.datadoghq.com/process?tags=service:goblin-assistant>
- **Infrastructure Map**: <https://app.datadoghq.com/infrastructure/map>
- **Live Containers**: <https://app.datadoghq.com/containers>
- **Dashboards**: <https://app.datadoghq.com/dashboard/lists>
- **Monitors**: <https://app.datadoghq.com/monitors>

## 🚨 Recommended Monitors

Created pre-configured monitor templates for:

1. **High CPU Usage**: Alert when process CPU > 80% for 5 minutes
2. **Memory Leak Detection**: Alert when memory > 2GB and increasing
3. **File Descriptor Exhaustion**: Alert when open files > 1000
4. **Process Crash Detection**: Alert when process restarts (uptime decreased)

## 🔍 Query Examples

### Datadog Dashboard Queries

```python
# Average CPU by process type
avg:system.processes.cpu.pct{service:goblin-assistant} by {process}

# Memory trend over time
sum:system.processes.mem.rss{service:goblin-assistant}

# I/O rate (bytes/second)
sum:system.processes.io.write_bytes{service:goblin-assistant}.as_rate()

# Top processes by CPU
top(avg:system.processes.cpu.pct{service:goblin-assistant} by {process}, 10, 'mean', 'desc')
```

### Filter by Tags

```python

# Production only
service:goblin-assistant AND env:production

# Specific component
service:goblin-assistant AND component:backend

# By container
service:goblin-assistant AND container_name:goblin-backend
```

## 🎓 Key Concepts

### Optimized Process Collection

For Datadog Agent v7.53.0+, process collection runs in the core agent instead of a separate process-agent, reducing:

- CPU usage by 30-50%
- Memory usage by 100-200 MB
- Container overhead

### System Probe

Requires elevated privileges but provides:

- Detailed I/O statistics (read/write bytes/ops)
- Open file descriptor tracking
- Network connection monitoring
- Real-time performance data

### Sensitive Data Scrubbing

Protects credentials in two ways:

1. **Pattern Matching**: Hides values for known sensitive arguments
2. **Custom Words**: Add your own patterns (wildcards supported)
3. **Strip All**: Option to hide all arguments (max security)

## 📈 Performance Impact

**Agent Resource Usage:**

- CPU: 0.5-2% (optimized mode)
- Memory: 200-500 MB
- Network: ~50 KB/s per 1000 processes
- Disk: Minimal (logs only)

**Collection Overhead:**

- Process data collected every 10s (configurable)
- System-probe adds <1% CPU overhead
- Container monitoring adds <0.5% overhead

## 🔧 Configuration Tuning

### Reduce Data Volume

```yaml
# Filter unwanted processes
process_config:
  blacklist_patterns:
    - ^/sbin/
    - ^/usr/sbin/
    - .*kernel.*
```

### Adjust Collection Frequency

```yaml
# Collect less frequently
process_config:
  intervals:
    container: 30 # Default: 10s
    process: 30 # Default: 10s
```

### Disable Optional Features

```yaml
# If not using Network Performance Monitoring
network_config:
  enabled: false

# If not using Universal Service Monitoring
service_monitoring_config:
  enabled: false
```

## 🐛 Troubleshooting

### Common Issues & Solutions

**Issue: No processes visible in UI**

```bash

# Check if enabled
grep -A5 "process_config:" /etc/datadog-agent/datadog.yaml
sudo systemctl restart datadog-agent
```

**Issue: No I/O statistics**

```bash
# Verify system-probe is running
ps aux | grep system-probe
sudo systemctl restart datadog-agent
```

**Issue: Sensitive data visible**

```bash

# Enable scrubbing
sudo vi /etc/datadog-agent/datadog.yaml

# Set: scrub_args: true

# Add custom_sensitive_words
sudo systemctl restart datadog-agent
```

**Issue: High agent CPU**

```bash
# Enable optimized mode (v7.53.0+)
echo "process_config:
  run_in_core_agent: true" | sudo tee -a /etc/datadog-agent/datadog.yaml
sudo systemctl restart datadog-agent
```

## 📚 Documentation Structure

```
apps/goblin-assistant/
├── infra/observability/datadog/
│   ├── README.md                      # Complete guide (700+ lines)
│   ├── QUICKSTART.md                  # Quick reference
│   ├── datadog-agent.yaml             # Main agent config
│   ├── system-probe.yaml              # System probe config
│   ├── docker-compose-datadog.yml     # Docker deployment
│   ├── k8s-datadog-agent.yaml         # Kubernetes deployment
│   ├── setup-datadog-processes.sh     # Automated setup
│   ├── setup-env.sh                   # Environment config
│   └── verify-setup.sh                # Verification script
└── datadog/
    └── DATADOG_SLOS.md                # SLO definitions
```

## 🚀 Next Steps

### Immediate Actions

1. **Install Agent**: Choose deployment method (Linux/Docker/K8s)
2. **Verify Setup**: Run `verify-setup.sh` to confirm installation
3. **View Processes**: Check Datadog UI for process data
4. **Create Monitors**: Set up alerts for critical thresholds

### Short-term (Week 1)

1. **Baseline Metrics**: Collect 1 week of data to establish normal ranges
2. **Create Dashboards**: Build custom dashboards for your team
3. **Set Thresholds**: Adjust monitor thresholds based on baseline
4. **Test Alerts**: Verify notification channels work

### Medium-term (Month 1)

1. **Optimize Collection**: Fine-tune which processes to monitor
2. **Tag Strategy**: Refine tags for better filtering and correlation
3. **APM Integration**: Link process metrics with traces
4. **Cost Review**: Assess data volume and optimize if needed

### Long-term (Quarter 1)

1. **SLO Tracking**: Monitor SLOs defined in `DATADOG_SLOS.md`
2. **Capacity Planning**: Use trend data for resource forecasting
3. **Incident Response**: Integrate with on-call workflows
4. **Documentation**: Keep runbooks updated with learnings

## 🔗 Integration Points

### With Existing Goblin Assistant Infrastructure

- **Backend API** (`apps/goblin-assistant/backend/`): Process monitoring tracks FastAPI/Gunicorn workers
- **Cloudflare Workers** (`infra/cloudflare/`): Correlate edge metrics with backend processes
- **Prometheus** (`middleware/metrics.py`): Datadog can scrape Prometheus endpoints
- **Structured Logging** (`middleware/logging_middleware.py`): JSON logs integrate with Datadog logs

### With Other Monitoring Systems

- **Grafana**: Can query Datadog as data source
- **Prometheus**: Datadog supports Prometheus metric format
- **OpenTelemetry**: Agent can receive OTLP traces
- **CloudWatch**: Can forward metrics to CloudWatch (if needed)

## 💰 Cost Considerations

### Datadog Pricing (Approximate)

- **Infrastructure Monitoring**: $15/host/month
- **APM**: $31/host/month
- **Logs**: $0.10/GB ingested + $1.70/million events
- **Custom Metrics**: Included (100 custom metrics/host)

### Optimization Tips

1. **Use Host-based Billing**: More cost-effective than container-based for small deployments
2. **Filter Aggressively**: Only monitor processes you need
3. **Adjust Intervals**: Collect less frequently for non-critical processes
4. **Log Sampling**: Use log sampling for high-volume apps
5. **Metric Limits**: Stay within included custom metric limits

## 🎯 Success Metrics

After 1 week, you should see:

- ✅ All Python/Gunicorn processes visible in Process Explorer
- ✅ CPU and memory trends tracked over time
- ✅ I/O statistics available for all processes
- ✅ Sensitive arguments successfully scrubbed
- ✅ Monitors firing (test with manual threshold breach)
- ✅ No gaps in data collection

## 📞 Support Resources

- **Setup Scripts**: Run with `--help` for detailed options
- **Documentation**: See `README.md` for complete guide
- **Datadog Support**: <https://docs.datadoghq.com/help/>
- **Community**: <https://datadoghq.slack.com>
- **Status Page**: <https://status.datadoghq.com>

## 🔄 Maintenance Schedule

| Task                     | Frequency | Owner         |
| ------------------------ | --------- | ------------- |
| Review process metrics   | Daily     | On-call       |
| Check monitor thresholds | Weekly    | SRE team      |
| Update agent             | Monthly   | DevOps        |
| Audit tag strategy       | Quarterly | Platform team |
| Review costs             | Quarterly | FinOps        |
| Test disaster recovery   | Quarterly | SRE team      |

## ✅ Verification Checklist

Before marking this task complete:

- [ ] Datadog Agent installed and running
- [ ] Process collection enabled and verified
- [ ] System-probe running (I/O stats available)
- [ ] Processes visible in Datadog UI
- [ ] Sensitive data scrubbing confirmed
- [ ] Tags correctly applied
- [ ] At least 1 monitor created
- [ ] Dashboard created for team
- [ ] Documentation read by team
- [ ] On-call runbook updated

---

**Setup Date**: December 3, 2025
**Version**: 1.0.0
**Datadog Agent Version**: 7.53.0+ (recommended 7.65.0+)
**Maintained By**: Goblin Assistant DevOps Team
**Last Updated**: 2025-12-03
