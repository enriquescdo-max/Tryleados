/**
 * LeadOS Lead Database Browser
 * Insurance-native Apollo killer — drop into React/Vite app
 * Brand: #0C0C0C bg · #E05A1A orange · IBM Plex Mono data values
 */

import { useState, useEffect, useCallback } from "react";

// ─── Mock data generator ─────────────────────────────────────────────────────
const LIFE_EVENTS = ["New Move", "Car Purchase", "Deed Transfer", "Apt Listing", "Policy Renewal", "New Homeowner"];
const POLICY_NEEDS = ["Auto", "Home", "Renters", "Bundle", "Life"];
const LEAD_SOURCES = ["FB Marketplace", "Craigslist", "Deed Records", "Reddit", "Google My Business", "Smart City Ref"];
const CARRIERS_AUTO = ["Progressive", "GEICO", "Root", "National General", "Bristol West"];
const CARRIERS_HOME = ["Orion180", "Swyfft", "Sagesure", "Lemonade"];
const STATUSES = ["New", "Contacted", "Quoted", "Hot", "Closed", "Nurture"];
const FIRST = ["James","Maria","Carlos","Ashley","Devon","Patricia","Marcus","Sandra","Tyrone","Olivia","Rafael","Linda","Andre","Stephanie","Miguel","Brittany","Kevin","Jasmine","Derek","Vanessa"];
const LAST = ["Thompson","Rodriguez","Johnson","Martinez","Williams","Davis","Brown","Wilson","Anderson","Taylor","Garcia","Moore","Jackson","Lee","Harris","Clark","Lewis","Walker","Hall","Young"];

function rand(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function randInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

function generateLeads(count = 80) {
  return Array.from({ length: count }, (_, i) => {
    const policyNeed = rand(POLICY_NEEDS);
    const carriers = policyNeed === "Home" ? CARRIERS_HOME : policyNeed === "Renters" ? ["Lemonade", "Sagesure"] : CARRIERS_AUTO;
    const lifeEvent = rand(LIFE_EVENTS);
    const score = randInt(42, 99);
    const phone = `(${randInt(200,999)}) ${randInt(200,999)}-${String(randInt(1000,9999))}`;
    const zips = ["78701","78704","78745","78702","77001","77002","77494","77379"];
    const states = { "78":"TX", "77":"TX" };
    const zip = rand(zips);
    const st = zip.startsWith("78") || zip.startsWith("77") ? "TX" : "FL";
    const daysAgo = randInt(0, 14);
    const now = new Date();
    now.setDate(now.getDate() - daysAgo);
    return {
      id: `LD-${String(i + 1001).padStart(5,"0")}`,
      firstName: rand(FIRST),
      lastName: rand(LAST),
      phone,
      email: `${rand(FIRST).toLowerCase()}.${rand(LAST).toLowerCase()}@${rand(["gmail","yahoo","outlook"])}.com`,
      lifeEvent,
      policyNeed,
      source: rand(LEAD_SOURCES),
      zip,
      state: st,
      county: st === "TX" && zip.startsWith("78") ? "Travis County" : "Harris County",
      carriers: [rand(carriers), rand(carriers.filter((c,j)=>j>0))].filter((v,i,a)=>a.indexOf(v)===i),
      fitScore: score,
      tcpaOk: Math.random() > 0.12,
      dncOk: Math.random() > 0.08,
      sb942Ok: Math.random() > 0.05,
      status: rand(STATUSES),
      addedDate: now.toISOString(),
      daysAgo,
      propertyAge: randInt(1, 45),
      vehicleYear: randInt(2008, 2024),
    };
  });
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const STATUS_COLORS = {
  New: { bg: "#1a2a1a", text: "#4ade80", border: "#166534" },
  Contacted: { bg: "#1a1f2a", text: "#60a5fa", border: "#1d4ed8" },
  Quoted: { bg: "#2a1f0a", text: "#fbbf24", border: "#92400e" },
  Hot: { bg: "#2a0f0f", text: "#f87171", border: "#991b1b" },
  Closed: { bg: "#E05A1A22", text: "#E05A1A", border: "#E05A1A" },
  Nurture: { bg: "#1a1a2a", text: "#a78bfa", border: "#5b21b6" },
};

const EVENT_COLORS = {
  "New Move": "#3b82f6",
  "Car Purchase": "#10b981",
  "Deed Transfer": "#f59e0b",
  "Apt Listing": "#8b5cf6",
  "Policy Renewal": "#E05A1A",
  "New Homeowner": "#06b6d4",
};

const POLICY_COLORS = {
  Auto: "#3b82f6",
  Home: "#f59e0b",
  Renters: "#8b5cf6",
  Bundle: "#E05A1A",
  Life: "#10b981",
};

function ScoreBadge({ score }) {
  const color = score >= 80 ? "#4ade80" : score >= 65 ? "#fbbf24" : "#f87171";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, height: 4, background: "#1e1e1e", borderRadius: 2, minWidth: 48 }}>
        <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: 2, transition: "width .3s" }} />
      </div>
      <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color, minWidth: 26 }}>{score}</span>
    </div>
  );
}

function ComplianceDots({ tcpa, dnc, sb942 }) {
  const dot = (ok, label) => (
    <div key={label} title={`${label}: ${ok ? "OK" : "FAIL"}`} style={{
      width: 7, height: 7, borderRadius: "50%",
      background: ok ? "#4ade80" : "#ef4444",
      boxShadow: ok ? "0 0 4px #4ade8088" : "0 0 4px #ef444488",
    }} />
  );
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
      {dot(tcpa, "TCPA")}
      {dot(dnc, "DNC")}
      {dot(sb942, "SB942")}
    </div>
  );
}

function Pill({ label, color, small }) {
  return (
    <span style={{
      display: "inline-block",
      padding: small ? "1px 7px" : "2px 9px",
      borderRadius: 4,
      fontSize: small ? 10 : 11,
      fontWeight: 600,
      letterSpacing: "0.03em",
      background: `${color}18`,
      color,
      border: `1px solid ${color}40`,
      whiteSpace: "nowrap",
    }}>{label}</span>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function LeadBrowser({ apiBase = "" }) {
  const [allLeads] = useState(() => generateLeads(80));
  const [selected, setSelected] = useState(new Set());
  const [activeLeadId, setActiveLeadId] = useState(null);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({
    lifeEvents: [],
    policyNeeds: [],
    sources: [],
    statuses: [],
    minScore: 0,
    complianceOnly: false,
  });
  const [sortKey, setSortKey] = useState("fitScore");
  const [sortDir, setSortDir] = useState("desc");
  const [page, setPage] = useState(0);
  const PER_PAGE = 15;

  const activeLead = allLeads.find(l => l.id === activeLeadId);

  const toggleFilter = useCallback((key, val) => {
    setFilters(f => {
      const arr = f[key];
      return { ...f, [key]: arr.includes(val) ? arr.filter(x => x !== val) : [...arr, val] };
    });
    setPage(0);
  }, []);

  const filtered = allLeads.filter(l => {
    if (search && !`${l.firstName} ${l.lastName} ${l.zip} ${l.phone} ${l.email}`.toLowerCase().includes(search.toLowerCase())) return false;
    if (filters.lifeEvents.length && !filters.lifeEvents.includes(l.lifeEvent)) return false;
    if (filters.policyNeeds.length && !filters.policyNeeds.includes(l.policyNeed)) return false;
    if (filters.sources.length && !filters.sources.includes(l.source)) return false;
    if (filters.statuses.length && !filters.statuses.includes(l.status)) return false;
    if (l.fitScore < filters.minScore) return false;
    if (filters.complianceOnly && (!l.tcpaOk || !l.dncOk || !l.sb942Ok)) return false;
    return true;
  }).sort((a, b) => {
    const mult = sortDir === "asc" ? 1 : -1;
    if (sortKey === "name") return mult * `${a.lastName}${a.firstName}`.localeCompare(`${b.lastName}${b.firstName}`);
    if (sortKey === "fitScore") return mult * (a.fitScore - b.fitScore);
    if (sortKey === "addedDate") return mult * (new Date(a.addedDate) - new Date(b.addedDate));
    return 0;
  });

  const paged = filtered.slice(page * PER_PAGE, (page + 1) * PER_PAGE);
  const totalPages = Math.ceil(filtered.length / PER_PAGE);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const toggleSelect = (id) => setSelected(s => {
    const n = new Set(s);
    n.has(id) ? n.delete(id) : n.add(id);
    return n;
  });

  const selectAll = () => setSelected(new Set(paged.map(l => l.id)));
  const clearAll = () => setSelected(new Set());

  const activeFiltersCount = filters.lifeEvents.length + filters.policyNeeds.length + filters.sources.length + filters.statuses.length + (filters.minScore > 0 ? 1 : 0) + (filters.complianceOnly ? 1 : 0);

  return (
    <div style={{ display: "flex", height: "100vh", background: "#0C0C0C", color: "#e5e5e5", fontFamily: "'DM Sans', sans-serif", fontSize: 13, overflow: "hidden" }}>

      {/* ── Sidebar ── */}
      <div style={{ width: 220, flexShrink: 0, borderRight: "1px solid #1e1e1e", padding: "16px 0", overflowY: "auto", display: "flex", flexDirection: "column", gap: 0 }}>
        {/* Logo */}
        <div style={{ padding: "0 16px 16px", borderBottom: "1px solid #1e1e1e" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 28, height: 28, background: "#E05A1A", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, fontWeight: 700, color: "#fff" }}>L</span>
            </div>
            <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: "0.02em" }}>LeadOS</span>
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: "#555", fontFamily: "'IBM Plex Mono', monospace" }}>
            {filtered.length} leads · {activeFiltersCount > 0 && <span style={{ color: "#E05A1A" }}>{activeFiltersCount} filter{activeFiltersCount > 1 ? "s" : ""}</span>}
            {activeFiltersCount === 0 && <span>no filters</span>}
          </div>
        </div>

        {/* Nav items */}
        {[
          { icon: "◈", label: "Lead Browser", active: true },
          { icon: "◎", label: "Heartbeat", active: false },
          { icon: "◷", label: "Warm Transfer", active: false },
          { icon: "◆", label: "Compliance Guard", active: false },
          { icon: "◉", label: "Carrier Scorer", active: false },
          { icon: "◌", label: "Campaigns", active: false },
        ].map(n => (
          <div key={n.label} style={{
            display: "flex", alignItems: "center", gap: 10, padding: "9px 16px",
            background: n.active ? "#E05A1A14" : "transparent",
            borderLeft: n.active ? "2px solid #E05A1A" : "2px solid transparent",
            cursor: "pointer", color: n.active ? "#E05A1A" : "#555",
            fontSize: 13,
          }}>
            <span style={{ fontSize: 14 }}>{n.icon}</span>
            <span>{n.label}</span>
          </div>
        ))}

        {/* Divider */}
        <div style={{ borderTop: "1px solid #1e1e1e", margin: "12px 0" }} />

        {/* Filters */}
        <div style={{ padding: "0 12px", display: "flex", flexDirection: "column", gap: 16 }}>

          <FilterSection label="Life Event" items={LIFE_EVENTS} active={filters.lifeEvents} onToggle={v => toggleFilter("lifeEvents", v)} colorMap={EVENT_COLORS} />
          <FilterSection label="Policy Need" items={POLICY_NEEDS} active={filters.policyNeeds} onToggle={v => toggleFilter("policyNeeds", v)} colorMap={POLICY_COLORS} />
          <FilterSection label="Source" items={LEAD_SOURCES} active={filters.sources} onToggle={v => toggleFilter("sources", v)} />
          <FilterSection label="Status" items={STATUSES} active={filters.statuses} onToggle={v => toggleFilter("statuses", v)} colorMap={STATUS_COLORS} isStatus />

          {/* Min Score */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "#444", textTransform: "uppercase", marginBottom: 8 }}>Min Fit Score</div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="range" min={0} max={90} step={5} value={filters.minScore}
                onChange={e => { setFilters(f => ({ ...f, minScore: +e.target.value })); setPage(0); }}
                style={{ flex: 1, accentColor: "#E05A1A", height: 2 }} />
              <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#E05A1A", minWidth: 24 }}>{filters.minScore}</span>
            </div>
          </div>

          {/* Compliance only */}
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input type="checkbox" checked={filters.complianceOnly}
              onChange={e => { setFilters(f => ({ ...f, complianceOnly: e.target.checked })); setPage(0); }}
              style={{ accentColor: "#E05A1A", width: 13, height: 13 }} />
            <span style={{ fontSize: 12, color: "#888" }}>Compliance clean only</span>
          </label>

          {activeFiltersCount > 0 && (
            <button onClick={() => { setFilters({ lifeEvents: [], policyNeeds: [], sources: [], statuses: [], minScore: 0, complianceOnly: false }); setPage(0); }}
              style={{ background: "#1a1a1a", border: "1px solid #333", borderRadius: 6, padding: "6px 0", color: "#888", fontSize: 12, cursor: "pointer" }}>
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* ── Main ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Top bar */}
        <div style={{ padding: "12px 20px", borderBottom: "1px solid #1e1e1e", display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
          <div style={{ flex: 1, position: "relative" }}>
            <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#444", fontSize: 13 }}>⌕</span>
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
              placeholder="Search name, ZIP, phone, email..."
              style={{ width: "100%", background: "#111", border: "1px solid #222", borderRadius: 8, padding: "8px 12px 8px 30px", color: "#e5e5e5", fontSize: 13, outline: "none", boxSizing: "border-box" }}
            />
          </div>
          {selected.size > 0 && (
            <>
              <ActionBtn onClick={() => {}} label={`Dial ${selected.size}`} color="#3b82f6" />
              <ActionBtn onClick={() => {}} label="Bulk email" color="#10b981" />
              <ActionBtn onClick={() => {}} label="Export CSV" color="#888" />
              <ActionBtn onClick={clearAll} label="✕" color="#555" />
            </>
          )}
          <ActionBtn onClick={() => {}} label="+ Add Lead" color="#E05A1A" primary />
        </div>

        {/* Column headers */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "36px 28px 180px 110px 90px 90px 110px 80px 70px 80px 100px",
          padding: "8px 16px",
          borderBottom: "1px solid #1e1e1e",
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.08em",
          color: "#444",
          textTransform: "uppercase",
          flexShrink: 0,
        }}>
          <div><input type="checkbox" style={{ accentColor: "#E05A1A" }} onChange={e => e.target.checked ? selectAll() : clearAll()} /></div>
          <div />
          <SortHeader label="Lead" sortKey="name" current={sortKey} dir={sortDir} onSort={toggleSort} />
          <div>Life Event</div>
          <div>Policy</div>
          <div>Source</div>
          <div>Location</div>
          <SortHeader label="Score" sortKey="fitScore" current={sortKey} dir={sortDir} onSort={toggleSort} />
          <div>Comply</div>
          <div>Status</div>
          <SortHeader label="Added" sortKey="addedDate" current={sortKey} dir={sortDir} onSort={toggleSort} />
        </div>

        {/* Rows */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {paged.map((lead, idx) => (
            <LeadRow
              key={lead.id}
              lead={lead}
              selected={selected.has(lead.id)}
              active={lead.id === activeLeadId}
              onSelect={() => toggleSelect(lead.id)}
              onClick={() => setActiveLeadId(id => id === lead.id ? null : lead.id)}
              idx={idx}
            />
          ))}
          {paged.length === 0 && (
            <div style={{ textAlign: "center", padding: "60px 20px", color: "#444" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>◌</div>
              <div>No leads match your filters</div>
            </div>
          )}
        </div>

        {/* Pagination */}
        <div style={{ padding: "10px 20px", borderTop: "1px solid #1e1e1e", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0, fontSize: 12, color: "#555" }}>
          <span style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
            {page * PER_PAGE + 1}–{Math.min((page + 1) * PER_PAGE, filtered.length)} of {filtered.length}
          </span>
          <div style={{ display: "flex", gap: 6 }}>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i).map(i => (
              <button key={i} onClick={() => setPage(i)} style={{
                width: 28, height: 28, borderRadius: 6, border: "1px solid",
                borderColor: i === page ? "#E05A1A" : "#1e1e1e",
                background: i === page ? "#E05A1A18" : "transparent",
                color: i === page ? "#E05A1A" : "#555",
                cursor: "pointer", fontSize: 12,
              }}>{i + 1}</button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <PagBtn label="←" disabled={page === 0} onClick={() => setPage(p => p - 1)} />
            <PagBtn label="→" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} />
          </div>
        </div>
      </div>

      {/* ── Detail Drawer ── */}
      {activeLead && (
        <LeadDrawer lead={activeLead} onClose={() => setActiveLeadId(null)} />
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function FilterSection({ label, items, active, onToggle, colorMap, isStatus }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "#444", textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {items.map(item => {
          const isActive = active.includes(item);
          const color = colorMap ? (isStatus ? colorMap[item]?.text : colorMap[item]) : "#888";
          return (
            <button key={item} onClick={() => onToggle(item)} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              background: isActive ? `${color}14` : "transparent",
              border: `1px solid ${isActive ? `${color}44` : "transparent"}`,
              borderRadius: 5, padding: "4px 8px", cursor: "pointer",
              color: isActive ? color : "#666", fontSize: 11, textAlign: "left",
            }}>
              <span>{item}</span>
              {isActive && <span style={{ fontSize: 9, opacity: .7 }}>✓</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SortHeader({ label, sortKey, current, dir, onSort }) {
  const active = current === sortKey;
  return (
    <div onClick={() => onSort(sortKey)} style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 3, userSelect: "none", color: active ? "#E05A1A" : "inherit" }}>
      {label} {active ? (dir === "desc" ? "↓" : "↑") : ""}
    </div>
  );
}

function ActionBtn({ onClick, label, color, primary }) {
  return (
    <button onClick={onClick} style={{
      padding: "7px 14px", borderRadius: 7, fontSize: 12, fontWeight: 500, cursor: "pointer",
      border: `1px solid ${primary ? "#E05A1A" : color + "44"}`,
      background: primary ? "#E05A1A" : "transparent",
      color: primary ? "#fff" : color,
      whiteSpace: "nowrap",
    }}>{label}</button>
  );
}

function PagBtn({ label, disabled, onClick }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      width: 28, height: 28, borderRadius: 6, border: "1px solid #1e1e1e",
      background: "transparent", color: disabled ? "#2a2a2a" : "#888",
      cursor: disabled ? "default" : "pointer", fontSize: 13,
    }}>{label}</button>
  );
}

function LeadRow({ lead, selected, active, onSelect, onClick, idx }) {
  const eventColor = EVENT_COLORS[lead.lifeEvent] || "#888";
  const policyColor = POLICY_COLORS[lead.policyNeed] || "#888";
  const statusStyle = STATUS_COLORS[lead.status] || { bg: "#1a1a1a", text: "#888", border: "#333" };
  const allClean = lead.tcpaOk && lead.dncOk && lead.sb942Ok;

  return (
    <div onClick={onClick} style={{
      display: "grid",
      gridTemplateColumns: "36px 28px 180px 110px 90px 90px 110px 80px 70px 80px 100px",
      padding: "8px 16px",
      borderBottom: "1px solid #0f0f0f",
      background: active ? "#E05A1A08" : selected ? "#ffffff04" : idx % 2 === 0 ? "transparent" : "#080808",
      borderLeft: active ? "2px solid #E05A1A" : "2px solid transparent",
      cursor: "pointer",
      transition: "background .1s",
      alignItems: "center",
    }}
    onMouseEnter={e => { if (!active) e.currentTarget.style.background = "#141414"; }}
    onMouseLeave={e => { if (!active) e.currentTarget.style.background = idx % 2 === 0 ? "transparent" : "#080808"; }}
    >
      {/* Checkbox */}
      <div onClick={e => { e.stopPropagation(); onSelect(); }}>
        <input type="checkbox" checked={selected} onChange={() => {}} style={{ accentColor: "#E05A1A", cursor: "pointer" }} />
      </div>

      {/* Compliance dot */}
      <div style={{ width: 7, height: 7, borderRadius: "50%", background: allClean ? "#4ade80" : "#ef4444", boxShadow: allClean ? "0 0 4px #4ade8066" : "0 0 4px #ef444466" }} />

      {/* Name / contact */}
      <div>
        <div style={{ fontWeight: 500, fontSize: 13 }}>{lead.firstName} {lead.lastName}</div>
        <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#555", marginTop: 1 }}>{lead.phone}</div>
      </div>

      {/* Life event */}
      <div><Pill label={lead.lifeEvent} color={eventColor} small /></div>

      {/* Policy */}
      <div><Pill label={lead.policyNeed} color={policyColor} small /></div>

      {/* Source */}
      <div style={{ fontSize: 11, color: "#555", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{lead.source}</div>

      {/* Location */}
      <div>
        <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#888" }}>{lead.zip} · {lead.state}</div>
        <div style={{ fontSize: 10, color: "#444", marginTop: 1 }}>{lead.county}</div>
      </div>

      {/* Score */}
      <ScoreBadge score={lead.fitScore} />

      {/* Compliance */}
      <ComplianceDots tcpa={lead.tcpaOk} dnc={lead.dncOk} sb942={lead.sb942Ok} />

      {/* Status */}
      <div>
        <span style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 10, fontWeight: 600, letterSpacing: "0.05em",
          padding: "2px 7px", borderRadius: 4,
          background: statusStyle.bg, color: statusStyle.text,
          border: `1px solid ${statusStyle.border}`,
        }}>{lead.status}</span>
      </div>

      {/* Added */}
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#444" }}>
        {lead.daysAgo === 0 ? "Today" : lead.daysAgo === 1 ? "Yesterday" : `${lead.daysAgo}d ago`}
      </div>
    </div>
  );
}

function LeadDrawer({ lead, onClose }) {
  const eventColor = EVENT_COLORS[lead.lifeEvent] || "#888";
  const policyColor = POLICY_COLORS[lead.policyNeed] || "#888";
  const statusStyle = STATUS_COLORS[lead.status] || { bg: "#1a1a1a", text: "#888", border: "#333" };
  const carriers = lead.policyNeed === "Home" ? CARRIERS_HOME : lead.policyNeed === "Renters" ? ["Lemonade", "Sagesure"] : CARRIERS_AUTO;

  return (
    <div style={{ width: 320, flexShrink: 0, borderLeft: "1px solid #1e1e1e", overflowY: "auto", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e1e1e", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 16 }}>{lead.firstName} {lead.lastName}</div>
          <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#555", marginTop: 3 }}>{lead.id}</div>
        </div>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#555", cursor: "pointer", fontSize: 18, padding: 0, lineHeight: 1 }}>×</button>
      </div>

      {/* Contact */}
      <Section title="Contact">
        <Field label="Phone" value={lead.phone} mono />
        <Field label="Email" value={lead.email} mono small />
        <Field label="ZIP" value={`${lead.zip} · ${lead.state}`} mono />
        <Field label="County" value={lead.county} />
      </Section>

      {/* Lead Intel */}
      <Section title="Lead Intel">
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
          <Pill label={lead.lifeEvent} color={eventColor} />
          <Pill label={lead.policyNeed} color={policyColor} />
        </div>
        <Field label="Source" value={lead.source} />
        <Field label="Added" value={lead.daysAgo === 0 ? "Today" : lead.daysAgo === 1 ? "Yesterday" : `${lead.daysAgo} days ago`} />
        {lead.vehicleYear && lead.policyNeed !== "Home" && <Field label="Vehicle year" value={String(lead.vehicleYear)} mono />}
        {lead.propertyAge && (lead.policyNeed === "Home" || lead.policyNeed === "Renters") && <Field label="Property age" value={`${lead.propertyAge} yrs`} mono />}
      </Section>

      {/* Carrier Fit */}
      <Section title="Carrier Fit Score">
        <div style={{ marginBottom: 10 }}>
          <ScoreBadge score={lead.fitScore} />
        </div>
        <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>Recommended carriers</div>
        {carriers.slice(0, 4).map((c, i) => {
          const score = Math.max(40, lead.fitScore - i * 8 + Math.floor(Math.random() * 6));
          return (
            <div key={c} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: "1px solid #111" }}>
              <span style={{ fontSize: 12 }}>{c}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 40, height: 3, background: "#1e1e1e", borderRadius: 2 }}>
                  <div style={{ width: `${score}%`, height: "100%", background: i === 0 ? "#E05A1A" : "#3b82f6", borderRadius: 2 }} />
                </div>
                <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: i === 0 ? "#E05A1A" : "#888", minWidth: 22 }}>{score}</span>
              </div>
            </div>
          );
        })}
      </Section>

      {/* Compliance */}
      <Section title="Compliance Status">
        {[
          { label: "TCPA", ok: lead.tcpaOk, note: "Telemarketing consent" },
          { label: "DNC Registry", ok: lead.dncOk, note: "Do Not Call check" },
          { label: "SB 942", ok: lead.sb942Ok, note: "CA insurance solicitation" },
        ].map(({ label, ok, note }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #111" }}>
            <div>
              <div style={{ fontSize: 12 }}>{label}</div>
              <div style={{ fontSize: 10, color: "#444" }}>{note}</div>
            </div>
            <span style={{ fontSize: 11, fontWeight: 600, color: ok ? "#4ade80" : "#ef4444", fontFamily: "'IBM Plex Mono', monospace" }}>{ok ? "PASS" : "FAIL"}</span>
          </div>
        ))}
      </Section>

      {/* Actions */}
      <div style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 8 }}>
        <button style={{ background: "#E05A1A", border: "none", borderRadius: 8, padding: "10px 0", color: "#fff", fontWeight: 600, fontSize: 13, cursor: "pointer" }}>
          ◎ Warm Transfer Now
        </button>
        <button style={{ background: "#111", border: "1px solid #222", borderRadius: 8, padding: "10px 0", color: "#888", fontSize: 13, cursor: "pointer" }}>
          ✉ Add to Sequence
        </button>
        <button style={{ background: "#111", border: "1px solid #222", borderRadius: 8, padding: "10px 0", color: "#888", fontSize: 13, cursor: "pointer" }}>
          ⊕ Push to EZLynx
        </button>
        <button style={{ background: "#111", border: "1px solid #222", borderRadius: 8, padding: "10px 0", color: "#888", fontSize: 13, cursor: "pointer" }}>
          ◉ Run Quote
        </button>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ padding: "14px 20px", borderBottom: "1px solid #1e1e1e" }}>
      <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "#444", textTransform: "uppercase", marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}

function Field({ label, value, mono, small }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "4px 0" }}>
      <span style={{ fontSize: 11, color: "#555" }}>{label}</span>
      <span style={{ fontFamily: mono ? "'IBM Plex Mono', monospace" : "inherit", fontSize: small ? 10 : 12, color: "#888", textAlign: "right", maxWidth: 180, wordBreak: "break-all" }}>{value}</span>
    </div>
  );
}
