"""Check bilingual page structure and local links, not translation quality."""
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ENGLISH = "<!-- vrization:english -->"
CHINESE = "<!-- vrization:chinese -->"
# Add an exact path here only for a documented, verbatim upstream source.
# Never exempt project-written guides or attribution indexes.
VERBATIM_PAGES = frozenset()


def owned_pages():
    # Git includes new, unignored pages in any directory; build outputs stay out.
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
    ).decode("utf-8").split("\0")
    pages = set()
    for name in names:
        path = ROOT / name
        if not name or not path.is_file() or path.suffix.lower() != ".md":
            continue
        # Original upstream licenses stay verbatim; our license README indexes
        # are still bilingual public documentation and remain checked.
        if name.startswith("licenses/") and path.name.lower() != "readme.md":
            continue
        if name in VERBATIM_PAGES:
            continue
        pages.add(path)
    pages.add(ROOT / "NOTICE")
    return sorted(pages)


def check_page(path):
    errors = []
    text = path.read_text(encoding="utf-8")
    english_markers = list(re.finditer(r"(?m)^" + re.escape(ENGLISH) + r"$", text))
    chinese_markers = list(re.finditer(r"(?m)^" + re.escape(CHINESE) + r"$", text))
    if len(english_markers) != 1 or len(chinese_markers) != 1:
        errors.append("requires exactly one English marker and one Chinese marker")
    elif english_markers[0].start() >= chinese_markers[0].start():
        errors.append("English must precede Chinese")
    else:
        english = text[english_markers[0].end():chinese_markers[0].start()]
        chinese = text[chinese_markers[0].end():]
        for label, body, heading in (("English", english, "## English"),
                                     ("Chinese", chinese, "## 简体中文")):
            if heading not in body or len(body.strip()) < 100:
                errors.append(f"{label} section requires its heading and substantive content")

    # Ignore examples inside fences; verify relative files, not remote services/anchors.
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", prose):
        target = match.group(1).strip().split(' "', 1)[0].strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        destination = (path.parent / unquote(parsed.path)).resolve()
        if not destination.exists():
            errors.append(f"broken relative link: {target}")
    return errors


def main():
    pages = owned_pages()
    failures = [(path, error) for path in pages for error in check_page(path)]
    for path, error in failures:
        print(f"{path.relative_to(ROOT).as_posix()}: {error}")
    if failures:
        print(f"Documentation check failed: {len(failures)} problem(s).")
        return 1
    print(f"Checked {len(pages)} pages: English first, Chinese below, local links present.")
    print("This checks structure and nonempty sections; translation quality needs human review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
