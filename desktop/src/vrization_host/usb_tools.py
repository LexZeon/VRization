"""Offline import of a user-downloaded official Windows Platform Tools package.

No network requests, SDK license acceptance or executable invocation happen here.
The complete upstream package, including NOTICE.txt, remains unmodified. Bounds
and path validation apply even after the pinned SHA-256 check, before any write.
"""

from contextlib import suppress
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import zipfile


PLATFORM_TOOLS_VERSION = "37.0.1"
PLATFORM_TOOLS_SHA256 = "45f4d63113e895ebde0c90f194099a4676b6ac653bd28d54314a9e022bbc1a99"
OFFICIAL_DOWNLOAD_PAGE = "https://developer.android.com/tools/releases/platform-tools"
MAX_ZIP_BYTES = 32 * 1024 * 1024
MAX_FILES = 128
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
CHUNK = 128 * 1024
REQUIRED_FILES = {"adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "source.properties", "NOTICE.txt"}


class UsbToolsError(ValueError):
    """A stable, translatable error code; never includes untrusted ZIP text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def default_tools_directory() -> Path:
    """Keep tools beside a portable app or at the recognized release archive root."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parents[3] / "tools" / "android-sdk"
    program = Path(sys.executable).resolve().parent
    root = program
    if program.name.casefold() == "windows":
        container = program.parent
        root = container
        if container.name.casefold() == "latest" or re.fullmatch(
                r"previous-latest-\d{8}-\d{6}-[a-f0-9]{6}", container.name):
            root = container.parent
        elif container.parent.name.casefold() == "versions" and re.fullmatch(
                r"v\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", container.name):
            root = container.parent.parent
    return root / "tools" / "android-sdk"


def _safe_destination(value) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() or path == Path(path.anchor) or ".." in path.parts:
        raise UsbToolsError("unsafe_destination")
    # resolve() alone would silently follow a junction or symlink. Refuse both.
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode) or
                getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise UsbToolsError("unsafe_destination")
        if not stat.S_ISDIR(info.st_mode):
            raise UsbToolsError("unsafe_destination")
    return path


def _entries(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, PurePosixPath]]:
    entries = archive.infolist()
    if not entries or len(entries) > MAX_FILES:
        raise UsbToolsError("invalid_archive")
    result, seen, total = [], set(), 0
    for entry in entries:
        # ZipInfo normalizes backslashes and truncates NUL on some platforms;
        # validate the original spelling instead of trusting that normalization.
        name = entry.orig_filename
        parts = name.removesuffix("/").split("/")
        if (not name or len(name) > 512 or len(parts) > 16 or
                "\\" in name or "\x00" in name or ":" in name or
                any(part in ("", ".", "..") or part.endswith((".", " ")) or
                    re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
                    for part in parts) or parts[0] != "platform-tools"):
            raise UsbToolsError("invalid_archive")
        relative = PurePosixPath(*parts)
        folded = str(relative).casefold()
        mode = entry.external_attr >> 16
        if (folded in seen or entry.flag_bits & 1 or
                (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)) or
                (entry.is_dir() and entry.file_size != 0) or
                entry.file_size < 0 or entry.file_size > MAX_FILE_BYTES):
            raise UsbToolsError("invalid_archive")
        seen.add(folded)
        total += entry.file_size
        if total > MAX_TOTAL_BYTES:
            raise UsbToolsError("invalid_archive")
        result.append((entry, relative))
    files = {str(path.relative_to("platform-tools")) for entry, path in result if not entry.is_dir()}
    if not REQUIRED_FILES.issubset(files):
        raise UsbToolsError("invalid_archive")
    if archive.getinfo("platform-tools/source.properties").file_size > 4096:
        raise UsbToolsError("invalid_archive")
    properties = archive.read("platform-tools/source.properties")
    try:
        revision = re.findall(r"^Pkg\.Revision\s*=\s*(\S+)\s*$", properties.decode("ascii"), re.M)
    except UnicodeError as exc:
        raise UsbToolsError("invalid_archive") from exc
    if revision != [PLATFORM_TOOLS_VERSION]:
        raise UsbToolsError("wrong_version")
    if archive.getinfo("platform-tools/NOTICE.txt").file_size == 0:
        raise UsbToolsError("invalid_archive")
    return result


def _copy_member(archive, entry, output):
    remaining = entry.file_size
    with archive.open(entry) as source:
        while remaining:
            data = source.read(min(CHUNK, remaining))
            if not data:
                raise UsbToolsError("invalid_archive")
            output.write(data)
            remaining -= len(data)
        if source.read(1):
            raise UsbToolsError("invalid_archive")


def _identical(archive, entries, destination: Path) -> bool:
    if not destination.is_dir() or destination.is_symlink():
        return False
    info = destination.lstat()
    if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    expected = {str(path.relative_to("platform-tools")) for entry, path in entries if not entry.is_dir()}
    actual, visited = set(), 0
    for root, directories, files in os.walk(destination, followlinks=False):
        visited += len(directories) + len(files)
        if visited > MAX_FILES:
            return False
        for name in (*directories, *files):
            path = Path(root) / name
            info = path.lstat()
            if (stat.S_ISLNK(info.st_mode) or
                    getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                return False
        actual.update(str((Path(root) / name).relative_to(destination).as_posix()) for name in files)
        if len(actual) > MAX_FILES:
            return False
    if actual != expected:
        return False
    for entry, relative in entries:
        if entry.is_dir():
            continue
        target = destination.joinpath(*relative.parts[1:])
        if target.stat().st_size != entry.file_size:
            return False
        with archive.open(entry) as source, target.open("rb") as existing:
            remaining = entry.file_size
            while remaining:
                count = min(CHUNK, remaining)
                if source.read(count) != existing.read(count):
                    return False
                remaining -= count
            if source.read(1) or existing.read(1):
                return False
    return True


def import_platform_tools(zip_path, sdk_directory) -> Path:
    """Verify and import once; reuse only an identical complete existing package.

    Caller selects the ZIP after independently accepting Google's terms. All
    extraction uses an exclusively created staging directory; existing installs
    are never repaired, overwritten or deleted. This function never runs adb.
    """
    destination = _safe_destination(sdk_directory)
    stage = None
    lock_path = destination / ".vrization-platform-tools-import.lock"
    locked = False
    try:
        with Path(zip_path).open("rb") as package:
            length = os.fstat(package.fileno()).st_size
            if not 0 < length <= MAX_ZIP_BYTES:
                raise UsbToolsError("invalid_archive")
            digest = hashlib.sha256()
            hashed = 0
            while data := package.read(CHUNK):
                hashed += len(data)
                if hashed > MAX_ZIP_BYTES:
                    raise UsbToolsError("invalid_archive")
                digest.update(data)
            if digest.hexdigest() != PLATFORM_TOOLS_SHA256:
                raise UsbToolsError("wrong_hash")
            package.seek(0)
            with zipfile.ZipFile(package) as archive:
                entries = _entries(archive)
                destination.mkdir(parents=True, exist_ok=True)
                _safe_destination(destination)
                try:
                    with lock_path.open("xb"):
                        pass
                    locked = True
                except FileExistsError as exc:
                    raise UsbToolsError("busy") from exc
                target = destination / "platform-tools"
                if target.exists() or target.is_symlink():
                    if not _identical(archive, entries, target):
                        raise UsbToolsError("destination_conflict")
                    return target / "adb.exe"
                stage = Path(tempfile.mkdtemp(prefix=".vrization-platform-tools-", dir=destination))
                for entry, relative in entries:
                    output_path = stage.joinpath(*relative.parts)
                    if entry.is_dir():
                        output_path.mkdir(parents=True, exist_ok=True)
                    else:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with output_path.open("xb") as output:
                            _copy_member(archive, entry, output)
                _safe_destination(destination)
                if target.exists() or target.is_symlink():
                    raise UsbToolsError("destination_conflict")
                # Windows rename refuses an existing destination, including an
                # empty directory. The sibling stage keeps the move on one disk.
                (stage / "platform-tools").rename(target)
                return target / "adb.exe"
    except UsbToolsError:
        raise
    except (zipfile.BadZipFile, UnicodeError, EOFError, RuntimeError) as exc:
        raise UsbToolsError("invalid_archive") from exc
    except OSError as exc:
        raise UsbToolsError("write_failed") from exc
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        if locked:
            with suppress(OSError):
                lock_path.unlink()
