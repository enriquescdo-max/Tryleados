// LeadOS Content Script — Cars.com
(function () {
  "use strict";

  function scrape() {
    const lead = {
      source: "Cars.com",
      policyNeed: "Auto",
      policyNeedValue: "auto",
      lifeEventLabel: "Car Purchase",
      lifeEventValue: "car_purchase",
      sourceUrl: window.location.href,
      name: "",
    };

    // Title (year make model)
    const titleEl =
      document.querySelector("h1.listing-title") ||
      document.querySelector("[class*='listing-masthead__title']") ||
      document.querySelector("h1");
    if (titleEl) {
      const title = titleEl.textContent.trim();
      lead.vehicleTitle = title;
      const yearMatch = title.match(/\b(19|20)(\d{2})\b/);
      if (yearMatch) lead.vehicleYear = parseInt(yearMatch[0]);
      const parts = title.split(" ");
      if (parts.length >= 2) lead.vehicleMake = parts[parts.length >= 3 ? parts.indexOf(yearMatch?.[0]) + 1 : 0];
    }

    // Price
    const priceEl =
      document.querySelector(".primary-price") ||
      document.querySelector("[class*='price']");
    if (priceEl) lead.price = priceEl.textContent.trim();

    // ZIP / dealer location
    const dealerEl =
      document.querySelector(".dealer-address") ||
      document.querySelector("[class*='dealer-info'] address");
    if (dealerEl) {
      const zipMatch = dealerEl.textContent.match(/\b(\d{5})\b/);
      if (zipMatch) lead.zip = zipMatch[1];
    }

    // Mileage
    const mileageEl = document.querySelector("[class*='mileage']");
    if (mileageEl) lead.mileage = mileageEl.textContent.trim();

    return lead.vehicleYear ? lead : null;
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "GET_LEAD_DATA") sendResponse({ lead: scrape() });
    return true;
  });

  function injectBtn() {
    if (document.getElementById("leados-carscom-btn")) return;
    const lead = scrape();
    if (!lead) return;
    const btn = document.createElement("div");
    btn.id = "leados-carscom-btn";
    btn.innerHTML = `
      <div style="
        position: fixed; bottom: 20px; right: 20px; z-index: 999999;
        background: #E05A1A; color: #fff; padding: 9px 16px;
        border-radius: 7px; font-size: 13px; font-weight: 600;
        cursor: pointer; box-shadow: 0 3px 16px #E05A1A44;
        display: flex; align-items: center; gap: 7px; font-family: sans-serif;
      " id="leados-carscom-inner">
        <span>⊕</span> Capture Auto Lead
      </div>
    `;
    document.body.appendChild(btn);
    btn.querySelector("#leados-carscom-inner").addEventListener("click", () => {
      chrome.runtime.sendMessage({ type: "QUICK_CAPTURE", lead });
    });
  }

  setTimeout(injectBtn, 1200);
})();
