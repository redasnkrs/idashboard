/* idash Studio runtime: rendu SVG par widgets, themes, SSE, contact, media. */
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const DEFAULT_THEME = {
    font: '"Bahnschrift", "DIN Alternate", "Segoe UI", system-ui, sans-serif',
    units: { speed: "kmh", temp: "c" },
    colors: {
      ink: "#050505", ivory: "#ece6d6", muted: "#8a8272", rule: "#221e17",
      off: "#1c1812", amber: "#ff9a2e", red: "#ff3b2a", green: "#3ddc84",
      blue: "#3d8bff", violet: "#c98bff", dim: "#241f17",
    },
  };
  const MAP_D = "M42 196C16 162 18 112 48 88C74 68 100 78 112 102C124 126 148 138 172 128C196 118 208 92 194 72C180 52 154 56 144 76C134 96 112 104 96 90C78 74 50 84 42 110C34 136 50 154 74 152C98 150 112 128 132 126C156 124 172 146 168 170C164 194 136 208 108 204C80 200 58 210 42 196Z";
  const DEMO_ART = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">' +
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">' +
    '<stop offset="0" stop-color="#c98bff"/>' +
    '<stop offset="1" stop-color="#3d8bff"/></linearGradient></defs>' +
    '<rect width="120" height="120" fill="url(#g)"/>' +
    '<circle cx="86" cy="34" r="22" fill="#ffffff" opacity=".18"/>' +
    '<text x="12" y="102" font-family="sans-serif" font-size="16" ' +
    'fill="#ffffff" opacity=".85">CIDER</text></svg>');
  const DEMO_TRACKS = [
    { title: "Somewhere", artist: "Blu Mar Ten", album: "Somewhere",
      duration: 193 },
    { title: "Night Drive", artist: "Kavinsky", album: "OutRun",
      duration: 254 },
    { title: "Midnight City", artist: "M83", album: "Hurry Up",
      duration: 243 },
  ];
  let uid = 0;

  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in (attrs || {})) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const setT = (e, t) => { if (e.textContent !== t) e.textContent = t; };
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const role = (C, v, def = "ivory") => {
    if (typeof v === "string" && /^#[0-9a-fA-F]{6}$/.test(v)) return v;
    if (v === "none") return "none";
    return C[v] || C[def];
  };
  const num = (v, d = 0) => (v == null ? "--" : Number(v).toFixed(d));
  const timeText = ms => {
    if (!(ms > 0) || ms >= 3600000) return "-:--.---";
    const m = Math.floor(ms / 60000), s = Math.floor(ms % 60000 / 1000);
    const r = Math.floor(ms % 1000);
    return m + ":" + String(s).padStart(2, "0") + "." +
      String(r).padStart(3, "0");
  };
  const clockText = sec => {
    if (!(sec >= 0) || !isFinite(sec)) return "--:--";
    const s = Math.floor(sec);
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  };
  const gearText = g => g < 0 ? "R" : g === 0 ? "N" : String(g);
  const fieldValue = (state, field) => {
    if (!field || field === "none" || !state) return null;
    const v = state[field];
    return v === undefined || v === null ? null : v;
  };
  const scaled = (w, raw) => {
    if (typeof raw !== "number" || !isFinite(raw)) return raw;
    const scale = typeof w.scale === "number" ? w.scale : 1;
    const offset = typeof w.offset === "number" ? w.offset : 0;
    return raw * scale + offset;
  };
  const display = (w, state, theme) => {
    let raw = fieldValue(state, w.field);
    if (w.type === "text" && w.text && (w.field === "none" || raw == null)) {
      return { text: w.text, raw: null, value: null, unit: "" };
    }
    if (raw == null) return { text: "--", raw: null, value: null, unit: "" };
    raw = scaled(w, raw);
    let value = raw;
    let unit = "";
    const u = w.unit || "none";
    if (u === "auto") {
      if (w.field === "v") {
        if (theme.units.speed === "mph") { value = raw * 0.621371; unit = "mph"; }
        else unit = "km/h";
      } else if (["wt", "ot", "at"].includes(w.field)) {
        if (theme.units.temp === "f") { value = raw * 9 / 5 + 32; unit = "°F"; }
        else unit = "°C";
      } else if (w.field === "fuel") unit = "L";
      else if (w.field === "op" || w.field === "boost") unit = "bar";
      else if (w.field === "npos" || w.field === "fp") {
        value = raw * 100; unit = "%";
      }
    } else if (u === "kmh") unit = "km/h";
    else if (u === "mph") { value = raw * 0.621371; unit = "mph"; }
    else if (u === "c") unit = "°C";
    else if (u === "f") { value = raw * 9 / 5 + 32; unit = "°F"; }
    else if (u === "l") unit = "L";
    else if (u === "bar") unit = "bar";
    else if (u === "percent") { value = raw * 100; unit = "%"; }
    const fmt = w.format || "text";
    let text;
    if (fmt === "int") text = String(Math.round(value));
    else if (fmt === "float1") text = Number(value).toFixed(1);
    else if (fmt === "float2") text = Number(value).toFixed(2);
    else if (fmt === "time" || fmt === "clock") text = timeText(value);
    else if (fmt === "delta") {
      text = raw && Math.abs(raw) < 60000
        ? (raw < 0 ? "-" : "+") + (Math.abs(raw) / 1000).toFixed(3) : "";
    } else if (fmt === "gear") text = gearText(raw);
    else if (fmt === "percent") text = Math.round(value) + "%";
    else text = String(value);
    return { text, raw, value, unit };
  };
  const thresholdColor = (w, raw, C) => {
    let color = role(C, w.color);
    if (raw != null && Array.isArray(w.thresholds)) {
      for (const t of w.thresholds) {
        if (!t || typeof t.at !== "number") continue;
        if (t.below ? raw < t.at : raw >= t.at) color = role(C, t.color, "red");
      }
    }
    return color;
  };
  const anchor = a => a === "center" ? "middle" : a === "right" ? "end" : "start";
  const textX = (w, a) => a === "center" ? w.x + w.w / 2
    : a === "right" ? w.x + w.w - 2 : w.x + 2;
  const fitText = (e, maxW, base) => {
    e.setAttribute("font-size", base);
    let size = base;
    let width = e.getComputedTextLength ? e.getComputedTextLength() : 0;
    if (width > maxW && width > 0) {
      size = Math.max(5, base * maxW / width);
      e.setAttribute("font-size", size);
    }
    return size;
  };

  /* ---------------- widgets ---------------- */
  function renderValue(g, w, ctx, staticText) {
    const color = role(ctx.C, w.color);
    const labelColor = role(ctx.C, w.labelColor);
    const unitColor = role(ctx.C, w.unitColor);
    const align = w.align || "left";
    const x = textX(w, align);
    let label = null;
    if (w.label) {
      label = el("text", {
        x, y: w.y + Math.max(9, w.labelSize || 11),
        "text-anchor": anchor(align), "font-size": w.labelSize || 11,
        fill: labelColor, "letter-spacing": ".08em",
      }, g);
      label.textContent = w.label;
    }
    const text = el("text", {
      x, y: w.y + w.h - (w.unit && w.unit !== "none" ? 4 : 2),
      "text-anchor": anchor(align), "font-size": w.size || 32,
      "font-weight": w.weight || 700, fill: color,
    }, g);
    const val = el("tspan", {}, text);
    const unit = el("tspan", { "font-size": ".34em",
      fill: unitColor, dx: 4 }, text);
    let last = "";
    function update(state) {
      const d = staticText ? { text: staticText, raw: null, unit: "" }
        : display(w, state, ctx.theme);
      const key = d.text + "|" + d.unit;
      if (key !== last) {
        last = key;
        val.textContent = d.text;
        unit.textContent = d.unit || "";
        fitText(text, Math.max(8, w.w - 4), w.size || 32);
      }
      const c = thresholdColor(w, d.raw, ctx.C);
      if (val.style.fill !== c) val.style.fill = c;
    }
    return { update };
  }

  function renderGauge(g, w, ctx) {
    const cx = w.x + w.w / 2, cy = w.y + w.h / 2;
    const r = Math.max(10, Math.min(w.w, w.h) / 2 - 4);
    const bg = role(ctx.C, w.bg || "off");
    el("circle", { cx, cy, r, fill: bg, opacity: .55,
      stroke: role(ctx.C, "rule"), "stroke-width": 1.5 }, g);
    const tach = el("g", {}, g);
    const ringG = el("g", {}, g);
    const value = el("text", {
      x: cx, y: cy + r * .12, "text-anchor": "middle",
      "font-size": Math.max(10, Math.min(r * .9, w.size || r * .42)),
      "font-weight": 700, fill: role(ctx.C, w.color),
    }, g);
    const label = el("text", {
      x: cx, y: cy + r * .48, "text-anchor": "middle",
      "font-size": Math.max(8, Math.min(r * .2, w.labelSize || r * .12)),
      fill: role(ctx.C, w.labelColor), "letter-spacing": ".1em",
    }, g);
    label.textContent = w.label || "";
    let needle = null;
    if (w.needle) {
      needle = el("g", { transform: `rotate(135 ${cx} ${cy})` }, g);
      el("polygon", {
        points: `${cx + r * .18},${cy - 2.5} ${cx + r * .86},${cy - 1} ` +
          `${cx + r * .86},${cy + 1} ${cx + r * .18},${cy + 2.5}`,
        fill: role(ctx.C, w.accent, "amber"),
      }, needle);
    }
    let builtMax = 0, segs = [];
    function build(max) {
      builtMax = max;
      tach.textContent = ""; ringG.textContent = ""; segs = [];
      const target = max / 8;
      const pow = Math.pow(10, Math.floor(Math.log10(target || 1)));
      const norm = target / pow;
      const major = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 :
        norm <= 5 ? 5 : 10) * pow;
      const minor = major / 5;
      const redFrom = max * (w.redline == null ? .89 : w.redline);
      for (let v = 0; v <= max + .1; v += minor) {
        const isMajor = Math.abs(v / major - Math.round(v / major)) < 1e-6;
        const a = 135 + 270 * v / max;
        const red = v >= redFrom - 1e-6;
        const [x0, y0] = [cx + r * Math.cos(a * Math.PI / 180),
          cy + r * Math.sin(a * Math.PI / 180)];
        const [x1, y1] = [cx + (isMajor ? r * .84 : r * .9) *
          Math.cos(a * Math.PI / 180),
          cy + (isMajor ? r * .84 : r * .9) * Math.sin(a * Math.PI / 180)];
        el("line", { x1: x0, y1: y0, x2: x1, y2: y1,
          stroke: red ? role(ctx.C, "red") : (isMajor ? role(ctx.C, "ivory")
            : role(ctx.C, "muted")),
          "stroke-width": isMajor ? 2.2 : 1.2 }, tach);
        if (isMajor && max / major <= 14) {
          const tx = cx + r * .7 * Math.cos(a * Math.PI / 180);
          const ty = cy + r * .7 * Math.sin(a * Math.PI / 180);
          const t = el("text", { x: tx, y: ty, "text-anchor": "middle",
            "dominant-baseline": "central",
            "font-size": Math.max(7, r * .1) }, tach);
          t.style.fill = red ? role(ctx.C, "red") : role(ctx.C, "ivory");
          t.textContent = String(Math.round(v / (major >= 1000 ? 1000 : 1)));
        }
      }
      const N = 54;
      for (let i = 0; i < N; i++) {
        const f = (i + .5) / N;
        const a0 = 135 + 270 * i / N + .5;
        const a1 = 135 + 270 * (i + 1) / N - .5;
        const p = el("path", { d: arc(cx, cy, r * .95, a0, a1),
          fill: "none", "stroke-width": Math.max(2, r * .035),
          stroke: role(ctx.C, "off") }, ringG);
        segs.push({ el: p, f, on: false,
          col: f < (w.redline == null ? .89 : w.redline)
            ? role(ctx.C, "amber") : role(ctx.C, "red") });
      }
    }
    function arc(cx, cy, rr, a0, a1) {
      const x0 = cx + rr * Math.cos(a0 * Math.PI / 180);
      const y0 = cy + rr * Math.sin(a0 * Math.PI / 180);
      const x1 = cx + rr * Math.cos(a1 * Math.PI / 180);
      const y1 = cy + rr * Math.sin(a1 * Math.PI / 180);
      return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${rr} ${rr} 0 0 1 ` +
        `${x1.toFixed(2)} ${y1.toFixed(2)}`;
    }
    function update(state) {
      const maxRaw = (w.maxField && w.maxField !== "none" &&
        state[w.maxField]) || w.max || 100;
      const max = (w.maxField && w.maxField !== "none")
        ? scaled(w, maxRaw) : maxRaw;
      if (Math.abs(max - builtMax) > .01) build(max);
      const raw = scaled(w, Number(fieldValue(state, w.field) || 0));
      const frac = clamp((raw - (w.min || 0)) /
        ((max - (w.min || 0)) || 1));
      for (const s of segs) {
        const on = s.f <= frac;
        if (on !== s.on) {
          s.on = on;
          s.el.setAttribute("stroke", on ? s.col : role(ctx.C, "off"));
        }
      }
      if (needle) needle.setAttribute("transform",
        `rotate(${135 + 270 * frac} ${cx} ${cy})`);
      const d = display(w, state, ctx.theme);
      setT(value, d.text);
      value.style.fill = thresholdColor(w, d.raw, ctx.C);
      if (w.showValue === false) value.style.display = "none";
    }
    build(w.max || 100);
    return { update };
  }

  function renderBar(g, w, ctx) {
    const color = role(ctx.C, w.color, "amber");
    const trackColor = role(ctx.C, w.trackColor);
    const vertical = w.orientation === "vertical";
    let label = null, value = null, track = null, fill = null;
    if (w.label) {
      label = el("text", { x: w.x + 2, y: w.y + 12, "font-size": 10,
        fill: role(ctx.C, w.labelColor), "letter-spacing": ".08em" }, g);
      label.textContent = w.label;
    }
    if (w.showValue !== false) {
      value = el("text", { x: w.x + w.w - 2, y: w.y + 18,
        "text-anchor": "end", "font-size": w.size || 18,
        "font-weight": 700, fill: color }, g);
    }
    if (vertical) {
      track = el("rect", { x: w.x + w.w - 12, y: w.y + 22, width: 6,
        height: Math.max(4, w.h - 26), rx: 3, fill: trackColor }, g);
      fill = el("rect", { x: w.x + w.w - 12, y: w.y + w.h - 4, width: 6,
        height: 0, rx: 3, fill: color }, g);
    } else {
      track = el("rect", { x: w.x + 2, y: w.y + w.h - 12,
        width: Math.max(4, w.w - 4), height: 6, rx: 3,
        fill: trackColor }, g);
      fill = el("rect", { x: w.x + 2, y: w.y + w.h - 12, width: 0,
        height: 6, rx: 3, fill: color }, g);
    }
    function update(state) {
      const raw = scaled(w, Number(fieldValue(state, w.field) || 0));
      const maxRaw = (w.maxField && w.maxField !== "none" &&
        state[w.maxField]) || w.max || 100;
      const max = (w.maxField && w.maxField !== "none")
        ? scaled(w, maxRaw) : maxRaw;
      const frac = clamp((raw - (w.min || 0)) /
        ((max - (w.min || 0)) || 1));
      const c = thresholdColor(w, raw, ctx.C);
      if (vertical) {
        const h = (w.h - 26) * frac;
        fill.setAttribute("height", h.toFixed(1));
        fill.setAttribute("y", (w.y + w.h - 4 - h).toFixed(1));
      } else {
        fill.setAttribute("width", ((w.w - 4) * frac).toFixed(1));
      }
      fill.setAttribute("fill", c);
      if (value) {
        const d = display(w, state, ctx.theme);
        setT(value, (d.text + " " + d.unit).trim());
        value.style.fill = c;
      }
    }
    return { update };
  }

  function renderIcon(g, w, ctx) {
    const size = Math.max(6, Math.min(w.w, w.h) - 4);
    const cx = w.x + w.w / 2, cy = w.y + w.h / 2;
    const group = el("g", { transform: `translate(${cx} ${cy})` }, g);
    const color = role(ctx.C, w.color);
    let shown = null;
    function draw(id, fill, opacity) {
      group.textContent = "";
      group.setAttribute("opacity", opacity);
      group.setAttribute("transform", `translate(${cx} ${cy})`);
      if (id && id.startsWith("custom:")) {
        el("image", { href: "/custom/icons/" + id.slice(7),
          x: -size / 2, y: -size / 2, width: size, height: size,
          preserveAspectRatio: "xMidYMid meet" }, group);
        return;
      }
      const all = ctx.icons && ctx.icons.byId;
      const icon = all && all[id] || (all && all["circle-dot"]);
      if (!icon) {
        el("circle", { r: size / 2, fill: "none",
          stroke: fill || color, "stroke-width": 2 }, group);
        return;
      }
      const vb = (icon.viewBox || "0 0 24 24").split(/\s+/).map(Number);
      const vw = vb[2] || 24, vh = vb[3] || 24;
      const s = size / Math.max(vw, vh);
      group.setAttribute("transform", `translate(${cx} ${cy}) scale(${s}) ` +
        `translate(${-vw / 2} ${-vh / 2})`);
      group.setAttribute("stroke", fill || color);
      group.setAttribute("fill", "none");
      group.setAttribute("stroke-width", "1.8");
      group.setAttribute("stroke-linecap", "round");
      group.setAttribute("stroke-linejoin", "round");
      group.innerHTML = icon.inner;
    }
    function update(state) {
      const raw = fieldValue(state, w.field);
      let on = true;
      if (w.field !== "none" && raw != null) {
        on = typeof raw === "boolean" ? raw : Number(raw) >= (w.onAt || 0.5);
      }
      const id = on ? (w.iconOn || w.icon) : (w.iconOff || w.icon);
      const fill = on ? role(ctx.C, w.onColor, "amber")
        : role(ctx.C, w.offColor, "dim");
      const opacity = on ? 1 : (w.showOff === false ? .16 : 1);
      const key = id + "|" + fill + "|" + opacity;
      if (key !== shown) { shown = key; draw(id, fill, opacity); }
    }
    return { update };
  }

  function renderImage(g, w, ctx) {
    const src = (w.src || "").startsWith("custom:")
      ? "/custom/icons/" + w.src.slice(7) : (w.src || "");
    if (src) {
      el("image", { href: src, x: w.x, y: w.y, width: w.w, height: w.h,
        preserveAspectRatio: w.fit === "cover" ? "xMidYMid slice"
          : "xMidYMid meet" }, g);
    }
    return { update() {} };
  }

  function renderShape(g, w, ctx) {
    const fill = role(ctx.C, w.fill, "off");
    const stroke = role(ctx.C, w.stroke, "rule");
    if (w.shape === "line") {
      el("line", { x1: w.x, y1: w.y + w.h / 2, x2: w.x + w.w,
        y2: w.y + w.h / 2, stroke, "stroke-width": w.strokeWidth || 1 }, g);
    } else if (w.shape === "circle") {
      el("circle", { cx: w.x + w.w / 2, cy: w.y + w.h / 2,
        r: Math.min(w.w, w.h) / 2, fill, stroke,
        "stroke-width": w.strokeWidth || 1 }, g);
    } else {
      el("rect", { x: w.x, y: w.y, width: w.w, height: w.h,
        rx: w.radius || 0, fill, stroke,
        "stroke-width": w.strokeWidth || 1 }, g);
    }
    return { update() {} };
  }

  function renderMap(g, w, ctx) {
    const s = Math.min(w.w, w.h) / 250 * .92;
    const tx = w.x + w.w / 2 - 125 * s;
    const ty = w.y + w.h / 2 - 125 * s;
    const map = el("g", { transform: `translate(${tx} ${ty}) scale(${s})` }, g);
    el("path", { d: MAP_D, fill: "none",
      stroke: role(ctx.C, w.roadColor, "dim"), "stroke-width": 16,
      "stroke-linejoin": "round", "stroke-linecap": "round" }, map);
    const path = el("path", { d: MAP_D, fill: "none",
      stroke: role(ctx.C, w.color, "amber"), "stroke-width": 3,
      "stroke-linejoin": "round", "stroke-linecap": "round" }, map);
    const dot = el("circle", { cx: 42, cy: 196, r: 7,
      fill: role(ctx.C, w.dotColor, "amber") }, map);
    const len = path.getTotalLength ? path.getTotalLength() : 0;
    function update(state) {
      const npos = fieldValue(state, w.field || "npos");
      if (npos == null || !len) { dot.style.display = "none"; return; }
      dot.style.display = "";
      const p = path.getPointAtLength(clamp(npos) * len);
      dot.setAttribute("cx", p.x.toFixed(2));
      dot.setAttribute("cy", p.y.toFixed(2));
    }
    return { update };
  }

  function renderClock(g, w, ctx) {
    const color = role(ctx.C, w.color);
    const date = el("text", { x: w.x + 2, y: w.y + 12, "font-size": 10,
      fill: role(ctx.C, w.labelColor), "letter-spacing": ".08em" }, g);
    const time = el("text", { x: w.x + 2, y: w.y + w.h - 4,
      "font-size": w.size || 22, "font-weight": 700, fill: color }, g);
    let last = "";
    function update() {
      const d = new Date();
      const locale = w.locale || "en-US";
      const ds = w.showDate === false ? "" :
        d.toLocaleDateString(locale, { weekday: "short", month: "short",
          day: "numeric" }).toUpperCase();
      const ts = w.showTime === false ? "" :
        d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
      const key = ds + "|" + ts;
      if (key !== last) {
        last = key;
        date.textContent = ds; time.textContent = ts;
        date.style.display = ds ? "" : "none";
        time.style.display = ts ? "" : "none";
        if (ds && ts) time.setAttribute("y", w.y + w.h - 4);
        else if (ds) { date.setAttribute("y", w.y + w.h - 4);
          date.setAttribute("font-size", w.size || 22); }
      }
    }
    return { update };
  }

  function renderShiftlights(g, w, ctx) {
    const n = Math.max(3, Math.min(60, w.count || 27));
    const leds = [];
    const spacing = w.w / (n + 1);
    const radius = Math.max(1.5, Math.min(w.h * .32, spacing * .36));
    const cy = w.y + w.h / 2;
    for (let i = 0; i < n; i++) {
      const level = Math.min(i, n - 1 - i);
      const col = level < n * .3 ? role(ctx.C, "green")
        : level < n * .65 ? role(ctx.C, "amber") : role(ctx.C, "red");
      leds.push({ el: el("circle", { cx: w.x + spacing * (i + 1), cy,
        r: radius, fill: role(ctx.C, "off") }, g), level, col, on: false });
    }
    function update(state) {
      const maxRaw = (w.maxField && w.maxField !== "none" &&
        state[w.maxField]) || 9000;
      const max = (w.maxField && w.maxField !== "none")
        ? scaled(w, maxRaw) : maxRaw;
      const raw = scaled(w, Number(fieldValue(state, w.field || "r") || 0));
      const frac = clamp(raw / (max || 1));
      const lim = state.lim || frac > .975;
      const flash = lim && Math.floor(performance.now() / 90) % 2 === 0;
      for (const l of leds) {
        const on = !flash && frac >= (w.low || .72) &&
          frac >= (w.low || .72) + (1 - (w.low || .72)) * (l.level / 13);
        if (on !== l.on) {
          l.on = on;
          l.el.setAttribute("fill", on ? l.col : role(ctx.C, "off"));
        }
      }
    }
    return { update };
  }

  function renderGearstrip(g, w, ctx) {
    const n = Math.max(1, Math.min(12, w.count || 8));
    const labels = ["R", "N"];
    for (let i = 1; i <= n; i++) labels.push(String(i));
    const step = w.w / (labels.length + 1);
    const els = labels.map((label, i) => {
      const t = el("text", { x: w.x + step * (i + 1), y: w.y + w.h / 2,
        "text-anchor": "middle", "dominant-baseline": "central",
        "font-size": w.size || 14, "font-weight": 700 }, g);
      t.textContent = label;
      t.style.fill = role(ctx.C, w.color, "muted");
      return t;
    });
    function update(state) {
      const gval = Number(fieldValue(state, w.field || "g") || 0);
      const idx = gval < 0 ? 0 : gval === 0 ? 1 : Math.min(labels.length - 1, gval + 1);
      els.forEach((e, i) => {
        e.style.fill = i === idx ? role(ctx.C, w.accent, "amber") :
          role(ctx.C, w.color, "muted");
        e.setAttribute("font-weight", i === idx ? 700 : 400);
      });
    }
    return { update };
  }

  function renderMedia(g, w, ctx) {
    const baseW = 280, baseH = 260;
    const s = Math.min(w.w / baseW, w.h / baseH);
    const tx = w.x + (w.w - baseW * s) / 2;
    const ty = w.y + (w.h - baseH * s) / 2;
    const root = el("g", { transform: `translate(${tx} ${ty}) scale(${s})` }, g);
    const id = "mg" + (++uid);
    const C = ctx.C;
    el("rect", { x: 0, y: 0, width: baseW, height: baseH, rx: 14,
      fill: role(C, "off"), stroke: role(C, "rule") }, root);
    const defs = el("defs", {}, root);
    const grad = el("linearGradient", { id: id + "g", x1: 0, y1: 0,
      x2: 1, y2: 1 }, defs);
    el("stop", { offset: 0, "stop-color": role(C, "violet") }, grad);
    el("stop", { offset: 1, "stop-color": role(C, "blue") }, grad);
    const clip = el("clipPath", { id: id + "c" }, defs);
    el("rect", { x: 16, y: 34, width: 76, height: 76, rx: 8 }, clip);
    const np = el("text", { x: 16, y: 20, "font-size": 9,
      fill: role(C, "muted"), "letter-spacing": ".14em" }, root);
    np.textContent = "NOW PLAYING";
    const state = el("text", { x: baseW - 16, y: 20, "text-anchor": "end",
      "font-size": 9, fill: role(C, "amber"),
      "letter-spacing": ".1em" }, root);
    el("rect", { x: 16, y: 34, width: 76, height: 76, fill: "url(#" + id + "g)",
      "clip-path": "url(#" + id + "c)" }, root);
    const letter = el("text", { x: 54, y: 84, "text-anchor": "middle",
      "font-size": 30, "font-weight": 700, fill: role(C, "ivory") }, root);
    const art = el("image", { x: 16, y: 34, width: 76, height: 76,
      "clip-path": "url(#" + id + "c)", style: "display:none" }, root);
    el("rect", { x: 16, y: 34, width: 76, height: 76, rx: 8, fill: "none",
      stroke: role(C, "rule") }, root);
    const title = el("text", { x: 104, y: 52, "font-size": 13,
      "font-weight": 700, fill: role(C, "ivory") }, root);
    const artist = el("text", { x: 104, y: 72, "font-size": 11,
      fill: role(C, "muted") }, root);
    const album = el("text", { x: 104, y: 90, "font-size": 10,
      fill: role(C, "muted") }, root);
    const source = el("text", { x: 16, y: 230, "font-size": 9,
      fill: role(C, "muted"), "letter-spacing": ".12em" }, root);
    const pbg = el("rect", { x: 16, y: 126, width: 248, height: 4, rx: 2,
      fill: role(C, "dim") }, root);
    const prog = el("rect", { x: 16, y: 126, width: 0, height: 4, rx: 2,
      fill: role(C, "amber") }, root);
    const pos = el("text", { x: 16, y: 146, "font-size": 9,
      fill: role(C, "muted") }, root);
    const dur = el("text", { x: baseW - 16, y: 146, "text-anchor": "end",
      "font-size": 9, fill: role(C, "muted") }, root);
    const controls = el("g", {}, root);
    const empty = el("text", { x: 140, y: 200, "text-anchor": "middle",
      "font-size": 10, fill: role(C, "muted"),
      "letter-spacing": ".1em", style: "display:none" }, root);
    empty.textContent = "NO MEDIA";
    const actions = ctx.mediaAction || (() => {});
    const btnPrev = el("g", { class: "ctl", style: "cursor:pointer" }, controls);
    el("circle", { cx: 68, cy: 196, r: 21, fill: role(C, "ink"),
      stroke: role(C, "rule") }, btnPrev);
    el("path", { d: "M6 -6L6 6L-4 0Z", fill: role(C, "ivory"),
      transform: "translate(68 196)" }, btnPrev);
    el("rect", { x: 57, y: 190, width: 2, height: 12,
      fill: role(C, "ivory") }, btnPrev);
    const btnPlay = el("g", { class: "ctl", style: "cursor:pointer" }, controls);
    el("circle", { cx: 140, cy: 196, r: 23, fill: role(C, "ink"),
      stroke: role(C, "rule") }, btnPlay);
    const playIcon = el("path", { d: "M-4 -8L9 0L-4 8Z",
      fill: role(C, "ivory"), transform: "translate(140 196)" }, btnPlay);
    const pauseIcon = el("g", { transform: "translate(140 196)",
      style: "display:none" }, btnPlay);
    el("rect", { x: -6, y: -8, width: 4, height: 16,
      fill: role(C, "ivory") }, pauseIcon);
    el("rect", { x: 2, y: -8, width: 4, height: 16,
      fill: role(C, "ivory") }, pauseIcon);
    const btnNext = el("g", { class: "ctl", style: "cursor:pointer" }, controls);
    el("circle", { cx: 212, cy: 196, r: 21, fill: role(C, "ink"),
      stroke: role(C, "rule") }, btnNext);
    el("path", { d: "M-6 -6L-6 6L4 0Z", fill: role(C, "ivory"),
      transform: "translate(212 196)" }, btnNext);
    el("rect", { x: 209, y: 190, width: 2, height: 12,
      fill: role(C, "ivory") }, btnNext);
    const stop = e => { e.stopPropagation(); };
    btnPrev.addEventListener("click", e => { stop(e); actions("prev"); });
    btnPlay.addEventListener("click", e => { stop(e); actions("playpause"); });
    btnNext.addEventListener("click", e => { stop(e); actions("next"); });
    let lastTitle = "", lastArt = null;
    function update(_, now, media) {
      const ok = !!(media && media.ok);
      empty.style.display = ok ? "none" : "";
      controls.style.display = ok && w.showControls !== false ? "" : "none";
      pbg.style.display = prog.style.display = pos.style.display =
        dur.style.display = ok && w.showTimeline !== false ? "" : "none";
      state.textContent = ok ? (media.playing ? "PLAYING" : "PAUSED") : "";
      const t = ok ? (media.title || "UNTITLED") : "NO MEDIA";
      if (t !== lastTitle) {
        lastTitle = t;
        title.textContent = t;
        artist.textContent = ok ? (media.artist || "") : "";
        album.textContent = ok ? (media.album || "") : "";
        const src = ok ? (/cider/i.test(media.source || "") ? "CIDER" :
          (media.source || "").split("!")[0].toUpperCase()) : "";
        source.textContent = src;
        letter.textContent = ok ? ((media.artist || media.title || "♪")
          .trim().charAt(0).toUpperCase() || "♪") : "♪";
      }
      const url = ok && media.has_art ? media.art_url : null;
      if (url !== lastArt) {
        lastArt = url;
        if (url) { art.setAttribute("href", url); art.style.display = ""; }
        else art.style.display = "none";
      }
      if (ok && media.duration > 0 && !media.stalled) {
        const p = clamp((media.position || 0) +
          (media.playing ? (now - (media.at || now)) / 1000 : 0),
          0, media.duration);
        prog.setAttribute("width", (248 * p / media.duration).toFixed(1));
        pos.textContent = clockText(p);
        dur.textContent = clockText(media.duration);
      }
      playIcon.style.display = ok && media.playing ? "none" : "";
      pauseIcon.style.display = ok && media.playing ? "" : "none";
    }
    return { update };
  }

  const WIDGETS = {
    value: (g, w, ctx) => renderValue(g, w, ctx),
    text: (g, w, ctx) => renderValue(g, w, ctx, w.text || null),
    gauge: renderGauge,
    bar: renderBar,
    icon: renderIcon,
    image: renderImage,
    shape: renderShape,
    map: renderMap,
    clock: renderClock,
    shiftlights: renderShiftlights,
    gearstrip: renderGearstrip,
    media: renderMedia,
  };

  function render(svg, layout, opts) {
    const theme = opts.theme || DEFAULT_THEME;
    const C = opts.C || theme.colors || DEFAULT_THEME.colors;
    const widgets = [];
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 1024 600");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("xmlns", NS);
    svg.setAttribute("font-family", theme.font || DEFAULT_THEME.font);
    el("rect", { x: 0, y: 0, width: 1024, height: 600,
      fill: role(C, layout.background || "ink", "ink") }, svg);
    for (const w of (layout.widgets || [])) {
      if (w.visible === false) continue;
      const attrs = { opacity: w.opacity == null ? 1 : w.opacity };
      if (w.rotation) {
        attrs.transform = `rotate(${w.rotation} ${w.x + w.w / 2} ` +
          `${w.y + w.h / 2})`;
      }
      if (w.font) attrs["font-family"] = w.font;
      const g = el("g", attrs, svg);
      const fn = WIDGETS[w.type] || WIDGETS.text;
      try {
        const inst = fn(g, w, { ...opts, C, theme });
        if (inst) widgets.push(inst);
      } catch (e) {
        el("rect", { x: w.x, y: w.y, width: w.w, height: w.h,
          fill: "none", stroke: C.red }, g);
      }
    }
    return {
      svg,
      update(state, now, media) {
        for (const inst of widgets) {
          try { inst.update(state, now, media); } catch (e) {}
        }
      },
    };
  }

  /* ---------------- runtime ---------------- */
  function demoState(t, ign) {
    const ratios = [0, 7.2, 11.4, 15.8, 20.3, 25, 29.5, 34];
    const speed = 28 + 240 * (.5 - .5 * Math.cos(2 * Math.PI * t / 28));
    const accel = Math.sin(2 * Math.PI * t / 28) > 0;
    let gear = 1;
    while (gear < 7 && speed / ratios[gear] * 1000 > 8900) gear++;
    const rpm = Math.max(900, speed / ratios[gear] * 1000);
    const off = ign === "off" || (ign === "wake" && t < 1.5);
    return {
      c: true, st: 2, v: speed, r: rpm, rm: 9000, g: gear,
      gas: accel ? .92 : 0, brk: accel ? 0 : .35,
      fuel: Math.max(5, 42 - t * .02), fp: .7, fpl: 2.4, laps: 17.5,
      wt: 89, ot: 105, op: 4.2, boost: .9, at: 25,
      low: true, high: Math.floor(t / 9) % 2 === 1, L: false, R: false,
      haz: false, hb: 0, pit: false, pitlane: false,
      tc: accel && speed < 90, abs: false, lim: false, up: rpm > 8700,
      run: !off, ign: !off, tcl: 3, absl: 2, bb: 56.5,
      lap: (t * 1000) % 88500, last: 89123, best: 88342,
      delta: Math.sin(t / 3) * 420, valid: true, pos: 3, nd: 12,
      npos: (t / 90) % 1, car: "FERRARI 296 GT3", track: "MONZA",
      cfg: "GRAND PRIX", mode: "SPORT+",
      game: "Assetto Corsa Evo", game_id: "acevo",
    };
  }

  function createMedia(demo) {
    const mgr = {
      state: { ok: false, title: "", artist: "", album: "", source: "",
        playing: false, status: "", position: 0, duration: 0,
        has_art: false, art_url: null, stalled: false, at: 0 },
      demo, demoPlaying: true, demoTrack: 0,
      prevServer: null, stalledSince: 0,
      poll: null,
      action(action) {
        if (this.demo) {
          const now = performance.now();
          if (action === "playpause") {
            this.demoPlaying = !this.demoPlaying;
            this.state.playing = this.demoPlaying;
            this.state.position = this.state.position +
              (now - (this.state.at || now)) / 1000;
            this.state.at = now;
          } else {
            this.demoTrack += action === "next" ? 1 : -1;
            this.applyDemo(now);
          }
          return;
        }
        fetch("/api/media/control", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action }),
        }).then(() => setTimeout(() => this.poll(), 250)).catch(() => {});
      },
      applyDemo(now) {
        const tr = DEMO_TRACKS[((this.demoTrack % DEMO_TRACKS.length) +
          DEMO_TRACKS.length) % DEMO_TRACKS.length];
        this.state = {
          ok: true, title: tr.title, artist: tr.artist, album: tr.album,
          source: "Cider", playing: this.demoPlaying, status: "",
          position: 0, duration: tr.duration, has_art: true,
          art_url: DEMO_ART, stalled: false, at: now,
        };
      },
      async poll() {
        if (this.demo) return;
        try {
          const data = await fetch("/api/media", { cache: "no-store" })
            .then(r => r.json());
          if (data.title !== this.state.title ||
              data.artist !== this.state.artist) {
            this.prevServer = null; this.stalledSince = 0;
          }
          const pos = Number(data.position) || 0;
          const dur = Number(data.duration) || 0;
          if (data.ok && data.playing && dur > 0) {
            if (this.prevServer != null && pos <= this.prevServer + .001) {
              if (!this.stalledSince) this.stalledSince = performance.now();
            } else this.stalledSince = 0;
            this.prevServer = pos;
          } else { this.prevServer = null; this.stalledSince = 0; }
          this.state = {
            ok: !!data.ok, title: data.title || "",
            artist: data.artist || "", album: data.album || "",
            source: data.source || "", playing: !!data.playing,
            status: data.status || "", position: pos, duration: dur,
            has_art: !!data.has_art,
            art_url: data.has_art ? "/api/media/art?v=" + data.art_rev : null,
            stalled: !!(this.stalledSince &&
              performance.now() - this.stalledSince > 3000),
            at: performance.now(),
          };
        } catch (e) {}
      },
      start() {
        if (this.demo) this.applyDemo(performance.now());
        else { this.poll(); setInterval(() => this.poll(), 1000); }
      },
    };
    return mgr;
  }

  async function start({ svg, wait, layoutId }) {
    const params = new URLSearchParams(location.search);
    const demo = params.has("demo");
    const demoOffset = Number(params.get("demo")) || 0;
    const demoIgn = params.get("ign");
    const META = window.__IDASH__ || {};
    const id = layoutId || META.id;
    if (!id) { if (wait) wait.textContent = "Dashboard introuvable"; return; }
    let data;
    try {
      data = await fetch("/api/layouts/" + encodeURIComponent(id))
        .then(r => r.json());
    } catch (e) {
      if (wait) wait.textContent = "Impossible de charger le dashboard";
      return;
    }
    if (!data || !data.layout) {
      if (wait) wait.textContent = "Dashboard introuvable";
      return;
    }
    const layout = data.layout;
    const meta = data.meta || META;
    document.title = (layout.name || "Dashboard") + " — idash";
    let theme = JSON.parse(JSON.stringify(DEFAULT_THEME));
    let C = theme.colors;
    let mediaMgr = createMedia(demo);
    const needsMedia = (layout.widgets || []).some(w => w.type === "media");
    let view = null;
    function build() {
      view = render(svg, layout, { C, theme,
        icons: window.IDashIcons || null,
        mediaAction: a => mediaMgr.action(a),
        media: mediaMgr.state, preview: false });
    }
    build();
    const DASHBOARD = params.has("nodash") ? null :
      (params.get("dashboard") || meta.spec || null);
    const GAME_OVERRIDE = params.get("game");
    let GAME = params.has("nogame") ? null :
      (GAME_OVERRIDE || meta.game_id || null);
    const CAR = params.get("car") || null;
    async function loadTheme(car) {
      const q = [];
      if (DASHBOARD) q.push("dashboard=" + encodeURIComponent(DASHBOARD));
      if (GAME) q.push("game=" + encodeURIComponent(GAME));
      if (car) q.push("car=" + encodeURIComponent(car));
      try {
        const t = await fetch("/api/themes/active" +
          (q.length ? "?" + q.join("&") : ""), { cache: "no-store" })
          .then(r => r.json());
        if (t && t.colors) {
          theme = t;
          C = t.colors;
          build();
        }
      } catch (e) {}
    }
    loadTheme(CAR);
    if (!demo) {
      const es = new EventSource("/api/themes/stream");
      es.onmessage = () => loadTheme(themeCar || CAR);
    }
    let state = { c: false }, lastMsg = 0, themeCar = null;
    if (!demo) {
      const es = new EventSource("/stream");
      es.onmessage = e => {
        try { state = JSON.parse(e.data); lastMsg = performance.now(); }
        catch (err) {}
      };
    }
    const WAKE_MS = 2400, DEBOUNCE = 220;
    let power = "on", rawContact = null, changed = 0, wakeAt = 0;
    function contact(d) {
      if (d.ign !== undefined) return !!(d.ign || d.run);
      if (d.run !== undefined) return !!d.run;
      return true;
    }
    function sleep(d) {
      return Object.assign({}, d, {
        st: 0, v: 0, r: 0, g: 0, gas: 0, brk: 0, hb: 0,
        low: false, high: false, L: false, R: false, haz: false,
        pit: false, pitlane: false, tc: false, abs: false, lim: false,
        up: false, run: false, ign: false, fuel: null, fp: 0, fpl: 0,
        laps: 0, wt: null, ot: null, op: null, boost: null,
        lap: 0, last: 0, best: 0, delta: 0, valid: true, pos: 0, nd: 0,
        npos: null, tcl: null, absl: null, bb: null, mode: "",
      });
    }
    function wake(d, elapsed) {
      const p = Math.min(1, elapsed / WAKE_MS);
      const sweep = p < .55 ? p / .55 : Math.max(0, 1 - (p - .55) / .45);
      return Object.assign({}, d, {
        st: 2, v: 0, r: (d.rm || 8000) * sweep, g: 0, gas: 0, brk: 0,
        hb: 0, low: false, high: false, L: false, R: false, haz: false,
        pit: false, pitlane: false, tc: false, abs: false, lim: false,
        up: false, ign: true, lap: 0, last: 0, best: 0, delta: 0,
        valid: true, pos: 0, nd: 0,
      });
    }
    function updatePower(d, live, now) {
      if (!live) {
        svg.classList.remove("sleep");
        power = "on"; rawContact = null;
        return { data: d };
      }
      const rc = contact(d);
      if (rawContact === null) {
        rawContact = rc; power = rc ? "on" : "off"; changed = now;
        svg.classList.toggle("sleep", !rc);
      } else if (rc !== rawContact) { rawContact = rc; changed = now; }
      if (now - changed >= DEBOUNCE) {
        if (rawContact && power === "off") {
          power = "wake"; wakeAt = now; svg.classList.remove("sleep");
        } else if (!rawContact && power !== "off") {
          power = "off"; svg.classList.add("sleep");
        }
      }
      if (power === "wake" && now - wakeAt >= WAKE_MS) power = "on";
      if (power === "off") return { data: sleep(d) };
      if (power === "wake") return { data: wake(d, now - wakeAt) };
      return { data: d };
    }
    if (needsMedia) mediaMgr.start();
    function frame(now) {
      const raw = demo ? demoState(now / 1000 + demoOffset, demoIgn) : state;
      const live = !!raw.c && (demo || now - lastMsg < 2000);
      if (wait) {
        wait.style.display = live ? "none" : "";
        const title = wait.querySelector("div");
        if (title && raw.game) title.textContent = "Waiting for " + raw.game;
      }
      if (!demo && raw.game_id && raw.game_id !== GAME &&
          !params.has("nogame") && !GAME_OVERRIDE) {
        GAME = raw.game_id;
        loadTheme(themeCar || CAR);
      }
      if (!demo && raw.car && raw.car !== themeCar) {
        themeCar = raw.car;
        loadTheme(themeCar);
      }
      const res = updatePower(raw, live, now);
      view.update(res.data, now, mediaMgr.state);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    addEventListener("click", () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
    });
  }

  window.IDashStudio = {
    render, start, demoState, DEMO_ART, DEFAULT_THEME,
    resolve: role, display,
  };
})();
