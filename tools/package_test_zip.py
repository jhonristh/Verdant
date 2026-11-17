"""Package only distributable files; never include the smoke-test database."""
import hashlib
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def package(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = [path for path in source.rglob("*") if path.is_file()
             and "data" not in path.relative_to(source).parts]
    with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, f"{source.name}/{path.relative_to(source).as_posix()}")
    with ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Corrupt ZIP member: {bad}")
        if len(archive.namelist()) != len(files):
            raise ValueError("ZIP member count differs from source file count.")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return len(files), destination.stat().st_size, digest


if __name__ == "__main__":
    count, size, digest = package(sys.argv[1], sys.argv[2])
    print(f"{count} files; {size / 1024 / 1024:.2f} MiB; SHA-256 {digest}")
