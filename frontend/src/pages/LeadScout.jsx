const LEADSCOUT_URL = "https://leadscout-production-b570.up.railway.app";

const FEATURES = [
  {
    icon: "🗺️",
    title: "City-Wide Business Discovery",
    desc: "Search any city for insurance agencies, dentists, lawyers, restaurants, or realtors. Pulls live from OpenStreetMap — zero API costs, zero credit limits.",
  },
  {
    icon: "✉️",
    title: "Direct Email Discovery",
    desc: "Every lead's website is scanned for a real contact email — trackers, platform junk, and false positives filtered out automatically.",
  },
  {
    icon: "📇",
    title: "Status Tracking + CSV Export",
    desc: "Tag leads new → contacted → won/lost, then export the whole list to CSV for one-click import into the LeadOS contact database.",
  },
];

export default function LeadScout() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <div className="text-center mb-14">
        <div className="inline-block px-3 py-1 mb-4 text-xs font-semibold rounded-full bg-[#E8F8F2] text-[#00A86B]">
          New Service
        </div>
        <h1 className="text-4xl font-bold text-[#1A1A1A] mb-4">LeadScout</h1>
        <p className="text-lg text-[#6B6B6B] max-w-2xl mx-auto">
          Top-of-funnel fuel for LeadOS. Scrape local business leads from free, open
          data — names, phones, websites, and verified emails — then feed them straight
          into your outbound campaigns.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-14">
        {FEATURES.map((f) => (
          <div key={f.title} className="bg-white border border-gray-100 rounded-xl p-6 shadow-sm">
            <div className="text-3xl mb-3">{f.icon}</div>
            <h3 className="font-semibold text-[#1A1A1A] mb-2">{f.title}</h3>
            <p className="text-sm text-[#6B6B6B] leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>

      <div className="bg-white border border-gray-100 rounded-xl p-8 text-center shadow-sm">
        <h2 className="text-xl font-semibold text-[#1A1A1A] mb-2">How it bridges to LeadOS</h2>
        <p className="text-sm text-[#6B6B6B] max-w-xl mx-auto mb-6">
          Run a LeadScout search, export the enriched CSV, bulk-import into your LeadOS
          contacts tagged <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">Outbound_Claude_Campaign</span>,
          and let LeadOS conversational AI handle qualification and booking.
        </p>
        <a
          href={LEADSCOUT_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block px-6 py-3 text-sm font-semibold rounded-lg bg-[#00A86B] text-white hover:bg-[#009960] transition-all"
        >
          Open LeadScout →
        </a>
        <p className="text-xs text-[#6B6B6B] mt-3">Token-gated — paste your API token on first visit.</p>
      </div>
    </div>
  );
}
