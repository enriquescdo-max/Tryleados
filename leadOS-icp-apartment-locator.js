// ============================================================
// LeadOS — Apartment Locator ICP Configuration
// For: Jamie's Apartment Locating — Austin, TX
// ============================================================

const APARTMENT_LOCATOR_ICP = {

  business: {
    name: "Jamie's Apartment Locating",
    owner: "Jamie Lynn Winkelstern-Saucedo",
    market: "Austin, TX",
    service: "Free apartment locating service — paid by properties",
    specialty: "Relocation clients, young professionals, remote workers",
  },

  // ── TARGET SIGNALS ────────────────────────────────────────
  signals: [
    {
      name: "New Austin Job Hire",
      description: "Person just accepted a job in Austin and needs housing",
      sources: ["LinkedIn new job announcements", "Indeed Austin postings", "Glassdoor"],
      score_weight: 95,
      urgency: "HIGH — usually needs housing within 30 days",
    },
    {
      name: "Corporate Relocation",
      description: "Company relocating employees to Austin office",
      sources: ["Company press releases", "Austin Business Journal", "LinkedIn"],
      score_weight: 92,
      urgency: "HIGH — company may pay for relocation service",
    },
    {
      name: "Remote Worker Moving to Austin",
      description: "Remote worker choosing Austin as new base",
      sources: ["Reddit r/Austin", "Facebook Austin groups", "Twitter/X"],
      score_weight: 85,
      urgency: "MEDIUM — flexible timeline but high intent",
    },
    {
      name: "UT Austin Grad / New Graduate",
      description: "Recent grad starting first job needs apartment",
      sources: ["LinkedIn new grad announcements", "UT Austin", "Indeed"],
      score_weight: 80,
      urgency: "HIGH — seasonal (May-August peak)",
    },
    {
      name: "Divorce / Life Change",
      description: "Person needing new apartment due to life transition",
      sources: ["Facebook community groups", "Nextdoor Austin"],
      score_weight: 75,
      urgency: "HIGH — immediate need",
    },
    {
      name: "Lease Ending Soon",
      description: "Current renter whose lease ends in 30-60 days",
      sources: ["Facebook Marketplace", "Austin Reddit", "Craigslist"],
      score_weight: 88,
      urgency: "VERY HIGH — active searcher right now",
    },
  ],

  // ── TARGET COMPANIES (referral partners) ──────────────────
  referral_partners: [
    {
      type: "HR Departments",
      companies: ["Tesla Gigafactory Austin", "Apple Austin Campus", "Samsung Austin", "Dell Technologies", "Oracle Austin", "Amazon Austin", "Google Austin", "Meta Austin", "Salesforce Austin", "Indeed HQ Austin"],
      pitch: "We help your new hires find housing fast — free to you and them",
      contact: "HR Director, Talent Acquisition, People Operations",
    },
    {
      type: "Relocation Companies",
      companies: ["Graebel", "Atlas Van Lines", "Allied Van Lines", "SIRVA", "Cartus"],
      pitch: "Partner with us for Austin apartment placement — we handle the local search",
      contact: "Partnership Manager, Relocation Consultant",
    },
    {
      type: "Real Estate Attorneys",
      companies: ["Austin family law firms", "Divorce attorneys"],
      pitch: "We help your clients find new apartments quickly and stress-free",
      contact: "Attorney, Office Manager",
    },
    {
      type: "Mortgage Brokers",
      companies: ["Austin mortgage companies"],
      pitch: "When clients aren't ready to buy, send them to us — we'll keep them happy until they are",
      contact: "Loan Officer, Branch Manager",
    },
  ],

  // ── EMAIL SEQUENCES ───────────────────────────────────────
  sequences: [

    {
      name: "New Austin Hire — Relocation Outreach",
      target: "Person who just posted a new job in Austin on LinkedIn",
      emails: [
        {
          step: 1,
          delay: "Same day",
          subject: "Congrats on the new role — need help finding a place in Austin?",
          body: `Hi {first_name},

I saw you just joined {company} in Austin — congratulations!

Moving to a new city is exciting but finding the right apartment can be overwhelming, especially in Austin's fast-moving market.

I'm Jamie, and I run a free apartment locating service here in Austin. I do all the legwork — searching properties, scheduling tours, negotiating — at zero cost to you (properties pay me directly).

Most of my clients find their perfect place within 1-2 weeks.

Would a quick 10-minute call this week be helpful? I can walk you through the best neighborhoods near {company}'s office and what to expect on pricing.

— Jamie
Jamie's Apartment Locating | Austin, TX
Free service. Zero pressure.`,
        },
        {
          step: 2,
          delay: "3 days",
          subject: "Quick Austin neighborhood guide for you",
          body: `Hi {first_name},

Just wanted to share this in case it's helpful as you plan your move:

The best Austin neighborhoods based on where {company} is located:

→ If you want walkability: South Congress, East Austin, Mueller
→ If you want space + value: Round Rock, Cedar Park, Pflugerville  
→ If you want nightlife + energy: Downtown, Rainey Street, 6th Street
→ If you want quiet + family-friendly: Westlake, Circle C, Steiner Ranch

Happy to help you narrow it down based on your budget and lifestyle. No commitment — just a conversation.

Reply here or grab 10 minutes on my calendar: {calendar_link}

— Jamie`,
        },
        {
          step: 3,
          delay: "7 days",
          subject: "Last check-in — Austin apartment market moving fast",
          body: `Hi {first_name},

Last note from me — I know you're probably swamped with the new role.

Just want to flag: Austin's rental market moves fast, especially in spring and summer. The best units at the best prices go within 24-48 hours of listing.

If you're still figuring out housing, I'm happy to get ahead of it for you at no cost.

If you've already sorted it — congrats and welcome to Austin! 🤘

Either way, feel free to reach out anytime.

— Jamie
Jamie's Apartment Locating
📱 {phone}`,
        },
      ],
    },

    {
      name: "HR Partner Outreach",
      target: "HR Directors at major Austin employers",
      emails: [
        {
          step: 1,
          delay: "Day 1",
          subject: "Free housing help for your Austin new hires",
          body: `Hi {first_name},

I work with several Austin companies to help their new hires find apartments quickly — at zero cost to your company or your employees.

Here's how it works: properties pay me a referral fee when I place a tenant. So your new hires get a dedicated local expert helping them find housing, and you get one less headache during onboarding.

Most placements happen within 1-2 weeks. I specialize in relocation clients and know the Austin market inside out.

Would it make sense to add this as a resource in your new hire welcome packet? Happy to send over a one-pager.

— Jamie
Jamie's Apartment Locating | Austin, TX`,
        },
        {
          step: 2,
          delay: "5 days",
          subject: "Quick question about your Austin relocation process",
          body: `Hi {first_name},

Quick follow-up — do you currently have a preferred apartment locator for Austin new hires?

If not, I'd love to be your go-to resource. I've helped employees from several Austin tech companies find housing and the feedback has been great — especially for out-of-state relocations where people have never visited Austin before.

No cost to {company}, no obligation. Just a partnership that makes your new hires' lives easier.

10 minutes this week?

— Jamie`,
        },
      ],
    },

    {
      name: "Reddit / Social Inbound — Apartment Seeker",
      target: "Person asking for Austin apartment help on Reddit/Facebook",
      emails: [
        {
          step: 1,
          delay: "Within 1 hour",
          subject: "Re: Looking for Austin apartment help",
          body: `Hi {first_name},

Saw your post about finding an apartment in Austin — I can help!

I'm a free apartment locator here in Austin. I search properties, schedule tours, and negotiate on your behalf. You pay nothing — properties cover my fee.

A few quick questions so I can find you the best options:
• What's your budget range?
• When do you need to move?
• Any preferred neighborhoods or areas?
• Pets? Roommates?

Reply here and I'll send you a personalized list of available units within 24 hours.

— Jamie
Jamie's Apartment Locating | Austin, TX 🤘`,
        },
      ],
    },

  ],

  // ── APIFY SEARCH QUERIES ──────────────────────────────────
  apify_searches: [
    "people relocating to Austin TX new job LinkedIn 2026",
    "Austin TX apartment needed Reddit moving",
    "HR director Austin TX tech companies relocation",
    "new hire Austin Texas housing help",
    "moving to Austin TX remote work apartment",
    "UT Austin graduates 2026 first apartment",
  ],

  // ── KEY METRICS ───────────────────────────────────────────
  targets: {
    leads_per_week: 50,
    sequences_per_week: 20,
    placements_per_month: 4,
    avg_commission: 500,
    monthly_revenue_target: 2000,
  },

};

// Export for LeadOS
if (typeof module !== 'undefined') module.exports = APARTMENT_LOCATOR_ICP;
window.APARTMENT_LOCATOR_ICP = APARTMENT_LOCATOR_ICP;
