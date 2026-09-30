"""Loading and validation of OUEM study-area definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class StudyAreaConfigError(ValueError):
    """Raised when a study-area file does not satisfy the OUEM schema."""


@dataclass(frozen=True)
class StudyArea:
    id: str
    name: str
    epsg: int
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    @property
    def extent(self) -> tuple[float, float, float, float]:
        return (self.xmin, self.ymin, self.xmax, self.ymax)


def _simple_yaml(path: Path) -> dict[str, dict[str, str]]:
    """Parse the deliberately small, two-level study-area YAML schema.

    Keeping this parser local avoids making a YAML package a prerequisite for
    the command. It rejects rather than guesses at unsupported YAML constructs.
    """
    sections: dict[str, dict[str, str]] = {}
    section: str | None = None
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")) and line.endswith(":"):
            section = line[:-1].strip()
            sections[section] = {}
            continue
        if section is None or ":" not in line or not line.startswith("  "):
            raise StudyAreaConfigError(f"unsupported YAML at {path}:{number}")
        key, value = line.strip().split(":", 1)
        sections[section][key.strip()] = value.strip().strip("'\"")
    return sections


def load_study_area(path: str | Path) -> StudyArea:
    """Load the canonical ID, CRS, and extent from a study-area YAML file."""
    source = Path(path)
    try:
        data = _simple_yaml(source)
        area = data["study_area"]
        crs = data["crs"]
        extent = data["extent"]
        result = StudyArea(
            id=area["id"],
            name=area.get("name", area["id"]),
            epsg=int(crs["epsg"]),
            xmin=float(extent["xmin"]),
            ymin=float(extent["ymin"]),
            xmax=float(extent["xmax"]),
            ymax=float(extent["ymax"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise StudyAreaConfigError(f"invalid study-area config {source}: {exc}") from exc
    if result.xmin >= result.xmax or result.ymin >= result.ymax:
        raise StudyAreaConfigError(f"invalid extent in {source}")
    return result
