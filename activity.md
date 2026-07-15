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

**Railway deep-dive (verified in dashboard):**
- MOCK_MODE=false confirmed live. HUBSPOT_API_KEY, STRIPE_SECRET_KEY,
  SUPABASE_URL/SERVICE_KEY, VAPI, HEYGEN, INSTANTLY, APIFY, ANTHROPIC
  all present as service variables.
- ROOT CAUSE of the stale backend: the Tryleados service (project
  "miraculous-motivation") has Root Directory = "leadOS", so Railway
  builds only that subfolder — the stripped v2.1.0 app with no leads
  routes. GitHub auto-deploy IS working (latest commit deployed
  successfully); it just deploys the wrong subtree.
- Fix: clear the Root Directory field (Service → Settings → Source) so
  the repo root deploys. Pre-verified in a clean venv: root main.py
  imports cleanly, /health + /api/leads + /api/leads/stats return 200,
  39 routes present. railway.toml healthcheck (/health) guards cutover.

## 2026-07-15 — Backend go-live (Claude Code session, continued)

- Root Directory cleared in Railway (by Enrique); first repo-root build
  failed: repo's nixpacks.toml pulled the pip-less python311 Nix package
  then called bare `pip` (exit 127). Removed nixpacks.toml + added
  .python-version (74817bd); Railway's Python provider then built clean.
- VERIFIED LIVE: /health + / report v3.2, /api/leads and
  /api/leads/stats return 200, 79 routes in openapi.json. Healthcheck
  kept the old deployment serving during both failed/new builds — no
  downtime observed.
- REMAINING BLOCKER: Supabase. Railway's SUPABASE_URL points at the
  project documented in CLAUDE.md, whose hostname no longer resolves
  (free-tier projects pause after inactivity; paused/deleted projects
  drop DNS). /api/leads therefore returns leads:[] with a DNS error and
  no data can persist. The other known project ref does resolve. Needs
  a decision in the Supabase dashboard (restore vs. re-point), fresh
  keys, and the Section-6 migration from CLAUDE.md if tables are absent.

**Manual follow-ups:**
1. Complete Stripe live-mode activation, create the live $49/mo payment
   link, paste it into STRIPE_PAYMENT_LINK in
   frontend/src/components/Nav.jsx.
2. Fix the Google Calendar connection error in Calendly (Availability →
   Calendar settings → Reconnect) or bookings won't sync.
3. Confirm MOCK_MODE=false in Railway → LeadOS service → Variables.
4. Complete the credential-hygiene items discussed in the session notes.
