/**
 * LeadOS Theme Engine  v1.0
 * ─────────────────────────────────────────────────────────────────────────
 * Applies white-label branding across every screen at runtime.
 * Loaded FIRST — before api-client, before any screen script.
 *
 * Script load order in every screen:
 *   1. leadOS-theme-engine.js   ← this file (sets CSS vars, patches DOM)
 *   2. leadOS-tenant-router.js  ← loads correct tenant config by domain
 *   3. leadOS-api-client.js     ← API calls (uses tenant's backend URL)
 *   4. [screen script]          ← dashboard / discovery / etc.
 */

(function() {
  'use strict';

  // ── Default LeadOS brand (used when no tenant config is active) ───────────
  const DEFAULTS = {
    brand: {
      name:      'LeadOS',
      namePart1: 'Lead',
      namePart2: 'OS',
      tagline:   'Lead Intelligence OS',
      logoText:  'L',
      logoMark:  null,
      favicon:   null,
      version:   'v2.0',
    },
    colors: {
      bg:        '#050810',
      surface:   '#0c1120',
      surface2:  '#111827',
      surface3:  '#161e30',
      border:    'rgba(255,255,255,0.06)',
      border2:   'rgba(255,255,255,0.11)',
      accent:    '#00ff88',
      a2:        '#0066ff',
      a3:        '#ff3366',
      a4:        '#ffaa00',
      a5:        '#aa44ff',
      text:      '#f0f4ff',
      muted:     '#6b7a99',
      glow:      'rgba(0,255,136,0.15)',
    },
    features: {
      leadDiscovery:   true,
      aiAgents:        true,
      pipeline:        true,
      outreach:        true,
      crmIntegrations: true,
      icpBuilder:      true,
      analytics:       true,
      linkedinIntel:   true,
      webCrawler:      true,
      settings:        true,
    },
    navLabels: {},
    poweredBy: { show: false, text: 'Powered by LeadOS', link: 'https://leadOS.ai' },
    support:   { email: 'support@leadOS.ai', docsUrl: 'https://docs.leadOS.ai' },
    customCSS: '',
    defaultICP: null,
  };

  // ── Deep merge helper ────────────────────────────────────────────────────
  function merge(base, override) {
    const out = Object.assign({}, base);
    for (const k in override) {
      if (override[k] && typeof override[k] === 'object' && !Array.isArray(override[k])) {
        out[k] = merge(base[k] || {}, override[k]);
      } else if (override[k] !== undefined && override[k] !== null) {
        out[k] = override[k];
      }
    }
    return out;
  }

  // ── Derive surface variants from base bg color ────────────────────────────
  function lightenHex(hex, amount) {
    const num = parseInt(hex.replace('#',''), 16);
    const r = Math.min(255, (num >> 16) + amount);
    const g = Math.min(255, ((num >> 8) & 0xff) + amount);
    const b = Math.min(255, (num & 0xff) + amount);
    return '#' + ((r<<16)|(g<<8)|b).toString(16).padStart(6,'0');
  }

  function buildColorSet(colors) {
    const c = Object.assign({}, colors);
    // Auto-derive surface variants if only bg is provided
    if (!c.surface)  c.surface  = lightenHex(c.bg, 10);
    if (!c.surface2) c.surface2 = lightenHex(c.bg, 16);
    if (!c.surface3) c.surface3 = lightenHex(c.bg, 22);
    // Auto-derive glow from accent
    if (!c.glow) {
      const hex = c.accent.replace('#','');
      const r = parseInt(hex.slice(0,2),16);
      const g = parseInt(hex.slice(2,4),16);
      const b = parseInt(hex.slice(4,6),16);
      c.glow = `rgba(${r},${g},${b},0.15)`;
    }
    return c;
  }

  // ── Apply CSS variables to :root ─────────────────────────────────────────
  function applyCSSVars(colors) {
    const c = buildColorSet(colors);
    const root = document.documentElement;
    const varMap = {
      '--bg':       c.bg,
      '--surface':  c.surface,
      '--surface2': c.surface2,
      '--surface3': c.surface3,
      '--border':   c.border  || 'rgba(255,255,255,0.06)',
      '--border2':  c.border2 || 'rgba(255,255,255,0.11)',
      '--accent':   c.accent,
      '--a2':       c.a2,
      '--a3':       c.a3,
      '--a4':       c.a4,
      '--a5':       c.a5,
      '--text':     c.text,
      '--muted':    c.muted,
      '--glow':     c.glow,
      // Legacy aliases (some older screen styles use these names)
      '--accent2':  c.a2,
      '--accent3':  c.a3,
      '--accent4':  c.a4,
    };
    for (const [prop, val] of Object.entries(varMap)) {
      if (val) root.style.setProperty(prop, val);
    }
  }

  // ── Patch inline styles that hardcode theme colors ────────────────────────
  // Scans rendered DOM for elements using hardcoded LeadOS default hex values
  // and replaces them with CSS variable equivalents.
  const HARDCODED_MAP = {
    '#050810': 'var(--bg)',
    '#0c1120': 'var(--surface)',
    '#111827': 'var(--surface2)',
    '#161e30': 'var(--surface3)',
    '#00ff88': 'var(--accent)',
    '#0066ff': 'var(--a2)',
    '#ff3366': 'var(--a3)',
    '#ffaa00': 'var(--a4)',
    '#aa44ff': 'var(--a5)',
    '#f0f4ff': 'var(--text)',
    '#6b7a99': 'var(--muted)',
  };

  function patchHardcodedColors() {
    // Only run when not default theme (no-op saves DOM query cost)
    if (!window._leadOSThemeActive) return;

    document.querySelectorAll('[style]').forEach(el => {
      let style = el.getAttribute('style');
      let changed = false;
      for (const [hex, cssVar] of Object.entries(HARDCODED_MAP)) {
        const re = new RegExp(hex.replace('#','#'), 'gi');
        if (re.test(style)) {
          style = style.replace(re, cssVar);
          changed = true;
        }
      }
      if (changed) el.setAttribute('style', style);
    });

    // Also patch inline style blocks in <style> tags where vars aren't used
    document.querySelectorAll('style:not(#wl-theme):not(#_leadOS_styles)').forEach(tag => {
      let css = tag.textContent;
      let changed = false;
      for (const [hex, cssVar] of Object.entries(HARDCODED_MAP)) {
        const re = new RegExp(hex.replace('#','#'), 'gi');
        if (re.test(css)) {
          css = css.replace(re, cssVar);
          changed = true;
        }
      }
      if (changed) tag.textContent = css;
    });
  }

  // ── Apply brand identity to DOM ───────────────────────────────────────────
  function applyBrand(brand) {
    // Parse brand name into two parts for colored logo rendering
    const name = brand.name || 'LeadOS';
    let part1 = brand.namePart1 || name;
    let part2 = brand.namePart2 || '';
    if (!brand.namePart1) {
      // Auto-split: last uppercase run becomes part2
      const m = name.match(/^(.*?)([A-Z][A-Z0-9]*)$/);
      if (m) { part1 = m[1]; part2 = m[2]; }
    }

    // Logo icon
    document.querySelectorAll('.logo-icon').forEach(el => {
      if (brand.logoMark) {
        el.innerHTML = `<img src="${brand.logoMark}" style="width:22px;height:22px;object-fit:contain;border-radius:4px" alt="${name}"/>`;
        el.style.background = 'transparent';
      } else {
        el.textContent = brand.logoText || name[0].toUpperCase();
      }
    });

    // Logo text
    document.querySelectorAll('.logo').forEach(el => {
      const subEl = el.querySelector('.logo-sub');
      const subHTML = subEl ? subEl.outerHTML : `<div class="logo-sub">${brand.tagline} · ${brand.version}</div>`;
      el.innerHTML = `
        <div class="logo-icon">${brand.logoMark
          ? `<img src="${brand.logoMark}" style="width:22px;height:22px;object-fit:contain;border-radius:4px" alt="${name}"/>`
          : (brand.logoText || name[0].toUpperCase())
        }</div>
        ${part1}<span>${part2}</span>
        ${subHTML}
      `;
      // Ensure logo-sub tagline is current
      const sub = el.querySelector('.logo-sub');
      if (sub) sub.textContent = `${brand.tagline} · ${brand.version}`;
    });

    // Page title
    document.title = document.title.replace('LeadOS', name);

    // Favicon
    if (brand.favicon) {
      let link = document.querySelector("link[rel~='icon']");
      if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.head.appendChild(link);
      }
      link.href = brand.favicon;
    }
  }

  // ── Apply nav label overrides ────────────────────────────────────────────
  function applyNavLabels(labels) {
    if (!labels || !Object.keys(labels).length) return;
    document.querySelectorAll('.nav-item').forEach(item => {
      const iconEl = item.querySelector('.icon');
      const badgeEl = item.querySelector('.badge');
      // Get text content without icon/badge
      const rawText = [...item.childNodes]
        .filter(n => n.nodeType === Node.TEXT_NODE)
        .map(n => n.textContent.trim())
        .join('').trim();
      for (const [original, replacement] of Object.entries(labels)) {
        if (rawText === original && replacement) {
          [...item.childNodes]
            .filter(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim())
            .forEach(n => { n.textContent = ' ' + replacement; });
          break;
        }
      }
    });
  }

  // ── Hide disabled features ────────────────────────────────────────────────
  function applyFeatureFlags(features) {
    const navMap = {
      leadDiscovery:   ['Lead Discovery', 'Prospect Finder'],
      aiAgents:        ['AI Agents', 'Automation Engine'],
      pipeline:        ['Pipeline', 'Opportunity Board'],
      outreach:        ['Outreach', 'Email Campaigns', 'Sequences'],
      crmIntegrations: ['Integrations', 'CRM Integrations'],
      icpBuilder:      ['ICP Builder', 'Ideal Client Profile'],
      analytics:       ['Analytics', 'Performance'],
      settings:        ['Settings'],
    };
    for (const [feature, enabled] of Object.entries(features)) {
      if (!enabled && navMap[feature]) {
        document.querySelectorAll('.nav-item').forEach(item => {
          const text = item.textContent.trim();
          if (navMap[feature].some(label => text.includes(label))) {
            item.style.display = 'none';
          }
        });
      }
    }
  }

  // ── Powered-by attribution ────────────────────────────────────────────────
  function applyAttribution(poweredBy) {
    if (!poweredBy.show) return;
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar || document.getElementById('wl-powered-by')) return;
    const pb = document.createElement('div');
    pb.id = 'wl-powered-by';
    pb.style.cssText = [
      'padding:10px 20px',
      'font-size:9px',
      'color:var(--muted)',
      'border-top:1px solid var(--border)',
      'text-align:center',
      'letter-spacing:0.5px',
    ].join(';');
    pb.innerHTML = `<a href="${poweredBy.link}" target="_blank" rel="noopener"
      style="color:var(--muted);text-decoration:none;transition:color .2s"
      onmouseover="this.style.color='var(--accent)'"
      onmouseout="this.style.color='var(--muted)'"
    >${poweredBy.text}</a>`;
    sidebar.appendChild(pb);
  }

  // ── Inject custom CSS ─────────────────────────────────────────────────────
  function applyCustomCSS(css) {
    if (!css || !css.trim()) return;
    let el = document.getElementById('wl-custom-css');
    if (!el) {
      el = document.createElement('style');
      el.id = 'wl-custom-css';
      document.head.appendChild(el);
    }
    el.textContent = css;
  }

  // ── Support link injection ────────────────────────────────────────────────
  function applySupport(support) {
    // Update any mailto: links in the page
    document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
      a.href = `mailto:${support.email}`;
    });
    // Update docs links
    document.querySelectorAll('a[href*="docs.leadOS"]').forEach(a => {
      a.href = support.docsUrl;
    });
  }

  // ── Main apply function ───────────────────────────────────────────────────
  function applyTheme(tenantConfig) {
    const cfg = merge(DEFAULTS, tenantConfig || {});
    window._leadOSThemeActive = !!(tenantConfig && tenantConfig.enabled);
    window._leadOSTenant = cfg;

    // 1. CSS variables (instant, no DOM needed)
    applyCSSVars(cfg.colors);

    // 2. Custom CSS overrides
    applyCustomCSS(cfg.customCSS);

    // 3. Wait for DOM then apply identity + structural changes
    const domReady = () => {
      applyBrand(cfg.brand);
      applyNavLabels(cfg.navLabels);
      applyFeatureFlags(cfg.features);
      applyAttribution(cfg.poweredBy);
      applySupport(cfg.support);
      if (window._leadOSThemeActive) {
        // Patch any remaining hardcoded colors
        patchHardcodedColors();
        // Re-patch after dynamic content loads (api-client fills in data)
        setTimeout(patchHardcodedColors, 1500);
        setTimeout(patchHardcodedColors, 4000);
      }
      // Load default ICP if configured
      if (cfg.defaultICP && window.LeadOSAPI) {
        const key = 'wl_icp_' + (cfg.brand.name || 'default').replace(/\s/g,'_');
        if (!sessionStorage.getItem(key)) {
          LeadOSAPI.updateICP(cfg.defaultICP).then(() => {
            sessionStorage.setItem(key, '1');
          });
        }
      }
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', domReady);
    } else {
      domReady();
    }
  }

  // ── Public API ────────────────────────────────────────────────────────────
  window.LeadOSTheme = {
    apply:    applyTheme,
    defaults: DEFAULTS,
    merge:    merge,

    // Live preview — call this from the Reseller Admin panel
    preview: function(partialConfig) {
      applyTheme(merge(window._leadOSTenant || DEFAULTS, partialConfig));
    },

    // Reset to LeadOS defaults
    reset: function() {
      window._leadOSThemeActive = false;
      applyTheme(null);
    },
  };

  // Apply defaults immediately so :root vars are set before first paint
  applyCSSVars(DEFAULTS.colors);

  console.log('%c LeadOS Theme Engine loaded ', 'background:#00ff88;color:#000;font-weight:bold;padding:4px 8px;border-radius:4px;font-family:monospace;font-size:11px;');
})();
