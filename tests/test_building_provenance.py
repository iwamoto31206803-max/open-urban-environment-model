"""Pure Python declaration/byte tests; placeholder files are NOT valid GIS data."""

import copy
import hashlib
import json

import pytest

from ouem.native.building import provenance as p


@pytest.fixture
def record(tmp_path):
    artifacts = {}
    for identifier, role, name in (
        ("raw", "raw_citygml", "raw.gml"),
        ("converter", "converter_gpkg", "converter.gpkg"),
        ("native", "native_gpkg", "native.gpkg"),
        ("cli", "converter_cli", "nusamai.exe"),
        ("evidence", "source_evidence", "source.txt"),
    ):
        data = f"deliberately non-GIS synthetic bytes: {identifier}".encode()
        (tmp_path / name).write_bytes(data)
        artifacts[identifier] = {"role": role, "path": name, "size_bytes": len(data),
                                 "sha256": hashlib.sha256(data).hexdigest()}
        if role.endswith("gpkg"):
            artifacts[identifier]["layer"] = "building"
    return {
        "schema": p.NATIVE_SCHEMA, "profile": p.SOURCE_H_PROFILE, "artifacts": artifacts,
        "source_declaration": {"srs_name": "http://www.opengis.net/def/crs/EPSG/0/6697",
            "horizontal_epsg": 6668, "vertical_epsg": 6695, "quantity": "gravity_related_height",
            "unit": "metre", "axes": ["latitude", "longitude", "H"], "evidence_artifact_id": "evidence"},
        "coordinate_contract": {"input_epsg": 6697, "horizontal_epsg": 6668, "vertical_epsg": 6695,
            "quantity": "gravity_related_height", "unit": "metre", "storage_axes": ["longitude", "latitude", "H"]},
        "geometry_selection": {"requested_lod": 2, "split_components": False},
        "converter": {"schema": p.CONVERTER_SCHEMA, "repository": p.REPOSITORY,
            "commit": "ce7766df9788ce391b149c55df16d33082d0bc72", "version": "0.1.19",
            "cli_artifact_id": "cli", "input_artifact_ids": ["raw"], "output_artifact_id": "converter",
            "argv": ["nusamai.exe", "raw.gml", "--sink", "gpkg", "--output", "converter.gpkg",
                     "--epsg", "6697", "-t", "use_lod=lod2"],
            "resolved_options": {"sink": "gpkg", "epsg": 6697, "use_lod": "lod2", "split_components": False},
            "exit_code": 0, "execution_status": "COMPLETED"},
        "native": {"input_artifact_id": "converter", "output_artifact_id": "native"},
        "operations": [
            {"input_artifact_ids": ["raw"], "output_artifact_id": "converter",
             "horizontal_operation": "latitude_longitude_to_gis_longitude_latitude",
             "vertical_operation": "identity_H", "offset_m": 0, "geoid_model": None},
            {"input_artifact_ids": ["converter"], "output_artifact_id": "native",
             "horizontal_operation": "identity_XY", "vertical_operation": "identity_H",
             "offset_m": 0.0, "geoid_model": None},
        ],
    }


def validate(record, root):
    return p.validate_source_h_record(record, artifact_root=root)


def codes(report):
    return {issue.code for issue in report.issues}


def set_at(record, dotted, value):
    parts = dotted.split(".")
    for part in parts[:-1]:
        record = record[int(part)] if isinstance(record, list) else record[part]
    if isinstance(record, list):
        record[int(parts[-1])] = value
    else:
        record[parts[-1]] = value


def test_exact_profile_and_schema_are_different(record, tmp_path):
    assert p.identify_profile(p.SOURCE_H_PROFILE) == p.SOURCE_H_PROFILE
    assert p.NATIVE_SCHEMA != p.SOURCE_H_PROFILE
    before = copy.deepcopy(record)
    report = validate(record, tmp_path)
    assert report.foundation_valid and report.format_status == report.file_hash_status == "PASS"
    assert set(report.checked_artifact_ids) == set(record["artifacts"])
    assert record == before
    assert json.loads(json.dumps(report.to_dict()))["foundation_valid"] is True


def test_placeholder_bytes_do_not_prove_semantics_or_eligibility(record, tmp_path):
    record["validation"] = {"checks": [{"result": "PASS"}]}
    record["eligibility_review"] = {"reviewer": "claimed reviewer", "decision": "ELIGIBLE"}
    record["acceptance"] = {"status": "ACCEPTED"}
    report = validate(record, tmp_path)
    assert report.foundation_valid
    assert report.coordinate_geometry_status == "NOT_RUN"
    assert report.converter_qualification_status == "NOT_VERIFIED"
    assert report.human_review_status == report.formal_acceptance_status == "NOT_VERIFIED"
    assert report.eligibility == "NOT_ESTABLISHED"


def test_epsg_only_does_not_select_profile(record, tmp_path):
    del record["profile"]
    assert "PROFILE_UNSUPPORTED" in codes(validate(record, tmp_path))


@pytest.mark.parametrize("profile", [None, "", p.SOURCE_H_PROFILE.replace("v0.1", "v0.2"),
                                     "EPSG:6697", {}, p.NATIVE_SCHEMA])
def test_unknown_profiles_rejected(record, tmp_path, profile):
    record["profile"] = profile
    assert "PROFILE_UNSUPPORTED" in codes(validate(record, tmp_path))


def test_legacy_never_automatically_selected_or_registered(record, tmp_path):
    record["profile"] = p.LEGACY_PROFILE
    record["coordinate_contract"]["input_epsg"] = 4979
    record["extensions"] = {"legacy_registration": {"approved": True}}
    assert "LEGACY_NOT_REGISTERED" in codes(validate(record, tmp_path))
    with pytest.raises(p.ProfileValidationError) as exc:
        p.identify_profile(p.LEGACY_PROFILE)
    assert exc.value.issue.code == "LEGACY_NOT_REGISTERED"


@pytest.mark.parametrize("field,value,code", [
    ("schema", p.SOURCE_H_PROFILE, "SCHEMA_UNSUPPORTED"),
    ("converter.schema", "ouem-building-converter-run/v0.2", "SCHEMA_UNSUPPORTED"),
    ("coordinate_contract.input_epsg", 4979, "VERTICAL_SEMANTICS_CONFLICT"),
    ("coordinate_contract.horizontal_epsg", 4326, "VERTICAL_SEMANTICS_CONFLICT"),
    ("source_declaration.vertical_epsg", 0, "VERTICAL_SEMANTICS_CONFLICT"),
    ("source_declaration.quantity", "ellipsoidal_height", "VERTICAL_SEMANTICS_CONFLICT"),
    ("source_declaration.unit", "foot", "VERTICAL_SEMANTICS_CONFLICT"),
    ("coordinate_contract.storage_axes", ["latitude", "longitude", "H"], "AXIS_MISMATCH"),
    ("source_declaration.axes", ["longitude", "latitude", "H"], "AXIS_MISMATCH"),
    ("operations.0.vertical_operation", "H_to_h", "VERTICAL_SEMANTICS_CONFLICT"),
    ("operations.1.offset_m", 37, "VERTICAL_SEMANTICS_CONFLICT"),
    ("operations.1.offset_m", float("nan"), "VERTICAL_SEMANTICS_CONFLICT"),
    ("operations.1.geoid_model", "GSIGEO2011", "VERTICAL_SEMANTICS_CONFLICT"),
    ("converter.resolved_options.epsg", 4979, "VERTICAL_SEMANTICS_CONFLICT"),
    ("geometry_selection.requested_lod", True, "PROVENANCE_INVALID"),
    ("geometry_selection.split_components", 0, "PROVENANCE_INVALID"),
    ("converter.exit_code", False, "PROVENANCE_INVALID"),
    ("converter.commit", "main", "PROVENANCE_INVALID"),
    ("converter.execution_status", "FAILED", "PROVENANCE_INVALID"),
    ("artifacts.raw.size_bytes", True, "PROVENANCE_INVALID"),
    ("artifacts.cli.sha256", "a"*63, "PROVENANCE_INVALID"),
    ("native.input_artifact_id", "raw", "PROVENANCE_INVALID"),
    ("native.input_artifact_id", [], "PROVENANCE_INVALID"),
    ("converter.input_artifact_ids", ["raw", "raw"], "PROVENANCE_INVALID"),
    ("converter.input_artifact_ids", [[]], "PROVENANCE_INVALID"),
    ("operations.1.input_artifact_ids", ["native"], "PROVENANCE_INVALID"),
])
def test_conflicting_declarations(record, tmp_path, field, value, code):
    set_at(record, field, value)
    report = validate(record, tmp_path)
    assert code in codes(report)
    assert report.format_status == "FAIL" and report.file_hash_status == "NOT_RUN"
    assert not report.foundation_valid


@pytest.mark.parametrize("field", ["artifacts", "source_declaration", "operations", "converter", "native"])
def test_missing_provenance(record, tmp_path, field):
    del record[field]
    report = validate(record, tmp_path)
    assert "PROVENANCE_MISSING" in codes(report)


def test_missing_nested_reference(record, tmp_path):
    del record["artifacts"]["native"]
    report = validate(record, tmp_path)
    assert "PROVENANCE_MISSING" in codes(report)


@pytest.mark.parametrize("change", ["same_size", "size", "declared_hash"])
def test_real_hash_mismatch_is_traceable(record, tmp_path, change):
    artifact = record["artifacts"]["native"]
    path = tmp_path / artifact["path"]
    if change == "same_size":
        data = path.read_bytes();path.write_bytes(b"X" + data[1:])
    elif change == "size":
        path.write_bytes(b"shorter")
    else:
        artifact["sha256"] = "0"*64
    report = validate(record, tmp_path)
    assert report.format_status == "PASS" and report.file_hash_status == "FAIL"
    error = next(i for i in report.issues if i.code == "HASH_MISMATCH")
    assert error.artifact_id == "native" and error.field == "artifacts.native"
    assert error.reason and not report.foundation_valid


def test_files_verified_each_call_no_receipt_cache(record, tmp_path):
    assert validate(record, tmp_path).foundation_valid
    (tmp_path / record["artifacts"]["cli"]["path"]).unlink()
    report = validate(record, tmp_path)
    assert "PROVENANCE_MISSING" in codes(report)
    assert "cli" not in report.checked_artifact_ids


@pytest.mark.parametrize("path", ["../outside", "missing.gpkg", "."])
def test_confined_readonly_paths(record, tmp_path, path):
    record["artifacts"]["native"]["path"] = path
    report = validate(record, tmp_path)
    assert "PROVENANCE_MISSING" in codes(report)


def test_absolute_path_rejected(record, tmp_path):
    record["artifacts"]["native"]["path"] = str(tmp_path / "native.gpkg")
    assert "PROVENANCE_MISSING" in codes(validate(record, tmp_path))


def test_artifact_alias_is_not_a_new_source_edge(record, tmp_path):
    record["artifacts"]["native"] |= {k:record["artifacts"]["converter"][k] for k in ("path", "size_bytes", "sha256")}
    assert "PROVENANCE_MISSING" in codes(validate(record, tmp_path))


def test_format_only_is_not_byte_validation(record, tmp_path):
    result = p.validate_source_h_record(record, artifact_root=tmp_path / "not-created", verify_files=False)
    assert result.format_status == "PASS" and result.file_hash_status == "NOT_RUN"
    assert not result.foundation_valid
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("argument", ["--epsg=4979", "--rules=unknown.json", "-tuse_lod=lod1"])
def test_argv_cannot_hide_conflicting_options(record, tmp_path, argument):
    record["converter"]["argv"].append(argument)
    assert not validate(record, tmp_path).foundation_valid


def test_inline_argv_supported(record, tmp_path):
    record["converter"]["argv"] = ["nusamai.exe", "raw.gml", "--sink=gpkg", "--output=converter.gpkg",
                                    "--epsg=6697", "-t=use_lod=lod2", "-t=split_components=false"]
    assert validate(record, tmp_path).foundation_valid


def test_unknown_required_fields_not_silently_ignored(record, tmp_path):
    record["coordinate_contract"]["gravity_related"] = True
    assert "PROVENANCE_INVALID" in codes(validate(record, tmp_path))


@pytest.mark.parametrize("text", ['{"profile":1,"profile":2}', '{"value":NaN}',
                                '{"value":1e999}', '{bad', '[]'])
def test_strict_json_loader_returns_structured_failure(tmp_path, text):
    path=tmp_path/'record.json';path.write_text(text,encoding='utf-8')
    result=p.load_source_h_record(path,artifact_root=tmp_path)
    assert result.format_status=='FAIL' and result.issues


def test_load_valid_and_no_artifact_modification(record, tmp_path):
    before={path.name:path.read_bytes() for path in tmp_path.iterdir()}
    path=tmp_path/'record.json';path.write_text(json.dumps(record),encoding='utf-8')
    assert p.load_source_h_record(path,artifact_root=tmp_path).foundation_valid
    assert all((tmp_path/name).read_bytes()==data for name,data in before.items())


def test_dependency_is_required_in_both_converter_and_operation_inputs(record, tmp_path):
    data=b'local dependency'
    (tmp_path/'dependency.xml').write_bytes(data)
    record['artifacts']['dependency']={'path':'dependency.xml','size_bytes':len(data),
        'sha256':hashlib.sha256(data).hexdigest(),'role':'raw_dependency'}
    assert not validate(record,tmp_path).foundation_valid
    record['converter']['input_artifact_ids'].append('dependency')
    assert not validate(record,tmp_path).foundation_valid
    record['operations'][0]['input_artifact_ids'].append('dependency')
    assert validate(record,tmp_path).foundation_valid


@pytest.mark.parametrize('field,value', [('artifacts.raw', []), ('source_declaration', None),
    ('converter', []), ('operations.0', None), ('artifacts.raw.role', []),
    ('converter.argv', [None]), ('native.output_artifact_id', {})])
def test_malformed_nested_values_report_errors_not_type_errors(record,tmp_path,field,value):
    set_at(record,field,value)
    result=validate(record,tmp_path)
    assert result.format_status=='FAIL' and result.issues


def test_missing_root_and_record_are_structured(record,tmp_path):
    result=validate(record,tmp_path/'missing')
    assert result.format_status=='PASS' and result.file_hash_status=='FAIL'
    assert 'PROVENANCE_MISSING' in codes(result)
    assert 'PROVENANCE_MISSING' in codes(p.load_source_h_record(tmp_path/'absent.json',artifact_root=tmp_path))


def test_directed_cycle_and_wrong_reference_rejected(record,tmp_path):
    record['operations'][0]['input_artifact_ids']=['native']
    assert 'PROVENANCE_INVALID' in codes(validate(record,tmp_path))
