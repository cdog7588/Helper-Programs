const jsonFile = document.getElementById("jsonFile");
const endpointInput = document.getElementById("endpoint");
const jsonText = document.getElementById("jsonText");
const status = document.getElementById("status");

function setStatus(message) {
  status.textContent = message;
}

function parsePayload() {
  return JSON.parse(jsonText.value);
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
    const response = await fetch(endpointInput.value.trim(), { method: "GET" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    jsonText.value = JSON.stringify(data, null, 2);
    setStatus("Fetched payload from endpoint.");
  } catch (err) {
    setStatus(`Fetch failed: ${err.message}`);
  }
};

document.getElementById("apply").onclick = () => {
  try {
    const payload = parsePayload();
    parent.postMessage({ pluginMessage: { type: "apply-json", payload } }, "*");
    setStatus("Payload sent to plugin.");
  } catch (err) {
    setStatus(`Invalid JSON: ${err.message}`);
  }
};
