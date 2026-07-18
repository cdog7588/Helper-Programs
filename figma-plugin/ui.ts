const jsonFile = document.getElementById("jsonFile") as HTMLInputElement;
const endpointInput = document.getElementById("endpoint") as HTMLInputElement;
const jsonText = document.getElementById("jsonText") as HTMLTextAreaElement;
const status = document.getElementById("status") as HTMLDivElement;
const pollMsSelect = document.getElementById("pollMs") as HTMLSelectElement;
const autoApplyInput = document.getElementById("autoApply") as HTMLInputElement;

let pollTimer: number | null = null;
let lastPayloadSignature = "";

function setStatus(message: string): void {
  status.textContent = message;
}

function parsePayload(): unknown {
  return JSON.parse(jsonText.value);
}

function payloadSignature(value: unknown): string {
  return JSON.stringify(value);
}

function applyCurrentPayload(): void {
  try {
    const payload = parsePayload();
    parent.postMessage({ pluginMessage: { type: "apply-json", payload } }, "*");
    setStatus("Payload sent to plugin.");
  } catch (err) {
    setStatus(`Invalid JSON: ${(err as Error).message}`);
  }
}

async function fetchEndpointPayload(reason: "manual" | "live"): Promise<void> {
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

function stopLiveSync(): void {
  if (pollTimer !== null) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
  setStatus("Live sync stopped.");
}

function startLiveSync(): void {
  stopLiveSync();

  const pollMs = Number.parseInt(pollMsSelect.value, 10);
  const intervalMs = Number.isFinite(pollMs) ? Math.max(500, pollMs) : 3000;

  const tick = async () => {
    try {
      await fetchEndpointPayload("live");
    } catch (err) {
      setStatus(`Live sync failed: ${(err as Error).message}`);
    }
  };

  void tick();
  pollTimer = window.setInterval(() => {
    void tick();
  }, intervalMs);
  setStatus(`Live sync started (${intervalMs} ms).`);
}

(document.getElementById("loadFile") as HTMLButtonElement).onclick = async () => {
  const file = jsonFile.files?.[0];
  if (!file) {
    setStatus("Choose a JSON file first.");
    return;
  }
  const text = await file.text();
  jsonText.value = text;
  setStatus("Loaded JSON file.");
};

(document.getElementById("fetchEndpoint") as HTMLButtonElement).onclick = async () => {
  try {
    await fetchEndpointPayload("manual");
  } catch (err) {
    setStatus(`Fetch failed: ${(err as Error).message}`);
  }
};

(document.getElementById("apply") as HTMLButtonElement).onclick = () => {
  applyCurrentPayload();
};

(document.getElementById("startLive") as HTMLButtonElement).onclick = () => {
  startLiveSync();
};

(document.getElementById("stopLive") as HTMLButtonElement).onclick = () => {
  stopLiveSync();
};

window.addEventListener("beforeunload", () => {
  stopLiveSync();
});
