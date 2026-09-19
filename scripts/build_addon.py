"""Build an installable add-on ZIP from an explicit source allowlist."""

from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist"
PACKAGE = "exr2nuke"
VERSION = "1.1.1"


def build():
    OUTPUT.mkdir(exist_ok=True)
    target = OUTPUT / f"Exr2Nuke-{VERSION}.zip"
    files = [ROOT / "__init__.py", ROOT / "README.md"]
    if (ROOT / "LICENSE").exists():
        files.append(ROOT / "LICENSE")
    for directory, suffix in [("modules", ".py"), ("libraries", ".json")]:
        files.extend(
            sorted(path for path in (ROOT / directory).glob("*" + suffix) if path.is_file())
        )
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            name = PACKAGE + "/" + path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert PACKAGE + "/__init__.py" in archive.namelist()
        assert not any("__pycache__" in name or ".git/" in name for name in archive.namelist())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (OUTPUT / "SHA256SUMS.txt").write_text(f"{digest}  {target.name}\n", encoding="ascii")
    print(target.name, digest)
    return target


if __name__ == "__main__":
    build()
