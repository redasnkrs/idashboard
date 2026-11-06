"""Construit le ZIP d'une release idash (sans donnees utilisateur)."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FILES = ["main.py", "acevo_bridge.py", "lancer.bat", "README.md",
         "Mini Deck App Roadmap.md", "VERSION", "requirements.txt",
         "requirements-windows.txt", "requirements-build.txt"]
DIRS = ["core", "adapters", "assets", "dashboards", "home", "settings",
        "studio", "tools", "update"]
SKIP = {"__pycache__", ".DS_Store", "screenshots"}


def iter_dir(base):
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP for part in path.parts):
            continue
        if path.suffix in (".pyc", ".pyo"):
            continue
        yield path


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    DIST.mkdir(exist_ok=True)
    target = DIST / ("idash-v%s.zip" % version)
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            path = ROOT / name
            if path.is_file():
                archive.write(path, name)
                count += 1
        for name in DIRS:
            base = ROOT / name
            if not base.is_dir():
                continue
            for path in iter_dir(base):
                arc = path.relative_to(ROOT).as_posix()
                archive.write(path, arc)
                count += 1
        themes = ROOT / "themes"
        if themes.is_dir():
            for path in sorted(themes.glob("*.json")):
                if path.name == "active.json":
                    continue
                archive.write(path, "themes/" + path.name)
                count += 1
    print("%s (%d fichiers, %.1f Ko)" %
          (target, count, target.stat().st_size / 1024))


if __name__ == "__main__":
    main()
