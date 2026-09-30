from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
WORK_SCRIPTS = REPOSITORY_ROOT / "scripts" / "work"


def test_plateau_launcher_keeps_osgeo_and_ouem_python_separate() -> None:
    launcher = (WORK_SCRIPTS / "plateau_komae_local_acceptance.cmd").read_text()

    assert 'cmd /d /c ""%~dp0check_osgeo4w_environment.cmd""' in launcher
    assert 'set "VENV_PYTHON=%REPO_ROOT%\\.venv\\Scripts\\python.exe"' in launcher
    assert '"%VENV_PYTHON%" -m ouem.native.building.plateau %*' in launcher
    assert "call \"%OSGEO_ENV%\"" not in launcher


def test_osgeo_check_retains_required_capability_checks() -> None:
    check = (WORK_SCRIPTS / "check_osgeo4w_environment.cmd").read_text()

    assert "where ogr2ogr" in check
    assert "gdalinfo --version" in check
    assert "from osgeo import ogr, osr" in check
    assert "QGIS 4" not in check
