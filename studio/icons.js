/* Built-in icon library. Lucide icons are ISC licensed; see ICONS_LICENSE.txt. */
window.IDashIcons = (() => {
  const icons = [
  {
    "id": "low-beam",
    "label": "Low Beam",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<path d=\"M10 12C22 12 28 16 28 20C28 24 22 28 10 28Z\"/><path d=\"M8 16L0 20M8 20L0 23M8 24L0 26\"/>"
  },
  {
    "id": "high-beam",
    "label": "High Beam",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<path d=\"M10 12C22 12 28 16 28 20C28 24 22 28 10 28Z\"/><path d=\"M8 16H0M8 20H0M8 24H0\"/>"
  },
  {
    "id": "handbrake",
    "label": "Handbrake",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<circle cx=\"20\" cy=\"20\" r=\"12\"/><path d=\"M6 12A16 16 0 0 0 6 28M34 12A16 16 0 0 1 34 28\"/><text x=\"20\" y=\"20\" font-size=\"16\" font-weight=\"700\" text-anchor=\"middle\" dominant-baseline=\"central\" stroke=\"none\" fill=\"currentColor\">P</text>"
  },
  {
    "id": "pit",
    "label": "Pit Limiter",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<rect x=\"4\" y=\"12\" width=\"32\" height=\"16\" rx=\"4\"/><text x=\"20\" y=\"20\" font-size=\"10\" font-weight=\"700\" text-anchor=\"middle\" dominant-baseline=\"central\" stroke=\"none\" fill=\"currentColor\">PIT</text>"
  },
  {
    "id": "tyre",
    "label": "Tyre",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<circle cx=\"20\" cy=\"20\" r=\"15\"/><circle cx=\"20\" cy=\"20\" r=\"7\"/><path d=\"M20 5V9M20 31V35M5 20H9M31 20H35M9.4 9.4L12.2 12.2M27.8 27.8L30.6 30.6M30.6 9.4L27.8 12.2M12.2 27.8L9.4 30.6\"/>"
  },
  {
    "id": "brake-disc",
    "label": "Brake Disc",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<circle cx=\"20\" cy=\"20\" r=\"15\"/><circle cx=\"20\" cy=\"20\" r=\"5\"/><circle cx=\"20\" cy=\"10\" r=\"1.5\"/><circle cx=\"28.7\" cy=\"15\" r=\"1.5\"/><circle cx=\"28.7\" cy=\"25\" r=\"1.5\"/><circle cx=\"20\" cy=\"30\" r=\"1.5\"/><circle cx=\"11.3\" cy=\"25\" r=\"1.5\"/><circle cx=\"11.3\" cy=\"15\" r=\"1.5\"/>"
  },
  {
    "id": "engine",
    "label": "Engine",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<path d=\"M8 14H16L20 10H30V16H34V26H28V30H10V24H6V18H8Z\"/><path d=\"M14 18V24H24V18Z\"/><path d=\"M30 18H34\"/>"
  },
  {
    "id": "turbo",
    "label": "Turbo",
    "cat": "Automotive",
    "viewBox": "0 0 40 40",
    "inner": "<circle cx=\"20\" cy=\"20\" r=\"13\"/><path d=\"M20 20L28 12M20 20L12 12M20 20L20 32\"/><circle cx=\"20\" cy=\"20\" r=\"3\" fill=\"currentColor\" stroke=\"none\"/>"
  },
  {
    "id": "fuel",
    "label": "Fuel",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M14 13h2a2 2 0 0 1 2 2v2a2 2 0 0 0 4 0v-6.998a2 2 0 0 0-.59-1.42L18 5\" /> <path d=\"M14 21V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v16\" /> <path d=\"M2 21h13\" /> <path d=\"M3 9h11\" />"
  },
  {
    "id": "gauge",
    "label": "Gauge",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"m12 14 4-4\" /> <path d=\"M3.34 19a10 10 0 1 1 17.32 0\" />"
  },
  {
    "id": "disc",
    "label": "Disc",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" /> <circle cx=\"12\" cy=\"12\" r=\"2\" />"
  },
  {
    "id": "car",
    "label": "Car",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2\" /> <circle cx=\"7\" cy=\"17\" r=\"2\" /> <path d=\"M9 17h6\" /> <circle cx=\"17\" cy=\"17\" r=\"2\" />"
  },
  {
    "id": "wrench",
    "label": "Wrench",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z\" />"
  },
  {
    "id": "cog",
    "label": "Cog",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M11 10.27 7 3.34\" /> <path d=\"m11 13.73-4 6.93\" /> <path d=\"M12 22v-2\" /> <path d=\"M12 2v2\" /> <path d=\"M14 12h8\" /> <path d=\"m17 20.66-1-1.73\" /> <path d=\"m17 3.34-1 1.73\" /> <path d=\"M2 12h2\" /> <path d=\"m20.66 17-1.73-1\" /> <path d=\"m20.66 7-1.73 1\" /> <path d=\"m3.34 17 1.73-1\" /> <path d=\"m3.34 7 1.73 1\" /> <circle cx=\"12\" cy=\"12\" r=\"2\" /> <circle cx=\"12\" cy=\"12\" r=\"8\" />"
  },
  {
    "id": "settings",
    "label": "Settings",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915\" /> <circle cx=\"12\" cy=\"12\" r=\"3\" />"
  },
  {
    "id": "thermometer",
    "label": "Thermometer",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z\" />"
  },
  {
    "id": "droplet",
    "label": "Droplet",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z\" />"
  },
  {
    "id": "wind",
    "label": "Wind",
    "cat": "Weather",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12.8 19.6A2 2 0 1 0 14 16H2\" /> <path d=\"M17.5 8a2.5 2.5 0 1 1 2 4H2\" /> <path d=\"M9.8 4.4A2 2 0 1 1 11 8H2\" />"
  },
  {
    "id": "battery",
    "label": "Battery",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M 22 14 L 22 10\" /> <rect x=\"2\" y=\"6\" width=\"16\" height=\"12\" rx=\"2\" />"
  },
  {
    "id": "battery-charging",
    "label": "Battery Charging",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"m11 7-3 5h4l-3 5\" /> <path d=\"M14.856 6H16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.935\" /> <path d=\"M22 14v-4\" /> <path d=\"M5.14 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2.936\" />"
  },
  {
    "id": "zap",
    "label": "Zap",
    "cat": "Vehicle",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M15.914 4a1.5 1.5 0 00-2.474-1.561l-9 9A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l9-9A1.5 1.5 0 0018.5 10h-3.997a.5.5 0 01-.472-.667z\" />"
  },
  {
    "id": "activity",
    "label": "Activity",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2\" />"
  },
  {
    "id": "target",
    "label": "Target",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" /> <circle cx=\"12\" cy=\"12\" r=\"6\" /> <circle cx=\"12\" cy=\"12\" r=\"2\" />"
  },
  {
    "id": "crosshair",
    "label": "Crosshair",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" /> <line x1=\"22\" x2=\"18\" y1=\"12\" y2=\"12\" /> <line x1=\"6\" x2=\"2\" y1=\"12\" y2=\"12\" /> <line x1=\"12\" x2=\"12\" y1=\"6\" y2=\"2\" /> <line x1=\"12\" x2=\"12\" y1=\"22\" y2=\"18\" />"
  },
  {
    "id": "flag",
    "label": "Flag",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528\" />"
  },
  {
    "id": "trophy",
    "label": "Trophy",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M10 14.66V17a1 1 0 0 1-1 1 2 2 0 0 0-2 2v2\" /> <path d=\"M14 14.66V17a1 1 0 0 0 1 1 2 2 0 0 1 2 2v2\" /> <path d=\"M17.916 10H19.5A2.5 2.5 0 0 0 22 7.5V5a1 1 0 0 0-1-1h-3\" /> <path d=\"M4 22h16\" /> <path d=\"M6 9a6 6 0 0 0 12 0V3a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1z\" /> <path d=\"M6.084 10H4.5A2.5 2.5 0 0 1 2 7.5V5a1 1 0 0 1 1-1h3\" />"
  },
  {
    "id": "medal",
    "label": "Medal",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M7.21 15 2.66 7.14a2 2 0 0 1 .13-2.2L4.4 2.8A2 2 0 0 1 6 2h12a2 2 0 0 1 1.6.8l1.6 2.14a2 2 0 0 1 .14 2.2L16.79 15\" /> <path d=\"M11 12 5.12 2.2\" /> <path d=\"m13 12 5.88-9.8\" /> <path d=\"M8 7h8\" /> <circle cx=\"12\" cy=\"17\" r=\"5\" /> <path d=\"M12 18v-2h-.5\" />"
  },
  {
    "id": "timer",
    "label": "Timer",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<line x1=\"10\" x2=\"14\" y1=\"2\" y2=\"2\" /> <line x1=\"12\" x2=\"15\" y1=\"14\" y2=\"11\" /> <circle cx=\"12\" cy=\"14\" r=\"8\" />"
  },
  {
    "id": "hourglass",
    "label": "Hourglass",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M5 22h14\" /> <path d=\"M5 2h14\" /> <path d=\"M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22\" /> <path d=\"M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2\" />"
  },
  {
    "id": "calendar",
    "label": "Calendar",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M8 2v3\" /> <path d=\"M16 2v3\" /> <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" /> <path d=\"M3 9h18\" />"
  },
  {
    "id": "clock",
    "label": "Clock",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" /> <path d=\"M12 6v6l4 2\" />"
  },
  {
    "id": "play",
    "label": "Play",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z\" />"
  },
  {
    "id": "pause",
    "label": "Pause",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<rect x=\"14\" y=\"3\" width=\"5\" height=\"18\" rx=\"1\" /> <rect x=\"5\" y=\"3\" width=\"5\" height=\"18\" rx=\"1\" />"
  },
  {
    "id": "skip-back",
    "label": "Skip Back",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M17.971 4.285A2 2 0 0 1 21 6v12a2 2 0 0 1-3.029 1.715l-9.997-5.998a2 2 0 0 1-.003-3.432z\" /> <path d=\"M3 20V4\" />"
  },
  {
    "id": "skip-forward",
    "label": "Skip Forward",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M21 4v16\" /> <path d=\"M6.029 4.285A2 2 0 0 0 3 6v12a2 2 0 0 0 3.029 1.715l9.997-5.998a2 2 0 0 0 .003-3.432z\" />"
  },
  {
    "id": "volume-2",
    "label": "Volume 2",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z\" /> <path d=\"M16 9a5 5 0 0 1 0 6\" /> <path d=\"M19.364 18.364a9 9 0 0 0 0-12.728\" />"
  },
  {
    "id": "radio",
    "label": "Radio",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M16.247 7.761a6 6 0 0 1 0 8.478\" /> <path d=\"M19.075 4.933a10 10 0 0 1 0 14.134\" /> <path d=\"M4.925 19.067a10 10 0 0 1 0-14.134\" /> <path d=\"M7.753 16.239a6 6 0 0 1 0-8.478\" /> <circle cx=\"12\" cy=\"12\" r=\"2\" />"
  },
  {
    "id": "headphones",
    "label": "Headphones",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3\" />"
  },
  {
    "id": "mic",
    "label": "Mic",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12 19v3\" /> <path d=\"M19 10v2a7 7 0 0 1-14 0v-2\" /> <rect x=\"9\" y=\"2\" width=\"6\" height=\"13\" rx=\"3\" />"
  },
  {
    "id": "camera",
    "label": "Camera",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M13.997 4a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 1.759-1.048l.489-.904A2 2 0 0 1 10.004 4z\" /> <circle cx=\"12\" cy=\"13\" r=\"3\" />"
  },
  {
    "id": "smartphone",
    "label": "Smartphone",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<rect width=\"14\" height=\"20\" x=\"5\" y=\"2\" rx=\"2\" ry=\"2\" /> <path d=\"M12 18h.01\" />"
  },
  {
    "id": "monitor",
    "label": "Monitor",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<rect width=\"20\" height=\"14\" x=\"2\" y=\"3\" rx=\"2\" /> <line x1=\"8\" x2=\"16\" y1=\"21\" y2=\"21\" /> <line x1=\"12\" x2=\"12\" y1=\"17\" y2=\"21\" />"
  },
  {
    "id": "disc-3",
    "label": "Disc 3",
    "cat": "Media",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" /> <path d=\"M6 12c0-1.7.7-3.2 1.8-4.2\" /> <circle cx=\"12\" cy=\"12\" r=\"2\" /> <path d=\"M18 12c0 1.7-.7 3.2-1.8 4.2\" />"
  },
  {
    "id": "sun",
    "label": "Sun",
    "cat": "Weather",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"4\" /> <path d=\"M12 2v2\" /> <path d=\"M12 20v2\" /> <path d=\"m4.93 4.93 1.41 1.41\" /> <path d=\"m17.66 17.66 1.41 1.41\" /> <path d=\"M2 12h2\" /> <path d=\"M20 12h2\" /> <path d=\"m6.34 17.66-1.41 1.41\" /> <path d=\"m19.07 4.93-1.41 1.41\" />"
  },
  {
    "id": "cloud",
    "label": "Cloud",
    "cat": "Weather",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z\" />"
  },
  {
    "id": "cloud-rain",
    "label": "Cloud Rain",
    "cat": "Weather",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242\" /> <path d=\"M16 14v6\" /> <path d=\"M8 14v6\" /> <path d=\"M12 16v6\" />"
  },
  {
    "id": "cloud-snow",
    "label": "Cloud Snow",
    "cat": "Weather",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242\" /> <path d=\"M8 15h.01\" /> <path d=\"M8 19h.01\" /> <path d=\"M12 17h.01\" /> <path d=\"M12 21h.01\" /> <path d=\"M16 15h.01\" /> <path d=\"M16 19h.01\" />"
  },
  {
    "id": "snowflake",
    "label": "Snowflake",
    "cat": "Weather",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"m10 20-1.25-2.5L6 18\" /> <path d=\"M10 4 8.75 6.5 6 6\" /> <path d=\"m14 20 1.25-2.5L18 18\" /> <path d=\"m14 4 1.25 2.5L18 6\" /> <path d=\"m17 21-3-6h-4\" /> <path d=\"m17 3-3 6 1.5 3\" /> <path d=\"M2 12h6.5L10 9\" /> <path d=\"m20 10-1.5 2 1.5 2\" /> <path d=\"M22 12h-6.5L14 15\" /> <path d=\"m4 10 1.5 2L4 14\" /> <path d=\"m7 21 3-6-1.5-3\" /> <path d=\"m7 3 3 6h4\" />"
  },
  {
    "id": "umbrella",
    "label": "Umbrella",
    "cat": "Weather",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12 13v7a2 2 0 0 0 4 0\" /> <path d=\"M12 2v2\" /> <path d=\"M20.992 13a1 1 0 0 0 .97-1.274 10.284 10.284 0 0 0-19.923 0A1 1 0 0 0 3 13z\" />"
  },
  {
    "id": "map",
    "label": "Map",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z\" /> <path d=\"M15 5.764v15\" /> <path d=\"M9 3.236v15\" />"
  },
  {
    "id": "map-pin",
    "label": "Map Pin",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0\" /> <circle cx=\"12\" cy=\"10\" r=\"3\" />"
  },
  {
    "id": "navigation",
    "label": "Navigation",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<polygon points=\"3 11 22 2 13 21 11 13 3 11\" />"
  },
  {
    "id": "compass",
    "label": "Compass",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" /> <path d=\"m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z\" />"
  },
  {
    "id": "route",
    "label": "Route",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"6\" cy=\"19\" r=\"3\" /> <path d=\"M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15\" /> <circle cx=\"18\" cy=\"5\" r=\"3\" />"
  },
  {
    "id": "locate",
    "label": "Locate",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<line x1=\"2\" x2=\"5\" y1=\"12\" y2=\"12\" /> <line x1=\"19\" x2=\"22\" y1=\"12\" y2=\"12\" /> <line x1=\"12\" x2=\"12\" y1=\"2\" y2=\"5\" /> <line x1=\"12\" x2=\"12\" y1=\"19\" y2=\"22\" /> <circle cx=\"12\" cy=\"12\" r=\"7\" />"
  },
  {
    "id": "arrow-up",
    "label": "Arrow Up",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"m5 12 7-7 7 7\" /> <path d=\"M12 19V5\" />"
  },
  {
    "id": "arrow-down",
    "label": "Arrow Down",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12 5v14\" /> <path d=\"m19 12-7 7-7-7\" />"
  },
  {
    "id": "arrow-left",
    "label": "Arrow Left",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"m12 19-7-7 7-7\" /> <path d=\"M19 12H5\" />"
  },
  {
    "id": "arrow-right",
    "label": "Arrow Right",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M5 12h14\" /> <path d=\"m12 5 7 7-7 7\" />"
  },
  {
    "id": "corner-up-left",
    "label": "Corner Up Left",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M20 20v-7a4 4 0 0 0-4-4H4\" /> <path d=\"M9 14 4 9l5-5\" />"
  },
  {
    "id": "corner-up-right",
    "label": "Corner Up Right",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"m15 14 5-5-5-5\" /> <path d=\"M4 20v-7a4 4 0 0 1 4-4h12\" />"
  },
  {
    "id": "flag-triangle-right",
    "label": "Flag Triangle Right",
    "cat": "Navigation",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M6 22V2.8a.8.8 0 0 1 1.17-.71l11.38 5.69a.8.8 0 0 1 0 1.44L6 15.5\" />"
  },
  {
    "id": "check",
    "label": "Check",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M20 6 9 17l-5-5\" />"
  },
  {
    "id": "x",
    "label": "X",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M18 6 6 18\" /> <path d=\"m6 6 12 12\" />"
  },
  {
    "id": "info",
    "label": "Info",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" /> <path d=\"M12 16v-4\" /> <path d=\"M12 8h.01\" />"
  },
  {
    "id": "power",
    "label": "Power",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12 2v10\" /> <path d=\"M18.4 6.6a9 9 0 1 1-12.77.04\" />"
  },
  {
    "id": "signal",
    "label": "Signal",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M2 20h.01\" /> <path d=\"M7 20v-4\" /> <path d=\"M12 20v-8\" /> <path d=\"M17 20V8\" /> <path d=\"M22 4v16\" />"
  },
  {
    "id": "wifi",
    "label": "Wifi",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12 20h.01\" /> <path d=\"M2 8.82a15 15 0 0 1 20 0\" /> <path d=\"M5 12.859a10 10 0 0 1 14 0\" /> <path d=\"M8.5 16.429a5 5 0 0 1 7 0\" />"
  },
  {
    "id": "bell",
    "label": "Bell",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M10.268 21a2 2 0 0 0 3.464 0\" /> <path d=\"M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326\" />"
  },
  {
    "id": "eye",
    "label": "Eye",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0\" /> <circle cx=\"12\" cy=\"12\" r=\"3\" />"
  },
  {
    "id": "eye-off",
    "label": "Eye Off",
    "cat": "Status",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49\" /> <path d=\"M14.084 14.158a3 3 0 0 1-4.242-4.242\" /> <path d=\"M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143\" /> <path d=\"m2 2 20 20\" />"
  },
  {
    "id": "plus",
    "label": "Plus",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M5 12h14\" /> <path d=\"M12 5v14\" />"
  },
  {
    "id": "minus",
    "label": "Minus",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M5 12h14\" />"
  },
  {
    "id": "search",
    "label": "Search",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"m21 21-4.34-4.34\" /> <circle cx=\"11\" cy=\"11\" r=\"8\" />"
  },
  {
    "id": "refresh-cw",
    "label": "Refresh Cw",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8\" /> <path d=\"M21 3v5h-5\" /> <path d=\"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16\" /> <path d=\"M8 16H3v5\" />"
  },
  {
    "id": "layout-grid",
    "label": "Layout Grid",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<rect width=\"7\" height=\"7\" x=\"3\" y=\"3\" rx=\"1\" /> <rect width=\"7\" height=\"7\" x=\"14\" y=\"3\" rx=\"1\" /> <rect width=\"7\" height=\"7\" x=\"14\" y=\"14\" rx=\"1\" /> <rect width=\"7\" height=\"7\" x=\"3\" y=\"14\" rx=\"1\" />"
  },
  {
    "id": "move",
    "label": "Move",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M12 2v20\" /> <path d=\"m15 19-3 3-3-3\" /> <path d=\"m19 9 3 3-3 3\" /> <path d=\"M2 12h20\" /> <path d=\"m5 9-3 3 3 3\" /> <path d=\"m9 5 3-3 3 3\" />"
  },
  {
    "id": "maximize",
    "label": "Maximize",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M8 3H5a2 2 0 0 0-2 2v3\" /> <path d=\"M21 8V5a2 2 0 0 0-2-2h-3\" /> <path d=\"M3 16v3a2 2 0 0 0 2 2h3\" /> <path d=\"M16 21h3a2 2 0 0 0 2-2v-3\" />"
  },
  {
    "id": "minimize",
    "label": "Minimize",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M8 3v3a2 2 0 0 1-2 2H3\" /> <path d=\"M21 8h-3a2 2 0 0 1-2-2V3\" /> <path d=\"M3 16h3a2 2 0 0 1 2 2v3\" /> <path d=\"M16 21v-3a2 2 0 0 1 2-2h3\" />"
  },
  {
    "id": "list",
    "label": "List",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M3 5h.01\" /> <path d=\"M3 12h.01\" /> <path d=\"M3 19h.01\" /> <path d=\"M8 5h13\" /> <path d=\"M8 12h13\" /> <path d=\"M8 19h13\" />"
  },
  {
    "id": "circle-dot",
    "label": "Circle Dot",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"1\" /> <circle cx=\"12\" cy=\"12\" r=\"10\" />"
  },
  {
    "id": "circle",
    "label": "Circle",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<circle cx=\"12\" cy=\"12\" r=\"10\" />"
  },
  {
    "id": "square",
    "label": "Square",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<rect width=\"18\" height=\"18\" x=\"3\" y=\"3\" rx=\"2\" />"
  },
  {
    "id": "triangle",
    "label": "Triangle",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M13.73 4a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z\" />"
  },
  {
    "id": "panel-top",
    "label": "Panel Top",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<rect width=\"18\" height=\"18\" x=\"3\" y=\"3\" rx=\"2\" /> <path d=\"M3 9h18\" />"
  },
  {
    "id": "panels-top-left",
    "label": "Panels Top Left",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<rect width=\"18\" height=\"18\" x=\"3\" y=\"3\" rx=\"2\" /> <path d=\"M3 9h18\" /> <path d=\"M9 21V9\" />"
  },
  {
    "id": "settings-2",
    "label": "Settings 2",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M14 17H5\" /> <path d=\"M19 7h-9\" /> <circle cx=\"17\" cy=\"17\" r=\"3\" /> <circle cx=\"7\" cy=\"7\" r=\"3\" />"
  },
  {
    "id": "mouse",
    "label": "Mouse",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<rect x=\"5\" y=\"2\" width=\"14\" height=\"20\" rx=\"7\" /> <path d=\"M12 6v4\" />"
  },
  {
    "id": "keyboard",
    "label": "Keyboard",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<path d=\"M10 8h.01\" /> <path d=\"M12 12h.01\" /> <path d=\"M14 8h.01\" /> <path d=\"M16 12h.01\" /> <path d=\"M18 8h.01\" /> <path d=\"M6 8h.01\" /> <path d=\"M7 16h10\" /> <path d=\"M8 12h.01\" /> <rect width=\"20\" height=\"16\" x=\"2\" y=\"4\" rx=\"2\" />"
  },
  {
    "id": "gamepad-2",
    "label": "Gamepad 2",
    "cat": "UI",
    "viewBox": "0 0 24 24",
    "inner": "<line x1=\"6\" x2=\"10\" y1=\"11\" y2=\"11\" /> <line x1=\"8\" x2=\"8\" y1=\"9\" y2=\"13\" /> <line x1=\"15\" x2=\"15.01\" y1=\"12\" y2=\"12\" /> <line x1=\"18\" x2=\"18.01\" y1=\"10\" y2=\"10\" /> <path d=\"M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0 0 17.32 5z\" />"
  }
];
  const byId = {};
  icons.forEach(i => { byId[i.id] = i; });
  return { icons, byId };
})();
