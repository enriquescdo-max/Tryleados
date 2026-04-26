// LeadOS Content Script — Craigslist Cars (For Sale by Owner)
(function () {
  "use strict";

  function scrape() {
    const lead = {
      source: "Craigslist Cars",
      policyNeed: "Auto",
      policyNeedValue: "auto",
      lifeEventLabel: "Car Purchase",
      lifeEventValue: "car_purchase",
      sourceUrl: window.location.href,
      name: "",
    };

    const titleEl = document.querySelector("#titletextonly");
    if (titleEl) {
      const title = titleEl.textContent.trim();
      lead.vehicleTitle = title;
      // Extract year if present
      const yearMatch = title.match(/\b(19|20)(\d{2})\b/);
      if (yearMatch) lead.vehicleYear = parseInt(yearMatch[0]);
      // Extract make (first word after year)
      const afterYear = title.replace(/\b(19|20)\d{2}\b/, "").trim();
      lead.vehicleMake = afterYear.split(" ")[0];
    }

    const priceEl = document.querySelector(".price");
    if (priceEl) lead.price = priceEl.textContent.trim();

    const body = document.querySelector("#postingbody");
    if (body) {
      const zipMatch = body.textContent.match(/\b(\d{5})\b/);
      if (zipMatch) lead.zip = zipMatch[1];
    }

    return lead.vehicleYear ? lead : null;
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "GET_LEAD_DATA") sendResponse({ lead: scrape() });
    return true;
  });

  function injectBtn() {
    if (document.getElementById("leados-cars-cl-btn")) return;
    const lead = scrape();
    if (!lead) return;
    const btn = document.createElement("div");
    btn.id = "leados-cars-cl-btn";
    btn.innerHTML = `
      <div style="
        position: fixed; bottom: 20px; right: 20px; z-index: 999999;
        background: #E05A1A; color: #fff; padding: 9px 16px;
        border-radius: 7px; font-size: 13px; font-weight: 600;
        cursor: pointer; box-shadow: 0 3px 16px #E05A1A44;
        display: flex; align-items: center; gap: 7px; font-family: sans-serif;
      " id="leados-cars-cl-inner">
        <span>⊕</span> Capture Auto Lead
      </div>
    `;
    document.body.appendChild(btn);
    btn.querySelector("#leados-cars-cl-inner").addEventListener("click", () => {
      chrome.runtime.sendMessage({ type: "QUICK_CAPTURE", lead });
    });
  }

  setTimeout(injectBtn, 1000);
})();
