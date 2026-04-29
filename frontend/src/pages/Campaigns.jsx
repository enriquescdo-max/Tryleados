import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const SEED_HYPOTHESES = [
  { id:"H001", persona:"New Renter", signal:"Craigslist apartment listing engagement", angle:"Landlord will require renters insurance — be ready before you sign", policy_type:"renters", channel:"email", urgency:"high", expected_reply_tier:"high", copy_hook:"Moving soon? Your landlord will ask for proof of renters insurance on day one." },
  { id:"H002", persona:"Apartment Locator Partner", signal:"Locator posted client needing apartment on social", angle:"Become their silent insurance concierge — zero work, happy clients", policy_type:"renters", channel:"email", urgency:"medium", expected_reply_tier:"high", copy_hook:"Your clients need renters insurance before move-in. I handle it same-day so you never delay a lease." },
  { id:"H003", persona:"Smart City Locating Referral", signal:"Smart City Apartment Locating partner referral", angle:"Warm referral — client has locator's endorsement", policy_type:"renters", channel:"sms", urgency:"high", expected_reply_tier:"very_high", copy_hook:"[Locator name] sent me your way. I can get your renters insurance proof emailed to you today." },
  { id:"H004", persona:"FB Marketplace Car Buyer", signal:"Facebook Marketplace listing — car shopping post", angle:"You'll need insurance the moment you buy — let me have a quote ready", policy_type:"auto", channel:"email", urgency:"high", expected_reply_tier:"medium", copy_hook:"Buying a car soon? I can have auto insurance ready in 20 minutes so you can drive it home today." },
  { id:"H005", persona:"Auto Dealer Finance Manager", signal:"Dealer posting about high volume / new inventory", angle:"I close insurance in 30 min so your buyers don't hold up delivery", policy_type:"auto", channel:"email", urgency:"medium", expected_reply_tier:"high", copy_hook:"When a buyer is in your chair and needs insurance fast, I'm your call. 30-minute binder, every time." },
  { id:"H006", persona:"Non-Standard Auto Buyer", signal:"Prior claims or lapse mentioned in Craigslist car post", angle:"Even with prior issues, we have carriers that will write you", policy_type:"auto", channel:"email", urgency:"high", expected_reply_tier:"medium", copy_hook:"Had a lapse or a couple claims? Most agents turn you away. We have carriers that won't." },
  { id:"H007", persona:"New Homeowner", signal:"County deed transfer record", angle:"Lender needs homeowners insurance before funding — we place same day", policy_type:"home", channel:"email", urgency:"very_high", expected_reply_tier:"very_high", copy_hook:"Congratulations on your new home. Your lender needs a binder before closing — I can have it to you today." },
  { id:"H008", persona:"Realtor Partner", signal:"Realtor listing property in Travis/Harris County", angle:"Your buyers need insurance before closing — I specialize in hard-to-place TX homes", policy_type:"home", channel:"email", urgency:"medium", expected_reply_tier:"high", copy_hook:"TX home insurance is a nightmare right now. I have carriers that accept older roofs and prior claims. Your buyers won't get stuck." },
  { id:"H009", persona:"Difficult TX Homeowner", signal:"Older property or prior claim mentioned in listing", angle:"Carriers rejected you? We have specialty markets others don't", policy_type:"home", channel:"email", urgency:"high", expected_reply_tier:"high", copy_hook:"Got declined or dropped by your home carrier? I place TX homes that most agents can't — older roofs, prior claims, no problem." },
  { id:"H010", persona:"New Mover — Full Bundle", signal:"Moving post on Reddit Austin/Houston", angle:"Bundle auto + renters when you move — one call, one agent, discount", policy_type:"bundle", channel:"email", urgency:"high", expected_reply_tier:"medium", copy_hook:"Moving to Austin? Bundle your auto and renters insurance together — one call, save 10-15%, coverage starts your move-in date." },
  { id:"H011", persona:"Renewal Shoppers", signal:"Renewal reminder date approaching", angle:"Rates changed — let me run a quick comparison before you auto-renew", policy_type:"auto", channel:"email", urgency:"medium", expected_reply_tier:"medium", copy_hook:"Your auto insurance is likely renewing soon. TX rates shifted this year — takes 10 minutes to see if you're overpaying." },
  { id:"H012", persona:"Mortgage Broker Partner", signal:"Mortgage broker closing a deal in Austin/Houston", angle:"Hard TX market means clients get stuck — I have specialty carriers", policy_type:"home", channel:"email", urgency:"medium", expected_reply_tier:"high", copy_hook:"How many of your closings get delayed waiting for homeowners insurance? I specialize in the hard TX cases. Let's fix that." },
];

const BRAIN_FILES = {
  "carriers": [
    { name:"auto_carriers", path:"carriers/auto_carriers.md", size:1800 },
    { name:"home_carriers", path:"carriers/home_carriers.md", size:1600 },
  ],
  "personas": [
    { name:"apartment_locators", path:"personas/apartment_locators.md", size:1200 },
    { name:"auto_dealers", path:"personas/auto_dealers.md", size:1100 },
    { name:"realtors", path:"personas/realtors.md", size:1000 },
  ],
  "states": [
    { name:"texas", path:"states/texas.md", size:900 },
  ],
  "scripts": [
    { name:"warm_transfer", path:"scripts/warm_transfer.md", size:800 },
  ],
  "root": [
    { name:"icp", path:"icp.md", size:2100 },
  ],
};



const TIER_STYLES = {
  scale:    { bg: "bg-green-50",  text: "text-green-700",  border: "border-green-200", label: "🚀 Scale",    action: "Add LinkedIn + increase volume" },
  optimize: { bg: "bg-amber-50",  text: "text-amber-700",  border: "border-amber-200", label: "🔧 Optimize", action: "Tweak copy, test new angles" },
  kill:     { bg: "bg-red-50",    text: "text-red-700",    border: "border-red-200",   label: "💀 Kill",     action: "Pause immediately — < 1% reply rate" },
  new:      { bg: "bg-blue-50",   text: "text-blue-700",   border: "border-blue-200",  label: "🆕 New",      action: "Need 50+ sends for data" },
};

const PHASE_COLORS = ["bg-[#E05A1A]","bg-blue-600","bg-purple-600","bg-green-600","bg-amber-600"];

export default function Campaigns() {
  const [activeTab, setActiveTab] = useState("write");
  const [hypotheses, setHypotheses] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [brainFiles, setBrainFiles] = useState({});

  // Write & Test state
  const [selectedHyp, setSelectedHyp] = useState(null);
  const [leadContext, setLeadContext] = useState({ first_name: "", zip: "", policy_type: "auto" });
  const [writing, setWriting] = useState(false);
  const [writeResult, setWriteResult] = useState(null);

  // Stress test state
  const [stressSubject, setStressSubject] = useState("");
  const [stressBody, setStressBody] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // Validate lead state
  const [validateText, setValidateText] = useState("");
  const [validateZip, setValidateZip] = useState("");
  const [validating, setValidating] = useState(false);
  const [validateResult, setValidateResult] = useState(null);

  useEffect(() => {
    setHypotheses(SEED_HYPOTHESES);
    setBrainFiles(BRAIN_FILES);
    loadCampaigns();
  }, []);

  async function api(path, opts = {}) {
    const res = await fetch(`${API}/api/v1/campaigns${path}`, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  }

  async function loadCampaigns() {
    try { const d = await api("/"); setCampaigns(d.campaigns || []); } catch {}
  }

  async function runWriteAndTest() {
    if (!selectedHyp) return;
    setWriting(true); setWriteResult(null);
    try {
      const result = await api("/write-and-test", {
        method: "POST",
        body: JSON.stringify({
          hypothesis_id: selectedHyp.id,
          lead_context: leadContext,
          max_attempts: 3,
        }),
      });
      setWriteResult(result);
      if (result.status === "approved") {
        setStressSubject(result.final_draft.subject);
        setStressBody(result.final_draft.body);
      }
    } catch (e) { setWriteResult({ error: e.message }); }
    setWriting(false);
  }

  async function runStressTest() {
    if (!stressSubject || !stressBody) return;
    setTesting(true); setTestResult(null);
    try {
      const result = await api("/stress-test", {
        method: "POST",
        body: JSON.stringify({ subject: stressSubject, body: stressBody }),
      });
      setTestResult(result);
    } catch (e) { setTestResult({ error: e.message }); }
    setTesting(false);
  }

  async function runValidate() {
    if (!validateText && !validateZip) return;
    setValidating(true); setValidateResult(null);
    try {
      const result = await api("/validate-lead", {
        method: "POST",
        body: JSON.stringify({ lead_text: validateText, zip_code: validateZip }),
      });
      setValidateResult(result);
    } catch (e) { setValidateResult({ error: e.message }); }
    setValidating(false);
  }

  const tabs = [
    { id: "write",      label: "✍️ Write & Test" },
    { id: "stress",     label: "🎯 Stress Test" },
    { id: "hypotheses", label: "💡 Hypotheses" },
    { id: "validate",   label: "🔍 Validate Lead" },
    { id: "brain",      label: "🧠 Second Brain" },
    { id: "campaigns",  label: "📊 Campaigns" },
  ];

  return (
    <div className="min-h-screen bg-[#F8F8F6]">

      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-100 bg-white">
        <h1 className="text-2xl font-semibold text-[#1A1A1A]" style={{ fontFamily:"'Playfair Display',serif" }}>
          Campaign Engine
        </h1>
        <p className="text-sm text-[#6B6B6B] mt-1">
          Growth Band playbook — Second Brain + Hypothesis × Signal × Angle + Stress Test
        </p>

        {/* Phase pills */}
        <div className="flex flex-wrap gap-2 mt-3">
          {["1. Second Brain","2. Hypotheses","3. Write & Stress Test","4. Validate Leads","5. Scale / Kill"].map((p,i) => (
            <span key={p} className={`text-xs font-medium text-white px-3 py-1 rounded-full ${PHASE_COLORS[i]}`}>{p}</span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-gray-100 bg-white px-6">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === t.id ? "border-[#E05A1A] text-[#E05A1A]" : "border-transparent text-[#6B6B6B] hover:text-[#1A1A1A]"
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="px-6 py-6 max-w-6xl mx-auto">

        {/* ── Write & Test ── */}
        {activeTab === "write" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: hypothesis picker + lead context */}
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-gray-100 p-5">
                <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B] mb-3">1. Pick a Campaign Hypothesis</div>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {hypotheses.map(h => (
                    <button key={h.id} onClick={() => setSelectedHyp(h)}
                      className={`w-full text-left p-3 rounded-lg border text-sm transition-all ${
                        selectedHyp?.id === h.id ? "border-[#E05A1A] bg-[#E05A1A08]" : "border-gray-100 hover:border-gray-200"
                      }`}>
                      <div className="font-medium text-[#1A1A1A]">{h.id} · {h.persona}</div>
                      <div className="text-xs text-[#6B6B6B] mt-0.5">{h.signal}</div>
                      <div className="text-xs text-[#E05A1A] mt-0.5 italic">{h.copy_hook}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-gray-100 p-5">
                <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B] mb-3">2. Lead Context (optional)</div>
                <div className="space-y-3">
                  {[["first_name","First Name","Maria"],["zip","ZIP Code","78704"],["policy_type","Policy Type","auto"]].map(([k,l,p]) => (
                    <div key={k}>
                      <label className="text-xs text-[#6B6B6B] mb-1 block">{l}</label>
                      <input value={leadContext[k] || ""} onChange={e => setLeadContext(c=>({...c,[k]:e.target.value}))}
                        placeholder={p}
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#E05A1A88]" />
                    </div>
                  ))}
                </div>
              </div>

              <button onClick={runWriteAndTest} disabled={writing || !selectedHyp}
                className="w-full py-3 bg-[#E05A1A] text-white font-semibold rounded-xl text-sm disabled:opacity-50">
                {writing ? "Writing + stress testing... (up to 3 attempts)" : "✍️ Write, Test & Approve"}
              </button>
            </div>

            {/* Right: result */}
            <div>
              <AnimatePresence>
                {writeResult && (
                  <motion.div initial={{opacity:0,y:12}} animate={{opacity:1,y:0}}>
                    {writeResult.error ? (
                      <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">{writeResult.error}</div>
                    ) : writeResult.status === "approved" ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2 text-green-700 font-semibold">
                          <span>✅ APPROVED</span>
                          <span className="text-sm font-normal text-[#6B6B6B]">Score: {writeResult.score}/10 · {writeResult.attempts} attempt{writeResult.attempts>1?"s":""}</span>
                        </div>

                        <div className="bg-white rounded-xl border border-green-200 p-4">
                          <div className="text-xs font-semibold text-[#6B6B6B] mb-1">SUBJECT</div>
                          <div className="font-medium text-[#1A1A1A] mb-3">{writeResult.final_draft.subject}</div>
                          <div className="text-xs font-semibold text-[#6B6B6B] mb-1">BODY</div>
                          <div className="text-sm text-[#1A1A1A] leading-relaxed whitespace-pre-wrap">{writeResult.final_draft.body}</div>
                        </div>

                        {writeResult.spintax?.variations && (
                          <div className="bg-white rounded-xl border border-gray-100 p-4">
                            <div className="text-xs font-semibold text-[#6B6B6B] mb-2">SPINTAX VARIATIONS</div>
                            {writeResult.spintax.variations.map((v,i) => (
                              <div key={i} className="text-xs text-[#6B6B6B] p-2 bg-gray-50 rounded-lg mb-1">
                                <span className="font-medium text-[#1A1A1A]">v{v.version}:</span> {v.subject}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                        <div className="font-semibold text-amber-700 mb-1">❌ Quality Gate Failed</div>
                        <div className="text-sm text-amber-600">Best score: {writeResult.best_score}/10 after {writeResult.attempts} attempts</div>
                        <div className="text-sm text-[#6B6B6B] mt-2">{writeResult.note}</div>
                        {writeResult.best_draft && (
                          <div className="mt-3 bg-white rounded-lg p-3 text-sm">
                            <div className="font-medium">{writeResult.best_draft.subject}</div>
                            <div className="text-[#6B6B6B] mt-1 text-xs">{writeResult.best_draft.body}</div>
                          </div>
                        )}
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
              {!writeResult && !writing && (
                <div className="h-64 flex items-center justify-center text-[#6B6B6B] text-sm text-center">
                  <div><div className="text-3xl mb-2">✍️</div>Pick a hypothesis and click Write</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Stress Test ── */}
        {activeTab === "stress" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">Paste any email draft — score it 0–10</div>
              <div>
                <label className="text-xs text-[#6B6B6B] mb-1 block">Subject line</label>
                <input value={stressSubject} onChange={e=>setStressSubject(e.target.value)}
                  placeholder="Quick question about your renters insurance"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#E05A1A88]" />
              </div>
              <div>
                <label className="text-xs text-[#6B6B6B] mb-1 block">Email body</label>
                <textarea value={stressBody} onChange={e=>setStressBody(e.target.value)} rows={8}
                  placeholder="Hey Maria,&#10;&#10;Saw you're moving to Austin next month..."
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#E05A1A88] resize-none" />
                <div className="text-xs text-[#6B6B6B] mt-1">{stressBody.split(/\s+/).filter(Boolean).length} words · Must score ≥ 8.1 to pass</div>
              </div>
              <button onClick={runStressTest} disabled={testing || !stressSubject || !stressBody}
                className="w-full py-3 bg-[#E05A1A] text-white font-semibold rounded-xl text-sm disabled:opacity-50">
                {testing ? "Testing..." : "🎯 Run Stress Test"}
              </button>
            </div>

            <div>
              <AnimatePresence>
                {testResult && (
                  <motion.div initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} className="space-y-4">
                    {testResult.error ? (
                      <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">{testResult.error}</div>
                    ) : (
                      <>
                        {/* Score header */}
                        <div className={`rounded-xl p-4 border ${testResult.pass ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                          <div className="flex items-center justify-between">
                            <span className={`text-2xl font-bold ${testResult.pass ? "text-green-700" : "text-red-700"}`}>
                              {testResult.score}/10
                            </span>
                            <span className={`font-semibold ${testResult.pass ? "text-green-700" : "text-red-700"}`}>
                              {testResult.pass ? "✅ PASS" : "❌ FAIL"} (min 8.1)
                            </span>
                          </div>
                          <div className="h-2 bg-white rounded-full mt-2 overflow-hidden">
                            <motion.div initial={{width:0}} animate={{width:`${testResult.score*10}%`}} transition={{duration:.6}}
                              className={`h-full rounded-full ${testResult.pass ? "bg-green-500" : "bg-red-500"}`} />
                          </div>
                        </div>

                        {/* Breakdown */}
                        {testResult.breakdown && Object.keys(testResult.breakdown).length > 0 && (
                          <div className="bg-white rounded-xl border border-gray-100 p-4">
                            <div className="text-xs font-semibold text-[#6B6B6B] uppercase tracking-wide mb-3">Score Breakdown</div>
                            {Object.entries(testResult.breakdown).map(([k,v]) => (
                              <div key={k} className="flex items-center gap-2 py-1">
                                <div className="text-xs text-[#6B6B6B] w-32 capitalize">{k.replace(/_/g," ")}</div>
                                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                  <div className="h-full rounded-full bg-[#E05A1A]" style={{width:`${v*10}%`}} />
                                </div>
                                <div className="text-xs font-mono text-[#1A1A1A] w-8">{v}</div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Rewrites */}
                        {testResult.rewrites?.length > 0 && (
                          <div className="bg-white rounded-xl border border-gray-100 p-4">
                            <div className="text-xs font-semibold text-[#6B6B6B] uppercase tracking-wide mb-3">Suggested Rewrites</div>
                            {testResult.rewrites.map((r,i) => (
                              <div key={i} className="mb-3 pb-3 border-b border-gray-50 last:border-0">
                                <div className="text-xs font-semibold text-[#E05A1A] uppercase mb-1">{r.element}</div>
                                <div className="text-xs text-red-500 line-through mb-1">{r.original}</div>
                                <div className="text-xs text-green-700">{r.improved}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}

        {/* ── Hypotheses ── */}
        {activeTab === "hypotheses" && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {hypotheses.map(h => (
              <div key={h.id} className="bg-white rounded-xl border border-gray-100 p-4 hover:border-gray-200 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs font-mono text-[#6B6B6B]">{h.id}</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    h.expected_reply_tier === "very_high" ? "bg-green-100 text-green-700" :
                    h.expected_reply_tier === "high" ? "bg-blue-100 text-blue-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>{h.expected_reply_tier} reply</span>
                </div>
                <div className="font-medium text-sm text-[#1A1A1A] mb-1">{h.persona}</div>
                <div className="text-xs text-[#6B6B6B] mb-2">📡 {h.signal}</div>
                <div className="text-xs text-[#E05A1A] italic mb-3">"{h.copy_hook}"</div>
                <div className="flex gap-2">
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{h.policy_type}</span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{h.channel}</span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{h.urgency} urgency</span>
                </div>
                <button onClick={() => { setSelectedHyp(h); setActiveTab("write"); }}
                  className="mt-3 w-full py-1.5 bg-[#E05A1A] text-white text-xs font-medium rounded-lg">
                  Use this hypothesis →
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ── Validate Lead ── */}
        {activeTab === "validate" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">
                Paste raw lead text — Claude validates ICP fit
              </div>
              <div>
                <label className="text-xs text-[#6B6B6B] mb-1 block">Lead text (listing, post, notes)</label>
                <textarea value={validateText} onChange={e=>setValidateText(e.target.value)} rows={6}
                  placeholder="Just bought a 2019 Camry in Austin, need insurance before I drive it off the lot..."
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#E05A1A88] resize-none" />
              </div>
              <div>
                <label className="text-xs text-[#6B6B6B] mb-1 block">ZIP Code</label>
                <input value={validateZip} onChange={e=>setValidateZip(e.target.value)} placeholder="78704"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#E05A1A88]" />
              </div>
              <button onClick={runValidate} disabled={validating || (!validateText && !validateZip)}
                className="w-full py-3 bg-[#E05A1A] text-white font-semibold rounded-xl text-sm disabled:opacity-50">
                {validating ? "Validating..." : "🔍 Validate ICP Fit"}
              </button>
            </div>

            <div>
              <AnimatePresence>
                {validateResult && (
                  <motion.div initial={{opacity:0,y:12}} animate={{opacity:1,y:0}}>
                    {validateResult.error ? (
                      <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">{validateResult.error}</div>
                    ) : (
                      <div className={`rounded-xl border p-5 ${validateResult.icp_match ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-xl">{validateResult.icp_match ? "✅" : "❌"}</span>
                          <span className={`font-bold text-lg ${validateResult.icp_match ? "text-green-700" : "text-red-700"}`}>
                            {validateResult.icp_match ? "ICP Match" : "Not a Match"}
                          </span>
                          <span className="text-sm text-[#6B6B6B]">({validateResult.confidence}% confidence)</span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          {[["Persona",validateResult.persona],["Insurance Need",validateResult.insurance_need],
                            ["Urgency",`${validateResult.urgency}/10`],["Angle",validateResult.angle]].map(([k,v])=>(
                            <div key={k}>
                              <div className="text-xs text-[#6B6B6B] uppercase tracking-wide">{k}</div>
                              <div className="font-medium text-[#1A1A1A]">{v || "—"}</div>
                            </div>
                          ))}
                        </div>
                        {validateResult.flags?.length > 0 && (
                          <div className="mt-3 space-y-1">
                            {validateResult.flags.map((f,i) => (
                              <div key={i} className="text-xs text-red-600">⚠️ {f}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}

        {/* ── Second Brain ── */}
        {activeTab === "brain" && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Object.entries(brainFiles).length === 0 ? (
              <div className="col-span-3 text-center py-16 text-[#6B6B6B] text-sm">
                <div className="text-4xl mb-2">🧠</div>
                <p>Second Brain is loading... Check Railway logs if this persists.</p>
              </div>
            ) : (
              Object.entries(brainFiles).map(([section, files]) => (
                <div key={section} className="bg-white rounded-xl border border-gray-100 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-[#E05A1A] mb-3">{section || "root"}</div>
                  {files.map(f => (
                    <div key={f.name} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                      <span className="text-sm text-[#1A1A1A]">{f.name}.md</span>
                      <span className="text-xs text-[#6B6B6B] font-mono">{(f.size/1024).toFixed(1)}kb</span>
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        )}

        {/* ── Campaigns ── */}
        {activeTab === "campaigns" && (
          <div>
            {campaigns.length === 0 ? (
              <div className="text-center py-16 text-[#6B6B6B] text-sm">
                <div className="text-4xl mb-2">📊</div>
                <p>No campaigns yet. Generate emails from a hypothesis to create campaigns.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {campaigns.map(c => {
                  const tier = TIER_STYLES[c.tier] || TIER_STYLES.new;
                  return (
                    <div key={c.id} className="bg-white rounded-xl border border-gray-100 p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="font-medium text-sm text-[#1A1A1A]">{c.name}</div>
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${tier.bg} ${tier.text} ${tier.border}`}>
                          {tier.label}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 mt-3">
                        {[["Sends",c.sends],["Replies",c.replies],["Reply %", `${((c.reply_rate||0)*100).toFixed(1)}%`]].map(([l,v])=>(
                          <div key={l} className="text-center bg-gray-50 rounded-lg py-2">
                            <div className="text-base font-bold text-[#1A1A1A]">{v}</div>
                            <div className="text-xs text-[#6B6B6B]">{l}</div>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 text-xs text-[#6B6B6B]">→ {tier.action}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
