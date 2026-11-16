"""Package a clean, current onedir build for the setup executable."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dist" / "Verdant_Disclosure_Scorer"
OUTPUT = ROOT / "build" / "installer_payload.zip"


def main():
    executable = SOURCE / "Verdant_Disclosure_Scorer.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    files = [path for path in SOURCE.rglob("*") if path.is_file()
             and "data" not in path.relative_to(SOURCE).parts]
    if not any(path.name == "scoring_rubric.json" for path in files):
        raise RuntimeError("Rubric missing from the onedir build")
    if not any(path.name == "eng.traineddata" for path in files):
        raise RuntimeError("English OCR data missing from the onedir build")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(SOURCE).as_posix())
    with ZipFile(OUTPUT) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Installer payload CRC verification failed")
    print(f"Installer payload: {len(files)} files, {OUTPUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
