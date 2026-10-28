"""Normal-path actual CPU solar integration, no replacement ray tracer."""
import math

import numpy as np
import pytest

from integration.source_h_25d_fixture import build_chain
from ouem.synthetic_building_solar import run_synthetic_building_solar


@pytest.fixture(scope='module')
def analysis(tmp_path_factory):
    root=tmp_path_factory.mktemp('synthetic-solar')
    standard,config,terrain=build_chain(root)
    before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
    from voxcity.simulator.solar import radiation
    actual=radiation.get_direct_solar_irradiance_map
    calls=[]
    def observed(scene,*args,**kwargs):
        calls.append({'voxels':scene.voxels.classes.copy(),'dem':scene.dem.elevation.copy(),
                      'rotation':scene.extras['rotation_angle'],'args':args,'kwargs':kwargs})
        return actual(scene,*args,**kwargs)  # real API/kernel, never fabricated output
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(radiation,'get_direct_solar_irradiance_map',observed)
        result=run_synthetic_building_solar(standard['manifest'],root,config,terrain=terrain,
            synthetic_source_ids=['synthetic_tokyo','synthetic_niigata'])
    assert before=={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
    return result,calls


def test_actual_api_pair_same_grid_ground_observer_and_shadow(analysis):
    result,calls=analysis
    assert len(calls)==2
    a,b=calls
    assert a['args']==b['args']==(135.,35.,800.) and a['kwargs']==b['kwargs']
    assert a['rotation']==b['rotation']
    assert a['voxels'].shape==b['voxels'].shape==(64,64,18)
    assert np.array_equal(a['dem'],b['dem']) and np.all(a['dem']==0)
    assert not np.any(a['voxels']==-3) and np.count_nonzero(b['voxels']==-3)==2400
    assert np.array_equal(a['voxels'][b['voxels']!=-3],b['voxels'][b['voxels']!=-3])
    assert np.all(a['voxels'][:,:,0]==1) and np.all(b['voxels'][:,:,0]==1)
    mask=result.valid_ground
    assert mask.shape==result.terrain_only.shape==result.with_buildings.shape==result.reduction.shape==(64,64)
    assert int(mask.sum())==3904 and np.array_equal(mask,result.building_ids==0)
    assert np.array_equal(np.isfinite(result.terrain_only),mask)
    assert np.array_equal(np.isfinite(result.with_buildings),mask)
    assert np.allclose(result.terrain_only[mask],800*math.sin(math.radians(35)),rtol=0,atol=1e-9)
    assert np.all(result.reduction[mask]>=0) and np.any(result.reduction[mask]>1e-9)
    assert np.allclose(result.reduction[mask],result.terrain_only[mask]-result.with_buildings[mask])
    assert result.metadata['observer']['DDA_origin_cell_centre_k']==2.5
    assert result.metadata['observer']['nominal_origin_H_m']==12.75


def test_true_sun_and_coarse_shadow_direction_and_governance(analysis):
    result,_=analysis;m=result.metadata
    direction=m['sun']['ray_toward_sun_uv_up']
    assert direction[0]<0 and direction[1]>0 and direction[2]>0  # towards SE, shade NW
    assert m['qa']['shadow_direction_corridor']=='PASS'
    assert m['qa']['shadow_corridor_max_min_lateral_cells']<=math.sqrt(2)/2+1e-8
    assert m['results']['shadow_cells']>0 and m['qa']['irradiance_increase_cells']==0
    assert m['qa']['unexpected_invalid_valid_ground_cells']==0
    assert m['base_voxel_npy_sha256']=='346a5bcc1c649cc3de70674a50cf1a539b6425a7a1edcaf9f0ed8a5f772612f2'
    assert m['source_h_eligibility']=='NOT_ESTABLISHED'
    assert m['human_review']==m['formal_acceptance']=='NOT_VERIFIED'
    assert set(m['phase5_gates'].values())=={'OPEN'}
