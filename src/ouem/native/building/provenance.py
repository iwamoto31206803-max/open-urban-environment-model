"""Source-H foundation checks only: declarations and bytes, never eligibility.

Legacy ingest/Standardizer do not call this module. Independent Step 2 uses its
reports; GPKG/XML contents and human review authenticity remain outside this layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any

SOURCE_H_PROFILE = "ouem-native-building/plateau-source-h/v0.1"
LEGACY_PROFILE = "ouem-native-building/plateau-legacy-4979-claimed-tp/v0.1"
NATIVE_SCHEMA = "ouem-plateau-native-ingest/v0.2"
CONVERTER_SCHEMA = "ouem-building-converter-run/v0.1"
REPOSITORY = "https://github.com/MIERUNE/plateau-gis-converter"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
ROLES = {"raw_citygml", "raw_dependency", "raw_archive", "converter_cli",
         "converter_gpkg", "native_gpkg", "source_evidence"}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    field: str
    reason: str
    artifact_id: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    format_status: str
    file_hash_status: str
    issues: tuple[ValidationIssue, ...] = ()
    checked_artifact_ids: tuple[str, ...] = ()
    coordinate_geometry_status: str = "NOT_RUN"
    converter_qualification_status: str = "NOT_VERIFIED"
    human_review_status: str = "NOT_VERIFIED"
    formal_acceptance_status: str = "NOT_VERIFIED"
    eligibility: str = "NOT_ESTABLISHED"
    validation_scope: str = "source-h-foundation/v0.1"

    @property
    def foundation_valid(self) -> bool:
        """Only format + file checks succeeded; NOT an eligibility predicate."""
        return self.format_status == self.file_hash_status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"foundation_valid": self.foundation_valid}


class ProfileValidationError(ValueError):
    def __init__(self, issue: ValidationIssue):
        self.issue = issue
        super().__init__(f"{issue.code}: {issue.field}: {issue.reason}")


def identify_profile(profile: object) -> str:
    """Exact key only; no EPSG inference and no legacy registration in Step 1."""
    if profile == LEGACY_PROFILE:
        raise ProfileValidationError(ValidationIssue(
            "LEGACY_NOT_REGISTERED", "profile", "legacy replay registration is not implemented here"))
    if profile != SOURCE_H_PROFILE:
        raise ProfileValidationError(ValidationIssue(
            "PROFILE_UNSUPPORTED", "profile", "explicit supported source-H profile/version required"))
    return SOURCE_H_PROFILE


class _Checks:
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def fail(self, field: str, reason: str, code: str = "PROVENANCE_INVALID",
             artifact: str | None = None) -> None:
        self.issues.append(ValidationIssue(code, field, reason, artifact))

    def obj(self, value: object, field: str, required: set[str],
            optional: set[str] = frozenset()) -> dict:
        if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
            self.fail(field, "JSON object required", "PROVENANCE_MISSING")
            return {}
        for k in sorted(required - value.keys()):
            self.fail(f"{field}.{k}", "required field missing", "PROVENANCE_MISSING")
        for k in sorted(value.keys() - required - optional):
            self.fail(f"{field}.{k}", "unknown field; informational additions belong in extensions")
        if "extensions" in value and not isinstance(value["extensions"], dict):
            self.fail(f"{field}.extensions", "extensions must be an object")
        return value

    def exact(self, value: object, expected: object, field: str,
              code: str = "PROVENANCE_INVALID") -> None:
        if type(value) is not type(expected) or value != expected:
            self.fail(field, f"expected {expected!r}", code)

    def text(self, value: object, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            self.fail(field, "nonempty string required")


def _ids(value: object, field: str, checks: _Checks) -> list[str]:
    if (not isinstance(value, list) or not value
            or any(not isinstance(v, str) or not v for v in value)
            or len(value) != len(set(value))):
        checks.fail(field, "nonempty unique artifact-ID array required")
        return []
    return value


def _validate_format(record: object, c: _Checks, *, planned_native: bool = False) -> dict:
    r = c.obj(record, "record", {"schema", "profile", "artifacts", "source_declaration",
              "coordinate_contract", "converter", "geometry_selection", "native", "operations"},
              {"validation", "eligibility_review", "acceptance", "extensions"})
    try:
        identify_profile(r.get("profile"))
    except ProfileValidationError as exc:
        c.issues.append(exc.issue)
    c.exact(r.get("schema"), NATIVE_SCHEMA, "schema", "SCHEMA_UNSUPPORTED")
    artifacts = r.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        c.fail("artifacts", "nonempty artifact map required", "PROVENANCE_MISSING")
        artifacts = {}
    roles: dict[str, list[str]] = {role: [] for role in ROLES}
    for identifier, value in artifacts.items():
        if not isinstance(identifier, str) or not identifier:
            c.fail("artifacts", "nonempty string artifact IDs required")
            continue
        prefix = f"artifacts.{identifier}"
        planned = planned_native and isinstance(value, dict) and value.get("role") == "native_gpkg"
        required = {"path", "role", "layer"} if planned else {"path", "size_bytes", "sha256", "role"}
        a = c.obj(value, prefix, required, {"layer", "extensions"})
        c.text(a.get("path"), prefix + ".path")
        size = a.get("size_bytes")
        if not planned and (type(size) is not int or size < 0):
            c.fail(prefix + ".size_bytes", "nonnegative integer required", artifact=identifier)
        digest = a.get("sha256")
        if not planned and (not isinstance(digest, str) or not SHA256.fullmatch(digest)):
            c.fail(prefix + ".sha256", "lowercase SHA-256 required", artifact=identifier)
        role = a.get("role")
        if isinstance(role, str) and role in roles:
            roles[role].append(identifier)
        else:
            c.fail(prefix + ".role", "unknown artifact role", artifact=identifier)
        if role in ("converter_gpkg", "native_gpkg"):
            c.text(a.get("layer"), prefix + ".layer")
    for role in ("converter_cli", "converter_gpkg", "native_gpkg", "source_evidence"):
        if len(roles[role]) != 1:
            c.fail("artifacts", f"exactly one {role} artifact required", "PROVENANCE_MISSING")
    if not roles["raw_citygml"]:
        c.fail("artifacts", "at least one Raw CityGML artifact required", "PROVENANCE_MISSING")

    declaration = c.obj(r.get("source_declaration"), "source_declaration",
        {"srs_name", "horizontal_epsg", "vertical_epsg", "quantity", "unit", "axes", "evidence_artifact_id"})
    contract = c.obj(r.get("coordinate_contract"), "coordinate_contract",
        {"input_epsg", "horizontal_epsg", "vertical_epsg", "quantity", "unit", "storage_axes"})
    for group, obj in (("source_declaration", declaration), ("coordinate_contract", contract)):
        for name, expected in (("horizontal_epsg", 6668), ("vertical_epsg", 6695),
                               ("quantity", "gravity_related_height"), ("unit", "metre")):
            c.exact(obj.get(name), expected, f"{group}.{name}", "VERTICAL_SEMANTICS_CONFLICT")
    c.exact(declaration.get("srs_name"), "http://www.opengis.net/def/crs/EPSG/0/6697",
            "source_declaration.srs_name", "VERTICAL_SEMANTICS_CONFLICT")
    c.exact(declaration.get("axes"), ["latitude", "longitude", "H"], "source_declaration.axes", "AXIS_MISMATCH")
    c.exact(contract.get("input_epsg"), 6697, "coordinate_contract.input_epsg", "VERTICAL_SEMANTICS_CONFLICT")
    c.exact(contract.get("storage_axes"), ["longitude", "latitude", "H"], "coordinate_contract.storage_axes", "AXIS_MISMATCH")
    if declaration.get("evidence_artifact_id") not in roles["source_evidence"]:
        c.fail("source_declaration.evidence_artifact_id", "must reference source evidence artifact")

    selection = c.obj(r.get("geometry_selection"), "geometry_selection", {"requested_lod", "split_components"})
    c.exact(selection.get("requested_lod"), 2, "geometry_selection.requested_lod")
    c.exact(selection.get("split_components"), False, "geometry_selection.split_components")
    converter = c.obj(r.get("converter"), "converter", {"schema", "repository", "commit", "version",
        "cli_artifact_id", "input_artifact_ids", "output_artifact_id", "argv", "resolved_options",
        "exit_code", "execution_status"})
    c.exact(converter.get("schema"), CONVERTER_SCHEMA, "converter.schema", "SCHEMA_UNSUPPORTED")
    c.exact(converter.get("repository"), REPOSITORY, "converter.repository")
    commit = converter.get("commit")
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        c.fail("converter.commit", "full lowercase 40-hex commit required")
    c.text(converter.get("version"), "converter.version")
    inputs = _ids(converter.get("input_artifact_ids"), "converter.input_artifact_ids", c)
    if set(inputs) != set(roles["raw_citygml"] + roles["raw_dependency"]):
        c.fail("converter.input_artifact_ids", "must reference all declared Raw members/dependencies exactly")
    for key, role in (("cli_artifact_id", "converter_cli"), ("output_artifact_id", "converter_gpkg")):
        if converter.get(key) not in roles[role]:
            c.fail("converter." + key, f"must reference {role}")
    c.exact(converter.get("exit_code"), 0, "converter.exit_code")
    c.exact(converter.get("execution_status"), "COMPLETED", "converter.execution_status")
    options = c.obj(converter.get("resolved_options"), "converter.resolved_options",
                    {"sink", "epsg", "use_lod", "split_components"})
    for key, expected in (("sink", "gpkg"), ("epsg", 6697), ("use_lod", "lod2"), ("split_components", False)):
        c.exact(options.get(key), expected, "converter.resolved_options." + key,
                "VERTICAL_SEMANTICS_CONFLICT" if key == "epsg" else "PROVENANCE_INVALID")
    _argv(converter.get("argv"), c)
    native = c.obj(r.get("native"), "native", {"input_artifact_id", "output_artifact_id"})
    if native.get("input_artifact_id") not in roles["converter_gpkg"]:
        c.fail("native.input_artifact_id", "must reference Converter GPKG")
    if native.get("output_artifact_id") not in roles["native_gpkg"]:
        c.fail("native.output_artifact_id", "must reference Native GPKG")
    operations = r.get("operations")
    if not isinstance(operations, list) or len(operations) != 2:
        c.fail("operations", "exactly two ordered Raw-to-Converter-to-Native edges required")
    else:
        expected_edges = [(inputs, converter.get("output_artifact_id"), "latitude_longitude_to_gis_longitude_latitude"),
                          ([native.get("input_artifact_id")], native.get("output_artifact_id"), "identity_XY")]
        for index, (value, edge) in enumerate(zip(operations, expected_edges)):
            prefix = f"operations[{index}]"
            op = c.obj(value, prefix, {"input_artifact_ids", "output_artifact_id", "horizontal_operation",
                                     "vertical_operation", "offset_m", "geoid_model"})
            ids = _ids(op.get("input_artifact_ids"), prefix + ".input_artifact_ids", c)
            if (any(not isinstance(v, str) for v in edge[0]) or set(ids) != set(edge[0])
                    or op.get("output_artifact_id") != edge[1]):
                c.fail(prefix, "edge must match declared Raw/Converter/Native artifact references")
            c.exact(op.get("horizontal_operation"), edge[2], prefix + ".horizontal_operation")
            c.exact(op.get("vertical_operation"), "identity_H", prefix + ".vertical_operation", "VERTICAL_SEMANTICS_CONFLICT")
            if type(op.get("offset_m")) not in (int, float) or op.get("offset_m") != 0:
                c.fail(prefix + ".offset_m", "identity_H requires zero offset", "VERTICAL_SEMANTICS_CONFLICT")
            c.exact(op.get("geoid_model"), None, prefix + ".geoid_model", "VERTICAL_SEMANTICS_CONFLICT")
    return artifacts


def validate_source_h_inputs(record: object, *, artifact_root: str | Path) -> ValidationReport:
    """Step 2 preflight: Native is a plan WITHOUT size/hash, all inputs exist.

    This does not alter validate_source_h_record's completed-record requirements.
    Every checked ID is an actual input; the planned Native ID is never included.
    """
    c = _Checks()
    artifacts = _validate_format(record, c, planned_native=True)
    if c.issues:
        return ValidationReport("FAIL", "NOT_RUN", tuple(c.issues),
                                validation_scope="source-h-input-preflight/v0.1")
    try:
        root = Path(artifact_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("artifact_root must be a directory")
    except (OSError, ValueError) as exc:
        c.fail("artifact_root", str(exc), "PROVENANCE_MISSING")
        return ValidationReport("PASS", "FAIL", tuple(c.issues),
                                validation_scope="source-h-input-preflight/v0.1")
    inputs = {k: v for k, v in artifacts.items() if v["role"] != "native_gpkg"}
    checked = _files(inputs, root, c)
    return ValidationReport("PASS", "FAIL" if c.issues else "PASS", tuple(c.issues), checked,
                            validation_scope="source-h-input-preflight/v0.1")


def _argv(value: object, c: _Checks) -> None:
    if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v for v in value):
        c.fail("converter.argv", "nonempty argv string array required")
        return
    # Only declarations are checked; this does not prove what a binary executed.
    options: dict[str, list[str]] = {"--sink": [], "--epsg": [], "--output": [], "-t": []}
    inputs = []
    index = 1
    while index < len(value):
        token = value[index]
        key, separator, argument = token.partition("=")
        if key in options:
            if not separator:
                index += 1
                argument = value[index] if index < len(value) else ""
            if not argument or argument.startswith("-"):
                c.fail("converter.argv", f"missing value for {key}")
            options[key].append(argument)
        elif token.startswith("-"):
            c.fail("converter.argv", f"unsupported option spelling: {token}")
        else:
            inputs.append(token)
        index += 1
    if not inputs or len(options["--output"]) != 1 or not options["--output"][0]:
        c.fail("converter.argv", "input arguments and exactly one nonempty --output required")
    if options["--sink"] != ["gpkg"]:
        c.fail("converter.argv", "exactly one --sink gpkg declaration required")
    if options["--epsg"] != ["6697"]:
        c.fail("converter.argv", "exactly one --epsg 6697 required", "VERTICAL_SEMANTICS_CONFLICT")
    if (options["-t"].count("use_lod=lod2") != 1
            or options["-t"].count("split_components=false") > 1
            or any(v not in ("use_lod=lod2", "split_components=false") for v in options["-t"])):
        c.fail("converter.argv", "explicit LoD2 and no conflicting transformer options required")


def _files(artifacts: dict, root: Path, c: _Checks) -> tuple[str, ...]:
    checked = []
    resolved_paths: set[Path] = set()
    for identifier, artifact in artifacts.items():
        field = f"artifacts.{identifier}"
        try:
            locator = Path(artifact["path"])
            if locator.is_absolute() or locator.drive or ".." in locator.parts:
                raise ValueError("artifact path must be relative within artifact_root")
            path = (root / locator).resolve(strict=True)
            if not path.is_relative_to(root):
                raise ValueError("resolved artifact escapes artifact_root")
            if path in resolved_paths:
                raise ValueError("distinct artifact IDs must not alias one file")
            resolved_paths.add(path)
            if not stat.S_ISREG(path.stat().st_mode):
                raise ValueError("regular file required")
            with path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError("regular file required")
                digest = hashlib.sha256()
                remaining = artifact["size_bytes"] + 1
                count = 0
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    digest.update(chunk)
                    count += len(chunk)
                    remaining -= len(chunk)
                after = os.fstat(stream.fileno())
            current = path.stat()
            if (before.st_size != artifact["size_bytes"] or count != artifact["size_bytes"]
                    or digest.hexdigest() != artifact["sha256"]):
                c.fail(field, "actual file size/SHA-256 differs from reference", "HASH_MISMATCH", identifier)
            elif ((before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
                    or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                    != (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)):
                c.fail(field, "artifact changed while reading", "HASH_MISMATCH", identifier)
            else:
                checked.append(identifier)
        except (OSError, ValueError) as exc:
            c.fail(field + ".path", str(exc), "PROVENANCE_MISSING", identifier)
    return tuple(checked)


def validate_source_h_record(record: object, *, artifact_root: str | Path,
                             verify_files: bool = True) -> ValidationReport:
    """Check a candidate Native v0.2 foundation view; never authorize processing.

    verify_files=False is format-only and performs no artifact IO. Root confines
    relative artifact locators. Geometry/CRS contents and evidence/review claims
    remain unverified even when every reported foundation check passes.
    """
    c = _Checks()
    artifacts = _validate_format(record, c)
    if c.issues:
        return ValidationReport("FAIL", "NOT_RUN", tuple(c.issues))
    if not verify_files:
        return ValidationReport("PASS", "NOT_RUN")
    try:
        root = Path(artifact_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("artifact_root must be a directory")
    except (OSError, ValueError) as exc:
        c.fail("artifact_root", str(exc), "PROVENANCE_MISSING")
        return ValidationReport("PASS", "FAIL", tuple(c.issues))
    checked = _files(artifacts, root, c)
    return ValidationReport("PASS", "FAIL" if c.issues else "PASS", tuple(c.issues), checked)


def load_source_h_record(path: str | Path, *, artifact_root: str | Path,
                        verify_files: bool = True) -> ValidationReport:
    """Load strict JSON (no duplicate keys/nonfinite constants), then validate."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            nonfinite(value)
        return number

    try:
        with Path(path).open(encoding="utf-8") as stream:
            record = json.load(stream, object_pairs_hook=unique,
                               parse_constant=nonfinite, parse_float=finite_float)
    except OSError as exc:
        return ValidationReport("FAIL", "NOT_RUN", (
            ValidationIssue("PROVENANCE_MISSING", "record", str(exc)),))
    except (ValueError, UnicodeError) as exc:
        return ValidationReport("FAIL", "NOT_RUN", (
            ValidationIssue("PROVENANCE_INVALID", "record", str(exc)),))
    return validate_source_h_record(record, artifact_root=artifact_root, verify_files=verify_files)
