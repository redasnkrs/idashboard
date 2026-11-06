"""Construit l'application Windows portable (exe + helper update)."""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def run(*args):
    print("+", " ".join(args), flush=True)
    subprocess.check_call(args, cwd=str(ROOT))


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    DIST.mkdir(exist_ok=True)
    shutil.rmtree(DIST / "idash", ignore_errors=True)
    suffix = ".exe" if sys.platform == "win32" else ""
    run(sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
        str(ROOT / "tools" / "idash_update.spec"))
    helper = DIST / ("idash-update" + suffix)
    if not helper.is_file():
        raise SystemExit("idash-update non construit")
    run(sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
        str(ROOT / "tools" / "idash.spec"))
    base = DIST / "idash"
    exe = base / ("idash.exe" if sys.platform == "win32" else "idash")
    if not exe.is_file():
        raise SystemExit("idash non construit")
    bundled = base / "_internal" / "tools" / ("idash-update" + suffix)
    if not bundled.is_file():
        bundled.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(helper, bundled)
    label = "win64" if sys.platform == "win32" else sys.platform
    target = DIST / ("idash-v%s-%s.zip" % (version, label))
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            archive.write(path, path.relative_to(base).as_posix())
            count += 1
    print("%s (%d fichiers, %.1f Mo)" %
          (target, count, target.stat().st_size / (1024 * 1024)))


if __name__ == "__main__":
    main()
