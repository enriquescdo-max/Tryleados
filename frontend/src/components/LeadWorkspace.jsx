import { useState } from "react";
import { apiFetch } from "../api";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function slaLabel(lead) {
  if (!lead?.sla_started_at) return { elapsedMin: 0, late: false, missing: true };
  const started = new Date(lead.sla_started_at).getTime();
  const due = lead.sla_due_at ? new Date(lead.sla_due_at).getTime() : started + 5 * 60 * 1000;
  const elapsedMin = Math.max(0, Math.round((Date.now() - started) / 60000));
  const late = Date.now() > due && !lead.first_response_at;
  return { elapsedMin, late };
}

export default function LeadWorkspace({ lead, onClose }) {
  const [draft, setDraft] = useState(null);
  const [note, setNote] = useState("");
  if (!lead) return null;
  const sla = slaLabel(lead);
  const flags = lead.disqualifiers || [];

  async function createDraft() {
    const res = await apiFetch(`${API}/api/leads/${lead.id}/followups`, { method: "POST" });
    if (!res.ok) {
      setNote("Could not draft a follow-up.");
      return;
    }
    setDraft(await res.json());
    setNote("Draft only. Nothing was sent.");
  }

  async function approve() {
    const res = await apiFetch(`${API}/api/leads/${lead.id}/followups/${draft.id}/approve`, { method: "POST" });
    if (!res.ok) {
      setNote("Could not approve.");
      return;
    }
    setDraft(await res.json());
    setNote("Approved. This did not send the message. Copy it and send it yourself.");
  }

  return (
    <aside className="bg-white border border-gray-100 rounded-[10px] p-5 mb-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl text-[#1A1A1A]" style={{ fontFamily: "'Playfair Display', serif" }}>
            {lead.raw_name || "Lead"}
          </h2>
          <p className="text-sm text-[#6B6B6B]">
            {lead.line_of_business || lead.insurance_type || "—"} · {lead.language || "—"} · ZIP {lead.zip || lead.location || "—"}
          </p>
        </div>
        <button onClick={onClose} className="text-sm text-[#6B6B6B]">Close</button>
      </div>
      <p className="text-sm mt-3 text-[#1A1A1A]">{lead.transcript_summary || "No intake summary yet."}</p>
      <div className="flex flex-wrap gap-2 mt-3">
        {flags.length === 0 ? (
          <span className="text-xs px-2 py-1 rounded-full bg-[#E8F8F2] text-[#00A86B]">No disqualifiers</span>
        ) : (
          flags.map((flag) => (
            <span key={flag} className="text-xs px-2 py-1 rounded-full bg-red-50 text-[#E24B4A]">{flag}</span>
          ))
        )}
        <span className={`text-xs px-2 py-1 rounded-full ${sla.late ? "bg-red-50 text-[#E24B4A]" : "bg-gray-100 text-[#6B6B6B]"}`}>
          {sla.missing ? "No speed-to-lead timer" : sla.late ? `SLA missed · ${sla.elapsedMin} min` : `${sla.elapsedMin} min since intake`}
        </span>
      </div>
      <div className="mt-4">
        <button onClick={createDraft} className="px-3 py-2 text-sm rounded-[10px] bg-[#1A1A1A] text-white">
          Draft follow-up
        </button>
        {draft && (
          <div className="mt-3">
            <textarea readOnly value={draft.body} className="w-full text-sm border border-gray-200 rounded-[10px] p-3" rows={4} />
            <button onClick={approve} className="mt-2 px-3 py-2 text-sm rounded-[10px] border border-gray-200">
              Approve (does not send)
            </button>
          </div>
        )}
        {note && <p className="text-xs text-[#6B6B6B] mt-2">{note}</p>}
      </div>
    </aside>
  );
}
