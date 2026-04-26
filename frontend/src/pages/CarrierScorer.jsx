import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CARRIER_LOGOS = {
  Progressive: "🔵", GEICO: "🦎", Root: "🌱",
  "National General": "🛡️", "Bristol West": "⚓",
  Orion180: "🌊", Swyfft: "⚡", Sagesure: "🏔️", Lemonade: "🍋",
};

const MARKET_COLORS = {
  standard: { bg: "bg-blue-50", text: "text-blue-700", label: "Standard" },
  "non-standard": { bg: "bg-amber-50", text: "text-amber-700", label: "Non-Standard" },
  specialty: { bg: "bg-purple-50", text: "text-purple-700", label: "Specialty" },
};

export default function CarrierScorer() {
  const [form, setForm] = useState({
    zip_code: "78704",
    policy_type: "auto",
    credit_tier: "fair",
    life_event: "new_move",
    vehicle_year: "",
    prior_claims: "0",
    property_age: "",
    roof_age: "",
    prior_lapses: false,
    is_new_driver: false,
    dwelling_type: "single_family",
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  async function score() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body = {
        zip_code: form.zip_code,
        policy_type: form.policy_type,
        credit_tier: form.credit_tier,
        life_event: form.life_event || null,
        prior_claims: parseInt(form.prior_claims) || 0,
        prior_lapses: form.prior_lapses,
        is_new_driver: form.is_new_driver,
        dwelling_type: form.dwelling_type,
      };
      if (form.vehicle_year) body.vehicle_year = parseInt(form.vehicle_year);
      if (form.property_age) body.property_age = parseInt(form.property_age);
      if (form.roof_age) body.roof_age = parseInt(form.roof_age);

      const res = await fetch(`${API}/api/v1/carrier-score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const isAuto = form.policy_type === "auto" || form.policy_type === "bundle";
  const isHome = form.policy_type === "home" || form.policy_type === "renters" || form.policy_type === "bundle";

  return (
    <div className="min-h-screen bg-[#F8F8F6] px-6 py-6">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-[#1A1A1A]" style={{ fontFamily: "'Playfair Display', serif" }}>
            Carrier Appetite Scorer
          </h1>
          <p className="text-sm text-[#6B6B6B] mt-1">
            Score Progressive, GEICO, Root, Orion180, Swyfft + more for any lead profile. Built for TX P&C agents.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Form */}
          <div className="bg-white rounded-[12px] border border-gray-100 shadow-sm p-6">
            <h2 className="text-sm font-semibold text-[#1A1A1A] mb-4 uppercase tracking-wide">Lead Profile</h2>

            <div className="space-y-4">
              <Row label="ZIP Code">
                <input type="text" maxLength={5} value={form.zip_code}
                  onChange={e => set("zip_code", e.target.value)}
                  className="input-base font-mono" placeholder="78704" />
              </Row>

              <Row label="Policy Type">
                <select value={form.policy_type} onChange={e => set("policy_type", e.target.value)} className="input-base">
                  <option value="auto">Auto</option>
                  <option value="home">Home</option>
                  <option value="renters">Renters</option>
                  <option value="bundle">Bundle (Auto + Home)</option>
                </select>
              </Row>

              <Row label="Credit Tier">
                <select value={form.credit_tier} onChange={e => set("credit_tier", e.target.value)} className="input-base">
                  <option value="excellent">Excellent (750+)</option>
                  <option value="good">Good (680–749)</option>
                  <option value="fair">Fair (600–679)</option>
                  <option value="poor">Poor (&lt;600)</option>
                  <option value="unknown">Unknown</option>
                </select>
              </Row>

              <Row label="Life Event">
                <select value={form.life_event} onChange={e => set("life_event", e.target.value)} className="input-base">
                  <option value="">None</option>
                  <option value="new_move">New Move</option>
                  <option value="car_purchase">Car Purchase</option>
                  <option value="deed_transfer">Deed Transfer</option>
                  <option value="apt_listing">Apartment Listing</option>
                  <option value="new_homeowner">New Homeowner</option>
                  <option value="renewal">Renewal</option>
                </select>
              </Row>

              <Row label="Prior Claims (3 yrs)">
                <select value={form.prior_claims} onChange={e => set("prior_claims", e.target.value)} className="input-base">
                  {[0,1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </Row>

              {isAuto && (
                <Row label="Vehicle Year">
                  <input type="number" min={1990} max={2025} value={form.vehicle_year}
                    onChange={e => set("vehicle_year", e.target.value)}
                    className="input-base font-mono" placeholder="2020" />
                </Row>
              )}

              {isHome && (
                <>
                  <Row label="Property Age (yrs)">
                    <input type="number" min={0} max={150} value={form.property_age}
                      onChange={e => set("property_age", e.target.value)}
                      className="input-base font-mono" placeholder="15" />
                  </Row>
                  <Row label="Roof Age (yrs)">
                    <input type="number" min={0} max={50} value={form.roof_age}
                      onChange={e => set("roof_age", e.target.value)}
                      className="input-base font-mono" placeholder="8" />
                  </Row>
                  <Row label="Dwelling Type">
                    <select value={form.dwelling_type} onChange={e => set("dwelling_type", e.target.value)} className="input-base">
                      <option value="single_family">Single Family</option>
                      <option value="condo">Condo</option>
                      <option value="mobile">Mobile / Manufactured</option>
                      <option value="apartment">Apartment</option>
                    </select>
                  </Row>
                </>
              )}

              <div className="flex gap-4 pt-1">
                <label className="flex items-center gap-2 text-sm text-[#6B6B6B] cursor-pointer">
                  <input type="checkbox" checked={form.prior_lapses}
                    onChange={e => set("prior_lapses", e.target.checked)}
                    className="accent-[#E05A1A]" />
                  Prior lapse
                </label>
                {isAuto && (
                  <label className="flex items-center gap-2 text-sm text-[#6B6B6B] cursor-pointer">
                    <input type="checkbox" checked={form.is_new_driver}
                      onChange={e => set("is_new_driver", e.target.checked)}
                      className="accent-[#E05A1A]" />
                    New driver
                  </label>
                )}
              </div>

              <button onClick={score} disabled={loading || form.zip_code.length !== 5}
                className="w-full py-3 rounded-[10px] bg-[#E05A1A] text-white font-semibold text-sm hover:bg-[#c94e15] transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2">
                {loading ? "Scoring carriers..." : "◉ Score Carrier Fit"}
              </button>

              {error && (
                <p className="text-xs text-red-500 bg-red-50 rounded-lg p-2">{error}</p>
              )}
            </div>
          </div>

          {/* Results */}
          <div>
            <AnimatePresence>
              {result && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>

                  {/* Strategy note */}
                  <div className="bg-[#E05A1A0D] border border-[#E05A1A22] rounded-[12px] p-4 mb-4">
                    <div className="text-xs font-semibold text-[#E05A1A] uppercase tracking-wide mb-1">Agent Strategy</div>
                    <p className="text-sm text-[#1A1A1A] leading-relaxed">{result.strategy_note}</p>
                  </div>

                  {/* Carrier results */}
                  <div className="bg-white rounded-[12px] border border-gray-100 shadow-sm overflow-hidden">
                    <div className="px-4 py-3 border-b border-gray-50">
                      <span className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">
                        Carrier Rankings — {result.lead_profile.state} · {result.lead_profile.zip} · {result.lead_profile.cat_zone}
                      </span>
                    </div>

                    {result.results.map((r, i) => {
                      const mkt = MARKET_COLORS[r.market_type] || MARKET_COLORS.standard;
                      const isTop = i === 0;
                      const scoreColor = r.score >= 80 ? "text-green-600" : r.score >= 60 ? "text-amber-600" : "text-red-500";
                      return (
                        <div key={r.carrier} className={`px-4 py-4 border-b border-gray-50 last:border-0 ${isTop ? "bg-[#E05A1A06]" : ""}`}>
                          <div className="flex items-start gap-3">
                            {/* Rank + emoji */}
                            <div className="text-center min-w-[28px]">
                              <div className="text-lg">{CARRIER_LOGOS[r.carrier] || "⚙️"}</div>
                              <div className="text-xs text-[#6B6B6B] font-mono">#{r.rank}</div>
                            </div>

                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-sm text-[#1A1A1A]">{r.carrier}</span>
                                {isTop && (
                                  <span className="text-[10px] font-bold text-[#E05A1A] bg-[#E05A1A18] px-2 py-0.5 rounded-full">TOP PICK</span>
                                )}
                                {r.flag === "decline" && (
                                  <span className="text-[10px] font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">DECLINE</span>
                                )}
                                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${mkt.bg} ${mkt.text}`}>{mkt.label}</span>
                              </div>

                              {/* Score bar */}
                              <div className="flex items-center gap-2 mb-2">
                                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${r.score}%` }}
                                    transition={{ delay: i * 0.08, duration: 0.5 }}
                                    className="h-full rounded-full"
                                    style={{ background: r.score >= 80 ? "#00A86B" : r.score >= 60 ? "#BA7517" : "#E24B4A" }}
                                  />
                                </div>
                                <span className={`font-mono text-xs font-bold min-w-[28px] ${scoreColor}`}>{r.score}</span>
                                <span className="text-xs text-[#6B6B6B]">{Math.round(r.binding_prob * 100)}% bind</span>
                              </div>

                              {/* Notes */}
                              <div className="space-y-0.5">
                                {r.notes.slice(0, 2).map((n, j) => (
                                  <p key={j} className="text-xs text-[#6B6B6B] leading-relaxed">· {n}</p>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Compliance note */}
                  <div className="mt-3 p-3 bg-blue-50 rounded-[10px]">
                    <p className="text-xs text-blue-700 leading-relaxed">{result.compliance_note}</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {!result && !loading && (
              <div className="h-full flex flex-col items-center justify-center py-24 text-center text-[#6B6B6B]">
                <div className="text-4xl mb-3">◉</div>
                <p className="text-sm font-medium text-[#1A1A1A]">Enter a lead profile</p>
                <p className="text-xs mt-1">Results will rank all carriers by appetite score</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        .input-base {
          width: 100%;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 7px 10px;
          font-size: 13px;
          color: #1A1A1A;
          background: white;
          outline: none;
          transition: border-color .15s;
        }
        .input-base:focus { border-color: #E05A1A88; }
        .font-mono { font-family: 'IBM Plex Mono', monospace; }
      `}</style>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <div>
      <label className="block text-xs font-medium text-[#6B6B6B] mb-1">{label}</label>
      {children}
    </div>
  );
}
