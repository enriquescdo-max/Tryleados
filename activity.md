# LeadOS Activity Log

## 2026-07-10 — Go-live punch list (Claude Code session)

**Audit findings (Phase A):**
- TryLeadOS.com serves the internal Agent Dashboard SPA — there was no
  capture CTA, form, HubSpot/Supabase submission path, Calendly, or Stripe
  anywhere on the live site. Capture was broken at step 0.
- Live Railway backend was serving a stale build (404 on /api/leads):
  root-caused to an unguarded ImportError + a syntax error in
  routers/content_engine_router.py — fixed in da03fa4.
- MOCK_MODE: not set in any repo file; backend code defaults to false.
  Actual Railway variable still needs a manual check in the dashboard.
- A stray committed env file was untracked in c517473 and .gitignore
  hardened (.env* now ignored, .env.example allowed).

**Wiring (Phase B):**
- Primary CTA "Book a Demo →" added to Nav.jsx (every route), pointing at
  the Calendly 30-minute booking page (9cd79d8).
- Stripe: checkout is not yet available in live mode. The nav's Pay now
  button is gated behind a STRIPE_PAYMENT_LINK constant in Nav.jsx and
  stays hidden while that constant is empty; pasting the live payment
  link there is the only change needed at activation.
- Verified on a local production build (vite preview): Book a Demo link
  renders with the correct Calendly href; Pay now is absent; dashboard
  unaffected.

**Manual follow-ups:**
1. Complete Stripe live-mode activation, create the live $49/mo payment
   link, paste it into STRIPE_PAYMENT_LINK in
   frontend/src/components/Nav.jsx.
2. Fix the Google Calendar connection error in Calendly (Availability →
   Calendar settings → Reconnect) or bookings won't sync.
3. Confirm MOCK_MODE=false in Railway → LeadOS service → Variables.
4. Complete the credential-hygiene items discussed in the session notes.
