/* idash SimHub faithful runtime: dessine le dashboard SimHub d'origine. */
(() => {
  const NS = "http://www.w3.org/2000/svg";
  const XHTML = "http://www.w3.org/1999/xhtml";
  let uid = 0;
  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in (attrs || {})) {
      if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    }
    if (parent) parent.appendChild(e);
    return e;
  };
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const num = (v, d = 0) => (v == null ? d : Number(v) || 0);

  function color(raw) {
    if (typeof raw !== "string") return null;
    const s = raw.trim().replace(/^#/, "");
    if (s.length === 8) {
      return { r: parseInt(s.slice(2, 4), 16), g: parseInt(s.slice(4, 6), 16),
        b: parseInt(s.slice(6, 8), 16), a: parseInt(s.slice(0, 2), 16) / 255 };
    }
    if (s.length === 6) {
      return { r: parseInt(s.slice(0, 2), 16), g: parseInt(s.slice(2, 4), 16),
        b: parseInt(s.slice(4, 6), 16), a: 1 };
    }
    return null;
  }
  const rgba = c => `rgba(${c.r},${c.g},${c.b},${c.a})`;
  function paint(brush, defs) {
    if (!brush) return "none";
    if (brush.kind === "solid") {
      const c = color(brush.color);
      return c && c.a > 0 ? rgba(c) : "none";
    }
    if (brush.kind !== "linear" || !brush.stops || !brush.stops.length) {
      return "none";
    }
    const id = "sg" + (++uid);
    const grad = el("linearGradient", {
      id, x1: brush.x1, y1: brush.y1, x2: brush.x2, y2: brush.y2,
      gradientUnits: "objectBoundingBox",
    }, defs);
    brush.stops.forEach(stop => {
      const c = color(stop.color);
      if (c) el("stop", { offset: clamp(stop.offset), "stop-color":
        `rgb(${c.r},${c.g},${c.b})`, "stop-opacity": c.a }, grad);
    });
    return `url(#${id})`;
  }
  function roundRect(x, y, w, h, corners) {
    const [tl, tr, br, bl] = corners || [0, 0, 0, 0];
    return `M${x + tl},${y}H${x + w - tr}A${tr},${tr} 0 0 1 ${x + w},${y + tr}` +
      `V${y + h - br}A${br},${br} 0 0 1 ${x + w - br},${y + h}` +
      `H${x + bl}A${bl},${bl} 0 0 1 ${x},${y + h - bl}` +
      `V${y + tl}A${tl},${tl} 0 0 1 ${x + tl},${y}Z`;
  }
  function timeText(ms) {
    if (!(ms > 0) || ms >= 3600000) return "-:--.---";
    const m = Math.floor(ms / 60000), s = Math.floor(ms % 60000 / 1000);
    return m + ":" + String(s).padStart(2, "0") + "." +
      String(Math.floor(ms % 1000)).padStart(3, "0");
  }
  function valueText(bind, state, fallback) {
    if (!bind) return fallback == null ? "" : String(fallback);
    const raw = state ? state[bind.field] : null;
    if (raw === undefined || raw === null) return fallback == null ? "" : String(fallback);
    let text;
    if (typeof raw === "string") {
      text = raw;
    } else if (typeof raw === "boolean") {
      text = raw ? "ON" : "OFF";
    } else {
      let v = Number(raw);
      if (!isFinite(v)) return fallback == null ? "" : String(fallback);
      v = v * (bind.scale == null ? 1 : bind.scale) +
        (bind.offset == null ? 0 : bind.offset);
      const fmt = bind.format || "int";
      if (fmt === "time" || fmt === "clock") text = timeText(v);
      else if (fmt === "delta") {
        text = Math.abs(v) < 60000
          ? (v < 0 ? "-" : "+") + (Math.abs(v) / 1000).toFixed(3) : "";
      } else if (fmt === "gear") {
        text = v < 0 ? "R" : v === 0 ? "N" : String(Math.round(v));
      } else if (fmt === "float2") text = Number(v).toFixed(2);
      else if (fmt === "float1") text = Number(v).toFixed(1);
      else if (fmt === "percent") text = Math.round(v * 100) + "%";
      else if (fmt === "text") text = String(raw);
      else text = String(Math.round(v));
    }
    let suffix = bind.suffix || "";
    if (bind.suffixField && state && state[bind.suffixField]) {
      suffix = (bind.suffixSpace ? " " : "") + state[bind.suffixField];
    }
    return text + suffix;
  }
  function axis(h) {
    return h === 1 ? "middle" : h === 2 ? "end" : "start";
  }
  function textPos(item) {
    const style = item.style || {};
    const h = style.hAlign == null ? 0 : style.hAlign;
    const v = style.vAlign == null ? 0 : style.vAlign;
    const size = style.size || 20;
    const x = h === 1 ? item.left + item.width / 2 :
      h === 2 ? item.left + item.width : item.left;
    const y = v === 1 ? item.top + item.height / 2 :
      v === 2 ? item.top + item.height : item.top + size;
    const baseline = v === 1 ? "middle" : v === 2 ? "text-after-edge" : "alphabetic";
    return { x, y, baseline, anchor: axis(h) };
  }
  function drawText(item, parent, updates) {
    const style = item.style || {};
    const pos = textPos(item);
    const node = el("text", {
      x: pos.x, y: pos.y, "text-anchor": pos.anchor,
      "dominant-baseline": pos.baseline,
      "font-family": style.font || "sans-serif",
      "font-size": style.size || 20,
      "font-weight": style.weight || 400,
      "font-style": style.italic ? "italic" : "normal",
      fill: paint({ kind: "solid", color: style.color }, null),
    }, parent);
    if (item.bind) {
      const update = state => {
        const text = valueText(item.bind, state, item.text);
        if (node.textContent !== text) node.textContent = text;
      };
      updates.push(update);
      update(null);
    } else {
      node.textContent = item.text || "";
    }
  }
  function gradientBrush(brush) {
    return brush;
  }
  function drawShape(item, parent, defs) {
    const fill = paint(gradientBrush(item.fill), defs);
    const border = item.border;
    if (item.type === "Ellipse") {
      el("ellipse", {
        cx: item.left + item.width / 2, cy: item.top + item.height / 2,
        rx: item.width / 2, ry: item.height / 2, fill,
        stroke: item.stroke ? paint({ kind: "solid", color: item.stroke }, defs) : "none",
        "stroke-width": item.strokeWidth || 0,
      }, parent);
      return;
    }
    el("path", {
      d: roundRect(item.left, item.top, item.width, item.height,
        border && border.corners),
      fill,
      stroke: border ? paint({ kind: "solid", color: border.color }, defs) : "none",
      "stroke-width": border ? border.width : 0,
    }, parent);
  }
  function drawImage(item, parent, updates) {
    const node = el("image", {
      href: item.src, x: item.left, y: item.top,
      width: item.width, height: item.height,
      preserveAspectRatio: "xMidYMid meet",
    }, parent);
    if (item.visible_bind) {
      updates.push(state => {
        const fields = item.visible_bind.any || [];
        const on = fields.some(field => !!state[field]);
        node.style.display = on ? "" : "none";
      });
    }
  }
  function parseSize(raw, fallback = [10, 2]) {
    const parts = String(raw || "").split(",").map(Number);
    return [parts[0] || fallback[0], parts[1] || fallback[1]];
  }
  function arcPath(cx, cy, r, a0, a1) {
    const rad = a => a * Math.PI / 180;
    const x0 = cx + r * Math.cos(rad(a0)), y0 = cy + r * Math.sin(rad(a0));
    const x1 = cx + r * Math.cos(rad(a1)), y1 = cy + r * Math.sin(rad(a1));
    const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
    const sweep = a1 >= a0 ? 1 : 0;
    return `M${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 ${large} ${sweep} ${x1.toFixed(2)} ${y1.toFixed(2)}`;
  }
  function labelValues(item) {
    const min = num(item.minimum, 0), max = num(item.maximum, 1);
    const custom = String(item.customLabels || "").split(";").filter(Boolean);
    if (custom.length) {
      return custom.map((label, i) => ({
        value: min + (max - min) * i / Math.max(1, custom.length - 1),
        label,
      }));
    }
    const range = max - min;
    let step;
    if (item.majorDivisions >= 2 && item.majorDivisions <= 14 &&
        range / item.majorDivisions >= 1) {
      step = range / item.majorDivisions;
    } else if (range <= 12) {
      step = 1;
    } else {
      const raw = range / 10, pow = Math.pow(10, Math.floor(Math.log10(raw)));
      const norm = raw / pow;
      step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * pow;
    }
    const out = [];
    for (let v = min; v <= max + step * .01; v += step) {
      out.push({ value: v, label: String(Math.round(v * 100) / 100) });
    }
    return out;
  }
  function drawGauge(item, parent, defs, updates) {
    const cx = item.left + item.width / 2;
    const cy = item.top + item.height / 2;
    const g = el("g", {}, parent);
    const outer = item.outerRadius || Math.min(item.width, item.height) / 2;
    const min = num(item.minimum, 0), max = num(item.maximum, 100);
    const start = num(item.start, 135), sweep = num(item.sweep, 270);
    const range = max - min || 1;
    const angle = value => start + sweep * clamp((value - min) / range);
    if (item.dialBg || item.outerStroke > 0) {
      el("circle", { cx, cy, r: outer, fill: paint(item.dialBg, defs),
        stroke: "none" }, g);
      if (item.outerStroke > 0) {
        el("circle", { cx, cy, r: outer, fill: "none",
          stroke: paint(item.dialStroke, defs),
          "stroke-width": item.outerStroke }, g);
      }
    }
    if (item.showRadial) {
      const r = item.radialRadius || outer;
      const stroke = item.optimal && item.optimal.ArcColor || item.radialColor ||
        "#FF808080";
      el("path", { d: arcPath(cx, cy, r, start, start + sweep), fill: "none",
        stroke: paint({ kind: "solid", color: stroke }, defs),
        "stroke-width": item.radialThickness || 4 }, g);
      const fg = el("path", { d: arcPath(cx, cy, r, start, start), fill: "none",
        stroke: paint({ kind: "solid", color: item.radialColor || "#FFFFFFFF" }, defs),
        "stroke-width": item.radialThickness || 4 }, g);
      updates.push(state => {
        const val = item.value ? Number(valueText(item.value, state, 0)
          .replace(/[^\d.+-]/g, "")) : 0;
        const frac = clamp((val - min) / range);
        const col = val < item.rangeStart ? (item.below.ArcColor || "#FFFF0000")
          : (item.radialColor || "#FFFFFFFF");
        fg.setAttribute("d", arcPath(cx, cy, r, start, start + sweep * frac));
        fg.setAttribute("stroke", paint({ kind: "solid", color: col }, defs));
      });
    }
    const labels = labelValues(item);
    const style = item.labelStyle || {};
    const labelColor = style.LabelColor || "#FFFFFFFF";
    const font = style.LabelFont || "sans-serif";
    const fontSize = style.LabelFontSize || 20;
    const labelRadius = style.LabelRadius || item.majorRadius || outer * .75;
    const above = item.above || {};
    const rangeEnd = item.rangeEnd || max + 1;
    labels.forEach(entry => {
      const a = angle(entry.value);
      const red = entry.value > rangeEnd && above.EnableLabelColor;
      const t = el("text", { x: cx + labelRadius * Math.cos(a * Math.PI / 180),
        y: cy + labelRadius * Math.sin(a * Math.PI / 180),
        "text-anchor": "middle", "dominant-baseline": "central",
        "font-family": font, "font-size": fontSize,
        "font-weight": (style.LabelFontWeight || "normal").toLowerCase() === "bold" ? 700 : 400,
        fill: paint({ kind: "solid", color: red ? (above.LabelColor || "#FFFF0000") : labelColor }, defs) }, g);
      t.textContent = entry.label;
    });
    const majorSize = parseSize(item.majorSize, [12, 2]);
    const minorSize = parseSize(item.minorSize, [6, 1]);
    const minorStep = labels.length > 1 && item.minorDivisions > 0
      ? (labels[1].value - labels[0].value) / item.minorDivisions : 0;
    if (item.majorRadius) {
      labels.forEach(entry => {
        const a = angle(entry.value) * Math.PI / 180;
        const r = item.majorRadius;
        const red = entry.value > rangeEnd && (above.EnableMajorColor || above.EnableMinorColor);
        el("line", {
          x1: cx + (r - majorSize[0]) * Math.cos(a),
          y1: cy + (r - majorSize[0]) * Math.sin(a),
          x2: cx + r * Math.cos(a), y2: cy + r * Math.sin(a),
          stroke: paint({ kind: "solid", color: red ? (above.MajorColor || above.MinorColor) : item.majorColor }, defs),
          "stroke-width": majorSize[1],
        }, g);
      });
    }
    if (item.minorRadius && minorStep > 0) {
      for (let v = min; v <= max + minorStep * .01; v += minorStep) {
        const a = angle(v) * Math.PI / 180;
        const r = item.minorRadius;
        el("line", {
          x1: cx + (r - minorSize[0]) * Math.cos(a),
          y1: cy + (r - minorSize[0]) * Math.sin(a),
          x2: cx + r * Math.cos(a), y2: cy + r * Math.sin(a),
          stroke: paint({ kind: "solid", color: item.minorColor }, defs),
          "stroke-width": minorSize[1],
        }, g);
      }
    }
    if (item.showNeedle && item.value) {
      const needle = el("g", {}, g);
      const thick = Math.max(2, (item.needleThickness || 8) * .28);
      el("line", { x1: cx, y1: cy, x2: cx + Math.max(8, item.needleLength || outer * .8),
        y2: cy, stroke: paint({ kind: "solid", color: "#FFFF0000" }, defs),
        "stroke-width": thick, "stroke-linecap": "round" }, needle);
      updates.push(state => {
        const val = Number(valueText(item.value, state, min)
          .replace(/[^\d.+-]/g, "")) || 0;
        const a = angle(val);
        needle.setAttribute("transform", `rotate(${a} ${cx} ${cy})`);
      });
    }
    if (item.capRadius > 0) {
      el("circle", { cx, cy, r: item.capRadius,
        fill: paint({ kind: "solid", color: "#FF1A1A1A" }, defs),
        stroke: paint(item.dialStroke, defs),
        "stroke-width": Math.max(1, item.outerStroke * .5 || 2) }, g);
    }
  }
  let etsMapInfo = null;
  const etsTiles = new Map();

  function loadETSMapInfo() {
    if (etsMapInfo) return Promise.resolve(etsMapInfo);
    etsMapInfo = fetch("/api/ets2/map", { cache: "no-store" })
      .then(r => r.json()).catch(() => ({ ok: false }));
    return etsMapInfo;
  }

  function drawETSMap(item, parent, updates) {
    const fo = el("foreignObject", {
      x: item.left, y: item.top, width: item.width, height: item.height,
    }, parent);
    const box = document.createElementNS(XHTML, "div");
    box.setAttribute("style", "width:100%;height:100%;background:#111;" +
      "overflow:hidden;position:relative");
    const canvas = document.createElementNS(XHTML, "canvas");
    canvas.width = Math.max(1, Math.round(item.width));
    canvas.height = Math.max(1, Math.round(item.height));
    canvas.setAttribute("style", "width:100%;height:100%;display:block;" +
      "touch-action:none;cursor:grab");
    box.appendChild(canvas);
    fo.appendChild(box);
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    let mapInfo = null, state = {}, lastKey = "", timer = 0;
    let follow = true, userZoom = null, viewX = null, viewY = null;
    let drag = null, pinch = null, lastTap = 0;

    function schedule() {
      if (timer) return;
      timer = setTimeout(() => {
        timer = 0;
        draw();
      }, 50);
    }

    function autoZoom(speed) {
      return speed > 100 ? 7 : 8;
    }

    function viewCenter(t, z, speed) {
      const span = 256 * Math.pow(2, z);
      let mx = state.map_x == null ? (t.x1 + t.x2) / 2 : Number(state.map_x);
      let my = state.map_y == null ? (t.y1 + t.y2) / 2 : Number(state.map_y);
      if (!isFinite(mx) || !isFinite(my) ||
          mx < t.x1 || mx > t.x2 || my < t.y1 || my > t.y2) {
        mx = (t.x1 + t.x2) / 2;
        my = (t.y1 + t.y2) / 2;
        return { x: mx, y: my, truck: false };
      }
      return { x: mx, y: my, truck: state.map_x != null };
    }

    function draw() {
      ctx.fillStyle = "#141414";
      ctx.fillRect(0, 0, W, H);
      if (!mapInfo || !mapInfo.ok || !mapInfo.tile) {
        ctx.fillStyle = "#8a8272";
        ctx.font = "16px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Carte ETS2 non installée", W / 2, H / 2 - 8);
        ctx.font = "13px sans-serif";
        ctx.fillText("Réglages → Jeux → Installer la carte", W / 2, H / 2 + 18);
        return;
      }
      const t = mapInfo.tile;
      const speed = Math.abs(Number(state.v) || 0);
      let z = userZoom == null ? autoZoom(speed) : userZoom;
      z = Math.max(t.minZoom || 0, Math.min((t.maxZoom || 8) + 2, z));
      const baseZ = Math.min(z, t.maxZoom || 8);
      const tileScale = Math.pow(2, z - baseZ);
      const tilePx = 256 * tileScale;
      const span = 256 * Math.pow(2, z);
      const worldW = (t.x2 - t.x1) || 1;
      const worldH = (t.y2 - t.y1) || 1;
      const center = viewCenter(t, z, speed);
      if (follow || viewX == null || viewY == null) {
        viewX = center.x;
        viewY = center.y;
      }
      const px = (viewX - t.x1) / worldW * span;
      const py = (viewY - t.y1) / worldH * span;
      const left = px - W / 2;
      const top = py - H / 2;
      const x0 = Math.floor(left / tilePx);
      const x1 = Math.floor((left + W) / tilePx);
      const y0 = Math.floor(top / tilePx);
      const y1 = Math.floor((top + H) / tilePx);
      const max = Math.pow(2, baseZ);
      for (let x = x0; x <= x1; x++) {
        if (x < 0 || x >= max) continue;
        for (let y = y0; y <= y1; y++) {
          if (y < 0 || y >= max) continue;
          const key = baseZ + "/" + x + "/" + y;
          let img = etsTiles.get(key);
          if (!img) {
            img = new Image();
            img.onload = schedule;
            img.onerror = () => { etsTiles.set(key, false); };
            img.src = "/api/ets2/map/tile/" + key + ".png";
            etsTiles.set(key, img);
          }
          if (img && img.complete && img.naturalWidth) {
            ctx.drawImage(img, x * tilePx - left, y * tilePx - top,
              tilePx, tilePx);
          }
        }
      }
      if (center.truck) {
        const tx = (Number(state.map_x) - t.x1) / worldW * span - left;
        const ty = (Number(state.map_y) - t.y1) / worldH * span - top;
        if (tx >= -20 && tx <= W + 20 && ty >= -20 && ty <= H + 20) {
          ctx.save();
          ctx.translate(tx, ty);
          ctx.rotate((Number(state.map_heading) || 0) * Math.PI / 180);
          ctx.beginPath();
          ctx.moveTo(0, -12);
          ctx.lineTo(8, 10);
          ctx.lineTo(0, 6);
          ctx.lineTo(-8, 10);
          ctx.closePath();
          ctx.fillStyle = "#ff5a2a";
          ctx.fill();
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.restore();
        }
      }
    }

    function update(next) {
      state = next || {};
      const key = [state.map_x, state.map_y, state.map_heading,
        Math.round((state.v || 0) / 10)].join("|");
      if (key !== lastKey) { lastKey = key; schedule(); }
    }

    function worldPerPixel(z) {
      if (!mapInfo || !mapInfo.tile) return 1;
      const t = mapInfo.tile;
      const span = 256 * Math.pow(2, z);
      return {
        x: (t.x2 - t.x1) / span,
        y: (t.y2 - t.y1) / span,
      };
    }

    function zoomBy(delta) {
      if (!mapInfo || !mapInfo.tile) return;
      const t = mapInfo.tile;
      const speed = Math.abs(Number(state.v) || 0);
      const base = userZoom == null ? autoZoom(speed) : userZoom;
      const next = Math.max(t.minZoom || 0,
        Math.min((t.maxZoom || 8) + 2, base + delta));
      if (next !== base) {
        userZoom = next;
        schedule();
      }
    }

    canvas.addEventListener("touchstart", e => {
      e.preventDefault();
      e.stopPropagation();
      if (e.touches.length === 2) {
        const a = e.touches[0], b = e.touches[1];
        pinch = {
          dist: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY),
          zoom: userZoom == null ? autoZoom(Math.abs(Number(state.v) || 0))
            : userZoom,
        };
        drag = null;
      } else if (e.touches.length === 1) {
        drag = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        if (follow) {
          const t = mapInfo && mapInfo.tile;
          if (t) {
            const speed = Math.abs(Number(state.v) || 0);
            const z = userZoom == null ? autoZoom(speed) : userZoom;
            const center = viewCenter(t, z, speed);
            viewX = center.x;
            viewY = center.y;
          }
        }
        follow = false;
      }
    }, { passive: false });

    canvas.addEventListener("touchmove", e => {
      e.preventDefault();
      e.stopPropagation();
      if (!mapInfo || !mapInfo.tile) return;
      if (e.touches.length === 2 && pinch) {
        const a = e.touches[0], b = e.touches[1];
        const dist = Math.hypot(a.clientX - b.clientX,
          a.clientY - b.clientY);
        if (pinch.dist > 0) {
          const z = Math.max(mapInfo.tile.minZoom || 0,
            Math.min((mapInfo.tile.maxZoom || 8) + 2,
              Math.round(pinch.zoom + Math.log2(dist / pinch.dist))));
          if (z !== userZoom) {
            userZoom = z;
            schedule();
          }
        }
      } else if (e.touches.length === 1 && drag) {
        const touch = e.touches[0];
        const dx = touch.clientX - drag.x;
        const dy = touch.clientY - drag.y;
        const z = userZoom == null
          ? autoZoom(Math.abs(Number(state.v) || 0)) : userZoom;
        const per = worldPerPixel(z);
        viewX -= dx * per.x;
        viewY -= dy * per.y;
        drag = { x: touch.clientX, y: touch.clientY };
        follow = false;
        schedule();
      }
    }, { passive: false });

    canvas.addEventListener("touchend", e => {
      e.stopPropagation();
      if (e.touches.length === 0) {
        pinch = null;
        drag = null;
        const now = performance.now();
        if (now - lastTap < 320) {
          follow = true;
          userZoom = null;
          schedule();
          lastTap = 0;
        } else {
          lastTap = now;
        }
      }
    }, { passive: false });

    canvas.addEventListener("touchcancel", () => {
      pinch = null;
      drag = null;
    }, { passive: true });

    canvas.addEventListener("wheel", e => {
      e.preventDefault();
      zoomBy(e.deltaY < 0 ? 1 : -1);
    }, { passive: false });

    loadETSMapInfo().then(info => {
      mapInfo = info;
      schedule();
    });
    setInterval(schedule, 500);
    updates.push(update);
    update({});
  }

  function drawLinearGauge(item, parent, updates, defs) {
    const frac = v => {
      const min = item.minimum == null ? 0 : item.minimum;
      const max = item.maximum == null ? 100 : item.maximum;
      return clamp((Number(v) - min) / ((max - min) || 1));
    };
    if (item.backgroundSrc) {
      el("image", {
        href: item.backgroundSrc, x: item.left, y: item.top,
        width: item.width, height: item.height,
        preserveAspectRatio: "xMidYMid meet",
      }, parent);
      return;
    }
    const vertical = item.orientation === 1;
    const track = el("rect", {
      x: item.left, y: item.top, width: item.width, height: item.height,
      rx: 2,
      fill: item.trackColor ? paint({ kind: "solid", color: item.trackColor }, defs) : "none",
      stroke: paint({ kind: "solid", color: "#FF555555" }, defs),
      "stroke-width": 1,
    }, parent);
    const fill = el("rect", {
      x: item.left, y: item.top, width: 0, height: 0,
      rx: 2,
      fill: paint({ kind: "solid", color: item.color || "#FFFFFFFF" }, defs),
    }, parent);
    updates.push(state => {
      let raw = item.value && state ? state[item.value.field] : null;
      if (raw != null && item.value) {
        raw = Number(raw) * (item.value.scale == null ? 1 : item.value.scale) +
          (item.value.offset == null ? 0 : item.value.offset);
      }
      const f = frac(raw == null ? item.minimum : raw);
      if (vertical) {
        const h = item.height * f;
        fill.setAttribute("x", item.left);
        fill.setAttribute("y", item.top + item.height - h);
        fill.setAttribute("width", item.width);
        fill.setAttribute("height", h);
      } else {
        fill.setAttribute("x", item.left);
        fill.setAttribute("y", item.top);
        fill.setAttribute("width", item.width * f);
        fill.setAttribute("height", item.height);
      }
    });
  }

  function drawItem(item, parent, ctx) {
    if (!item || item.visible === false) return;
    const g = el("g", {}, parent);
    if (item.opacity != null && item.opacity < 1) g.setAttribute("opacity", item.opacity);
    if (item.rotation) {
      const cx = item.left + item.width / 2, cy = item.top + item.height / 2;
      g.setAttribute("transform", `rotate(${item.rotation} ${cx} ${cy})`);
    }
    if (item.type === "Layer") {
      (item.children || []).forEach(child => drawItem(child, g, ctx));
    } else if (item.type === "Widget") {
      const child = item.child || {};
      const base = child.base || [800, 480];
      const cg = el("g", {
        transform: `translate(${item.left} ${item.top}) scale(${item.width / base[0]} ${item.height / base[1]})`,
      }, g);
      (child.items || []).forEach(ch => drawItem(ch, cg, ctx));
    } else if (item.type === "Text") {
      drawText(item, g, ctx.updates);
    } else if (item.type === "Image") {
      drawImage(item, g, ctx.updates);
    } else if (item.type === "Rectangle" || item.type === "Gradient" ||
               item.type === "Ellipse") {
      drawShape(item, g, ctx.defs);
    } else if (item.type === "DialGauge") {
      drawGauge(item, g, ctx.defs, ctx.updates);
    } else if (item.type === "ETSMap") {
      drawETSMap(item, g, ctx.updates);
    } else if (item.type === "LinearGauge") {
      drawLinearGauge(item, g, ctx.updates, ctx.defs);
    }
  }
  function render(svg, layout, opts) {
    const data = (layout && layout.simhub) || {};
    const base = data.base || [1280, 720];
    const W = base[0] || 1280, H = base[1] || 720;
    svg.textContent = "";
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("xmlns", NS);
    const defs = el("defs", {}, svg);
    const bg = color(data.background) || { r: 0, g: 0, b: 0, a: 1 };
    el("rect", { x: 0, y: 0, width: W, height: H, fill: rgba(bg) }, svg);
    const updates = [];
    const root = el("g", {}, svg);
    const ctx = {
      defs, updates,
      mapUrl: data.map_url || (opts && opts.mapUrl) ||
        "http://127.0.0.1:8888/maps/map.html#norefresh",
    };
    (data.items || []).forEach(item => drawItem(item, root, ctx));
    const view = {
      update(state) {
        updates.forEach(fn => {
          try { fn(state || {}); } catch (e) {}
        });
      },
    };
    view.update((opts && opts.state) || {});
    return view;
  }
  window.IDashSimhub = { render };
})();
