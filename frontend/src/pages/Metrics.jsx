import { useEffect, useState } from "react";
import { apiFetch, authHeaders } from "../api";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Metrics() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch(`${API}/api/metrics`)
      .then(async (res) => {
        if (!res.ok) throw new Error("unavailable");
        setStats(await res.json());
      })
      .catch(() => setError("Metrics are unavailable."));
  }, []);

  async function downloadCsv() {
    const res = await fetch(`${API}/api/metrics/export.csv`, { headers: authHeaders() });
    if (!res.ok) {
      setError("CSV export failed.");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "leados-metrics.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  const cards = stats
    ? [
        ["Calls", stats.calls],
        ["Leads", stats.leads],
        ["Median response (sec)", stats.median_response_seconds ?? "—"],
        ["Consent rate", `${Math.round((stats.consent_rate || 0) * 100)}%`],
      ]
    : [];

  return (
    <div className="min-h-screen bg-[#F8F8F6] px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl text-[#1A1A1A]" style={{ fontFamily: "'Playfair Display', serif" }}>
          Metrics
        </h1>
        <button onClick={downloadCsv} className="px-4 py-2 text-sm rounded-[10px] border border-gray-200 bg-white">
          Download CSV
        </button>
      </div>
      {error && <p className="text-sm text-[#E24B4A] mb-4">{error}</p>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl">
        {cards.map(([label, value]) => (
          <div key={label} className="bg-white border border-gray-100 rounded-[10px] p-4">
            <div className="text-2xl font-semibold text-[#1A1A1A]">{value}</div>
            <div className="text-xs uppercase tracking-wide text-[#6B6B6B] mt-1">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
