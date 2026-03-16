/**
 * LeadOS White-Label Configuration System
 * ─────────────────────────────────────────────────────────────────────────
 * This single file controls ALL branding across every LeadOS screen.
 *
 * HOW IT WORKS:
 *   1. Each reseller gets their own copy of this file with their branding
 *   2. They add ONE script tag to their deployment: <script src="whitelabel-config.js">
 *   3. Every screen — dashboard, discovery, outreach, analytics — instantly
 *      reflects their brand. No other files change.
 *
 * WHAT IT CONTROLS:
 *   - Logo, brand name, tagline
 *   - Primary/accent colors (full theme)
 *   - Custom domain & support links
 *   - Which features are visible/hidden
 *   - Custom ICP defaults for their industry
 *   - Powered-by attribution (show/hide "Powered by LeadOS")
 *   - Custom CSS overrides
 *
 * RESELLER TIERS:
 *   basic     → can change logo + colors, "Powered by LeadOS" shown
 *   pro       → full branding, attribution hidden, custom domain
 *   enterprise → full branding + custom features + dedicated support
 */

const WhiteLabelConfig = {

  // ── Identity ─────────────────────────────────────────────────────────────
  enabled: true,                          // false = show default LeadOS branding
  tier: 'pro',                            // 'basic' | 'pro' | 'enterprise'

  brand: {
    name: 'LeadOS',                       // ← reseller changes this
    tagline: 'Lead Intelligence OS',      // ← shown under logo
    logoText: 'L',                        // ← letter shown in logo mark
    logoMark: null,                       // ← URL to logo image (replaces letter)
    // logoMark: 'https://yourdomain.com/logo.png',
    favicon: null,                        // ← URL to favicon
    version: 'v2.0',
  },

  // ── Color Theme ───────────────────────────────────────────────────────────
  // Every CSS variable across all screens maps back to these values.
  // Pick your brand colors here — the entire UI updates automatically.
  colors: {
    bg:       '#050810',   // page background
    surface:  '#0c1120',   // card/panel background
    surface2: '#111827',   // input backgrounds
    accent:   '#00ff88',   // PRIMARY accent — buttons, highlights, scores
    a2:       '#0066ff',   // secondary accent — links, badges
    a3:       '#ff3366',   // danger/negative
    a4:       '#ffaa00',   // warning/signals
    text:     '#f0f4ff',   // primary text
    muted:    '#6b7a99',   // secondary text
  },

  // ── Example: Insurance Agency theme ──────────────────────────────────────
  // Uncomment to try a navy/gold insurance brand look:
  /*
  brand: {
    name: 'AgentIQ',
    tagline: 'Insurance Lead Intelligence',
    logoText: 'A',
    version: 'Pro',
  },
  colors: {
    bg:       '#020812',
    surface:  '#08111e',
    surface2: '#0e1a2a',
    accent:   '#c8a84b',   // gold
    a2:       '#3b82f6',   // blue
    a3:       '#ef4444',
    a4:       '#f59e0b',
    text:     '#f0f6ff',
    muted:    '#4a6280',
  },
  */

  // ── Example: Real Estate CRM theme ───────────────────────────────────────
  /*
  brand: {
    name: 'HomeLeads',
    tagline: 'Real Estate Lead Engine',
    logoText: 'H',
    version: '1.0',
  },
  colors: {
    bg:       '#050308',
    surface:  '#100d18',
    surface2: '#161320',
    accent:   '#e040fb',   // purple
    a2:       '#00bcd4',
    a3:       '#ff5722',
    a4:       '#ffc107',
    text:     '#f8f0ff',
    muted:    '#7060a0',
  },
  */

  // ── Features — show/hide per reseller ────────────────────────────────────
  features: {
    leadDiscovery:    true,
    aiAgents:         true,
    pipeline:         true,
    outreach:         true,
    crmIntegrations:  true,
    icpBuilder:       true,
    analytics:        true,
    linkedinIntel:    true,   // hide if reseller doesn't have LinkedIn data
    webCrawler:       true,
    settings:         true,
  },

  // ── Navigation label overrides ────────────────────────────────────────────
  // Lets resellers rename screens to match their industry language
  navLabels: {
    'Command Center':  'Command Center',    // → could be 'Home Base' for RE agents
    'Lead Discovery':  'Lead Discovery',    // → 'Prospect Finder' for insurance
    'AI Agents':       'AI Agents',         // → 'Automation Engine'
    'Pipeline':        'Pipeline',          // → 'Opportunity Board'
    'Outreach':        'Outreach',          // → 'Email Campaigns'
    'ICP Builder':     'ICP Builder',       // → 'Ideal Client Profile'
    'Analytics':       'Analytics',         // → 'Performance'
    'Integrations':    'Integrations',
  },

  // ── Attribution ───────────────────────────────────────────────────────────
  poweredBy: {
    show: false,            // true = show "Powered by LeadOS" in footer (basic tier)
    text: 'Powered by LeadOS',
    link: 'https://leadOS.ai',
  },

  // ── Support & Links ───────────────────────────────────────────────────────
  support: {
    email:      'support@leadOS.ai',      // ← reseller sets their own
    docsUrl:    'https://docs.leadOS.ai',
    chatWidget: false,                     // true = show support chat bubble
  },

  // ── Custom CSS ────────────────────────────────────────────────────────────
  // Inject any extra CSS overrides — border radius, font, shadows, etc.
  customCSS: `
    /* Example: rounder corners for a softer brand feel */
    /* .panel, .lead-card, .btn { border-radius: 16px !important; } */

    /* Example: custom font */
    /* @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&display=swap');
       body { font-family: 'Outfit', sans-serif !important; } */
  `,

  // ── Default ICP for this reseller's industry ─────────────────────────────
  // Pre-populates the ICP Builder when a new user signs up
  defaultICP: null,   // null = use LeadOS default
  // Set to a full ICP object (same shape as LeadOSAPI.updateICP) to pre-load
  // Example: load the P&C insurance ICP by default for an insurance reseller:
  // defaultICP: INSURANCE_ICP,  // from leadOS-icp-insurance.js
};

// ═══════════════════════════════════════════════════════════════════════════
// RUNTIME — applies branding automatically when script loads
// ═══════════════════════════════════════════════════════════════════════════
(function applyWhiteLabel() {
  if (!WhiteLabelConfig.enabled) return;

  const cfg = WhiteLabelConfig;
  const c = cfg.colors;

  // 1. Inject CSS variables into :root — overrides all default LeadOS colors
  const styleEl = document.createElement('style');
  styleEl.id = 'wl-theme';
  styleEl.textContent = `
    :root {
      --bg:      ${c.bg} !important;
      --surface: ${c.surface} !important;
      --surface2:${c.surface2} !important;
      --accent:  ${c.accent} !important;
      --a2:      ${c.a2} !important;
      --a3:      ${c.a3} !important;
      --a4:      ${c.a4} !important;
      --text:    ${c.text} !important;
      --muted:   ${c.muted} !important;
    }
    ${cfg.customCSS || ''}
  `;
  document.head.appendChild(styleEl);

  // 2. Swap logo text + brand name once DOM is ready
  function applyBranding() {
    // Logo icon letter
    document.querySelectorAll('.logo-icon').forEach(el => {
      if (cfg.brand.logoMark) {
        el.innerHTML = `<img src="${cfg.brand.logoMark}" style="width:22px;height:22px;object-fit:contain;border-radius:4px"/>`;
      } else {
        el.textContent = cfg.brand.logoText;
      }
    });

    // Brand name (the "Lead" + "OS" split)
    document.querySelectorAll('.logo').forEach(el => {
      const sub = el.querySelector('.logo-sub');
      const parts = cfg.brand.name.match(/^(.+?)([A-Z][a-z]*)$/) || [null, cfg.brand.name, ''];
      el.innerHTML = `
        <div class="logo-icon">${cfg.brand.logoMark
          ? `<img src="${cfg.brand.logoMark}" style="width:22px;height:22px;object-fit:contain;border-radius:4px"/>`
          : cfg.brand.logoText}</div>
        ${parts[1]}<span>${parts[2]}</span>
      `;
      if (sub) {
        sub.textContent = cfg.brand.tagline + ' · ' + cfg.brand.version;
        el.appendChild(sub);
      }
    });

    // Page <title>
    document.title = document.title.replace('LeadOS', cfg.brand.name);

    // Favicon
    if (cfg.brand.favicon) {
      let link = document.querySelector("link[rel~='icon']");
      if (!link) { link = document.createElement('link'); link.rel = 'icon'; document.head.appendChild(link); }
      link.href = cfg.brand.favicon;
    }

    // Nav label overrides
    document.querySelectorAll('.nav-item').forEach(item => {
      const textNodes = [...item.childNodes].filter(n => n.nodeType === 3);
      textNodes.forEach(node => {
        const trimmed = node.textContent.trim();
        if (cfg.navLabels[trimmed]) {
          node.textContent = ' ' + cfg.navLabels[trimmed];
        }
      });
    });

    // Hide features that are disabled
    const featureNavMap = {
      leadDiscovery:   'Lead Discovery',
      aiAgents:        'AI Agents',
      pipeline:        'Pipeline',
      outreach:        'Outreach',
      crmIntegrations: 'Integrations',
      icpBuilder:      'ICP Builder',
      analytics:       'Analytics',
    };
    Object.entries(cfg.features).forEach(([key, enabled]) => {
      if (!enabled && featureNavMap[key]) {
        document.querySelectorAll('.nav-item').forEach(item => {
          if (item.textContent.trim().includes(featureNavMap[key])) {
            item.style.display = 'none';
          }
        });
      }
    });

    // Powered-by attribution
    if (cfg.poweredBy.show) {
      const pb = document.createElement('div');
      pb.style.cssText = 'padding:12px 20px;font-size:9px;color:var(--muted);border-top:1px solid rgba(255,255,255,0.05);text-align:center;';
      pb.innerHTML = `<a href="${cfg.poweredBy.link}" target="_blank" style="color:var(--muted);text-decoration:none;">${cfg.poweredBy.text}</a>`;
      document.querySelector('.sidebar')?.appendChild(pb);
    }

    // Load default ICP if configured
    if (cfg.defaultICP && window.LeadOSAPI) {
      const hasLoadedICP = sessionStorage.getItem('wl_icp_loaded');
      if (!hasLoadedICP) {
        LeadOSAPI.updateICP(cfg.defaultICP);
        sessionStorage.setItem('wl_icp_loaded', '1');
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyBranding);
  } else {
    applyBranding();
  }
})();

// Export for programmatic use
window.WhiteLabelConfig = WhiteLabelConfig;
