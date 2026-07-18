const jsonFile = document.getElementById("jsonFile") as HTMLInputElement;
const endpointInput = document.getElementById("endpoint") as HTMLInputElement;
const jsonText = document.getElementById("jsonText") as HTMLTextAreaElement;
const status = document.getElementById("status") as HTMLDivElement;

function setStatus(message: string): void {
  status.textContent = message;
}

function parsePayload(): unknown {
  return JSON.parse(jsonText.value);
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
    const response = await fetch(endpointInput.value.trim(), { method: "GET" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    jsonText.value = JSON.stringify(data, null, 2);
    setStatus("Fetched payload from endpoint.");
  } catch (err) {
    setStatus(`Fetch failed: ${(err as Error).message}`);
  }
};

(document.getElementById("apply") as HTMLButtonElement).onclick = () => {
  try {
    const payload = parsePayload();
    parent.postMessage({ pluginMessage: { type: "apply-json", payload } }, "*");
    setStatus("Payload sent to plugin.");
  } catch (err) {
    setStatus(`Invalid JSON: ${(err as Error).message}`);
  }
};
