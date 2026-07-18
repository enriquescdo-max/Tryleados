/**
 * LeadOS Lead Database Browser
 * Live data from LeadScout (OpenStreetMap discovery + email enrichment)
 * Brand: #0C0C0C bg · #E05A1A orange · IBM Plex Mono data values
 */

import { useState, useEffect, useMemo } from "react";

const LEADSCOUT_API =
  import.meta.env.VITE_LEADSCOUT_URL || "https://leadscout-production-b570.up.railway.app";

const STATUS_COLORS = {
  new: { text: "#4ade80", border: "#166534" },
  contacted: { text: "#60a5fa", border: "#1d4ed8" },
  won: { text: "#E05A1A", border: "#E05A1A" },
  lost: { text: "#9ca3af", border: "#4b5563" },
};

const CATEGORY_COLORS = {
  insurance: "#E05A1A",
  restaurant: "#10b981",
  dentist: "#3b82f6",
  lawyer: "#f59e0b",
  real_estate: "#8b5cf6",
};

function Pill({ label, color }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 9px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.03em",
        background: `${color}18`,
        color,
        border: `1px solid ${color}40`,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}

const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export default function LeadBrowser() {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [emailOnly, setEmailOnly] = useState(false);

  useEffect(() => {
    fetch(`${LEADSCOUT_API}/api/leads`)
      .then((res) => {
        if (!res.ok) throw new Error(`LeadScout API error: ${res.status}`);
        return res.json();
      })
      .then(setLeads)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(
    () => [...new Set(leads.map((l) => l.category))].sort(),
    [leads]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return leads.filter((l) => {
      if (statusFilter !== "all" && l.status !== statusFilter) return false;
      if (categoryFilter !== "all" && l.category !== categoryFilter) return false;
      if (emailOnly && !l.email) return false;
      if (!q) return true;
      return [l.name, l.address, l.city, l.phone, l.email, l.website]
        .filter(Boolean)
        .some((v) => v.toLowerCase().includes(q));
    });
  }, [leads, search, statusFilter, categoryFilter, emailOnly]);

  const withEmail = leads.filter((l) => l.email).length;

  const inputStyle = {
    background: "#161616",
    border: "1px solid #2a2a2a",
    borderRadius: 6,
    color: "#e5e5e5",
    padding: "8px 12px",
    fontSize: 13,
    outline: "none",
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0C0C0C", color: "#e5e5e5", padding: "32px 24px" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 4 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#fff", margin: 0 }}>Lead Database</h1>
          <span style={{ ...mono, fontSize: 12, color: "#E05A1A" }}>LIVE · LeadScout</span>
        </div>
        <p style={{ fontSize: 13, color: "#8a8a8a", marginBottom: 24 }}>
          Real businesses discovered via OpenStreetMap, emails scraped from their own sites.
          Run new searches in{" "}
          <a href={LEADSCOUT_API} target="_blank" rel="noopener noreferrer" style={{ color: "#E05A1A" }}>
            LeadScout
          </a>
          .
        </p>

        {/* Stats */}
        <div style={{ display: "flex", gap: 24, marginBottom: 24, flexWrap: "wrap" }}>
          {[
            ["Total leads", leads.length],
            ["With direct email", withEmail],
            ["Showing", filtered.length],
          ].map(([label, value]) => (
            <div key={label} style={{ background: "#161616", border: "1px solid #2a2a2a", borderRadius: 8, padding: "12px 20px" }}>
              <div style={{ ...mono, fontSize: 20, color: "#fff" }}>{value}</div>
              <div style={{ fontSize: 11, color: "#8a8a8a", marginTop: 2 }}>{label}</div>
            </div>
          ))}
          <a
            href={`${LEADSCOUT_API}/api/leads/export.csv`}
            style={{
              marginLeft: "auto",
              alignSelf: "center",
              padding: "10px 18px",
              background: "#E05A1A",
              color: "#fff",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            Export CSV ↓
          </a>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
          <input
            style={{ ...inputStyle, flex: 1, minWidth: 220 }}
            placeholder="Search name, city, phone, email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select style={inputStyle} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">All statuses</option>
            {Object.keys(STATUS_COLORS).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select style={inputStyle} value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="all">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c.replace("_", " ")}</option>
            ))}
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#8a8a8a", cursor: "pointer" }}>
            <input type="checkbox" checked={emailOnly} onChange={(e) => setEmailOnly(e.target.checked)} />
            Email only
          </label>
        </div>

        {/* Table */}
        {loading ? (
          <p style={{ ...mono, color: "#8a8a8a", padding: 40, textAlign: "center" }}>Loading live leads…</p>
        ) : error ? (
          <p style={{ ...mono, color: "#f87171", padding: 40, textAlign: "center" }}>{error}</p>
        ) : filtered.length === 0 ? (
          <p style={{ color: "#8a8a8a", padding: 40, textAlign: "center" }}>
            {leads.length === 0
              ? "No leads yet — open LeadScout and run your first city search."
              : "No leads match the current filters."}
          </p>
        ) : (
          <div style={{ overflowX: "auto", border: "1px solid #2a2a2a", borderRadius: 10 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#161616" }}>
                  {["Business", "Category", "City", "Phone", "Email", "Website", "Status"].map((h) => (
                    <th key={h} style={{ textAlign: "left", padding: "10px 14px", color: "#8a8a8a", fontSize: 11, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase", borderBottom: "1px solid #2a2a2a", whiteSpace: "nowrap" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => {
                  const sc = STATUS_COLORS[l.status] ?? STATUS_COLORS.new;
                  return (
                    <tr key={l.id} style={{ borderBottom: "1px solid #1e1e1e" }}>
                      <td style={{ padding: "10px 14px", color: "#fff", fontWeight: 500 }}>
                        {l.name}
                        <div style={{ fontSize: 11, color: "#6a6a6a", marginTop: 2 }}>{l.address || ""}</div>
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <Pill label={l.category.replace("_", " ")} color={CATEGORY_COLORS[l.category] ?? "#8a8a8a"} />
                      </td>
                      <td style={{ padding: "10px 14px", color: "#c5c5c5" }}>{l.city}</td>
                      <td style={{ ...mono, padding: "10px 14px", fontSize: 12, color: "#c5c5c5", whiteSpace: "nowrap" }}>{l.phone || "—"}</td>
                      <td style={{ ...mono, padding: "10px 14px", fontSize: 12, whiteSpace: "nowrap" }}>
                        {l.email ? <span style={{ color: "#4ade80" }}>{l.email}</span> : <span style={{ color: "#4a4a4a" }}>—</span>}
                      </td>
                      <td style={{ padding: "10px 14px", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {l.website ? (
                          <a
                            href={l.website.startsWith("http") ? l.website : `https://${l.website}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: "#E05A1A", textDecoration: "none", fontSize: 12 }}
                          >
                            {l.website.replace(/^https?:\/\//, "")}
                          </a>
                        ) : (
                          <span style={{ color: "#4a4a4a" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <Pill label={l.status} color={sc.text} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
