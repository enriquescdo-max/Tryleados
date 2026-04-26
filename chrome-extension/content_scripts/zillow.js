// LeadOS Content Script — Zillow
// Extracts: address, ZIP, price, property details, beds/baths
// Sends to popup when polled via GET_LEAD_DATA message

(function () {
  "use strict";

  function scrapeZillow() {
    const lead = { source: "Zillow", policyNeed: "Home", policyNeedValue: "home" };

    // Address
    const addressEl =
      document.querySelector("h1[class*='Text']") ||
      document.querySelector('[data-testid="home-details-summary-headline"]') ||
      document.querySelector("h1");
    if (addressEl) lead.address = addressEl.textContent.trim();

    // Price
    const priceEl =
      document.querySelector('[data-testid="price"]') ||
      document.querySelector("span[class*='Price']") ||
      document.querySelector(".price-value");
    if (priceEl) lead.price = priceEl.textContent.trim().replace(/\s+/g, " ");

    // ZIP from URL or address
    const urlMatch = window.location.pathname.match(/(\d{5})/);
    if (urlMatch) lead.zip = urlMatch[1];
    else if (lead.address) {
      const zipMatch = lead.address.match(/\b(\d{5})\b/);
      if (zipMatch) lead.zip = zipMatch[1];
    }

    // City from address
    if (lead.address) {
      const parts = lead.address.split(",");
      if (parts.length >= 2) lead.city = parts[parts.length - 2].trim();
    }

    // Beds
    const bedEl =
      document.querySelector('[data-testid="bed-bath-beyond-icon-bed"] + span') ||
      document.querySelector('[aria-label*="bedrooms"]') ||
      document.querySelector("li[class*='bed']");
    if (bedEl) lead.bedrooms = bedEl.textContent.trim();

    // Property type: if it's a rental listing → renters
    const isRental =
      window.location.href.includes("/rentals/") ||
      window.location.href.includes("rent") ||
      document.title.toLowerCase().includes("rent");
    if (isRental) {
      lead.policyNeed = "Renters";
      lead.policyNeedValue = "renters";
      lead.lifeEventLabel = "Apt Listing";
      lead.lifeEventValue = "apt_listing";
    } else {
      lead.lifeEventLabel = "New Homeowner";
      lead.lifeEventValue = "new_homeowner";
    }

    lead.sourceUrl = window.location.href;
    lead.name = "";  // Zillow doesn't expose buyer info

    return lead.address ? lead : null;
  }

  // Listen for popup poll
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "GET_LEAD_DATA") {
      const lead = scrapeZillow();
      sendResponse({ lead });
    }
    return true;
  });

  // Show overlay button on property listings
  function injectCaptureButton() {
    if (document.getElementById("leados-capture-btn")) return;

    const lead = scrapeZillow();
    if (!lead) return;

    const btn = document.createElement("div");
    btn.id = "leados-capture-btn";
    btn.innerHTML = `
      <div style="
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
        background: #E05A1A;
        color: #fff;
        padding: 10px 18px;
        border-radius: 8px;
        font-family: -apple-system, sans-serif;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 4px 20px #E05A1A44;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: transform .15s;
        user-select: none;
      " id="leados-btn-inner">
        <span style="font-size:15px">⊕</span>
        Capture to LeadOS
      </div>
    `;
    document.body.appendChild(btn);

    btn.querySelector("#leados-btn-inner").addEventListener("click", () => {
      chrome.runtime.sendMessage({ type: "QUICK_CAPTURE", lead });
    });
    btn.querySelector("#leados-btn-inner").addEventListener("mouseenter", e => {
      e.target.style.transform = "scale(1.03)";
    });
    btn.querySelector("#leados-btn-inner").addEventListener("mouseleave", e => {
      e.target.style.transform = "scale(1)";
    });
  }

  // Inject on page load and after SPA navigation
  setTimeout(injectCaptureButton, 1500);
  const observer = new MutationObserver(() => {
    setTimeout(injectCaptureButton, 800);
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
