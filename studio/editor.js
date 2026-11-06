(() => {
  const $ = id => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const canvas = $("canvas"), wrap = $("canvasWrap"), overlay = $("overlay");
  const stage = $("stage"), gridEl = $("grid"), propsEl = $("props");
  const layersEl = $("layers"), galleryEl = $("iconGallery");
  const ROLES = ["ink", "ivory", "muted", "rule", "off", "amber", "red",
    "green", "blue", "violet", "dim"];
  const FIELDS = ["none", "v", "r", "rm", "g", "gas", "brk", "clu", "hb",
    "fuel", "fp", "fpl", "laps", "low", "high", "L", "R", "haz", "pit",
    "pitlane", "tc", "abs", "esc", "lim", "up", "run", "ign", "wt", "ot",
    "op", "boost", "at", "lap", "last", "best", "delta", "valid", "pos",
    "nd", "npos", "tcl", "absl", "bb", "car", "track", "cfg", "mode",
    "game", "game_id"];
  const FORMATS = ["int", "float1", "float2", "time", "clock", "delta",
    "gear", "text", "percent"];
  const UNITS = ["auto", "kmh", "mph", "c", "f", "l", "bar", "percent",
    "none"];
  const TYPE_LABELS = {
    value: "Value", text: "Text", gauge: "Gauge", bar: "Bar",
    icon: "Icon", image: "Image", shape: "Shape", map: "Map",
    media: "Media", clock: "Clock", shiftlights: "Shift lights",
    gearstrip: "Gear strip",
  };
  const DEFAULTS = {
    value: { w: 220, h: 90, label: "SPEED", field: "v", format: "int",
      unit: "auto", size: 64, color: "ivory", labelColor: "muted",
      unitColor: "muted", weight: 700, align: "left" },
    text: { w: 220, h: 44, text: "TEXT", label: "", size: 24,
      color: "ivory", align: "left", weight: 700 },
    gauge: { w: 260, h: 260, field: "r", maxField: "rm", max: 10000,
      min: 0, redline: .89, label: "RPM", color: "ivory",
      accent: "amber", bg: "off", labelColor: "muted", showValue: true,
      needle: false, format: "int", unit: "none", size: 48,
      labelSize: 10, weight: 700 },
    bar: { w: 220, h: 46, field: "fuel", min: 0, max: 60,
      maxField: "none", orientation: "horizontal", label: "FUEL",
      color: "amber", trackColor: "off", showValue: true,
      format: "float1", unit: "l", size: 18, labelSize: 10 },
    icon: { w: 44, h: 44, icon: "low-beam", field: "low",
      onColor: "green", offColor: "dim", showOff: true },
    image: { w: 96, h: 96, src: "", fit: "contain" },
    shape: { w: 300, h: 120, shape: "rect", fill: "off", stroke: "rule",
      strokeWidth: 1, radius: 14 },
    map: { w: 260, h: 260, field: "npos", color: "amber",
      roadColor: "dim", dotColor: "amber", showDot: true },
    media: { w: 280, h: 260, showControls: true, showTimeline: true },
    clock: { w: 180, h: 62, showDate: true, showTime: true,
      locale: "en-US", size: 22, color: "ivory", labelSize: 10 },
    shiftlights: { w: 330, h: 24, field: "r", maxField: "rm", count: 27,
      low: .72, high: .98 },
    gearstrip: { w: 220, h: 40, field: "g", count: 8, color: "muted",
      accent: "amber", size: 14, format: "gear", unit: "none" },
  };

  let layout = null, selected = null, theme = null, themes = {},
      customIcons = [], iconTab = "builtin", iconQuery = "";
  let view = null, scale = 1, undoStack = [], redoStack = [], dirty = false;
  let live = false, liveState = null, liveES = null, lastLive = 0;
  let propFocus = false, dragging = false, toastTimer = 0;
  const demoMedia = {
    ok: true, title: "Somewhere", artist: "Blu Mar Ten",
    album: "Somewhere", source: "Cider", playing: true,
    position: 9, duration: 193, has_art: true,
    art_url: window.IDashStudio.DEMO_ART, stalled: false,
    at: performance.now() - 9000,
  };
  const demoAction = () => {};
  function previewMedia(now) {
    return Object.assign({}, demoMedia, {
      position: (now / 1000) % demoMedia.duration,
      at: now, playing: true, stalled: false,
    });
  }

  function toast(msg, err) {
    const el = $("toast");
    el.textContent = msg;
    el.className = "show" + (err ? " err" : "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.className = ""; }, 3200);
  }
  const clone = o => JSON.parse(JSON.stringify(o));
  function markDirty() { dirty = true; }
  function pushUndo() {
    undoStack.push(JSON.stringify(layout));
    if (undoStack.length > 60) undoStack.shift();
    redoStack.length = 0;
  }
  function undo() {
    if (!undoStack.length) return;
    redoStack.push(JSON.stringify(layout));
    layout = JSON.parse(undoStack.pop());
    if (!layout.widgets.some(w => w.id === selected)) selected = null;
    renderAll();
  }
  function redo() {
    if (!redoStack.length) return;
    undoStack.push(JSON.stringify(layout));
    layout = JSON.parse(redoStack.pop());
    if (!layout.widgets.some(w => w.id === selected)) selected = null;
    renderAll();
  }

  function renderAll() {
    renderCanvas();
    renderOverlay();
    renderProps();
    renderLayers();
    renderLayoutProps();
    renderHeader();
    applyGrid();
  }
  function renderHeader() {
    $("name").value = layout.name || "";
    $("category").value = layout.category || "custom";
  }
  function applyGrid() {
    const g = (layout.canvas && layout.canvas.grid) || 16;
    wrap.style.setProperty("--grid", g + "px");
    $("gridLabel").textContent = g;
    gridEl.classList.toggle("off", !!layout.hideGrid || layout.kind === "simhub");
  }
  function renderCanvas() {
    if (layout.kind === "simhub" && window.IDashSimhub) {
      view = window.IDashSimhub.render(canvas, layout, {});
      updatePreview(performance.now());
      return;
    }
    const C = theme && theme.colors || window.IDashStudio.DEFAULT_THEME.colors;
    view = window.IDashStudio.render(canvas, layout, {
      C, theme: theme || window.IDashStudio.DEFAULT_THEME,
      icons: window.IDashIcons, mediaAction: demoAction,
      media: demoMedia, preview: true,
    });
    updatePreview(performance.now());
  }
  function updatePreview(now) {
    if (!view) return;
    const useLive = live && liveState && now - lastLive < 4000;
    const state = useLive ? liveState :
      window.IDashStudio.demoState(now / 1000);
    view.update(state, now, previewMedia(now));
  }
  function tick(now) {
    updatePreview(now);
    requestAnimationFrame(tick);
  }

  function renderOverlay() {
    overlay.textContent = "";
    if (layout.kind === "simhub") return;
    for (const w of layout.widgets || []) {
      if (w.visible === false) continue;
      const box = document.createElement("div");
      box.className = "wbox" + (w.id === selected ? " selected" : "");
      box.style.left = w.x + "px";
      box.style.top = w.y + "px";
      box.style.width = w.w + "px";
      box.style.height = w.h + "px";
      if (w.rotation) box.style.transform = "rotate(" + w.rotation + "deg)";
      box.dataset.id = w.id;
      box.addEventListener("pointerdown", e => startDrag(e, w, "move"));
      if (w.id === selected) {
        for (const h of ["nw", "n", "ne", "e", "se", "s", "sw", "w"]) {
          const handle = document.createElement("div");
          handle.className = "handle";
          handle.dataset.h = h;
          handle.addEventListener("pointerdown", e => startDrag(e, w, h));
          box.appendChild(handle);
        }
      }
      overlay.appendChild(box);
    }
  }

  function snap(v) {
    const g = (layout.canvas && layout.canvas.grid) || 16;
    return Math.round(v / g) * g;
  }
  function canvasPoint(e) {
    const r = canvas.getBoundingClientRect();
    const s = r.width / 1024;
    return { x: (e.clientX - r.left) / s, y: (e.clientY - r.top) / s, s };
  }
  function startDrag(e, w, mode) {
    if (e.button !== undefined && e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    select(w.id);
    pushUndo();
    const p = canvasPoint(e);
    const st = { mx: p.x, my: p.y, x: w.x, y: w.y, w: w.w, h: w.h,
      id: w.id, mode };
    let moved = false;
    function onMove(ev) {
      const q = canvasPoint(ev);
      let dx = q.x - st.mx, dy = q.y - st.my;
      const item = layout.widgets.find(x => x.id === st.id);
      if (!item) return;
      moved = true;
      if (mode === "move") {
        item.x = clamp(snap(st.x + dx), 0, 1024 - item.w);
        item.y = clamp(snap(st.y + dy), 0, 600 - item.h);
      } else {
        let x = st.x, y = st.y, ww = st.w, hh = st.h;
        if (mode.includes("e")) ww = st.w + dx;
        if (mode.includes("s")) hh = st.h + dy;
        if (mode.includes("w")) { x = st.x + dx; ww = st.w - dx; }
        if (mode.includes("n")) { y = st.y + dy; hh = st.h - dy; }
        x = snap(x); y = snap(y); ww = snap(ww); hh = snap(hh);
        if (ww < 8) { ww = 8; }
        if (hh < 8) { hh = 8; }
        if (x < 0) { ww += x; x = 0; }
        if (y < 0) { hh += y; y = 0; }
        if (x + ww > 1024) ww = 1024 - x;
        if (y + hh > 600) hh = 600 - y;
        item.x = x; item.y = y; item.w = Math.max(8, ww);
        item.h = Math.max(8, hh);
      }
      renderCanvas(); renderOverlay();
    }
    function onUp() {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      if (moved) { markDirty(); renderProps(); renderLayers(); }
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  function select(id) {
    selected = id;
    renderOverlay();
    renderProps();
    renderLayers();
  }

  /* ---------------- properties ---------------- */
  function row(label, node) {
    const d = document.createElement("label");
    d.className = "prop-row";
    const s = document.createElement("span");
    s.textContent = label;
    d.append(s, node);
    return d;
  }
  function textInput(value, on) {
    const i = document.createElement("input");
    i.type = "text";
    i.value = value == null ? "" : value;
    i.addEventListener("input", () => on(i.value));
    return i;
  }
  function textArea(value, on) {
    const i = document.createElement("textarea");
    i.value = value == null ? "" : value;
    i.addEventListener("input", () => on(i.value));
    return i;
  }
  function numInput(value, on, step = 1, min = null, max = null) {
    const i = document.createElement("input");
    i.type = "number";
    i.value = value == null ? 0 : value;
    i.step = step;
    if (min != null) i.min = min;
    if (max != null) i.max = max;
    i.addEventListener("input", () => {
      const v = parseFloat(i.value);
      if (!Number.isNaN(v)) on(v);
    });
    return i;
  }
  function selInput(value, options, on) {
    const s = document.createElement("select");
    options.forEach(o => {
      const opt = document.createElement("option");
      if (Array.isArray(o)) { opt.value = o[0]; opt.textContent = o[1]; }
      else { opt.value = o; opt.textContent = o; }
      s.appendChild(opt);
    });
    s.value = value == null ? options[0] : value;
    s.addEventListener("change", () => on(s.value));
    return s;
  }
  function checkInput(value, on) {
    const i = document.createElement("input");
    i.type = "checkbox";
    i.checked = value !== false;
    i.addEventListener("change", () => on(i.checked));
    return i;
  }
  function colorInput(value, on) {
    const wrap = document.createElement("div");
    wrap.className = "color-row";
    const t = document.createElement("input");
    t.type = "text";
    t.value = value || "ivory";
    t.placeholder = "amber or #ff9a2e";
    const c = document.createElement("input");
    c.type = "color";
    const resolved = resolveColor(t.value);
    c.value = /^#[0-9a-fA-F]{6}$/.test(resolved) ? resolved : "#ffffff";
    t.addEventListener("input", () => {
      const v = t.value.trim();
      if (ROLES.includes(v) || /^#[0-9a-fA-F]{6}$/.test(v)) {
        on(v);
        const r = resolveColor(v);
        if (/^#[0-9a-fA-F]{6}$/.test(r)) c.value = r;
      }
    });
    c.addEventListener("input", () => {
      t.value = c.value;
      on(c.value);
    });
    wrap.append(t, c);
    return wrap;
  }
  function resolveColor(v) {
    if (theme && theme.colors && theme.colors[v]) return theme.colors[v];
    return v;
  }
  function commit(w) {
    markDirty();
    renderCanvas();
    renderOverlay();
    renderLayers();
  }
  function set(w, key, value) {
    w[key] = value;
    commit(w);
  }

  function renderProps() {
    propsEl.textContent = "";
    const w = (layout.widgets || []).find(x => x.id === selected);
    if (!w) {
      const p = document.createElement("p");
      p.className = "empty";
      p.textContent = layout.kind === "simhub" ?
        "SimHub faithful mode: le design d'origine est conservé, les widgets ne sont pas éditables." :
        "Select a widget on the canvas.";
      propsEl.appendChild(p);
      return;
    }
    const common = document.createElement("div");
    common.appendChild(row("X", numInput(w.x, v => set(w, "x", v), 1, 0, 1024)));
    common.appendChild(row("Y", numInput(w.y, v => set(w, "y", v), 1, 0, 600)));
    common.appendChild(row("Width", numInput(w.w, v => set(w, "w", v), 1, 8, 1024)));
    common.appendChild(row("Height", numInput(w.h, v => set(w, "h", v), 1, 8, 600)));
    common.appendChild(row("Opacity", numInput(w.opacity == null ? 1 : w.opacity, v => set(w, "opacity", v), .05, 0, 1)));
    common.appendChild(row("Rotation", numInput(w.rotation || 0, v => set(w, "rotation", v), 1, -360, 360)));
    if (["value", "gauge", "bar", "shiftlights"].includes(w.type)) {
      common.appendChild(row("Scale", numInput(w.scale == null ? 1 : w.scale, v => set(w, "scale", v), .01, -1000, 1000)));
      common.appendChild(row("Offset", numInput(w.offset || 0, v => set(w, "offset", v), 1, -100000, 100000)));
    }
    common.appendChild(row("Visible", checkInput(w.visible, v => set(w, "visible", v))));
    propsEl.appendChild(common);
    const sep = document.createElement("div");
    sep.className = "prop-sep";
    propsEl.appendChild(sep);

    const add = (label, node) => propsEl.appendChild(row(label, node));
    if (w.type === "value" || w.type === "text" || w.type === "gauge" ||
        w.type === "bar" || w.type === "clock" || w.type === "gearstrip") {
      add("Label", textInput(w.label, v => set(w, "label", v)));
      add("Field", selInput(w.field, FIELDS, v => set(w, "field", v)));
      add("Format", selInput(w.format, FORMATS, v => set(w, "format", v)));
      add("Unit", selInput(w.unit, UNITS, v => set(w, "unit", v)));
      add("Size", numInput(w.size, v => set(w, "size", v), 1, 6, 300));
      add("Label size", numInput(w.labelSize, v => set(w, "labelSize", v), 1, 6, 80));
      add("Weight", numInput(w.weight, v => set(w, "weight", v), 100, 100, 900));
      add("Font", textInput(w.font, v => set(w, "font", v)));
      add("Align", selInput(w.align, ["left", "center", "right"], v => set(w, "align", v)));
      add("Color", colorInput(w.color, v => set(w, "color", v)));
      add("Label color", colorInput(w.labelColor, v => set(w, "labelColor", v)));
      add("Unit color", colorInput(w.unitColor, v => set(w, "unitColor", v)));
      if (w.type === "value" || w.type === "bar") {
        add("Thresholds", textInput(JSON.stringify(w.thresholds || []), v => {
          try {
            const arr = JSON.parse(v);
            if (Array.isArray(arr)) set(w, "thresholds", arr);
          } catch (e) {}
        }));
      }
    }
    if (w.type === "text") {
      add("Text", textArea(w.text, v => set(w, "text", v)));
      add("Letter spacing", numInput(w.letterSpacing || 0, v => set(w, "letterSpacing", v), .5, -5, 20));
    }
    if (w.type === "gauge") {
      add("Max field", selInput(w.maxField, FIELDS, v => set(w, "maxField", v)));
      add("Max", numInput(w.max, v => set(w, "max", v), 1));
      add("Min", numInput(w.min, v => set(w, "min", v), 1));
      add("Redline", numInput(w.redline, v => set(w, "redline", v), .01, 0, 1));
      add("Accent", colorInput(w.accent, v => set(w, "accent", v)));
      add("Face", colorInput(w.bg, v => set(w, "bg", v)));
      add("Show value", checkInput(w.showValue, v => set(w, "showValue", v)));
      add("Needle", checkInput(w.needle, v => set(w, "needle", v)));
    }
    if (w.type === "bar") {
      add("Max field", selInput(w.maxField, FIELDS, v => set(w, "maxField", v)));
      add("Max", numInput(w.max, v => set(w, "max", v), 1));
      add("Min", numInput(w.min, v => set(w, "min", v), 1));
      add("Orientation", selInput(w.orientation, ["horizontal", "vertical"], v => set(w, "orientation", v)));
      add("Track", colorInput(w.trackColor, v => set(w, "trackColor", v)));
      add("Show value", checkInput(w.showValue, v => set(w, "showValue", v)));
    }
    if (w.type === "icon") {
      add("Icon", textInput(w.icon, v => set(w, "icon", v)));
      add("Field", selInput(w.field, FIELDS, v => set(w, "field", v)));
      add("On at", numInput(w.onAt, v => set(w, "onAt", v), .1));
      add("On color", colorInput(w.onColor, v => set(w, "onColor", v)));
      add("Off color", colorInput(w.offColor, v => set(w, "offColor", v)));
      add("Show off", checkInput(w.showOff, v => set(w, "showOff", v)));
      add("Icon on", textInput(w.iconOn, v => set(w, "iconOn", v)));
      add("Icon off", textInput(w.iconOff, v => set(w, "iconOff", v)));
    }
    if (w.type === "image") {
      add("Source", textInput(w.src, v => set(w, "src", v)));
      add("Fit", selInput(w.fit, ["contain", "cover"], v => set(w, "fit", v)));
    }
    if (w.type === "shape") {
      add("Shape", selInput(w.shape, ["rect", "line", "circle"], v => set(w, "shape", v)));
      add("Fill", colorInput(w.fill, v => set(w, "fill", v)));
      add("Stroke", colorInput(w.stroke, v => set(w, "stroke", v)));
      add("Stroke width", numInput(w.strokeWidth, v => set(w, "strokeWidth", v), .5, 0, 40));
      add("Radius", numInput(w.radius, v => set(w, "radius", v), 1, 0, 200));
    }
    if (w.type === "map") {
      add("Field", selInput(w.field, FIELDS, v => set(w, "field", v)));
      add("Road", colorInput(w.roadColor, v => set(w, "roadColor", v)));
      add("Line", colorInput(w.color, v => set(w, "color", v)));
      add("Dot", colorInput(w.dotColor, v => set(w, "dotColor", v)));
      add("Show dot", checkInput(w.showDot, v => set(w, "showDot", v)));
    }
    if (w.type === "media") {
      add("Controls", checkInput(w.showControls, v => set(w, "showControls", v)));
      add("Timeline", checkInput(w.showTimeline, v => set(w, "showTimeline", v)));
    }
    if (w.type === "clock") {
      add("Date", checkInput(w.showDate, v => set(w, "showDate", v)));
      add("Time", checkInput(w.showTime, v => set(w, "showTime", v)));
      add("Locale", selInput(w.locale, ["en-US", "fr-FR"], v => set(w, "locale", v)));
      add("Color", colorInput(w.color, v => set(w, "color", v)));
    }
    if (w.type === "shiftlights") {
      add("Field", selInput(w.field, FIELDS, v => set(w, "field", v)));
      add("Max field", selInput(w.maxField, FIELDS, v => set(w, "maxField", v)));
      add("Count", numInput(w.count, v => set(w, "count", Math.round(v)), 1, 3, 60));
      add("Low", numInput(w.low, v => set(w, "low", v), .01, 0, 1));
      add("High", numInput(w.high, v => set(w, "high", v), .01, 0, 1));
    }
    if (w.type === "gearstrip") {
      add("Field", selInput(w.field, FIELDS, v => set(w, "field", v)));
      add("Count", numInput(w.count, v => set(w, "count", Math.round(v)), 1, 1, 12));
      add("Color", colorInput(w.color, v => set(w, "color", v)));
      add("Active", colorInput(w.accent, v => set(w, "accent", v)));
    }
  }

  function renderLayoutProps() {
    const el = $("layoutProps");
    el.textContent = "";
    const add = (label, node) => el.appendChild(row(label, node));
    add("Description", textArea(layout.description, v => {
      layout.description = v; markDirty();
    }));
    add("Order", numInput(layout.order == null ? 10 : layout.order,
      v => { layout.order = v; markDirty(); }, 1, 0, 999));
    add("Grid", numInput(layout.canvas.grid, v => {
      layout.canvas.grid = Math.max(4, Math.min(64, Math.round(v)));
      markDirty(); applyGrid();
    }, 1, 4, 64));
    add("Background", colorInput(layout.background, v => {
      layout.background = v; layout.canvas.background = v;
      markDirty(); renderCanvas();
    }));
    add("Tags", textInput((layout.tags || []).join(", "), v => {
      layout.tags = v.split(",").map(s => s.trim()).filter(Boolean).slice(0, 12);
      markDirty();
    }));
  }

  function renderLayers() {
    layersEl.textContent = "";
    if (layout.kind === "simhub") {
      const p = document.createElement("p");
      p.className = "empty";
      p.textContent = "Dashboard SimHub importé en mode fidèle.";
      layersEl.appendChild(p);
      return;
    }
    const list = (layout.widgets || []).slice().reverse();
    list.forEach(w => {
      const d = document.createElement("div");
      d.className = "layer" + (w.id === selected ? " selected" : "");
      const name = w.label || w.text ||
        (w.type === "icon" ? (w.icon || "Icon") :
          (TYPE_LABELS[w.type] || w.type));
      d.innerHTML = "";
      const n = document.createElement("span");
      n.className = "lname"; n.textContent = name;
      const t = document.createElement("span");
      t.className = "ltype"; t.textContent = w.type;
      const up = document.createElement("button");
      up.textContent = "↑"; up.title = "Bring forward";
      up.onclick = e => { e.stopPropagation(); moveLayer(w.id, 1); };
      const down = document.createElement("button");
      down.textContent = "↓"; down.title = "Send backward";
      down.onclick = e => { e.stopPropagation(); moveLayer(w.id, -1); };
      const del = document.createElement("button");
      del.textContent = "×"; del.title = "Delete";
      del.onclick = e => { e.stopPropagation(); deleteWidget(w.id); };
      d.append(n, t, up, down, del);
      d.onclick = () => select(w.id);
      layersEl.appendChild(d);
    });
  }
  function moveLayer(id, dir) {
    const arr = layout.widgets;
    const i = arr.findIndex(w => w.id === id);
    if (i < 0) return;
    const j = i + dir;
    if (j < 0 || j >= arr.length) return;
    pushUndo();
    [arr[i], arr[j]] = [arr[j], arr[i]];
    markDirty();
    renderCanvas(); renderOverlay(); renderLayers();
  }
  function deleteWidget(id) {
    pushUndo();
    layout.widgets = layout.widgets.filter(w => w.id !== id);
    if (selected === id) selected = null;
    markDirty();
    renderAll();
  }

  function addWidget(type) {
    if (layout.kind === "simhub") {
      toast("Mode fidèle SimHub : édition widgets désactivée.", true);
      return;
    }
    const d = DEFAULTS[type];
    if (!d) return;
    pushUndo();
    const n = (layout.widgets || []).length;
    const x = 40 + (n % 3) * 320;
    const y = 40 + (Math.floor(n / 3) % 2) * 280;
    const w = Object.assign({ id: "w" + Date.now().toString(36) + n,
      type, x, y, visible: true, opacity: 1 }, clone(d));
    w.w = Math.min(w.w, 1024 - w.x);
    w.h = Math.min(w.h, 600 - w.y);
    layout.widgets.push(w);
    selected = w.id;
    markDirty();
    renderAll();
  }

  /* ---------------- icons ---------------- */
  function renderIcons() {
    galleryEl.textContent = "";
    const q = iconQuery.toLowerCase();
    if (iconTab === "builtin") {
      const list = (window.IDashIcons && window.IDashIcons.icons || [])
        .filter(i => !q || (i.id + " " + i.label + " " + i.cat)
          .toLowerCase().includes(q));
      list.forEach(icon => {
        const b = document.createElement("div");
        b.className = "icon-item";
        b.title = icon.label + " (" + icon.cat + ")";
        const svg = document.createElementNS(NS, "svg");
        svg.setAttribute("viewBox", icon.viewBox || "0 0 24 24");
        svg.innerHTML = icon.inner;
        b.appendChild(svg);
        b.onclick = () => useIcon(icon.id);
        galleryEl.appendChild(b);
      });
    } else {
      customIcons.filter(i => !q || i.name.toLowerCase().includes(q))
        .forEach(icon => {
          const b = document.createElement("div");
          b.className = "icon-item";
          b.title = icon.name;
          const img = document.createElement("img");
          img.src = icon.url; img.alt = icon.name;
          b.appendChild(img);
          const del = document.createElement("button");
          del.className = "del"; del.textContent = "×";
          del.onclick = async e => {
            e.stopPropagation();
            if (!confirm("Delete icon " + icon.name + " ?")) return;
            await fetch("/api/icons/" + encodeURIComponent(icon.id),
              { method: "DELETE" });
            await loadIcons();
          };
          b.appendChild(del);
          b.onclick = () => useIcon("custom:" + icon.id);
          galleryEl.appendChild(b);
        });
    }
  }
  function useIcon(id) {
    const w = (layout.widgets || []).find(x => x.id === selected);
    if (w && w.type === "icon") {
      pushUndo(); w.icon = id; markDirty(); renderCanvas(); renderProps();
      return;
    }
    if (w && w.type === "image" && id.startsWith("custom:")) {
      pushUndo(); w.src = id;
      markDirty(); renderCanvas(); renderProps();
      return;
    }
    pushUndo();
    const n = layout.widgets.length;
    const iconW = { id: "w" + Date.now().toString(36) + n, type: "icon",
      x: 40 + (n % 5) * 32, y: 40 + (n % 5) * 32, w: 44, h: 44,
      icon: id, field: "none", onColor: "amber", offColor: "dim",
      showOff: true, opacity: 1, visible: true };
    layout.widgets.push(iconW);
    selected = iconW.id;
    markDirty(); renderAll();
  }
  async function loadIcons() {
    try {
      const data = await fetch("/api/icons", { cache: "no-store" })
        .then(r => r.json());
      customIcons = data.icons || [];
    } catch (e) { customIcons = []; }
    renderIcons();
  }
  async function uploadIcon() {
    const file = $("iconFile").files[0];
    if (!file) { toast("Choose a file first.", true); return; }
    if (file.size > 512 * 1024) { toast("Icon too large (max 512 KB).", true); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const r = await fetch("/api/icons", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: file.name.replace(/\.[^.]+$/, ""),
            data: reader.result }),
        });
        const data = await r.json();
        if (!r.ok || !data.ok) throw new Error(data.error || "upload failed");
        toast("Icon uploaded.");
        await loadIcons();
      } catch (e) { toast("Upload failed: " + e.message, true); }
    };
    reader.readAsDataURL(file);
  }

  /* ---------------- preview / save ---------------- */
  function makePreview() {
    try {
      const pv = document.createElementNS(NS, "svg");
      pv.setAttribute("width", "1024");
      pv.setAttribute("height", "600");
      pv.style.position = "fixed";
      pv.style.left = "-3000px";
      document.body.appendChild(pv);
      const now = performance.now();
      let text;
      if (layout.kind === "simhub" && window.IDashSimhub) {
        const v = window.IDashSimhub.render(pv, layout, {});
        v.update(window.IDashStudio.demoState(4));
        text = new XMLSerializer().serializeToString(pv);
      } else {
        const pm = Object.assign({}, demoMedia, {
          position: 9, at: now, playing: false, stalled: false,
        });
        const v = window.IDashStudio.render(pv, layout, {
          C: theme.colors, theme, icons: window.IDashIcons,
          mediaAction: demoAction, media: pm, preview: true,
        });
        v.update(window.IDashStudio.demoState(4), now, pm);
        text = new XMLSerializer().serializeToString(pv);
      }
      pv.remove();
      return text;
    } catch (e) {
      return null;
    }
  }
  async function save() {
    const payload = clone(layout);
    const preview = makePreview();
    if (preview) payload.preview_svg = preview;
    try {
      const r = await fetch("/api/layouts", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok || !data.ok) throw new Error(data.error || "save failed");
      layout = data.layout;
      selected = null;
      dirty = false;
      const url = new URL(location.href);
      url.searchParams.set("id", layout.id);
      history.replaceState(null, "", url);
      renderAll();
      toast("Saved.");
      return layout;
    } catch (e) {
      toast("Save failed: " + e.message, true);
      return null;
    }
  }
  async function launch() {
    const l = await save();
    if (!l) return;
    try {
      const r = await fetch("/api/launch", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dashboard: "custom/" + l.id }),
      });
      const data = await r.json();
      if (!r.ok || !data.ok) throw new Error(data.error || "launch failed");
      toast("Launched on the 7\".");
    } catch (e) { toast("Launch failed: " + e.message, true); }
  }
  async function duplicate() {
    const p = clone(layout);
    delete p.id;
    p.name = (p.name || "Dashboard") + " copy";
    layout = p;
    $("name").value = p.name;
    await save();
  }
  async function remove() {
    if (!layout.id) {
      if (!confirm("Discard this dashboard?")) return;
      location.href = "/studio";
      return;
    }
    if (!confirm("Delete this dashboard?")) return;
    try {
      const r = await fetch("/api/layouts/" + encodeURIComponent(layout.id),
        { method: "DELETE" });
      if (!r.ok) throw new Error("delete failed");
      location.href = "/";
    } catch (e) { toast("Delete failed: " + e.message, true); }
  }
  function exportJson() {
    const p = clone(layout);
    delete p.preview_svg;
    const blob = new Blob([JSON.stringify(p, null, 2)],
      { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (layout.name || "dashboard") + ".json";
    a.click();
    URL.revokeObjectURL(a.href);
  }
  function importJson(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        if (!data || typeof data !== "object") throw new Error("invalid file");
        delete data.id;
        data.name = (data.name || "Imported dashboard") + " import";
        layout = data;
        layout.canvas = layout.canvas || { width: 1024, height: 600, grid: 16 };
        layout.widgets = Array.isArray(layout.widgets) ? layout.widgets : [];
        selected = null;
        markDirty();
        renderAll();
        $("name").value = layout.name;
        toast("Imported.");
      } catch (e) { toast("Import failed: " + e.message, true); }
    };
    reader.readAsText(file);
  }
  function importSimHub(file) {
    toast("Importing SimHub…");
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const raw = String(reader.result || "");
        const data = raw.includes(",") ? raw.split(",", 2)[1] : raw;
        const r = await fetch("/api/simhub/import", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: file.name, data }),
        });
        const result = await r.json();
        if (!r.ok || !result.ok) throw new Error(result.error || "import failed");
        layout = result.layout;
        layout.canvas = layout.canvas || { width: 1024, height: 600, grid: 16 };
        layout.widgets = Array.isArray(layout.widgets) ? layout.widgets : [];
        selected = null;
        markDirty();
        renderAll();
        const report = result.report || {};
        if (report.warnings && report.warnings.length) {
          console.warn("SimHub import:", report.warnings);
        }
        toast("SimHub: " + (report.widgets || layout.widgets.length) +
          " widgets, " + (report.skipped || 0) + " ignored.");
      } catch (e) { toast("SimHub import failed: " + e.message, true); }
    };
    reader.readAsDataURL(file);
  }
  function importFile(file) {
    if (/\.(djson|simhubdash|zip)$/i.test(file.name)) importSimHub(file);
    else importJson(file);
  }

  /* ---------------- load / init ---------------- */
  function fit() {
    const pad = 28;
    const s = Math.min((stage.clientWidth - pad * 2) / 1024,
      (stage.clientHeight - 44) / 600);
    scale = Math.max(.15, s);
    const left = (stage.clientWidth - 1024 * scale) / 2;
    const top = Math.max(14, (stage.clientHeight - 600 * scale) / 2);
    wrap.style.transform = `translate(${left}px, ${top}px) scale(${scale})`;
  }
  function bindTop() {
    propsEl.addEventListener("focusin", () => {
      if (!propFocus) { pushUndo(); propFocus = true; }
    });
    propsEl.addEventListener("focusout", () => {
      setTimeout(() => {
        if (!propsEl.contains(document.activeElement)) propFocus = false;
      }, 0);
    });
    $("name").addEventListener("input", () => {
      layout.name = $("name").value; markDirty();
    });
    $("category").addEventListener("change", () => {
      layout.category = $("category").value; markDirty();
    });
    $("undo").onclick = undo;
    $("redo").onclick = redo;
    $("saveBtn").onclick = save;
    $("launchBtn").onclick = launch;
    $("duplicateBtn").onclick = duplicate;
    $("deleteBtn").onclick = remove;
    $("exportBtn").onclick = exportJson;
    $("importBtn").onclick = () => $("importFile").click();
    $("importFile").onchange = e => {
      if (e.target.files[0]) importFile(e.target.files[0]);
      e.target.value = "";
    };
    $("iconSearch").addEventListener("input", () => {
      iconQuery = $("iconSearch").value; renderIcons();
    });
    $("tabBuiltin").onclick = () => {
      iconTab = "builtin";
      $("tabBuiltin").classList.add("on"); $("tabCustom").classList.remove("on");
      $("uploadRow").style.display = "none"; renderIcons();
    };
    $("tabCustom").onclick = () => {
      iconTab = "custom";
      $("tabCustom").classList.add("on"); $("tabBuiltin").classList.remove("on");
      $("uploadRow").style.display = ""; renderIcons();
    };
    $("uploadBtn").onclick = uploadIcon;
    $("live").addEventListener("change", () => {
      live = $("live").checked;
      if (live) {
        if (!liveES) {
          liveES = new EventSource("/stream");
          liveES.onmessage = e => {
            try { liveState = JSON.parse(e.data); lastLive = performance.now(); }
            catch (err) {}
          };
        }
      } else if (liveES) {
        liveES.close(); liveES = null; liveState = null;
      }
    });
    wrap.addEventListener("pointerdown", e => {
      if (e.target === wrap || e.target === canvas || e.target === gridEl)
        select(null);
    });
    addEventListener("resize", fit);
    addEventListener("beforeunload", e => {
      if (dirty) { e.preventDefault(); e.returnValue = ""; }
    });
  }
  function buildPalette() {
    const box = $("paletteButtons");
    Object.keys(TYPE_LABELS).forEach(type => {
      const b = document.createElement("button");
      b.textContent = TYPE_LABELS[type];
      b.onclick = () => addWidget(type);
      box.appendChild(b);
    });
  }
  async function loadThemes() {
    try {
      const info = await fetch("/api/themes", { cache: "no-store" })
        .then(r => r.json());
      themes = info.themes || {};
      const sel = $("themeSel");
      sel.innerHTML = "";
      Object.values(themes).forEach(t => {
        const o = document.createElement("option");
        o.value = t.id; o.textContent = t.name || t.id;
        sel.appendChild(o);
      });
      theme = themes[info.state.active] || Object.values(themes)[0] ||
        window.IDashStudio.DEFAULT_THEME;
      sel.value = theme.id || sel.options[0]?.value;
      sel.onchange = () => {
        theme = themes[sel.value] || theme;
        renderCanvas();
      };
    } catch (e) {
      theme = window.IDashStudio.DEFAULT_THEME;
    }
  }
  async function loadActiveTheme() {
    const q = layout.id ? "?dashboard=" + encodeURIComponent("custom/" + layout.id) : "";
    try {
      const t = await fetch("/api/themes/active" + q,
        { cache: "no-store" }).then(r => r.json());
      if (t && t.colors) {
        theme = t;
        const sel = $("themeSel");
        if (t.id && themes[t.id]) sel.value = t.id;
        renderCanvas();
      }
    } catch (e) {}
  }
  async function init() {
    buildPalette();
    bindTop();
    $("uploadRow").style.display = "none";
    await loadThemes();
    await loadIcons();
    const id = new URLSearchParams(location.search).get("id");
    if (id) {
      try {
        const data = await fetch("/api/layouts/" + encodeURIComponent(id),
          { cache: "no-store" }).then(r => r.json());
        if (!data.layout) throw new Error("not found");
        layout = data.layout;
      } catch (e) {
        toast("Dashboard not found.", true);
        return;
      }
    } else {
      layout = {
        version: 1, id: "", name: "New dashboard", description: "",
        category: "custom", game: "Assetto Corsa Evo", game_id: "acevo",
        order: 10, tags: [], background: "ink",
        canvas: { width: 1024, height: 600, grid: 16, background: "ink" },
        widgets: [],
      };
    }
    layout.canvas = layout.canvas || { width: 1024, height: 600, grid: 16 };
    layout.widgets = Array.isArray(layout.widgets) ? layout.widgets : [];
    renderAll();
    fit();
    await loadActiveTheme();
    if (!layout.widgets.length && layout.kind !== "simhub") {
      addWidget("value");
      addWidget("gauge");
    }
    renderAll();
    requestAnimationFrame(tick);
  }
  init();
})();
