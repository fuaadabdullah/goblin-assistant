# Core Web Vitals Budgets

These budgets apply to the Next.js web app in `apps/web`.

## Targets

- `LCP < 2.5s` at p75
- `INP < 200ms` at p75
- `CLS < 0.1` at p75
- `FCP < 1.8s` at p75
- `TTFB < 800ms` at p75

## Instrumentation

- The app exports `reportWebVitals` from [`apps/web/src/pages/_app.tsx](/Volumes/GOBLINOS%201/goblin-assistant/apps/web/src/pages/_app.tsx).
- Metrics are forwarded through [`apps/web/src/utils/web-vitals.ts](/Volumes/GOBLINOS%201/goblin-assistant/apps/web/src/utils/web-vitals.ts).
- Every tracked vital is emitted through `trackPerformance(...)`.
- When analytics is enabled, the same events are also mirrored through `trackEvent(...)`.

## Metric Names

- `web_vital_lcp`
- `web_vital_inp`
- `web_vital_cls`
- `web_vital_fcp`
- `web_vital_ttfb`

## Verification

- Run the web app locally and open the browser dev tools console/network tabs.
- Confirm the `reportWebVitals` hook fires during page load and interaction.
- Check the monitoring sink used by `trackPerformance(...)` for the metric names above.
- Review changes alongside Chromatic and normal UI tests; this phase does not fail CI on vitals yet.
