// LeadOS Background Service Worker
const API_BASE = "https://tryleados-production.up.railway.app";

// Quick capture from content script button
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "QUICK_CAPTURE") {
    quickCapture(msg.lead).then(result => sendResponse(result));
    return true;
  }
});

async function quickCapture(lead) {
  try {
    const payload = {
      ...lead,
      capturedAt: new Date().toISOString(),
      capturedBy: "chrome_extension_overlay",
    };

    const res = await fetch(`${API_BASE}/api/v1/leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = res.ok ? await res.json() : {};
    const leadId = data.id || "LD-EXT";

    // Increment counter
    const { todayLeads = 0 } = await chrome.storage.local.get("todayLeads");
    await chrome.storage.local.set({ todayLeads: todayLeads + 1 });

    // Notification
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "LeadOS ✓",
      message: `Lead captured: ${leadId}. Heartbeat dials at 7am.`,
    });

    return { success: true, leadId };
  } catch (err) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "LeadOS — Capture Failed",
      message: "Could not connect to LeadOS. Check your connection.",
    });
    return { success: false };
  }
}

// Reset daily lead counter at midnight
function scheduleReset() {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setHours(24, 0, 0, 0);
  const msUntilMidnight = midnight - now;

  setTimeout(async () => {
    await chrome.storage.local.set({ todayLeads: 0 });
    scheduleReset(); // reschedule for next midnight
  }, msUntilMidnight);
}

scheduleReset();
