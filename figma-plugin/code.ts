figma.showUI(__html__, { width: 460, height: 520 });

type JsonValue = string | number | boolean | null | JsonObject | JsonArray;
interface JsonObject { [key: string]: JsonValue; }
interface JsonArray extends Array<JsonValue> {}

interface CreateNodeSpec {
  type: "frame" | "rectangle" | "text";
  name: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  text?: string;
  fillHex?: string;
}

interface MediatorPayload {
  textBindings?: Record<string, string>;
  createNodes?: CreateNodeSpec[];
  [key: string]: JsonValue;
}

function hexToRgb(hex: string): RGB | null {
  const normalized = hex.trim().replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) {
    return null;
  }
  const r = parseInt(normalized.slice(0, 2), 16) / 255;
  const g = parseInt(normalized.slice(2, 4), 16) / 255;
  const b = parseInt(normalized.slice(4, 6), 16) / 255;
  return { r, g, b };
}

function findNodeByName(name: string): SceneNode | null {
  return figma.currentPage.findOne((node) => node.name === name) as SceneNode | null;
}

function findTextTarget(node: SceneNode): TextNode | null {
  if (node.type === "TEXT") {
    return node;
  }
  if ("findOne" in node) {
    const child = node.findOne((n) => n.type === "TEXT");
    if (child && child.type === "TEXT") {
      return child;
    }
  }
  return null;
}

async function setTextOnNamedNode(nodeName: string, value: string): Promise<boolean> {
  const target = findNodeByName(nodeName);
  if (!target) {
    return false;
  }

  const textNode = findTextTarget(target);
  if (!textNode) {
    return false;
  }

  await figma.loadFontAsync(textNode.fontName as FontName);
  textNode.characters = value;
  return true;
}

function normalizeTextBindings(payload: MediatorPayload): Record<string, string> {
  if (payload.textBindings && typeof payload.textBindings === "object") {
    return payload.textBindings;
  }

  const inferred: Record<string, string> = {};
  for (const [key, value] of Object.entries(payload)) {
    if (typeof value !== "string") {
      continue;
    }
    if (
      key.startsWith("panel_") ||
      key.startsWith("status_") ||
      key.startsWith("log_") ||
      key.startsWith("input_") ||
      key.startsWith("meta_")
    ) {
      inferred[key] = value;
    }
  }
  return inferred;
}

async function applyCreateNode(spec: CreateNodeSpec): Promise<void> {
  const x = spec.x ?? 0;
  const y = spec.y ?? 0;
  const width = spec.width ?? 240;
  const height = spec.height ?? 96;

  if (spec.type === "frame") {
    const node = figma.createFrame();
    node.name = spec.name;
    node.x = x;
    node.y = y;
    node.resize(width, height);
    const rgb = spec.fillHex ? hexToRgb(spec.fillHex) : null;
    if (rgb) {
      node.fills = [{ type: "SOLID", color: rgb }];
    }
    figma.currentPage.appendChild(node);
    return;
  }

  if (spec.type === "rectangle") {
    const node = figma.createRectangle();
    node.name = spec.name;
    node.x = x;
    node.y = y;
    node.resize(width, height);
    const rgb = spec.fillHex ? hexToRgb(spec.fillHex) : null;
    if (rgb) {
      node.fills = [{ type: "SOLID", color: rgb }];
    }
    figma.currentPage.appendChild(node);
    return;
  }

  const node = figma.createText();
  node.name = spec.name;
  node.x = x;
  node.y = y;
  node.resize(width, height);
  await figma.loadFontAsync(node.fontName as FontName);
  node.characters = spec.text ?? spec.name;
  figma.currentPage.appendChild(node);
}

async function applyPayload(payload: MediatorPayload): Promise<void> {
  const textBindings = normalizeTextBindings(payload);
  const bindingEntries = Object.entries(textBindings);

  let updated = 0;
  for (const [name, value] of bindingEntries) {
    if (await setTextOnNamedNode(name, value)) {
      updated += 1;
    }
  }

  const createNodes = Array.isArray(payload.createNodes) ? payload.createNodes : [];
  for (const item of createNodes) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const nodeSpec = item as unknown as CreateNodeSpec;
    if (!nodeSpec.type || !nodeSpec.name) {
      continue;
    }
    await applyCreateNode(nodeSpec);
  }

  figma.notify(`Mediator sync applied: ${updated} text bindings, ${createNodes.length} creates`);
}

figma.ui.onmessage = async (msg: { type?: string; payload?: MediatorPayload }) => {
  if (msg.type !== "apply-json" || !msg.payload) {
    return;
  }

  try {
    await applyPayload(msg.payload);
  } catch (err) {
    figma.notify(`Mediator sync failed: ${(err as Error).message}`);
  }
};
