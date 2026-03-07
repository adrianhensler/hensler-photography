# Hensler Photography — Now / Next / Later (Concise)

Date: 2026-03-07
Inputs: DeepSeek + Mistral + Qwen independent reviews, Sonnet 4.6 debate + synthesis.

## Now (this week)
1. **Backup restore drill (must-pass)**
   - Restore to a fresh host and verify DB/images/config end-to-end.
2. **Harden admin access**
   - Add Caddy rate limiting for `/admin` and `/manage`.
   - Add TOTP 2FA in FastAPI auth.
3. **Set uptime monitoring**
   - Configure alerts for all three domains.

## Next (2–6 weeks)
1. **SEO/social metadata pass**
   - Dynamic Open Graph/Twitter/canonical tags per gallery page.
2. **Launch real `hensler.photography` landing page**
   - Replace placeholder with clear routing + contact/conversion intent.
3. **Liam parity with Adrian API path**
   - Reduce maintenance split and avoid feature drift.
4. **Consent/compliance layer**
   - Add cookie consent gating for analytics where applicable.

## Later
1. Object storage/CDN migration (triggered by disk/perf thresholds)
2. CI/CD hardening and deployment automation
3. Further filter UX refinements (only after analytics signal)
4. Additional AI feature expansion (after core reliability/security milestones)

## Risks to watch
- Untested backup risk (critical until validated)
- Admin endpoint exposure risk (critical until 2FA + rate limits)
- Maintenance split risk across Adrian/Liam site paths
- Compliance exposure if analytics consent is not gated
