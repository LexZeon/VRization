"""Keep release-page documentation links attached to the published version."""
import argparse
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

def prepare(tag):
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", tag):
        raise ValueError("Expected a release version tag")
    page = ROOT / "docs/RELEASE_NOTES.md"
    prose = page.read_text(encoding="utf-8")
    english, chinese = "<!-- vrization:english -->", "<!-- vrization:chinese -->"
    if english not in prose or chinese not in prose or prose.index(english) > prose.index(chinese):
        raise ValueError("Release notes must contain English first and Chinese below")
    def resolve(match):
        image, label, target = match.groups()
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)
        destination = (page.parent / parsed.path).resolve()
        if not destination.is_relative_to(ROOT) or not destination.exists():
            raise ValueError("Missing or external release documentation target")
        route = "raw" if image else "blob"
        url = (f"https://github.com/LexZeon/VRization/{route}/{tag}/"
               + quote(destination.relative_to(ROOT).as_posix(), safe="/"))
        if parsed.fragment:
            url += "#" + parsed.fragment
        return f"{image}[{label}]({url})"
    return re.sub(r"(!?)\[([^\]]*)\]\(([^)]+)\)", resolve, prose)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(prepare(args.tag), encoding="utf-8")
