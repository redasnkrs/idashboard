"""Extrait la section de CHANGELOG.md correspondant à VERSION."""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"


def extract(text, version):
    pattern = re.compile(
        r"^##\s+\[?v?%s\]?(?:\s+-\s+.*)?\s*$" % re.escape(version),
        re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    rest = text[match.end():]
    next_heading = re.search(r"^##\s+", rest, re.MULTILINE)
    if next_heading:
        rest = rest[:next_heading.start()]
    return rest.strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(CHANGELOG))
    ap.add_argument("--version", default="")
    ap.add_argument("--output", default="")
    args = ap.parse_args(argv)
    version = args.version.strip() or \
        (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    try:
        text = Path(args.file).read_text(encoding="utf-8")
    except OSError as exc:
        sys.exit("CHANGELOG.md illisible: %s" % exc)
    notes = extract(text, version)
    if not notes:
        sys.exit("Aucune entree de changelog pour la version %s" % version)
    body = "## idash v%s\n\n%s\n" % (version, notes)
    if args.output:
        Path(args.output).write_text(body, encoding="utf-8")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
