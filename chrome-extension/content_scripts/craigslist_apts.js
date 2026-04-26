// LeadOS Content Script — Craigslist Apartments
(function () {
  "use strict";

  function scrape() {
    const lead = {
      source: "Craigslist",
      policyNeed: "Renters",
      policyNeedValue: "renters",
      lifeEventLabel: "Apt Listing",
      lifeEventValue: "apt_listing",
      sourceUrl: window.location.href,
      name: "",
    };

    // Title / address from listing
    const titleEl = document.querySelector("#titletextonly") || document.querySelector("h2.postingtitle");
    if (titleEl) lead.address = titleEl.textContent.trim();

    // Price
    const priceEl = document.querySelector(".price");
    if (priceEl) lead.price = priceEl.textContent.trim();

    // Bedrooms
    const attrEl = document.querySelector(".housing");
    if (attrEl) lead.bedrooms = attrEl.textContent.trim();

    // ZIP from map or posting body
    const body = document.querySelector("#postingbody");
    if (body) {
      const zipMatch = body.textContent.match(/\b(\d{5})\b/);
      if (zipMatch) lead.zip = zipMatch[1];
    }

    // Map link sometimes has lat/lng we can reverse geocode later
    const mapLink = document.querySelector("a[href*='maps.google']");
    if (mapLink) lead.mapUrl = mapLink.href;

    return lead.address ? lead : null;
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "GET_LEAD_DATA") sendResponse({ lead: scrape() });
    return true;
  });

  function injectBtn() {
    if (document.getElementById("leados-cl-btn")) return;
    const lead = scrape();
    if (!lead) return;

    const btn = document.createElement("div");
    btn.id = "leados-cl-btn";
    btn.innerHTML = `
      <div style="
        position: fixed; bottom: 20px; right: 20px; z-index: 999999;
        background: #E05A1A; color: #fff; padding: 9px 16px;
        border-radius: 7px; font-size: 13px; font-weight: 600;
        cursor: pointer; box-shadow: 0 3px 16px #E05A1A44;
        display: flex; align-items: center; gap: 7px; font-family: sans-serif;
      " id="leados-cl-inner">
        <span>⊕</span> Capture Renter Lead
      </div>
    `;
    document.body.appendChild(btn);
    btn.querySelector("#leados-cl-inner").addEventListener("click", () => {
      chrome.runtime.sendMessage({ type: "QUICK_CAPTURE", lead });
    });
  }

  setTimeout(injectBtn, 1000);
})();
