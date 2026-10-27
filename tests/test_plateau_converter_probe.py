"""Recorder and fixture checks only; these do not run PLATEAU GIS Converter."""

import hashlib
import json
from pathlib import Path
import sys

import pytest

from ouem import plateau_converter_probe as probe

FIXTURES = Path(__file__).parent / "fixtures/plateau_converter"


def altered(tmp_path, mutate):
    source = FIXTURES / "two_buildings.gml"
    data = mutate(source.read_bytes())
    fixture = tmp_path / "test.gml"
    fixture.write_bytes(data)
    expected = json.loads((FIXTURES / "expected.json").read_text())
    expected["fixture_sha256"] = hashlib.sha256(data).hexdigest()
    expectation = tmp_path / "expected.json"
    expectation.write_text(json.dumps(expected))
    return fixture, expectation


def test_authored_fixture_contains_distinct_lods_surfaces_and_courtyards():
    result = probe.inspect_fixture(FIXTURES / "two_buildings.gml", FIXTURES / "expected.json")
    assert result["status"] == "PASS"
    assert [item["id"] for item in result["buildings"]] == ["synthetic_tokyo", "synthetic_niigata"]
    assert result["full_xsd_validation"] == "NOT RUN"


def test_fixture_mutation_is_not_hidden_by_expected_values(tmp_path):
    bad = tmp_path / "bad.gml"
    bad.write_bytes(b"modified")
    with pytest.raises(ValueError, match="hash mismatch"):
        probe.inspect_fixture(bad, FIXTURES / "expected.json")


@pytest.mark.parametrize("replacement,message", [
    (b"NaN", "nonfinite"), (b"invalid", "could not convert"),
])
def test_bad_coordinate_rejected_even_with_matching_input_hash(tmp_path, replacement, message):
    fixture, expected = altered(tmp_path, lambda data: data.replace(b"10.25", replacement, 1))
    with pytest.raises(ValueError, match=message):
        probe.inspect_fixture(fixture, expected)


def test_duplicate_identity_rejected_even_with_matching_hash(tmp_path):
    fixture, expected = altered(tmp_path, lambda data: data.replace(b'gml:id="synthetic_niigata"',
                                                                   b'gml:id="synthetic_tokyo"'))
    with pytest.raises(ValueError, match="duplicate"):
        probe.inspect_fixture(fixture, expected)


def test_recorder_retains_nonzero_exit_and_raw_output(tmp_path):
    receipt = probe.record_command([sys.executable, "-c",
                                   "import sys;print('fixture');print('failure',file=sys.stderr);sys.exit(7)"],
                                  tmp_path, "child")
    assert receipt["exit_code"] == 7
    assert b"fixture" in (tmp_path / "child.stdout.log").read_bytes()
    assert b"failure" in (tmp_path / "child.stderr.log").read_bytes()
    assert receipt["stdout_sha256"] == probe.sha256(tmp_path / "child.stdout.log")


def test_missing_executable_is_not_recorded_as_success(tmp_path):
    receipt = probe.record_command([str(tmp_path / "missing.exe")], tmp_path, "missing")
    assert receipt["exit_code"] is None and receipt["error"]


def test_invalid_log_name_does_not_launch_child(tmp_path):
    marker = tmp_path / "marker"
    with pytest.raises(ValueError, match="unsafe log label"):
        probe.record_command([sys.executable, "-c", f"open({str(marker)!r},'w').close()"], tmp_path, "../outside")
    assert not marker.exists()


def test_prepare_rejects_existing_or_outside_run_without_modifying_it(tmp_path):
    outside = tmp_path / "outside"
    with pytest.raises(ValueError, match="new child"):
        probe.prepare(tmp_path, outside)
    assert not outside.exists()
    existing = tmp_path / "data/work/plateau-converter-cli/existing"
    existing.mkdir(parents=True)
    marker = existing / "keep"
    marker.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        probe.prepare(tmp_path, existing)
    assert marker.read_bytes() == b"keep"
