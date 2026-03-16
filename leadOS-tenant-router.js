/**
 * LeadOS Tenant Router  v1.0
 * ─────────────────────────────────────────────────────────────────────────
 * Automatically detects which white-label tenant is being accessed and
 * loads their brand config — zero manual setup per-screen.
 *
 * HOW DOMAIN ROUTING WORKS:
 *
 *   leadOS.ai               → Default LeadOS brand (no white-label)
 *   agentiq.leadOS.ai       → AgentIQ tenant (insurance)
 *   app.agentiq.ai          → AgentIQ custom domain (CNAME → leadOS servers)
 *   leads.dealeriq.com      → DealerIQ tenant (auto dealers)
 *
 * The router checks:
 *   1. URL query param:  ?tenant=agentiq  (for testing / dev)
 *   2. Subdomain:        agentiq.leadOS.ai → tenant id = "agentiq"
 *   3. Custom domain:    app.agentiq.ai → looked up in tenant registry
 *   4. Falls back to:    default LeadOS brand
 *
 * TENANT REGISTRY:
 *   In production, this fetches from your backend API.
 *   In MOCK_MODE, it uses the hardcoded registry below.
 *   Each tenant record stores their full WhiteLabelConfig.
 */

(function() {
  'use strict';

  // ── Tenant Registry (mock data — replace with API call in production) ────
  // In production: GET /api/tenants/:id  or  GET /api/tenants/by-domain/:domain
  const TENANT_REGISTRY = {

    agentiq: {
      id: 'agentiq',
      enabled: true,
      tier: 'pro',
      customDomains: ['app.agentiq.ai', 'leads.agentiq.com'],
      brand: {
        name:      'AgentIQ',
        namePart1: 'Agent',
        namePart2: 'IQ',
        tagline:   'Insurance Lead Intelligence',
        logoText:  'A',
        logoMark:  null,
        version:   'Pro',
      },
      colors: {
        bg:       '#02060e',
        surface:  '#07101c',
        surface2: '#0c1826',
        accent:   '#c8a84b',   // gold — classic insurance/finance
        a2:       '#4a9eff',
        a3:       '#ef4444',
        a4:       '#f59e0b',
        a5:       '#8b5cf6',
        text:     '#f0f6ff',
        muted:    '#4a6280',
      },
      features: {
        leadDiscovery: true, aiAgents: true, pipeline: true, outreach: true,
        crmIntegrations: true, icpBuilder: true, analytics: true,
        linkedinIntel: true, webCrawler: true, settings: true,
      },
      navLabels: {
        'Lead Discovery': 'Prospect Finder',
        'ICP Builder':    'Client Profile',
        'Outreach':       'Email Campaigns',
        'Analytics':      'Performance',
      },
      poweredBy: { show: false },
      support: { email: 'support@agentiq.ai', docsUrl: 'https://docs.agentiq.ai' },
      customCSS: `
        .btn-primary { border-radius: 6px !important; }
        .panel { border-radius: 10px !important; }
      `,
      apiBaseUrl: 'https://api.agentiq.ai',    // tenant's own backend URL
    },

    homeleads: {
      id: 'homeleads',
      enabled: true,
      tier: 'pro',
      customDomains: ['app.homeleads.io'],
      brand: {
        name:      'HomeLeads',
        namePart1: 'Home',
        namePart2: 'Leads',
        tagline:   'Real Estate Lead Engine',
        logoText:  'H',
        version:   '1.0',
      },
      colors: {
        bg:       '#050308',
        surface:  '#0d0a14',
        surface2: '#140f1e',
        accent:   '#e040fb',   // purple
        a2:       '#00bcd4',
        a3:       '#ff5722',
        a4:       '#ffc107',
        a5:       '#7c4dff',
        text:     '#f8f0ff',
        muted:    '#7060a0',
      },
      features: {
        leadDiscovery: true, aiAgents: true, pipeline: true, outreach: true,
        crmIntegrations: true, icpBuilder: true, analytics: true,
        linkedinIntel: false,  // disabled for this tier
        webCrawler: true, settings: true,
      },
      navLabels: {
        'Lead Discovery': 'Find Buyers',
        'ICP Builder':    'Buyer Profile',
        'Outreach':       'Campaigns',
      },
      poweredBy: { show: false },
      support: { email: 'hello@homeleads.io', docsUrl: 'https://homeleads.io/help' },
      customCSS: '',
      apiBaseUrl: 'https://api.homeleads.io',
    },

    dealeriq: {
      id: 'dealeriq',
      enabled: true,
      tier: 'enterprise',
      customDomains: ['leads.dealeriq.com', 'app.dealeriq.com'],
      brand: {
        name:      'DealerIQ',
        namePart1: 'Dealer',
        namePart2: 'IQ',
        tagline:   'Auto Dealer Lead Intelligence',
        logoText:  'D',
        version:   'Enterprise',
      },
      colors: {
        bg:       '#030508',
        surface:  '#090d14',
        surface2: '#0f1520',
        accent:   '#00e5ff',   // cyan
        a2:       '#ff6b35',
        a3:       '#ff3b5c',
        a4:       '#ffd166',
        a5:       '#c084fc',
        text:     '#e8f4ff',
        muted:    '#3d5470',
      },
      features: {
        leadDiscovery: true, aiAgents: true, pipeline: true, outreach: true,
        crmIntegrations: true, icpBuilder: true, analytics: true,
        linkedinIntel: true, webCrawler: true, settings: true,
      },
      navLabels: {
        'Lead Discovery': 'Find Buyers',
        'ICP Builder':    'Buyer Profile',
        'Pipeline':       'Deal Board',
        'Analytics':      'Sales Intel',
      },
      poweredBy: { show: false },
      support: { email: 'support@dealeriq.com', docsUrl: 'https://dealeriq.com/docs' },
      customCSS: `
        .logo-icon { border-radius: 4px !important; }
      `,
      apiBaseUrl: 'https://api.dealeriq.com',
    },
  };

  // ── Domain detection ──────────────────────────────────────────────────────
  function detectTenantId() {
    const hostname = window.location.hostname;
    const params   = new URLSearchParams(window.location.search);

    // 1. Query param override (dev/testing: ?tenant=agentiq)
    const paramTenant = params.get('tenant');
    if (paramTenant) {
      console.log(`[LeadOS Router] Tenant override via query param: ${paramTenant}`);
      return paramTenant;
    }

    // 2. Subdomain on leadOS domain (agentiq.leadOS.ai → 'agentiq')
    const leadOSDomains = ['leadOS.ai', 'leadOS.app', 'localhost', '127.0.0.1'];
    for (const baseDomain of leadOSDomains) {
      if (hostname === baseDomain) return null; // root domain = default
      if (hostname.endsWith('.' + baseDomain)) {
        const subdomain = hostname.slice(0, -(baseDomain.length + 1));
        if (subdomain && subdomain !== 'www' && subdomain !== 'app') {
          console.log(`[LeadOS Router] Tenant from subdomain: ${subdomain}`);
          return subdomain;
        }
      }
    }

    // 3. Custom domain lookup
    for (const [tenantId, cfg] of Object.entries(TENANT_REGISTRY)) {
      if (cfg.customDomains && cfg.customDomains.includes(hostname)) {
        console.log(`[LeadOS Router] Tenant from custom domain: ${hostname} → ${tenantId}`);
        return tenantId;
      }
    }

    // 4. No tenant found — use defaults
    return null;
  }

  // ── Load tenant config ────────────────────────────────────────────────────
  async function loadTenantConfig(tenantId) {
    if (!tenantId) return null;

    // In MOCK_MODE: use registry
    if (!window.LeadOSConfig || window.LeadOSConfig.MOCK_MODE) {
      const cfg = TENANT_REGISTRY[tenantId.toLowerCase()];
      if (!cfg) {
        console.warn(`[LeadOS Router] Unknown tenant: "${tenantId}" — using defaults`);
        return null;
      }
      return cfg;
    }

    // In LIVE mode: fetch from your backend
    try {
      const res = await fetch(
        `${window.LeadOSConfig.API_BASE_URL}/api/tenants/${tenantId}`,
        { headers: { 'Content-Type': 'application/json' } }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(`[LeadOS Router] Failed to load tenant config:`, err);
      // Fall back to local registry
      return TENANT_REGISTRY[tenantId.toLowerCase()] || null;
    }
  }

  // ── Wire tenant API URL into the API client ───────────────────────────────
  function applyTenantAPIUrl(tenantConfig) {
    if (!tenantConfig?.apiBaseUrl) return;
    if (window.LeadOSConfig) {
      window.LeadOSConfig.API_BASE_URL = tenantConfig.apiBaseUrl;
      console.log(`[LeadOS Router] API URL set to: ${tenantConfig.apiBaseUrl}`);
    }
  }

  // ── Bootstrap ─────────────────────────────────────────────────────────────
  async function bootstrap() {
    const tenantId = detectTenantId();

    if (!tenantId) {
      console.log('%c LeadOS Router: Default brand (no tenant) ', 'background:#00ff88;color:#000;font-weight:bold;padding:3px 8px;border-radius:4px;font-family:monospace;font-size:10px;');
      // Still apply defaults through the theme engine
      if (window.LeadOSTheme) window.LeadOSTheme.apply(null);
      return;
    }

    const config = await loadTenantConfig(tenantId);

    if (!config) {
      if (window.LeadOSTheme) window.LeadOSTheme.apply(null);
      return;
    }

    // Apply brand via theme engine
    if (window.LeadOSTheme) {
      window.LeadOSTheme.apply(config);
    }

    // Point API calls at tenant's backend
    applyTenantAPIUrl(config);

    // Store tenant for other scripts to reference
    window._leadOSTenantId = tenantId;

    console.log(`%c LeadOS Router: Tenant "${config.brand.name}" loaded `,
      `background:${config.colors?.accent || '#00ff88'};color:#000;font-weight:bold;padding:3px 8px;border-radius:4px;font-family:monospace;font-size:10px;`);
  }

  // ── Public API ────────────────────────────────────────────────────────────
  window.LeadOSTenantRouter = {
    bootstrap,
    registry:    TENANT_REGISTRY,
    detectTenantId,
    loadTenantConfig,

    // Register a new tenant at runtime (used by Reseller Admin)
    registerTenant: function(id, config) {
      TENANT_REGISTRY[id] = config;
    },

    // List all tenants (for Reseller Admin panel)
    listTenants: function() {
      return Object.values(TENANT_REGISTRY);
    },
  };

  // Auto-bootstrap
  bootstrap();
})();
