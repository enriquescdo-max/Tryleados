/**
 * LeadOS — P&C Insurance Agent ICP Configuration
 * ─────────────────────────────────────────────────────────────────────────
 * Drop this script tag into your ICP Builder page (or run in browser console)
 * to pre-load the optimal ICP for a Property & Casualty insurance agent.
 *
 * Targets: Referral partners + direct consumer triggers
 * Best for: Home, Auto, Renters, Commercial P&C
 */

const INSURANCE_ICP = {
  name: "P&C Insurance — Referral Partner ICP",

  // ── Who to target ────────────────────────────────────────────────────────
  // Phase 1: Referral partners (highest ROI — each one sends you 10-50 clients)
  target_industries: [
    "Real Estate",
    "Mortgage Lending",
    "Auto Dealerships",
    "Property Management",
    "Moving & Relocation",
    "Financial Planning",
    "Home Builders",
    "Title Companies"
  ],

  // Decision-makers who can refer clients to you
  target_titles: [
    "Real Estate Agent",
    "Realtor",
    "Mortgage Broker",
    "Loan Officer",
    "Finance Manager",       // at car dealerships
    "Property Manager",
    "Financial Advisor",
    "Branch Manager"
  ],

  target_seniority: ["Director", "Manager", "Individual Contributor", "Owner"],

  // ── Company size sweet spot ──────────────────────────────────────────────
  // Small-to-mid agencies and brokerages — they close lots of transactions
  // and actively want trusted insurance partners to refer to
  min_employees: 1,
  max_employees: 200,

  // ── Geographies ──────────────────────────────────────────────────────────
  // Start hyper-local — referral partnerships require relationship
  target_geographies: [
    "Texas",          // ← change to your state/metro
    "Austin, TX",     // ← change to your city
  ],

  // ── Intent signals that mean "this person needs an insurance partner NOW" ─
  positive_signals: [
    "recently opened new office",         // expanding = needs more referral vendors
    "hiring loan officers",               // growing = more closings = more insurance needs
    "hiring real estate agents",
    "new property management contract",
    "new auto dealership location",
    "recently licensed",                  // new agents need to build their vendor network
    "high transaction volume",
    "new partnership announcement",
    "new construction project",
    "recently joined brokerage",
  ],

  // ── Signals that mean "skip for now" ────────────────────────────────────
  negative_signals: [
    "office closing",
    "license suspended",
    "bankruptcy filing",
    "business sold",
    "retired",
  ],

  // ── AI Scoring weight guidance (passed to Claude) ────────────────────────
  scoring_guidance: `
    Score leads based on likelihood to refer P&C insurance clients.
    Highest weight: title match (are they in a field that touches home/auto transactions?)
    Second weight: location (must be in agent's service territory)
    Third weight: company activity signals (growing businesses refer more)
    Lowest weight: company size (solo agents can be excellent referral partners)
    Auto-disqualify: any signals of business closure or license issues.
  `,
};

// ── Outreach sequence config ──────────────────────────────────────────────
const INSURANCE_SEQUENCES = {

  // Sequence 1: Realtor / Real Estate Agent outreach
  realtor_sequence: {
    name: "Realtor Referral Partnership",
    steps: [
      {
        day: 0,
        subject: "Quick question — do you have a go-to insurance agent?",
        body: `Hi {{first_name}},

I was looking at some of your recent listings in {{city}} — really nice work on {{recent_listing_area}}.

I'm a local P&C insurance agent specializing in home and auto. A lot of realtors I work with tell me the #1 thing that slows closings down is clients scrambling for insurance at the last minute.

I turn around home insurance quotes same-day and work with 12 carriers, so I can usually find coverage even for tricky properties (older homes, high-value, flood zones, etc.).

Would you be open to a quick 10-min call to see if we'd be a good fit to refer to each other?

{{your_name}}
{{your_phone}}
P&C Insurance Agent | {{your_agency}}`,
      },
      {
        day: 3,
        subject: "Re: Quick question — do you have a go-to insurance agent?",
        body: `Hi {{first_name}},

Just following up — I know you're busy.

One thing I didn't mention: when I work with a realtor's clients, I copy the realtor on every communication so you always know where things stand. No surprises at closing.

Happy to send you a one-pager on how I work with agents if that's helpful.

{{your_name}}`,
      },
      {
        day: 7,
        subject: "Insurance tip for your clients in {{city}}",
        body: `{{first_name}},

Sharing something useful regardless of whether we connect —

A lot of buyers in {{city}} are getting surprised by wind/hail surcharges right now. If you give clients a heads-up to ask about this before making an offer, it helps them budget accurately and avoids surprises.

Happy to be a resource whenever you need a second opinion on a property's insurability. That's a free call, no strings.

{{your_name}}
{{your_phone}}`,
      },
      {
        day: 14,
        subject: "Last note from me",
        body: `{{first_name}},

I'll keep this short — just didn't want to disappear without saying that the door's always open.

If you ever have a client who needs home insurance fast, or a property that's been declined elsewhere, feel free to reach out. I'll always make time for a referral from a realtor.

Take care,
{{your_name}}
{{your_phone}}`,
      },
    ],
  },

  // Sequence 2: Auto Dealership Finance Manager outreach
  dealer_sequence: {
    name: "Auto Dealer Finance Manager",
    steps: [
      {
        day: 0,
        subject: "Do your customers ever get held up on insurance?",
        body: `Hi {{first_name}},

I'm a local auto insurance agent and I work with a few dealerships in {{city}} to help their finance customers get same-day insurance so deals don't fall through.

Lenders require active insurance before they'll fund — and when buyers can't produce proof of insurance quickly, it delays or kills the deal.

I can typically get a buyer insured and deliver proof of insurance within the hour. Carriers I work with: {{list_carriers}}.

Would it make sense to have a quick call? I'm not looking to be pushy — just want to make sure your buyers have a fast option when they need it.

{{your_name}}
{{your_phone}}`,
      },
      {
        day: 4,
        subject: "Re: Insurance for your finance customers",
        body: `{{first_name}},

Quick follow-up. One of the dealerships I work with in {{nearby_city}} told me they were losing 2-3 deals a month to insurance delays before we started working together.

Happy to share exactly how we set that up if it's useful.

{{your_name}}`,
      },
      {
        day: 10,
        subject: "One thing before I go",
        body: `{{first_name}},

I'll stop reaching out after this — I know your inbox is full.

If you ever have a buyer who needs insurance fast and can't reach their agent, feel free to give them my number: {{your_phone}}. I'll take the call.

{{your_name}}`,
      },
    ],
  },

  // Sequence 3: Mortgage Broker / Loan Officer outreach
  mortgage_sequence: {
    name: "Mortgage Broker Partnership",
    steps: [
      {
        day: 0,
        subject: "Insurance bottleneck at closing — have you felt this?",
        body: `Hi {{first_name}},

I work with a handful of loan officers in {{city}} and the most common thing I hear is that home insurance is the last thing their clients get — and sometimes it causes closing delays.

I specialize in home insurance for purchase transactions. I turn around quotes same-day, work with buyers who have less-than-perfect claims history, and I coordinate directly with the lender so you get the binder without chasing anyone.

Would a 15-min intro call make sense? No pressure — just want to put a name to a face.

{{your_name}}
{{your_phone}}
P&C Insurance | {{your_agency}}`,
      },
      {
        day: 5,
        subject: "Re: Closing bottleneck",
        body: `{{first_name}},

Following up briefly. Something that's been useful for the LOs I work with: I send a one-page "insurance checklist" they can share with clients at pre-approval. It sets expectations early and prevents last-minute scrambles.

Happy to send it your way if you'd like — no strings, just useful.

{{your_name}}`,
      },
      {
        day: 12,
        subject: "Last note — leaving the door open",
        body: `{{first_name}},

Won't keep reaching out. If you ever need a fast home insurance quote for a client — especially a tough one with prior claims or an older home — feel free to call me directly.

{{your_name}}
{{your_phone}}`,
      },
    ],
  },
};

// Auto-load into LeadOS if running in the app
if (window.LeadOSAPI) {
  LeadOSAPI.updateICP(INSURANCE_ICP).then(() => {
    console.log('%c P&C Insurance ICP loaded into LeadOS ', 'background:#00ff88;color:#000;font-weight:bold;padding:4px 8px;border-radius:4px;font-family:monospace;');
    if (window.LeadOSUI) LeadOSUI.toast('P&C Insurance ICP loaded!', 'success');
  });
}

// Export for use outside the app
if (typeof module !== 'undefined') {
  module.exports = { INSURANCE_ICP, INSURANCE_SEQUENCES };
}
