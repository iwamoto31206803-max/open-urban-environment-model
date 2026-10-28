"""Small normal-path integration and essential boundary checks, no real data."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

from integration.source_h_25d_fixture import build_chain
from ouem.adapters import source_h_synthetic as a


IDS = ['synthetic_tokyo','synthetic_niigata']


@pytest.fixture
def chain(tmp_path):
    return build_chain(tmp_path)


def adapt(root,chain,**kwargs):
    standard,config,terrain = chain
    return a.adapt_synthetic_source_h(standard['manifest'],root,config,
        terrain=kwargs.pop('terrain',terrain),synthetic_source_ids=IDS,**kwargs)


def test_two_building_flat_ground_success(chain,tmp_path):
    before = {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = adapt(tmp_path,chain)
    assert result.summary['consumer_validation']=='PASS'
    assert result.summary['technical_validation']=='PASS'
    assert set(result.buildings.source_id)==set(IDS)
    for row in result.buildings.itertuples():
        expected = 9.5 if row.source_id=='synthetic_tokyo' else 14.75
        assert row.z_top_abs==10.25+expected
        assert row.ground_eff_abs==10.25 and row.height==expected and row.min_height==0
        assert row.ouem_id==a.deterministic_ouem_id(row.source_id)
        assert row.geometry.is_valid and row.geometry.area>0 and not row.geometry.has_z
        assert box(*chain[2].bounds).covers(row.geometry)
        assert np.any(result.building_ids==row.id)
        assert result.terrain_H[result.building_ids==row.id].tolist()==[10.25]*row.ground_sample_count
    assert result.terrain_H.shape==result.building_ids.shape==(64,64)
    assert result.buildings.crs.to_epsg()==6677 and result.voxcity_buildings.crs.to_epsg()==4326
    assert result.voxcity_buildings[['id','height','min_height']].equals(result.buildings[['id','height','min_height']])
    assert result.voxcity_buildings.is_valid.all()
    assert before=={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert result.summary['source_h_eligibility']=='NOT_ESTABLISHED'
    assert result.summary['human_review']==result.summary['formal_acceptance']=='NOT_VERIFIED'
    assert set(result.summary['phase5_gates'].values())=={'OPEN'}


def test_consumer_failure_refused(chain,tmp_path):
    Path(chain[0]['output']).write_bytes(b'corrupt')
    with pytest.raises(ValueError) as caught:adapt(tmp_path,chain)
    assert caught.value.code=='CONSUMER_FAILED'


def test_vertical_mismatch_refused(chain,tmp_path):
    with pytest.raises(ValueError) as caught:
        adapt(tmp_path,chain,terrain=replace(chain[2],vertical_crs='EPSG:4979'))
    assert caught.value.code=='VERTICAL_MISMATCH'


def test_use_time_binding_refuses_change(chain,tmp_path,monkeypatch):
    actual = a.validate_source_h_standard
    def modified(*args,**kwargs):
        report = actual(*args,**kwargs)
        assert report['technical_validation']=='PASS'
        with Path(chain[0]['output']).open('ab') as stream:stream.write(b'changed')
        return report
    monkeypatch.setattr(a,'validate_source_h_standard',modified)
    with pytest.raises(ValueError) as caught:adapt(tmp_path,chain)
    assert caught.value.code in ('HASH_MISMATCH','INPUT_CHANGED')
