// LeadOS Content Script — Realtor.com
(function () {
  "use strict";
  function scrape() {
    const lead = {
      source: "Realtor.com",
      policyNeed: "Home",
      policyNeedValue: "home",
      lifeEventLabel: "New Homeowner",
      lifeEventValue: "new_homeowner",
      sourceUrl: window.location.href,
      name: "",
    };
    const addressEl = document.querySelector("h1[class*='address']") || document.querySelector("h1");
    if (addressEl) lead.address = addressEl.textContent.trim();
    const priceEl = document.querySelector("[data-testid='list-price']") || document.querySelector("[class*='price']");
    if (priceEl) lead.price = priceEl.textContent.trim();
    const zipMatch = window.location.href.match(/_(\d{5})_/);
    if (zipMatch) lead.zip = zipMatch[1];
    else if (lead.address) {
      const zm = lead.address.match(/\b(\d{5})\b/);
      if (zm) lead.zip = zm[1];
    }
    return lead.address ? lead : null;
  }
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "GET_LEAD_DATA") sendResponse({ lead: scrape() });
    return true;
  });
  setTimeout(() => {
    if (document.getElementById("leados-realtor-btn")) return;
    const lead = scrape();
    if (!lead) return;
    const btn = document.createElement("div");
    btn.id = "leados-realtor-btn";
    btn.innerHTML = `<div style="position:fixed;bottom:20px;right:20px;z-index:999999;background:#E05A1A;color:#fff;padding:9px 16px;border-radius:7px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 3px 16px #E05A1A44;display:flex;align-items:center;gap:7px;font-family:sans-serif;" id="ld-r-inner"><span>⊕</span> Capture to LeadOS</div>`;
    document.body.appendChild(btn);
    btn.querySelector("#ld-r-inner").addEventListener("click", () => chrome.runtime.sendMessage({ type: "QUICK_CAPTURE", lead }));
  }, 1200);
})();
