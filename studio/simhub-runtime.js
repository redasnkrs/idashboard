/* idash SimHub faithful runtime: dessine le dashboard SimHub d'origine. */
(() => {
  const NS = "http://www.w3.org/2000/svg";
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
    if (typeof raw === "string") return raw;
    if (typeof raw === "boolean") return raw ? "ON" : "OFF";
    let v = Number(raw);
    if (!isFinite(v)) return fallback == null ? "" : String(fallback);
    v = v * (bind.scale == null ? 1 : bind.scale) +
      (bind.offset == null ? 0 : bind.offset);
    const fmt = bind.format || "int";
    if (fmt === "time" || fmt === "clock") return timeText(v);
    if (fmt === "delta") {
      if (Math.abs(v) >= 60000) return "";
      return (v < 0 ? "-" : "+") + (Math.abs(v) / 1000).toFixed(3);
    }
    if (fmt === "gear") return v < 0 ? "R" : v === 0 ? "N" : String(Math.round(v));
    if (fmt === "float2") return Number(v).toFixed(2);
    if (fmt === "float1") return Number(v).toFixed(1);
    if (fmt === "percent") return Math.round(v * 100) + "%";
    if (fmt === "text") return String(raw);
    return String(Math.round(v));
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
  function drawImage(item, parent) {
    el("image", {
      href: item.src, x: item.left, y: item.top,
      width: item.width, height: item.height,
      preserveAspectRatio: "xMidYMid meet",
    }, parent);
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
      drawImage(item, g);
    } else if (item.type === "Rectangle" || item.type === "Gradient" ||
               item.type === "Ellipse") {
      drawShape(item, g, ctx.defs);
    } else if (item.type === "DialGauge") {
      drawGauge(item, g, ctx.defs, ctx.updates);
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
    (data.items || []).forEach(item => drawItem(item, root, { defs, updates }));
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
