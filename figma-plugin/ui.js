const jsonFile = document.getElementById("jsonFile");
const endpointInput = document.getElementById("endpoint");
const jsonText = document.getElementById("jsonText");
const status = document.getElementById("status");
const pollMsSelect = document.getElementById("pollMs");
const autoApplyInput = document.getElementById("autoApply");

let pollTimer = null;
let lastPayloadSignature = "";

function setStatus(message) {
  status.textContent = message;
}

function parsePayload() {
  return JSON.parse(jsonText.value);
}

function payloadSignature(value) {
  return JSON.stringify(value);
}

function applyCurrentPayload() {
  try {
    const payload = parsePayload();
    parent.postMessage({ pluginMessage: { type: "apply-json", payload } }, "*");
    setStatus("Payload sent to plugin.");
  } catch (err) {
    setStatus(`Invalid JSON: ${err.message}`);
  }
}

async function fetchEndpointPayload(reason) {
  const response = await fetch(endpointInput.value.trim(), { method: "GET" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const data = await response.json();
  const signature = payloadSignature(data);
  const changed = signature !== lastPayloadSignature;
  jsonText.value = JSON.stringify(data, null, 2);
  lastPayloadSignature = signature;

  if (reason === "manual") {
    setStatus("Fetched payload from endpoint.");
    return;
  }

  if (!changed) {
    setStatus("Live sync: no change.");
    return;
  }

  if (autoApplyInput.checked) {
    applyCurrentPayload();
    setStatus("Live sync: fetched and auto-applied.");
  } else {
    setStatus("Live sync: fetched new payload.");
  }
}

function stopLiveSync() {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
  setStatus("Live sync stopped.");
}

function startLiveSync() {
  stopLiveSync();

  const pollMs = Number.parseInt(pollMsSelect.value, 10);
  const intervalMs = Number.isFinite(pollMs) ? Math.max(500, pollMs) : 3000;

  const tick = async () => {
    try {
      await fetchEndpointPayload("live");
    } catch (err) {
      setStatus(`Live sync failed: ${err.message}`);
    }
  };

  void tick();
  pollTimer = window.setInterval(() => {
    void tick();
  }, intervalMs);
  setStatus(`Live sync started (${intervalMs} ms).`);
}

document.getElementById("loadFile").onclick = async () => {
  const file = jsonFile.files && jsonFile.files[0];
  if (!file) {
    setStatus("Choose a JSON file first.");
    return;
  }
  const text = await file.text();
  jsonText.value = text;
  setStatus("Loaded JSON file.");
};

document.getElementById("fetchEndpoint").onclick = async () => {
  try {
    await fetchEndpointPayload("manual");
  } catch (err) {
    setStatus(`Fetch failed: ${err.message}`);
  }
};

document.getElementById("apply").onclick = () => {
  applyCurrentPayload();
};

document.getElementById("startLive").onclick = () => {
  startLiveSync();
};

document.getElementById("stopLive").onclick = () => {
  stopLiveSync();
};

window.addEventListener("beforeunload", () => {
  stopLiveSync();
});
