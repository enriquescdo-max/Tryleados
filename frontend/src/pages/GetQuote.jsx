import { useState } from "react";

const LEADSCOUT_API =
  import.meta.env.VITE_LEADSCOUT_URL || "https://leadscout-production-b570.up.railway.app";

const COVERAGE = [
  { id: "home", label: "🏠 Home" },
  { id: "auto", label: "🚗 Auto" },
  { id: "renters", label: "🔑 Renters" },
  { id: "pet", label: "🐾 Pet" },
  { id: "life", label: "❤️ Life" },
  { id: "bundle", label: "📦 Bundle" },
];

const inputCls =
  "w-full px-4 py-3 rounded-lg border border-gray-200 bg-white text-[#1A1A1A] text-sm focus:outline-none focus:ring-2 focus:ring-[#00A86B] focus:border-transparent";

export default function GetQuote() {
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    zip: "",
    current_insurer: "",
    note: "",
  });
  const [types, setTypes] = useState([]);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function toggleType(id) {
    setTypes((t) => (t.includes(id) ? t.filter((x) => x !== id) : [...t, id]));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch(`${LEADSCOUT_API}/api/consumer-leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, insurance_types: types, tcpa_consent: consent }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || "Something went wrong");
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="max-w-xl mx-auto px-6 py-24 text-center">
        <div className="text-5xl mb-6">✅</div>
        <h1 className="text-3xl font-bold text-[#1A1A1A] mb-3">Request received!</h1>
        <p className="text-[#6B6B6B]">
          A licensed agent will compare rates across 100+ carriers and reach out with your
          personalized quote — usually within one business day.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-6 py-16">
      <div className="text-center mb-10">
        <div className="inline-block px-3 py-1 mb-4 text-xs font-semibold rounded-full bg-[#E8F8F2] text-[#00A86B]">
          Free · No obligation
        </div>
        <h1 className="text-4xl font-bold text-[#1A1A1A] mb-3">Get your quote</h1>
        <p className="text-[#6B6B6B]">
          One quick form. A licensed agent compares 100+ carriers and finds your best rate.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <input required aria-label="First name" placeholder="First name *" className={inputCls} value={form.first_name} onChange={set("first_name")} />
          <input aria-label="Last name" placeholder="Last name" className={inputCls} value={form.last_name} onChange={set("last_name")} />
        </div>
        <input required type="email" aria-label="Email" placeholder="Email *" className={inputCls} value={form.email} onChange={set("email")} />
        <div className="grid grid-cols-2 gap-4">
          <input required type="tel" aria-label="Phone" placeholder="Phone *" className={inputCls} value={form.phone} onChange={set("phone")} />
          <input required aria-label="Zip code" placeholder="Zip code *" maxLength={5} pattern="\d{5}" className={inputCls} value={form.zip} onChange={set("zip")} />
        </div>

        <div>
          <p className="text-sm font-medium text-[#1A1A1A] mb-2">What coverage do you need? *</p>
          <div className="grid grid-cols-3 gap-2">
            {COVERAGE.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => toggleType(c.id)}
                className={`px-3 py-3 rounded-lg border text-sm font-medium transition-all ${
                  types.includes(c.id)
                    ? "border-[#00A86B] bg-[#E8F8F2] text-[#00A86B]"
                    : "border-gray-200 bg-white text-[#6B6B6B] hover:border-gray-300"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        <input aria-label="Current insurer" placeholder="Current insurer (optional)" className={inputCls} value={form.current_insurer} onChange={set("current_insurer")} />
        <textarea aria-label="Anything else" placeholder="Anything else we should know? (optional)" rows={3} className={inputCls} value={form.note} onChange={set("note")} />

        <label className="flex items-start gap-3 text-xs text-[#6B6B6B] leading-relaxed cursor-pointer">
          <input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5" />
          <span>
            I agree to be contacted by a licensed insurance agent by phone, text, or email about
            insurance quotes, including via automated technology. Consent is not a condition of
            purchase. Message and data rates may apply.
          </span>
        </label>

        {error && <p className="text-sm text-[#E24B4A]">{error}</p>}

        <button
          type="submit"
          disabled={submitting || types.length === 0 || !consent}
          className="w-full py-4 rounded-lg bg-[#00A86B] text-white font-semibold text-sm hover:bg-[#009960] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? "Sending…" : "Get my free quote →"}
        </button>
      </form>
    </div>
  );
}
