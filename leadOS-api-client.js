/**
 * LeadOS API Client
 * ─────────────────────────────────────────────────────────────────────────────
 * Single source of truth for all frontend ↔ backend communication.
 *
 * HOW IT WORKS:
 *   - When MOCK_MODE = true  → returns realistic fake data instantly (safe, no server needed)
 *   - When MOCK_MODE = false → makes real fetch() calls to your Python backend
 *
 * TO GO LIVE:
 *   1. Start your Python backend:  python main.py
 *   2. Change API_BASE_URL below to your server address
 *   3. Set MOCK_MODE = false
 *   That's it. No other files change.
 *
 * SAFE BY DEFAULT:
 *   Nothing real happens until you flip MOCK_MODE to false AND
 *   configure API keys in your backend's .env file.
 */

const LeadOSConfig = {
  API_BASE_URL: 'https://tryleados-production.up.railway.app',
  MOCK_MODE: false,
  MOCK_DELAY_MS: 400,                       // realistic loading feel in mock mode
  REQUEST_TIMEOUT_MS: 10000,
};

// ── Internal helpers ─────────────────────────────────────────────────────────

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function apiFetch(path, options = {}) {
  const url = `${LeadOSConfig.API_BASE_URL}${path}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), LeadOSConfig.REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      signal: controller.signal,
      ...options,
    });
    clearTimeout(timeout);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    clearTimeout(timeout);
    if (err.name === 'AbortError') throw new Error('Request timed out — is the backend running?');
    throw err;
  }
}

// ── Mock Data ────────────────────────────────────────────────────────────────

const MOCK = {
  status: {
    running: true,
    queue_size: 14,
    active_tasks: 3,
    total_leads: 12847,
    qualified_leads: 3291,
    agents: {
      crawler: 'active', linkedin: 'active', enricher: 'active',
      qualifier: 'active', email_verifier: 'active',
      signal_detector: 'active', crm_sync: 'active', outreach: 'active',
    },
    recent_events: [
      { timestamp: new Date().toISOString(), agent: 'crawler', message: 'Crawled G2.com — 147 companies found', level: 'success' },
      { timestamp: new Date(Date.now()-8000).toISOString(), agent: 'qualifier', message: 'Scored Sarah Chen @ Stripe — 94/100', level: 'success' },
      { timestamp: new Date(Date.now()-15000).toISOString(), agent: 'crm_sync', message: 'Pushed 3 leads to HubSpot', level: 'success' },
      { timestamp: new Date(Date.now()-31000).toISOString(), agent: 'enricher', message: 'Enriched Marcus Webb — 14 data points added', level: 'success' },
      { timestamp: new Date(Date.now()-45000).toISOString(), agent: 'email_verifier', message: 'Verified s.chen@stripe.com — 99% deliverable', level: 'success' },
    ],
  },

  leads: [
    { id: 'lead_001', name: 'Sarah Chen', email: 's.chen@stripe.com', phone: '+1 415-555-0191', title: 'VP Marketing', company: 'Stripe', source: 'web_crawler', status: 'qualified', ai_score: 94, ai_score_reasoning: 'VP Marketing at Series B SaaS actively expanding. Email verified 99%. Two strong signals: $50M raise + 8 AE roles open.', intent_signals: ['Raised $50M Series B', 'Hiring 8 AE roles'], email_verified: true, linkedin_url: 'https://linkedin.com/in/sarah-chen', created_at: new Date(Date.now()-7200000).toISOString() },
    { id: 'lead_002', name: 'Marcus Webb', email: 'm.webb@linear.app', phone: '+1 650-555-0142', title: 'Head of Growth', company: 'Linear', source: 'linkedin', status: 'qualified', ai_score: 88, ai_score_reasoning: 'Head of Growth at fast-growing dev tools. New VP Sales hire signals active pipeline building.', intent_signals: ['New VP Sales hired', 'Series A announced'], email_verified: true, linkedin_url: 'https://linkedin.com/in/marcus-webb', created_at: new Date(Date.now()-14400000).toISOString() },
    { id: 'lead_003', name: 'James Rodriguez', email: 'j.rodriguez@vercel.com', phone: '+1 415-555-0177', title: 'CEO & Founder', company: 'Vercel', source: 'web_crawler', status: 'qualified', ai_score: 91, ai_score_reasoning: 'Founder-CEO at infrastructure SaaS. Raised Series B 2 months ago, actively hiring senior roles.', intent_signals: ['Series B raised', 'Product launch announced'], email_verified: true, linkedin_url: 'https://linkedin.com/in/james-rodriguez', created_at: new Date(Date.now()-21600000).toISOString() },
    { id: 'lead_004', name: 'Priya Patel', email: 'p.patel@notion.so', phone: null, title: 'CMO', company: 'Notion', source: 'linkedin', status: 'qualified', ai_score: 76, ai_score_reasoning: 'CMO at productivity SaaS. Recent AI launch signals new budget allocation.', intent_signals: ['Product launch: Notion AI'], email_verified: true, linkedin_url: 'https://linkedin.com/in/priya-patel', created_at: new Date(Date.now()-28800000).toISOString() },
    { id: 'lead_005', name: 'Elena Kowalski', email: 'e.kowalski@figma.com', phone: null, title: 'Dir. Partnerships', company: 'Figma', source: 'social_signals', status: 'qualified', ai_score: 69, ai_score_reasoning: 'Director at design giant. Recent reorg may create new opportunities.', intent_signals: ['Internal reorg signal'], email_verified: false, linkedin_url: null, created_at: new Date(Date.now()-36000000).toISOString() },
  ],

  analytics: {
    total_leads: 12847,
    qualified_leads: 3291,
    pipeline_value: 2400000,
    avg_ai_score: 71.4,
    reply_rate: 8.2,
    open_rate: 47.1,
    leads_by_source: { web_crawler: 5841, linkedin: 3291, social_signals: 2017, job_boards: 1041, manual: 657 },
    leads_by_day: Array.from({length: 30}, (_, i) => ({
      date: new Date(Date.now() - (29-i)*86400000).toISOString().slice(0,10),
      discovered: Math.floor(300 + i*8 + (Math.random()-0.5)*80),
      qualified: Math.floor(78 + i*2 + (Math.random()-0.5)*20),
      converted: Math.floor(12 + i*0.3 + (Math.random()-0.5)*5),
    })),
  },

  icp_profile: {
    id: 'icp_001',
    name: 'Default SaaS ICP',
    target_industries: ['SaaS', 'Technology', 'FinTech', 'E-Commerce'],
    min_employees: 10,
    max_employees: 500,
    target_titles: ['CEO', 'CTO', 'VP Sales', 'VP Marketing', 'Founder'],
    target_seniority: ['C-Suite', 'VP', 'Director'],
    target_geographies: ['United States', 'Canada', 'United Kingdom'],
    positive_signals: ['recently raised funding', 'hiring sales roles', 'new leadership', 'product launch'],
    negative_signals: ['layoffs announced', 'acquisition completed'],
  },

  crm_status: {
    hubspot: { connected: true, contacts_synced: 24100, uptime: 99.9, last_sync: new Date(Date.now()-120000).toISOString(), sync_interval: '5m' },
    salesforce: { connected: true, contacts_synced: 18700, uptime: 99.7, last_sync: new Date(Date.now()-900000).toISOString(), sync_interval: '15m' },
    pipedrive: { connected: true, contacts_synced: 5400, uptime: 100, last_sync: new Date(Date.now()-60000).toISOString(), sync_interval: '1m' },
    gohighlevel: { connected: false },
    zoho: { connected: false },
  },

  sync_log: [
    { id: 's1', crm: 'hubspot', operation: 'push', success: true, records_affected: 1, created_at: new Date(Date.now()-2000).toISOString(), lead_name: 'Sarah Chen' },
    { id: 's2', crm: 'salesforce', operation: 'dedup', success: true, records_affected: 0, created_at: new Date(Date.now()-8000).toISOString(), note: 'Duplicate blocked: j.smith@acme.com' },
    { id: 's3', crm: 'pipedrive', operation: 'push', success: true, records_affected: 1, created_at: new Date(Date.now()-15000).toISOString(), lead_name: 'Marcus Webb' },
    { id: 's4', crm: 'hubspot', operation: 'pull', success: true, records_affected: 14, created_at: new Date(Date.now()-60000).toISOString(), note: 'Pulled 14 updated contacts' },
    { id: 's5', crm: 'pipedrive', operation: 'push', success: false, records_affected: 0, created_at: new Date(Date.now()-120000).toISOString(), note: 'Email validation failed' },
  ],

  sequences: [
    { id: 'seq_001', name: 'SaaS VP Outreach Q1', contacts: 142, active: true, steps_completed: 2, total_steps: 5, open_rate: 51, reply_rate: 9.4 },
    { id: 'seq_002', name: 'FinTech Decision Makers', contacts: 87, active: true, steps_completed: 2, total_steps: 5, open_rate: 44, reply_rate: 7.1 },
    { id: 'seq_003', name: 'YC Founder Blitz', contacts: 63, active: true, steps_completed: 1, total_steps: 5, open_rate: 58, reply_rate: 11.2 },
    { id: 'seq_004', name: 'LinkedIn Warm Follow-up', contacts: 211, active: false, steps_completed: 4, total_steps: 5, open_rate: 38, reply_rate: 6.8 },
  ],
};

// ── Public API ────────────────────────────────────────────────────────────────

const LeadOSAPI = {

  // ── System ────────────────────────────────────────────────────────────

  async getStatus() {
    if (LeadOSConfig.MOCK_MODE) { await delay(LeadOSConfig.MOCK_DELAY_MS); return MOCK.status; }
    return apiFetch('/status');
  },

  async getEvents(limit = 50) {
    if (LeadOSConfig.MOCK_MODE) { await delay(200); return { events: MOCK.status.recent_events, total: MOCK.status.recent_events.length }; }
    return apiFetch(`/events?limit=${limit}`);
  },

  // ── Leads ─────────────────────────────────────────────────────────────

  async getLeads({ limit = 50, status = null } = {}) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(LeadOSConfig.MOCK_DELAY_MS);
      let leads = [...MOCK.leads];
      if (status) leads = leads.filter(l => l.status === status);
      return { total: leads.length, leads: leads.slice(0, limit) };
    }
    const params = new URLSearchParams({ limit });
    if (status) params.set('status', status);
    return apiFetch(`/leads?${params}`);
  },

  async getLead(leadId) {
    if (LeadOSConfig.MOCK_MODE) { await delay(200); return MOCK.leads.find(l => l.id === leadId) || null; }
    return apiFetch(`/leads/${leadId}`);
  },

  async submitLead(leadData) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(600);
      const newLead = { id: 'lead_' + Date.now(), status: 'new', ai_score: null, created_at: new Date().toISOString(), ...leadData };
      MOCK.leads.unshift(newLead);
      return { lead_id: newLead.id, status: 'pipeline_started' };
    }
    return apiFetch('/leads', { method: 'POST', body: JSON.stringify(leadData) });
  },

  async deleteLead(leadId) {
    if (LeadOSConfig.MOCK_MODE) { await delay(300); MOCK.leads = MOCK.leads.filter(l => l.id !== leadId); return { deleted: leadId }; }
    return apiFetch(`/leads/${leadId}`, { method: 'DELETE' });
  },

  // ── Lead Search ───────────────────────────────────────────────────────

  async searchLeads(query, limit = 20) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(LeadOSConfig.MOCK_DELAY_MS);
      const q = query.toLowerCase();
      const filtered = MOCK.leads.filter(l =>
        l.name.toLowerCase().includes(q) ||
        (l.company || '').toLowerCase().includes(q) ||
        (l.title || '').toLowerCase().includes(q)
      );
      const results = filtered.length ? filtered : MOCK.leads;
      return { leads: results.slice(0, limit), total: results.length, query };
    }
    return apiFetch('/leads/search', {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    });
  },

  // ── Campaigns ─────────────────────────────────────────────────────────

  async runCampaign({ prompt, sources = ['crawler', 'linkedin'], max_leads = 50 }) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(800);
      return { status: 'campaign_started', prompt, sources, max_leads, campaign_id: 'camp_' + Date.now() };
    }
    return apiFetch('/campaigns', { method: 'POST', body: JSON.stringify({ prompt, sources, max_leads }) });
  },

  // ── ICP ───────────────────────────────────────────────────────────────

  async getICP() {
    if (LeadOSConfig.MOCK_MODE) { await delay(200); return MOCK.icp_profile; }
    return apiFetch('/icp');
  },

  async updateICP(icpData) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(500);
      Object.assign(MOCK.icp_profile, icpData);
      return { status: 'icp_updated', icp_name: icpData.name };
    }
    return apiFetch('/icp', { method: 'POST', body: JSON.stringify(icpData) });
  },

  // ── Analytics ─────────────────────────────────────────────────────────

  async getAnalytics() {
    if (LeadOSConfig.MOCK_MODE) { await delay(LeadOSConfig.MOCK_DELAY_MS); return MOCK.analytics; }
    return apiFetch('/analytics');
  },

  // ── CRM ───────────────────────────────────────────────────────────────

  async getCRMStatus() {
    if (LeadOSConfig.MOCK_MODE) { await delay(300); return MOCK.crm_status; }
    return apiFetch('/crm/status');
  },

  async getSyncLog(limit = 50) {
    if (LeadOSConfig.MOCK_MODE) { await delay(200); return { log: MOCK.sync_log, total: MOCK.sync_log.length }; }
    return apiFetch(`/crm/sync-log?limit=${limit}`);
  },

  async triggerCRMSync(crm = 'all') {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(600);
      const entry = { id: 'sync_' + Date.now(), crm, operation: 'push', success: true, records_affected: Math.floor(Math.random()*20+1), created_at: new Date().toISOString() };
      MOCK.sync_log.unshift(entry);
      return { status: 'sync_queued', crm, leads_queued: entry.records_affected };
    }
    return apiFetch('/crm/sync', { method: 'POST', body: JSON.stringify({ crm }) });
  },

  async connectCRM(crm, credentials) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(1200);
      if (MOCK.crm_status[crm]) MOCK.crm_status[crm].connected = true;
      return { status: 'connected', crm };
    }
    return apiFetch(`/crm/connect`, { method: 'POST', body: JSON.stringify({ crm, ...credentials }) });
  },

  // ── Outreach / Sequences ──────────────────────────────────────────────

  async getSequences() {
    if (LeadOSConfig.MOCK_MODE) { await delay(300); return { sequences: MOCK.sequences }; }
    return apiFetch('/sequences');
  },

  async createSequence(data) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(500);
      const seq = { id: 'seq_' + Date.now(), contacts: 0, active: false, steps_completed: 0, total_steps: 5, open_rate: 0, reply_rate: 0, ...data };
      MOCK.sequences.push(seq);
      return seq;
    }
    return apiFetch('/sequences', { method: 'POST', body: JSON.stringify(data) });
  },

  async generateEmailCopy(leadId, stepNum = 1) {
    if (LeadOSConfig.MOCK_MODE) {
      await delay(1500);
      const lead = MOCK.leads.find(l => l.id === leadId) || { name: 'there', company: 'your company', title: 'leader', intent_signals: ['recent growth'] };
      const signal = lead.intent_signals?.[0] || 'recent growth signals';
      return {
        subject: `Quick question about ${lead.company}'s growth`,
        body: `Hi ${lead.name?.split(' ')[0] || 'there'},\n\nSaw that ${lead.company} has been ${signal} — congrats on the momentum.\n\nWe help ${lead.title}s like yourself find and close the right leads 2x faster using AI agents that work around the clock.\n\nMost teams see a 40% improvement in qualified pipeline within 60 days.\n\nWorth a 15-min call this week?\n\nBest,\n[Your Name]`,
      };
    }
    return apiFetch(`/outreach/generate`, { method: 'POST', body: JSON.stringify({ lead_id: leadId, step: stepNum }) });
  },
};

// ── UI Utilities shared across all screens ────────────────────────────────────

const LeadOSUI = {

  // Show a loading skeleton inside any element
  skeleton(el, rows = 3) {
    el.innerHTML = Array.from({length: rows}, () =>
      `<div style="height:14px;background:rgba(255,255,255,0.05);border-radius:4px;margin-bottom:10px;animation:shimmer 1.5s infinite;"></div>`
    ).join('');
  },

  // Show a toast notification
  toast(message, type = 'success') {
    let t = document.getElementById('_leadOS_toast');
    if (!t) {
      t = document.createElement('div');
      t.id = '_leadOS_toast';
      t.style.cssText = 'position:fixed;bottom:28px;right:28px;z-index:9999;font-family:"DM Mono",monospace;font-size:12px;display:flex;flex-direction:column;gap:8px;';
      document.body.appendChild(t);
    }
    const item = document.createElement('div');
    const colors = { success: 'rgba(0,255,136,0.15)', error: 'rgba(255,51,102,0.15)', info: 'rgba(0,102,255,0.15)', warning: 'rgba(255,170,0,0.15)' };
    const borders = { success: 'rgba(0,255,136,0.3)', error: 'rgba(255,51,102,0.3)', info: 'rgba(0,102,255,0.3)', warning: 'rgba(255,170,0,0.3)' };
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    item.style.cssText = `background:${colors[type]};border:1px solid ${borders[type]};border-radius:10px;padding:12px 18px;display:flex;align-items:center;gap:10px;transform:translateX(120%);transition:transform .3s ease;box-shadow:0 8px 32px rgba(0,0,0,.5);backdrop-filter:blur(12px);max-width:360px;`;
    item.innerHTML = `<span style="font-size:16px">${icons[type]}</span><span style="color:#f0f4ff">${message}</span>`;
    t.appendChild(item);
    requestAnimationFrame(() => { item.style.transform = 'translateX(0)'; });
    setTimeout(() => { item.style.transform = 'translateX(120%)'; setTimeout(() => item.remove(), 300); }, 3500);
  },

  // Show inline error state
  error(el, message) {
    el.innerHTML = `<div style="padding:20px;text-align:center;color:#f87171;font-size:11px;font-family:'DM Mono',monospace;">⚠️ ${message}<br><span style="color:#4a6280;font-size:9px;margin-top:6px;display:block">Check browser console for details</span></div>`;
  },

  // Format a relative timestamp
  relativeTime(isoString) {
    const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return `${Math.floor(diff/86400)}d ago`;
  },

  // Score → color
  scoreColor(score) {
    if (score >= 85) return '#00ff88';
    if (score >= 70) return '#ffaa00';
    return '#ff3366';
  },

  // Add shimmer keyframe if not present
  initStyles() {
    if (document.getElementById('_leadOS_styles')) return;
    const s = document.createElement('style');
    s.id = '_leadOS_styles';
    s.textContent = `
      @keyframes shimmer { 0%,100%{opacity:.4} 50%{opacity:.8} }
      .leadOS-loading { pointer-events:none; opacity:.7; }
      .leadOS-btn-loading { position:relative; color:transparent !important; pointer-events:none; }
      .leadOS-btn-loading::after { content:''; position:absolute; top:50%; left:50%; width:14px; height:14px; margin:-7px 0 0 -7px; border:2px solid rgba(0,0,0,0.3); border-top-color:rgba(0,0,0,0.8); border-radius:50%; animation:spin .6s linear infinite; }
      @keyframes spin { to{transform:rotate(360deg)} }
    `;
    document.head.appendChild(s);
  },
};

LeadOSUI.initStyles();

// Export for use in each screen
window.LeadOSAPI = LeadOSAPI;
window.LeadOSUI = LeadOSUI;
window.LeadOSConfig = LeadOSConfig;

console.log('%c LeadOS API Client loaded ', 'background:#00ff88;color:#000;font-weight:bold;padding:4px 8px;border-radius:4px;font-family:monospace;');
console.log('%c MOCK_MODE: ' + LeadOSConfig.MOCK_MODE + ' | Backend: ' + LeadOSConfig.API_BASE_URL, 'color:#6b7a99;font-family:monospace;');
