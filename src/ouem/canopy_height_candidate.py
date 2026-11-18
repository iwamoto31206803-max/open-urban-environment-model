"""Synthetic-only review seam for M1 Meta/GSI canopy-height compatibility.

This is NOT a data-ingestion adapter, evidence validator, Standard Canopy
contract or permission to process real GSI inputs. The existing Meta production
and experimental gates in height_envelope.py are deliberately untouched.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ouem import height_envelope as env


def _require_shape(label, array, shape):
    if np.asarray(array).shape != shape:
        raise env.EnvelopeBlocked(f"{label}: shape differs from reviewed grid")


def _require_boolean(label, array, shape):
    values = np.asarray(array)
    _require_shape(label, values, shape)
    if values.dtype != np.dtype("bool"):
        raise env.EnvelopeBlocked(f"{label}: expected an explicit boolean mask")
    return values.copy()


def _require_samples(label, samples, shape):
    if not isinstance(samples, env.Samples):
        raise env.EnvelopeBlocked(f"{label}: expected sampled height/terrain arrays")
    _require_shape(label, samples.values, shape)
    if not isinstance(samples.values, np.ndarray) or samples.values.dtype.kind not in "uif":
        raise env.EnvelopeBlocked(f"{label}: expected numeric samples")
    if not isinstance(samples.metadata, Mapping):
        raise env.EnvelopeBlocked(f"{label}: expected source metadata mapping")
    _require_boolean(label + " missing", samples.missing, shape)
    _require_boolean(label + " outside", samples.outside, shape)


def review_synthetic_candidate(
    grid: env.GridSpec,
    hag: env.Samples,
    dem: env.Samples,
    *,
    profile: str,
    hag_aligned_transform,
    dem_aligned_transform,
    vertical_compatible: bool,
    synthetic_assertion: str,
    presence_mask=None,
    inference_valid=None,
    presence_aligned_transform=None,
    canopy_probability=None,
    epochs: Mapping[str, str] | None = None,
    crown_ratio: float = 0.60,
):
    """Check synthetic in-memory inputs and reuse the existing height core.

    The returned top/bottom are numeric candidate envelopes only, NOT TREE
    placement. The Meta-derived interpretation is separate from independent
    inference fields. A positive point-derived HAG in a model-background cell is
    deliberately retained in the numeric result. Source/rights/quality review
    and any masked-CHM fusion policy remain unimplemented.
    """
    if synthetic_assertion != "SYNTHETIC_TEST_ONLY":
        raise env.EnvelopeBlocked("Synthetic review cannot admit real source evidence")
    if profile not in ("meta_estimated_canopy_hag", "gsi_point_surface_hag"):
        raise env.EnvelopeBlocked("Unknown synthetic source quantity/profile")
    if vertical_compatible is not True:
        raise env.EnvelopeBlocked("No reviewed compatible height/ground reference")
    if not isinstance(grid, env.GridSpec):
        raise env.EnvelopeBlocked("Expected an explicit reviewed GridSpec")
    shape = (grid.height, grid.width)
    _require_samples("HAG", hag, shape)
    _require_samples("DEM", dem, shape)
    if hag_aligned_transform != grid.transform or dem_aligned_transform != grid.transform:
        raise env.EnvelopeBlocked("Aligned HAG/DEM transforms differ from GridSpec")

    if profile == "meta_estimated_canopy_hag":
        if any(x is not None for x in (presence_mask, inference_valid,
                                       presence_aligned_transform, canopy_probability)):
            raise env.EnvelopeBlocked("Meta height is not an independently classified canopy mask")
        prediction = None
        prediction_valid = None
        probability = None
    else:
        if presence_mask is None or inference_valid is None:
            raise env.EnvelopeBlocked("GSI synthetic candidate requires mask and inference validity")
        if presence_aligned_transform != grid.transform:
            raise env.EnvelopeBlocked("Predicted-mask transform differs from GridSpec")
        prediction = _require_boolean("predicted canopy", presence_mask, shape)
        prediction_valid = _require_boolean("inference validity", inference_valid, shape)
        probability = None
        if canopy_probability is not None:
            probability = np.asarray(canopy_probability, dtype=float).copy()
            _require_shape("canopy probability", probability, shape)
            observed = probability[prediction_valid]
            if not np.all(np.isfinite(observed) & (observed >= 0) & (observed <= 1)):
                raise env.EnvelopeBlocked("Valid inference requires finite probabilities in [0,1]")

    if epochs is None:
        epochs_copy = {}
    elif (not isinstance(epochs, Mapping)
          or not all(isinstance(k, str) and isinstance(v, str) for k, v in epochs.items())):
        raise env.EnvelopeBlocked("Synthetic epochs must be explicit string metadata")
    else:
        epochs_copy = dict(epochs)

    top, bottom, state, qa = env.calculate(grid, hag, dem, env.ConstantCR(crown_ratio))
    raw_hag = np.asarray(hag.values).copy()
    source_valid = effective_hag(hag)
    modelled_presence = None
    if prediction is None:
        modelled_presence = meta_presence_fields(hag, source_valid)
        modelled_presence.update(
            rule="meta_effective_valid_hag_positive_or_zero",
            surveyed_coverage=None,
            tree_candidate=modelled_presence["present"] & (state == env.VALID) & (top > bottom),
        )
        unknown_presence = np.ones(shape, dtype=bool)
        inferred_height_conflict = np.zeros(shape, dtype=bool)
        missing_height_for_predicted_canopy = np.zeros(shape, dtype=bool)
    else:
        unknown_presence = ~prediction_valid
        inferred_height_conflict = (prediction_valid & ~prediction
                                    & source_valid & (raw_hag > 0))
        missing_height_for_predicted_canopy = (prediction_valid & prediction
                                               & (state != env.VALID))
    return {
        "top_z": top, "bottom_z": bottom, "height_state": state, "height_qa": qa,
        "hag_valid": source_valid,
        "dem_valid": ~dem.outside & ~dem.missing & np.isfinite(dem.values),
        "absolute_z_valid": state == env.VALID,
        "meta_modelled_presence": modelled_presence,
        "envelope_grid": grid,
        "raw_hag": raw_hag, "profile": profile, "epochs": epochs_copy,
        "predicted_canopy": prediction, "inference_valid": prediction_valid,
        "canopy_probability": probability, "unknown_presence": unknown_presence,
        "background_positive_height_conflict": inferred_height_conflict,
        "predicted_canopy_height_unavailable": missing_height_for_predicted_canopy,
        "review_scope": "SYNTHETIC_ONLY_NOT_STANDARD_ACCEPTANCE",
    }


def effective_hag(hag):
    return ~hag.outside & ~hag.missing & np.isfinite(hag.values) & (hag.values >= 0)


def meta_presence_fields(hag, valid):
    """Classify already sampled HAG and preserve source support separately."""
    return {
        "present": valid & (hag.values > 0),
        "absent": valid & (hag.values == 0),
        "unknown": ~valid,
        "source_support": ~hag.outside,
        "assessed_domain": valid.copy(),
    }


def map_synthetic_meta_to_engine(review, centre_x, centre_y, *, centre_epsg):
    """Map reviewed Meta diagnostics through their Envelope grid.

    Centres are projected XY in the Envelope CRS and in engine array order.
    The sampler uses half-open pixel bounds, flooring fractional row/column
    at exact ties. Outside centres are unknown. No axis flip is applied.
    """
    grid = review.get("envelope_grid")
    model = review.get("meta_modelled_presence")
    if (review.get("review_scope") != "SYNTHETIC_ONLY_NOT_STANDARD_ACCEPTANCE"
            or model is None or not isinstance(grid, env.GridSpec)):
        raise env.EnvelopeBlocked("Expected a reviewed synthetic Meta envelope")
    fields = {
        "present": model["present"], "absent": model["absent"], "unknown": model["unknown"],
        "source_support": model["source_support"], "assessed_domain": model["assessed_domain"],
        "absolute_z_valid": review["absolute_z_valid"], "tree_candidate": model["tree_candidate"],
    }
    return map_envelope_fields(grid, fields, centre_x, centre_y, centre_epsg=centre_epsg)


def map_envelope_fields(grid, fields, centre_x, centre_y, *, centre_epsg):
    """Sample Boolean diagnostics on the Envelope grid in supplied XY order."""
    if centre_epsg != grid.epsg:
        raise env.EnvelopeBlocked("Engine centres must be projected in the Envelope CRS")
    x, y = np.asarray(centre_x, dtype=float), np.asarray(centre_y, dtype=float)
    if x.ndim != 2 or x.shape != y.shape or not x.size:
        raise env.EnvelopeBlocked("Engine centres require matching nonempty XY arrays")
    inside, rows, cols = env.nearest_cells(grid.transform, grid.width, grid.height, x, y)
    mapped = {}
    for name, values in fields.items():
        _require_shape(name, values, (grid.height, grid.width))
        mask = np.full(x.shape, name == "unknown", dtype=bool)
        mask[inside] = values[rows, cols]
        mapped[name] = mask
    mapped["outside_envelope"] = ~inside
    return mapped
