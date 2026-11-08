"""Independent synthetic control checks, without importing VoxCityGML."""
import xml.etree.ElementTree as ET
import json
import numpy as np
import pytest

from ouem import p1_lod2_f as p


def building(identifier=p.SOURCE_ID):
    b=ET.Element('{'+p.NS['bldg']+'}Building',{'{'+p.NS['gml']+'}id':identifier})
    for i,kind in enumerate(['RoofSurface','GroundSurface']+['WallSurface']*4):
        bounded=ET.SubElement(b,'{'+p.NS['bldg']+'}boundedBy')
        s=ET.SubElement(bounded,'{'+p.NS['bldg']+'}'+kind)
        lod=ET.SubElement(s,'{'+p.NS['bldg']+'}lod2MultiSurface')
        polygon=ET.SubElement(lod,'{'+p.NS['gml']+'}Polygon',{'{'+p.NS['gml']+'}id':str(i)})
        ext=ET.SubElement(polygon,'{'+p.NS['gml']+'}exterior')
        ET.SubElement(ext,'{'+p.NS['gml']+'}posList').text='35 139 0 35 140 0 36 140 0 36 139 0 35 139 0'
    return b


def test_exact_id_selection_and_duplicate_rejection(tmp_path):
    root=ET.Element('CityModel');root.extend([building('other'),building()])
    path=tmp_path/'source.gml';ET.ElementTree(root).write(path)
    selected,b=p.select_f(path)
    assert len(selected)==1 and b.get('{'+p.NS['gml']+'}id')==p.SOURCE_ID
    assert len(p.face_records(b))==6
    root.append(building());ET.ElementTree(root).write(path)
    with pytest.raises(ValueError,match='duplicated'):p.select_f(path)


@pytest.mark.parametrize('change',['lod','face','ring','hole'])
def test_strict_lod_faces_rings_holes(change):
    b=building()
    if change=='lod':b.find('.//bldg:lod2MultiSurface',p.NS).tag='{'+p.NS['bldg']+'}lod1MultiSurface'
    elif change=='face':b.remove(b[-1])
    elif change=='ring':b.find('.//gml:posList',p.NS).text='35 139 0 35 140 0 36 140 0 36 139 0'
    else:
        polygon=b.find('.//gml:Polygon',p.NS);interior=ET.SubElement(polygon,'{'+p.NS['gml']+'}interior')
        ET.SubElement(interior,'{'+p.NS['gml']+'}posList').text='35 139 0 35 140 0 36 140 0 35 139 0'
    with pytest.raises(ValueError):p.face_records(b)


def test_projection_keeps_exact_absolute_Z_and_cyclic_ring_mapping():
    raw=np.array([[35.6,139.5,0.],[35.6,139.50001,2.],[35.60001,139.50001,2.],[35.60001,139.5,0.],[35.6,139.5,0.]])
    out=p.project(raw)
    np.testing.assert_array_equal(out[:,2],raw[:,2])
    shifted=np.roll(out[:-1][::-1],1,axis=0);shifted=np.vstack((shifted,shifted[0]))
    assert p.align_ring(out,shifted)['reversed']
    shifted[:,2]+=1
    with pytest.raises(ValueError):p.align_ring(out,shifted)


def test_documented_merge_bound_and_face_loss_rejected():
    vertices=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,1.]])
    faces=np.array([[0,1,2]])
    assert p.repair_correspondence(vertices,faces,vertices.copy(),faces[:,::-1])['source_H_values_unchanged']
    with pytest.raises(ValueError,match='face'):p.repair_correspondence(vertices,faces,vertices,np.empty((0,3),dtype=int))
    changed=vertices.copy();changed[0,0]+=.01
    with pytest.raises(ValueError,match='rounding'):p.repair_correspondence(vertices,faces,changed,faces)
    changed=vertices.copy();changed[:,2]+=.0000001
    with pytest.raises(ValueError,match='H'):p.repair_correspondence(vertices,faces,changed,faces)


def test_partial_failure_cannot_publish_completion(tmp_path,monkeypatch):
    inputs=[]
    for name in ('member','standard','audit'):
        path=tmp_path/name;path.write_text('synthetic');inputs.append(path)
    monkeypatch.setattr(p.sys,'prefix',p.sys.base_prefix)
    output=tmp_path/'failed'
    result=p.run(*inputs,output)
    manifest=json.loads((output/'manifest.json').read_text())
    assert manifest['status']=='BLOCKED'
    assert result['P1-1b_READY']=='BLOCKED'
    assert all(state=='NOT_EXECUTED' for state in manifest['stages'].values())
    assert not (output/'voxels.npy').exists()
