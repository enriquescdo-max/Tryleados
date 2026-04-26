// LeadOS Chrome Extension — popup.js
const API_BASE = "https://tryleados-production.up.railway.app";
const DASHBOARD = "https://tryleados.com";

let currentLead = null;

document.addEventListener("DOMContentLoaded", async () => {
  // Load today's count
  const { todayLeads = 0 } = await chrome.storage.local.get("todayLeads");
  document.getElementById("todayCount").textContent = todayLeads;
  document.getElementById("dashLink").href = DASHBOARD;
  document.getElementById("dashLink").addEventListener("click", (e) => {
    e.preventDefault();
    chrome.tabs.create({ url: DASHBOARD });
  });

  // Try to get lead data from active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  // Ping the content script for lead data
  try {
    const resp = await chrome.tabs.sendMessage(tab.id, { type: "GET_LEAD_DATA" });
    if (resp && resp.lead) {
      showLead(resp.lead);
    }
  } catch (e) {
    // Content script not running on this tab — show no-detect state
    // Already visible by default
  }

  // Buttons
  document.getElementById("captureBtn").addEventListener("click", captureLead);
  document.getElementById("scoreBtn").addEventListener("click", scoreLead);
  document.getElementById("anotherBtn").addEventListener("click", resetToCapture);
});

function showLead(lead) {
  currentLead = lead;

  document.getElementById("noDetect").classList.remove("show");
  document.getElementById("detectedBanner").classList.add("show");
  document.getElementById("statusDot").classList.remove("inactive");

  // Set detected banner text
  document.getElementById("detectedText").textContent =
    `${lead.lifeEventLabel} detected · ${lead.source}`;

  // Build tags
  const tags = document.getElementById("leadTags");
  tags.innerHTML = `
    <span class="tag tag-event">${lead.lifeEventLabel}</span>
    <span class="tag tag-policy">${lead.policyNeed}</span>
    <span class="tag tag-source">${lead.source}</span>
  `;

  // Build fields
  const fields = document.getElementById("leadFields");
  const rows = [];
  if (lead.name) rows.push(["Name", lead.name]);
  if (lead.address) rows.push(["Address", lead.address]);
  if (lead.city) rows.push(["City", lead.city]);
  if (lead.zip) rows.push(["ZIP", lead.zip]);
  if (lead.price) rows.push(["Price", lead.price, true]);
  if (lead.vehicleYear) rows.push(["Vehicle", `${lead.vehicleYear} ${lead.vehicleMake || ""}`]);
  if (lead.bedrooms) rows.push(["Bedrooms", lead.bedrooms]);
  if (lead.sourceUrl) rows.push(["Source URL", lead.sourceUrl.substring(0, 38) + "…"]);

  fields.innerHTML = rows.map(([label, value, highlight]) => `
    <div class="field-row">
      <div class="field-label">${label}</div>
      <div class="field-value ${highlight ? "highlight" : ""}">${value}</div>
    </div>
  `).join("");

  // Set policy and event selects to detected values
  const policySelect = document.getElementById("policySelect");
  if (lead.policyNeedValue) policySelect.value = lead.policyNeedValue;

  const eventSelect = document.getElementById("eventSelect");
  if (lead.lifeEventValue) eventSelect.value = lead.lifeEventValue;

  // Show sections
  document.getElementById("leadCard").classList.add("show");
  document.getElementById("editSection").style.display = "block";
  document.getElementById("actionsSection").style.display = "flex";
}

async function captureLead() {
  if (!currentLead) return;

  const btn = document.getElementById("captureBtn");
  btn.disabled = true;
  btn.textContent = "Capturing…";

  const payload = {
    ...currentLead,
    policyNeed: document.getElementById("policySelect").value,
    lifeEvent: document.getElementById("eventSelect").value,
    note: document.getElementById("noteInput").value,
    capturedAt: new Date().toISOString(),
    capturedBy: "chrome_extension",
  };

  try {
    const res = await fetch(`${API_BASE}/api/v1/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let leadId = "LD-EXT";
    if (res.ok) {
      const data = await res.json();
      leadId = data.id || leadId;
    }

    // Increment today's count
    const { todayLeads = 0 } = await chrome.storage.local.get("todayLeads");
    const newCount = todayLeads + 1;
    await chrome.storage.local.set({
      todayLeads: newCount,
      lastCapturedAt: new Date().toISOString(),
    });
    document.getElementById("todayCount").textContent = newCount;

    // Show success
    document.getElementById("successId").textContent = leadId;
    document.getElementById("leadCard").classList.remove("show");
    document.getElementById("editSection").style.display = "none";
    document.getElementById("actionsSection").style.display = "none";
    document.getElementById("detectedBanner").classList.remove("show");
    document.getElementById("successState").classList.add("show");

    // Chrome notification
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "LeadOS: Lead Captured",
      message: `${currentLead.name || "Lead"} added to your pipeline. Heartbeat dials at 7am.`,
    });

  } catch (err) {
    btn.disabled = false;
    btn.textContent = "⊕ Capture Lead to LeadOS";
    alert("Failed to capture lead. Check your connection.");
  }
}

async function scoreLead() {
  if (!currentLead) return;

  const scoreBtn = document.getElementById("scoreBtn");
  scoreBtn.textContent = "Scoring…";
  scoreBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/v1/carrier-score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        zip_code: currentLead.zip || "78701",
        policy_type: document.getElementById("policySelect").value,
        life_event: document.getElementById("eventSelect").value,
        vehicle_year: currentLead.vehicleYear || null,
      }),
    });

    if (res.ok) {
      const data = await res.json();
      const top = data.results[0];
      scoreBtn.textContent = `◉ Best: ${top.carrier} (${top.score})`;
      scoreBtn.style.color = "#E05A1A";
    } else {
      scoreBtn.textContent = "◉ Score Carrier Fit";
    }
  } catch {
    scoreBtn.textContent = "◉ Score Carrier Fit";
  }
  scoreBtn.disabled = false;
}

function resetToCapture() {
  document.getElementById("successState").classList.remove("show");
  document.getElementById("noDetect").classList.add("show");
  currentLead = null;
}
