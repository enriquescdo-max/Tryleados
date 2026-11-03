import { useEffect, useState } from "react";
import { apiFetch } from "../api";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Callbacks() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    const res = await apiFetch(`${API}/api/callbacks`);
    if (!res.ok) {
      setError("Could not load the callback queue.");
      return;
    }
    const data = await res.json();
    setRows(data.callbacks || []);
    setError("");
  }

  useEffect(() => {
    load();
  }, []);

  async function markCalled(id) {
    const res = await apiFetch(`${API}/api/callbacks/${id}/complete`, { method: "POST" });
    if (res.ok) load();
  }

  return (
    <div className="min-h-screen bg-[#F8F8F6] px-6 py-8">
      <h1 className="text-3xl text-[#1A1A1A] mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
        Callbacks
      </h1>
      <p className="text-sm text-[#6B6B6B] mb-6 max-w-xl">
        These people agreed the licensed agent may call them back. The AI does not dial. When you have called them, mark it here.
      </p>
      {error && <p className="text-sm text-[#E24B4A] mb-4">{error}</p>}
      {rows.length === 0 ? (
        <p className="text-sm text-[#6B6B6B]">No consented callbacks waiting.</p>
      ) : (
        <ul className="space-y-3 max-w-2xl">
          {rows.map((lead) => (
            <li key={lead.id} className="bg-white border border-gray-100 rounded-[10px] p-4 flex items-start justify-between gap-4">
              <div>
                <div className="font-medium text-[#1A1A1A]">{lead.raw_name || "Unknown"}</div>
                <div className="text-sm text-[#6B6B6B]">{lead.phone || lead.raw_contact} · {lead.line_of_business || lead.insurance_type} · {lead.zip}</div>
                <p className="text-sm mt-2 text-[#1A1A1A]">{lead.transcript_summary}</p>
              </div>
              <button
                onClick={() => markCalled(lead.id)}
                className="shrink-0 px-3 py-2 text-sm rounded-[10px] bg-[#00A86B] text-white"
              >
                I called them
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
