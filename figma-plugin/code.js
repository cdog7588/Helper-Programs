figma.showUI(__html__, { width: 460, height: 520 });

function hexToRgb(hex) {
  const normalized = hex.trim().replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) {
    return null;
  }
  const r = parseInt(normalized.slice(0, 2), 16) / 255;
  const g = parseInt(normalized.slice(2, 4), 16) / 255;
  const b = parseInt(normalized.slice(4, 6), 16) / 255;
  return { r, g, b };
}

function findNodeByName(name) {
  return figma.currentPage.findOne((node) => node.name === name);
}

function findNodesByName(name) {
  return figma.currentPage.findAll((node) => node.name === name);
}

function nearestGrid(value, gridSize) {
  if (gridSize <= 1) {
    return value;
  }
  return Math.round(value / gridSize) * gridSize;
}

function normalizeSpec(spec, rules) {
  const gridSize = Math.max(1, Number((rules && rules.gridSize) ?? 1));
  const padding = Math.max(0, Number((rules && rules.padding) ?? 0));
  const alignment = (rules && rules.alignment) ?? "left";

  let x = nearestGrid(spec.x, gridSize);
  let y = nearestGrid(spec.y, gridSize);
  const width = Math.max(gridSize, nearestGrid(spec.width, gridSize));
  const height = Math.max(gridSize, nearestGrid(spec.height, gridSize));

  const viewport = figma.viewport.bounds;
  if (alignment === "center") {
    x = nearestGrid(viewport.x + viewport.width / 2 - width / 2, gridSize);
  } else if (alignment === "right") {
    x = nearestGrid(viewport.x + viewport.width - padding - width, gridSize);
  }

  y = y + padding;
  return { ...spec, x, y, width, height };
}

function findTextTarget(node) {
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

async function setTextOnNamedNode(nodeName, value) {
  const target = findNodeByName(nodeName);
  if (!target) {
    return false;
  }

  const textNode = findTextTarget(target);
  if (!textNode) {
    return false;
  }

  await figma.loadFontAsync(textNode.fontName);
  textNode.characters = value;
  return true;
}

function applyNodeStyle(node, style) {
  if (!style) {
    return;
  }
  const fill = style.fill ? hexToRgb(style.fill) : null;
  const stroke = style.stroke ? hexToRgb(style.stroke) : null;

  if (fill && "fills" in node) {
    node.fills = [{ type: "SOLID", color: fill }];
  }
  if (stroke && "strokes" in node) {
    node.strokes = [{ type: "SOLID", color: stroke }];
    if ("strokeWeight" in node) {
      node.strokeWeight = 1;
    }
  }
}

function normalizeTextBindings(payload) {
  if (payload.textBindings && typeof payload.textBindings === "object") {
    return payload.textBindings;
  }

  const inferred = {};
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

async function applyCreateNode(spec, rules) {
  const normalized = normalizeSpec(spec, rules);
  const { x, y, width, height } = normalized;

  if (normalized.type === "FRAME") {
    const frame = figma.createFrame();
    frame.name = normalized.name;
    frame.x = x;
    frame.y = y;
    frame.resize(width, height);
    applyNodeStyle(frame, normalized.style);

    if (normalized.text) {
      const textNode = figma.createText();
      await figma.loadFontAsync(textNode.fontName);
      textNode.characters = normalized.text;
      textNode.x = 12;
      textNode.y = 12;
      if (normalized.style && normalized.style.fontSize) {
        textNode.fontSize = normalized.style.fontSize;
      }
      frame.appendChild(textNode);
    }
    figma.currentPage.appendChild(frame);
    return;
  }

  if (normalized.type === "COMPONENT") {
    const component = figma.createComponent();
    component.name = normalized.name;
    component.x = x;
    component.y = y;
    component.resize(width, height);
    applyNodeStyle(component, normalized.style);

    if (normalized.text) {
      const textNode = figma.createText();
      await figma.loadFontAsync(textNode.fontName);
      textNode.characters = normalized.text;
      textNode.x = 12;
      textNode.y = 12;
      if (normalized.style && normalized.style.fontSize) {
        textNode.fontSize = normalized.style.fontSize;
      }
      component.appendChild(textNode);
    }
    figma.currentPage.appendChild(component);
    return;
  }

  if (normalized.type === "RECTANGLE") {
    const rect = figma.createRectangle();
    rect.name = normalized.name;
    rect.x = x;
    rect.y = y;
    rect.resize(width, height);
    applyNodeStyle(rect, normalized.style);
    figma.currentPage.appendChild(rect);
    return;
  }

  const textNode = figma.createText();
  textNode.name = normalized.name;
  textNode.x = x;
  textNode.y = y;
  textNode.resize(width, height);
  await figma.loadFontAsync(textNode.fontName);
  textNode.characters = normalized.text ?? normalized.name;
  if (normalized.style && normalized.style.fontSize) {
    textNode.fontSize = normalized.style.fontSize;
  }
  applyNodeStyle(textNode, normalized.style);
  figma.currentPage.appendChild(textNode);
}

async function deleteNodeByName(nodeName) {
  const target = findNodeByName(nodeName);
  if (!target) {
    return false;
  }
  target.remove();
  return true;
}

function defaultTabOrigin(index) {
  return {
    x: 48 + index * 220,
    y: 40,
    width: 200,
    height: 52,
  };
}

function defaultPanelOrigin(index) {
  return {
    x: 48 + (index % 3) * 360,
    y: 130 + Math.floor(index / 3) * 220,
    width: 336,
    height: 190,
  };
}

function ensureFrameNode(name, index, kind) {
  const existing = findNodeByName(name);
  if (existing && existing.type === "FRAME") {
    return existing;
  }

  const frame = figma.createFrame();
  frame.name = name;
  const origin = kind === "tab" ? defaultTabOrigin(index) : defaultPanelOrigin(index);
  frame.x = origin.x;
  frame.y = origin.y;
  frame.resize(origin.width, origin.height);
  frame.fills = [{ type: "SOLID", color: { r: 0.08, g: 0.11, b: 0.17 } }];
  frame.strokes = [{ type: "SOLID", color: { r: 0.18, g: 0.24, b: 0.34 } }];
  frame.strokeWeight = 1;
  figma.currentPage.appendChild(frame);
  return frame;
}

async function ensureHiddenDetectionLayer(tabName) {
  const tabNode = findNodeByName(tabName);
  if (!tabNode || tabNode.type !== "FRAME") {
    return false;
  }

  const markerName = `${tabName}__detect`;
  const already = tabNode.findOne((node) => node.name === markerName);
  if (already) {
    already.visible = false;
    return true;
  }

  const marker = figma.createText();
  marker.name = markerName;
  await figma.loadFontAsync(marker.fontName);
  marker.characters = tabName;
  marker.x = 2;
  marker.y = 2;
  marker.visible = false;
  tabNode.appendChild(marker);
  return true;
}

function applyRenameMap(renameMap) {
  let renamed = 0;
  for (const [from, to] of Object.entries(renameMap)) {
    const targets = findNodesByName(from);
    for (const node of targets) {
      if (node.name !== to) {
        node.name = to;
        renamed += 1;
      }
    }
  }
  return renamed;
}

async function applyRewritePayload(payload) {
  const renameMap = payload.rename ?? {};
  const panelRenameMap = payload.panelRename ?? {};
  const hiddenTargets = Array.isArray(payload.createHiddenLayers) ? payload.createHiddenLayers : [];
  const autoCreateTabs = Array.isArray(payload.autoCreate?.tabs) ? payload.autoCreate.tabs : [];
  const autoCreatePanels = Array.isArray(payload.autoCreate?.panels) ? payload.autoCreate.panels : [];

  const renamedTabs = applyRenameMap(renameMap);
  const renamedPanels = applyRenameMap(panelRenameMap);

  let createdTabs = 0;
  autoCreateTabs.forEach((name, index) => {
    if (!findNodeByName(name)) {
      ensureFrameNode(name, index, "tab");
      createdTabs += 1;
    }
  });

  let createdPanels = 0;
  autoCreatePanels.forEach((name, index) => {
    if (!findNodeByName(name)) {
      ensureFrameNode(name, index, "panel");
      createdPanels += 1;
    }
  });

  let hiddenCreated = 0;
  for (const tabName of hiddenTargets) {
    if (await ensureHiddenDetectionLayer(tabName)) {
      hiddenCreated += 1;
    }
  }

  return `rewrite applied: renamed=${renamedTabs + renamedPanels}, createdTabs=${createdTabs}, createdPanels=${createdPanels}, hiddenMarkers=${hiddenCreated}`;
}

function normalizeCreateSpecs(payload) {
  if (Array.isArray(payload.componentCreate)) {
    return payload.componentCreate;
  }

  const legacy = Array.isArray(payload.createNodes) ? payload.createNodes : [];
  return legacy.map((item) => ({
    name: item.name,
    type: String(item.type).toUpperCase(),
    x: item.x ?? 0,
    y: item.y ?? 0,
    width: item.width ?? 240,
    height: item.height ?? 96,
    text: item.text,
    style: item.fillHex ? { fill: item.fillHex } : undefined,
  }));
}

async function applyPayload(payload) {
  const operation = (payload.meta && payload.meta.operation) ?? "update";

  if (operation === "rewrite") {
    const result = await applyRewritePayload(payload);
    figma.notify(`Mediator sync ${result}`);
    return;
  }

  const textBindings = normalizeTextBindings(payload);
  const bindingEntries = Object.entries(textBindings);
  const createSpecs = normalizeCreateSpecs(payload);
  const layoutRules = payload.layoutRules;

  if (operation === "delete") {
    let removed = 0;
    for (const [name] of bindingEntries) {
      if (await deleteNodeByName(name)) {
        removed += 1;
      }
    }
    for (const spec of createSpecs) {
      if (await deleteNodeByName(spec.name)) {
        removed += 1;
      }
    }
    figma.notify(`Mediator sync delete applied: ${removed} nodes removed`);
    return;
  }

  let updated = 0;
  for (const [name, value] of bindingEntries) {
    if (await setTextOnNamedNode(name, value)) {
      updated += 1;
    }
  }

  let created = 0;
  if (operation === "create" || operation === "update") {
    for (const spec of createSpecs) {
      if (!spec || !spec.type || !spec.name) {
        continue;
      }
      await applyCreateNode(spec, layoutRules);
      created += 1;
    }
  }

  figma.notify(`Mediator sync ${operation} applied: ${updated} text bindings, ${created} creates`);
}

figma.ui.onmessage = async (msg) => {
  if (msg.type !== "apply-json" || !msg.payload) {
    return;
  }

  try {
    await applyPayload(msg.payload);
  } catch (err) {
    figma.notify(`Mediator sync failed: ${err.message}`);
  }
};
