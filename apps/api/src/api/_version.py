from pathlib import Path


def get_version() -> str:
    version_file = Path(__file__).parents[4] / "VERSION"
    try:
        return version_file.read_text().strip()
    except FileNotFoundError:
        return "0.0.0"
