import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast, { Toaster } from "react-hot-toast";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const URGENCY_COLORS = {
  hot: { bg: "bg-red-50", badge: "bg-[#E24B4A] text-white", label: "HOT" },
  warm: { bg: "bg-amber-50", badge: "bg-[#BA7517] text-white", label: "WARM" },
  cool: { bg: "", badge: "bg-[#888780] text-white", label: "COOL" },
};

const TYPE_ICONS = {
  auto: "🚗",
  renters: "🏠",
  bundle: "📦",
  home: "🏡",
};

function getUrgencyTier(score) {
  if (score >= 8) return "hot";
  if (score >= 5) return "warm";
  return "cool";
}

function UrgencyBadge({ score }) {
  const tier = getUrgencyTier(score);
  const { badge, label } = URGENCY_COLORS[tier];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${badge}`}>
      {score} {label}
    </span>
  );
}

function StatsBar({ stats, onScrape, scraping }) {
  return (
    <div className="flex flex-wrap items-center gap-4 px-6 py-4 bg-white border-b border-gray-100">
      <div className="flex items-center gap-2 mr-auto">
        <span className="font-heading text-xl font-semibold text-[#1A1A1A]" style={{ fontFamily: "'Playfair Display', serif" }}>
          LeadOS
        </span>
        <span className="text-xs text-[#6B6B6B] bg-[#E8F8F2] text-[#00A86B] px-2 py-0.5 rounded-full font-medium">
          Agent Dashboard
        </span>
      </div>

      <div className="flex gap-4 text-sm">
        <StatChip label="Total" value={stats?.total ?? "—"} />
        <StatChip label="Hot" value={stats?.hot_leads ?? "—"} color="text-[#E24B4A]" />
        <StatChip label="New" value={stats?.new ?? "—"} color="text-[#00A86B]" />
        <StatChip label="Quoted" value={stats?.quoted ?? "—"} />
        <StatChip label="Closed" value={stats?.closed ?? "—"} color="text-[#00A86B]" />
      </div>

      <motion.button
        onClick={onScrape}
        disabled={scraping}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className="flex items-center gap-2 px-4 py-2 rounded-[10px] bg-[#00A86B] text-white text-sm font-semibold shadow-sm hover:bg-[#009960] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        <span className={`w-2 h-2 rounded-full ${scraping ? "bg-yellow-300 animate-pulse" : "bg-green-200"}`} />
        {scraping ? "Running..." : "Run New Scrape"}
      </motion.button>
    </div>
  );
}

function StatChip({ label, value, color = "text-[#1A1A1A]" }) {
  return (
    <div className="text-center">
      <div className={`font-bold text-base ${color}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-[#6B6B6B]">{label}</div>
    </div>
  );
}

function FilterBar({ statusFilter, setStatusFilter, typeFilter, setTypeFilter }) {
  const statuses = ["all", "new", "contacted", "quoted", "closed"];
  const types = ["all", "auto", "renters", "bundle", "home"];

  return (
    <div className="flex flex-wrap items-center gap-4 px-6 py-3 bg-white border-b border-gray-100">
      <div className="flex gap-1">
        {statuses.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium capitalize transition-all ${
              statusFilter === s
                ? "bg-[#1A1A1A] text-white"
                : "text-[#6B6B6B] hover:bg-gray-100"
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="w-px h-4 bg-gray-200" />
      <div className="flex gap-1">
        {types.map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1 rounded-full text-xs font-medium capitalize transition-all ${
              typeFilter === t
                ? "bg-[#00A86B] text-white"
                : "text-[#6B6B6B] hover:bg-gray-100"
            }`}
          >
            {t !== "all" ? `${TYPE_ICONS[t]} ` : ""}
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}

function LeadRow({ lead, onStatusChange }) {
  const tier = getUrgencyTier(lead.urgency_score);
  const rowBg = tier === "hot" ? "hover:bg-red-50/40" : tier === "warm" ? "hover:bg-amber-50/40" : "hover:bg-[#F0FAF5]/60";

  function copyMessage() {
    navigator.clipboard.writeText(lead.outreach_message || "");
    toast.success("Message copied!", { duration: 2000, icon: "📋" });
  }

  return (
    <motion.tr
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={`border-b border-gray-50 transition-colors ${rowBg}`}
    >
      {/* Score */}
      <td className="px-4 py-3 w-24">
        <UrgencyBadge score={lead.urgency_score} />
      </td>

      {/* Name + Source */}
      <td className="px-4 py-3">
        <div className="font-medium text-sm text-[#1A1A1A]">{lead.raw_name || "Unknown"}</div>
        <div className="text-xs text-[#6B6B6B] mt-0.5">{lead.source?.replace("_", " ")}</div>
      </td>

      {/* Type */}
      <td className="px-4 py-3 w-28">
        <span className="inline-flex items-center gap-1 text-xs font-medium text-[#1A1A1A] bg-gray-100 px-2 py-1 rounded-full capitalize">
          {TYPE_ICONS[lead.insurance_type] || "📄"} {lead.insurance_type}
        </span>
      </td>

      {/* Carrier */}
      <td className="px-4 py-3 w-36">
        <span className="text-xs font-medium text-[#00A86B]">{lead.carrier_recommendation}</span>
      </td>

      {/* Outreach Script */}
      <td className="px-4 py-3 max-w-xs">
        <div className="flex items-start gap-2">
          <p className="text-xs text-[#6B6B6B] leading-relaxed line-clamp-2 flex-1">
            {lead.outreach_message || "—"}
          </p>
          {lead.outreach_message && (
            <button
              onClick={copyMessage}
              className="shrink-0 text-xs text-[#00A86B] hover:text-[#009960] font-medium transition-colors"
              title="Copy message"
            >
              📋
            </button>
          )}
        </div>
      </td>

      {/* Status */}
      <td className="px-4 py-3 w-36">
        <select
          value={lead.status}
          onChange={(e) => onStatusChange(lead.id, e.target.value)}
          className="text-xs border border-gray-200 rounded-[8px] px-2 py-1.5 bg-white text-[#1A1A1A] focus:outline-none focus:ring-1 focus:ring-[#00A86B] cursor-pointer"
        >
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="quoted">Quoted</option>
          <option value="closed">Closed</option>
          <option value="not_interested">Not Interested</option>
        </select>
      </td>
    </motion.tr>
  );
}

export default function Dashboard() {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [scraping, setScraping] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLeads = useCallback(async () => {
    try {
      const url = new URL(`${API}/api/leads`);
      if (statusFilter !== "all") url.searchParams.set("status", statusFilter);
      const res = await fetch(url);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setLeads(data.leads || []);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/leads/stats`);
      if (!res.ok) return;
      setStats(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [fetchLeads, fetchStats]);

  async function handleScrape() {
    setScraping(true);
    try {
      const res = await fetch(`${API}/api/leads/run-scrape`, { method: "POST" });
      const data = await res.json();
      toast.success(data.message || "Scrape started!", { duration: 4000 });
      setTimeout(() => {
        fetchLeads();
        fetchStats();
        setScraping(false);
      }, 120000);
    } catch (e) {
      toast.error("Failed to start scrape");
      setScraping(false);
    }
  }

  async function handleStatusChange(leadId, newStatus) {
    try {
      const res = await fetch(
        `${API}/api/leads/${leadId}/status?status=${newStatus}`,
        { method: "PATCH" }
      );
      if (!res.ok) throw new Error();
      setLeads((prev) =>
        prev.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l))
      );
      fetchStats();
      toast.success("Status updated", { duration: 1500 });
    } catch {
      toast.error("Failed to update status");
    }
  }

  const filteredLeads = leads.filter((l) => {
    if (typeFilter !== "all" && l.insurance_type !== typeFilter) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#F8F8F6]">
      <Toaster position="top-right" />

      <StatsBar stats={stats} onScrape={handleScrape} scraping={scraping} />
      <FilterBar
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        typeFilter={typeFilter}
        setTypeFilter={setTypeFilter}
      />

      <div className="px-6 py-4">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-100 rounded-[10px] text-sm text-red-600">
            Could not reach API: {error}. Make sure the backend is running.
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-24 text-[#6B6B6B]">
            <span className="animate-spin mr-2">⟳</span> Loading leads...
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <p className="text-4xl mb-3">🔍</p>
            <p className="text-[#1A1A1A] font-medium">No leads yet</p>
            <p className="text-sm text-[#6B6B6B] mt-1">
              Hit "Run New Scrape" to pull live leads from Facebook, Craigslist, and Reddit.
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-[10px] border border-gray-100 overflow-hidden shadow-sm">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-100 bg-[#F8F8F6]">
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[#6B6B6B] w-24">Score</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Name / Source</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[#6B6B6B] w-28">Type</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[#6B6B6B] w-36">Carrier</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Outreach Script</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[#6B6B6B] w-36">Status</th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {filteredLeads.map((lead) => (
                    <LeadRow
                      key={lead.id}
                      lead={lead}
                      onStatusChange={handleStatusChange}
                    />
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
            <div className="px-4 py-2 text-xs text-[#6B6B6B] border-t border-gray-50">
              {filteredLeads.length} lead{filteredLeads.length !== 1 ? "s" : ""} — sorted by urgency
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
