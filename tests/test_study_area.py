from pathlib import Path

import pytest

from ouem.study_area import StudyAreaConfigError, load_study_area


ROOT = Path(__file__).parents[1]


def test_load_komae_canonical_study_area():
    area = load_study_area(ROOT / "config/study_areas/komae_09LD3451.yaml")

    assert area.id == "komae_09LD3451"
    assert area.epsg == 6677
    assert area.extent == (-23600.0, -40800.0, -23200.0, -40500.0)


def test_rejects_inverted_extent(tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text(
        "study_area:\n  id: bad\ncrs:\n  epsg: 6677\nextent:\n"
        "  xmin: 2\n  ymin: 0\n  xmax: 1\n  ymax: 1\n",
        encoding="utf-8",
    )

    with pytest.raises(StudyAreaConfigError, match="invalid extent"):
        load_study_area(config)
