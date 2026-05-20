import type { NextWebVitalsMetric } from 'next/app';
import { trackEvent } from './analytics';
import { trackPerformance } from './error-tracking';

const WEB_VITAL_METRICS = new Set(['CLS', 'FCP', 'INP', 'LCP', 'TTFB']);

const toContext = (metric: NextWebVitalsMetric) => ({
  id: metric.id,
  label: metric.label,
  startTime: Number(metric.startTime.toFixed(4)),
  attribution: metric.attribution,
});

export const reportWebVitalMetric = (metric: NextWebVitalsMetric) => {
  if (!WEB_VITAL_METRICS.has(metric.name)) {
    return;
  }

  trackPerformance(`web_vital_${metric.name.toLowerCase()}`, metric.value, toContext(metric));
  trackEvent('web_vital', {
    metric_name: metric.name,
    value: Number(metric.value.toFixed(4)),
    label: metric.label,
  });
};
