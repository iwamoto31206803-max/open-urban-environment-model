"""PoC-P1-1a: strict single-F LoD2 mesh diagnostics in the isolated P1 venv."""
from copy import deepcopy
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sqlite3
import sys
import xml.etree.ElementTree as ET

import numpy as np
from pyproj import Transformer

from ouem.consumers._source_h_geometry import decode
from ouem.native.building.source_h_geometry import polygons

SOURCE_ID = "bldg_09532951-4dab-457d-b1c6-56d509900d1b"
OUEM_ID = "oub-c56cb020-c11c-5f9c-a37f-73018266a333"
GML_COMMIT = "19628c033b1cbbbdee80fe781f516672765d1eee"
VOX_COMMIT = "fa212656305328a9a657973bae26f352bfe813bc"
NS = dict(gml="http://www.opengis.net/gml",bldg="http://www.opengis.net/citygml/building/2.0")
XY_TOLERANCE = 1e-7  # Existing source-H consumer contract, not fitted to F.


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def array_sha(a):
    return hashlib.sha256(a.tobytes(order="C")).hexdigest()


def write(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    require(json.loads(path.read_bytes())==value,"JSON readback mismatch")


def select_f(path):
    """Exact XML ID selection, never rectangle selection or a parser cache."""
    selected=[]
    for _,elem in ET.iterparse(path,events=('end',)):
        if elem.tag=='{'+NS['bldg']+'}Building':
            if elem.get('{'+NS['gml']+'}id')==SOURCE_ID:selected.append(deepcopy(elem))
            elem.clear()
    require(len(selected)==1,"F source ID absent/duplicated")
    root=ET.Element('CityModel')
    root.append(selected[0])
    return root,selected[0]


def face_records(building):
    records=[]
    for bounded in building.findall('bldg:boundedBy',NS):
        require(len(bounded)==1,"ambiguous boundary surface")
        surface=bounded[0];kind=surface.tag.split('}')[-1]
        require(kind in ('RoofSurface','WallSurface','GroundSurface'),"unexpected semantic surface")
        geometry=surface.find('bldg:lod2MultiSurface',NS)
        require(geometry is not None,"missing explicit LoD2; fallback forbidden")
        for p in geometry.findall('.//gml:Polygon',NS):
            rings=[]
            for name in ('exterior','interior'):
                for ring in p.findall('gml:'+name,NS):
                    pos=ring.find('.//gml:posList',NS)
                    require(pos is not None and pos.text,"posList required by bounded F profile")
                    values=np.array([float(x) for x in pos.text.split()],dtype=float)
                    require(values.size%3==0,"invalid XYZ count")
                    xyz=values.reshape(-1,3)
                    require(len(xyz)>=4 and np.isfinite(xyz).all() and np.array_equal(xyz[0],xyz[-1]),"invalid/unclosed ring")
                    rings.append(dict(kind=name,xyz=xyz.tolist()))
            require(sum(r['kind']=='exterior' for r in rings)==1,"exterior ring missing")
            records.append(dict(polygon_id=p.get('{'+NS['gml']+'}id'),semantic=kind,rings=rings,element=p))
    require({k:sum(r['semantic']==k for r in records) for k in ('RoofSurface','WallSurface','GroundSurface')}
            ==dict(RoofSurface=1,WallSurface=4,GroundSurface=1),"wrong F face population")
    require(all(sum(x['kind']=='interior' for x in r['rings'])==0 for r in records),"F profile unexpectedly has holes; stop")
    require(len({r['polygon_id'] for r in records})==6,"duplicate face IDs")
    return records


def project(raw):
    """Raw (lat,lon,H) -> EPSG:6677 (X,Y,H); H is never passed to PROJ."""
    x,y=Transformer.from_crs(6668,6677,always_xy=True).transform(raw[:,1],raw[:,0],errcheck=True)
    projected=np.column_stack((x,y,raw[:,2]))
    require(np.array_equal(projected[:,2],raw[:,2]),"vertical H changed")
    return projected


def repair_correspondence(before,faces,after,newfaces):
    # The pinned merge stage rounds coordinates to six decimals. The bound
    # is fixed by that operation, not chosen after seeing the real geometry.
    distance=np.max(np.abs(after[:,None,:]-before[None,:,:]),axis=2)
    index=np.argmin(distance,axis=1)
    error=distance[np.arange(len(after)),index]
    require(np.all(error<=.5e-6+np.spacing(np.abs(before).max())),"repair exceeds pinned six-decimal merge rounding")
    require(np.array_equal(np.unique(before[:,2]),np.unique(after[:,2])),"repair changes source H")
    # Canonical coordinate-based triangle keys preserve all original surfaces
    # while allowing duplicate welding, reordering and winding correction.
    canonical=lambda v,f:sorted(tuple(sorted(tuple(np.round(v[i],6)) for i in tri)) for tri in f)
    require(canonical(before,faces)==canonical(after,newfaces),"repair loses/adds/retriangulates a face")
    return dict(max_coordinate_delta_m=float(error.max()),rounding_rule="pinned merge precision=6; <=0.5e-6 m per coordinate + one source ULP",
                source_H_values_unchanged=True,all_triangles_preserved_ignoring_winding=True,
                arrays_identical=bool(np.array_equal(before,after) and np.array_equal(faces,newfaces)),source_and_repaired_are_distinct=True)


def align_ring(source,target):
    require(source.shape==target.shape,"Standard ring count differs")
    matches=[]
    for reverse in (False,True):
        v=source[:-1][::-1] if reverse else source[:-1]
        for shift in range(len(v)):
            candidate=np.roll(v,shift,axis=0)
            error=float(np.max(np.abs(candidate[:,:2]-target[:-1,:2])))
            if np.array_equal(candidate[:,2],target[:-1,2]) and error<=XY_TOLERANCE:
                matches.append(dict(reversed=reverse,cyclic_shift=shift,max_XY_error_m=error))
    require(len(matches)==1,"Standard ring/H correspondence not unique")
    return matches[0]


def mesh_stats(vertices,faces):
    import trimesh
    m=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    return dict(vertices=len(vertices),triangles=len(faces),bounds=m.bounds.tolist(),area_m2=float(m.area),
                signed_volume_m3=float(m.volume),watertight=bool(m.is_watertight),is_volume=bool(m.is_volume),
                vertices_sha256=array_sha(vertices),faces_sha256=array_sha(faces))


def guard(output,protected):
    events=[]
    def audit(event,args):
        if event in ('socket.connect','socket.getaddrinfo'):
            events.append(event);raise RuntimeError("external communication forbidden")
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=Path(args[0]).resolve()
            mode,flags=args[1],args[2]
            writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&0x3!=0)
            if writing and not path.is_relative_to(output) and any(path.is_relative_to(p) for p in protected):
                events.append('protected_write');raise RuntimeError("protected input/environment write forbidden")
    sys.addaudithook(audit)
    return events


def run(member,standard,audit_report,output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    stages={key:'NOT_EXECUTED' for key in ('ENVIRONMENT','SOURCE_IDENTITY','GEOMETRY','VERTICAL','VOXEL')}
    diagnostics=dict(profile='ouem-p1-1a-single-F/v0.1',stages=stages)
    inputs={str(p):sha(p) for p in (member,standard,audit_report)}
    try:
        require(sys.prefix!=sys.base_prefix and Path(sys.prefix).name=='ouem-voxcitygml-p1',"isolated P1 venv required")
        require(inputs[str(member)]=='6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9',"CityGML SHA mismatch")
        require(inputs[str(standard)]=='954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60',"Standard SHA mismatch")
        require(inputs[str(audit_report)]=='71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e',"audit report SHA mismatch")
        events=guard(output,[Path(member).resolve().parent,Path(standard).resolve().parent,Path(audit_report).resolve().parent,Path.cwd()/'.venv'])
        import voxcitygml
        import voxcity
        from voxcitygml.citygml import geometry,extractors
        from voxcitygml import watertight,voxelizer3d
        require(not voxelizer3d._MESHLIB_VOXEL_AVAILABLE and not watertight._MESHLIB_AVAILABLE,"MeshLib must be absent")
        require(metadata.version('voxcity')=='1.7.0' and metadata.version('voxcitygml')=='0.3.0',"engine version mismatch")
        origin=json.loads(metadata.distribution('voxcity').read_text('direct_url.json'))
        require(origin['vcs_info']['commit_id']==VOX_COMMIT,"VoxCity commit mismatch")
        source_evidence=Path(__file__).resolve().parents[2]/'docs/experiments/voxcitygml_p1/evidence/static_compatibility.json'
        expected=json.loads(source_evidence.read_bytes())['voxcitygml']
        require(expected['commit']==GML_COMMIT,"source audit commit mismatch")
        package_root=Path(voxcitygml.__file__).resolve().parent.parent
        require(all(sha(package_root/name)==h for name,h in expected['source_sha256'].items()),"installed VoxCityGML source differs from pinned audit")
        from ouem.komae_integration import voxcity_provenance
        engine=voxcity_provenance();require(engine['verified'],"VoxCity installed source RECORD/provenance mismatch")
        diagnostics['environment']=dict(python=sys.version.split()[0],packages={n:metadata.version(n) for n in ('voxcitygml','voxcity','numpy','numba','trimesh','pyproj','mapbox-earcut')},voxcity_commit=VOX_COMMIT,voxcitygml_commit=GML_COMMIT,meshlib=False)
        diagnostics['environment'].update(voxcitygml_source_files_matched=len(expected['source_sha256']),voxcity_provenance=engine)
        stages['ENVIRONMENT']='PASS'
        root,building=select_f(member);records=face_records(building)
        ET.ElementTree(root).write(output/'F-only.xml',encoding='utf-8',xml_declaration=True)
        archived=json.loads(Path(audit_report).read_bytes())
        old=next(b for b in archived['buildings'] if b['source_id']==SOURCE_ID)
        require(old['ouem_id']==OUEM_ID and all(f['mapping']=='VERIFIED' for f in old['faces']),"archived F mapping differs")
        require({r['polygon_id'] for r in records}=={f['polygon_id'] for f in old['faces']},"polygon ID population differs")
        with sqlite3.connect(Path(standard).resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
            rows=db.execute('SELECT ouem_id,source_lod,geometry FROM building WHERE source_id=?',(SOURCE_ID,)).fetchall()
        require(len(rows)==1 and rows[0][:2]==(OUEM_ID,2),"Standard ID/LoD differs")
        standard_faces=polygons(decode(rows[0][2]));mapping={f['polygon_id']:f['standard_face_index'] for f in old['faces']}
        triangles=[];vertices=[];offset=0;face_table=[];max_xy=0.
        for r in records:
            raw=np.array(r['rings'][0]['xyz']);closed=project(raw)
            target=np.array(standard_faces[mapping[r['polygon_id']]][0])
            alignment=align_ring(closed,target);max_xy=max(max_xy,alignment['max_XY_error_m'])
            v,f=geometry.parse_polygon_to_triangles(r['element'],NS)
            require(np.array_equal(v,raw[:-1]) and len(f)==len(v)-2,"triangulation changes/drops ring vertices or faces")
            metric=project(v);vertices.append(metric);triangles.append(f+offset)
            face_table.append(dict(polygon_id=r['polygon_id'],semantic=r['semantic'],rings=r['rings'],standard_alignment=alignment,triangle_indices=list(range(sum(len(x) for x in triangles[:-1]),sum(len(x) for x in triangles))),triangles=len(f),holes=0))
            offset+=len(v)
        meshes=extractors.extract_buildings_from_root(root,NS,prefer_lod=2,max_lod=2)
        require(len(meshes)==1 and meshes[0].feature_id==SOURCE_ID and meshes[0].attributes['lod']==2,"foreign building/LoD fallback")
        raw_vertices=np.vstack(vertices);faces=np.vstack(triangles).astype(np.int32)
        require(len(meshes[0].faces)==len(faces),"whole-building extractor face loss")
        key=lambda v,f:sorted(tuple(sorted(tuple(v[i]) for i in tri)) for tri in f)
        require(key(project(meshes[0].vertices),meshes[0].faces)==key(raw_vertices,faces),"whole-building extractor changed triangle geometry")
        stages['SOURCE_IDENTITY']='PASS';stages['VERTICAL']='PASS_SOURCE_H_PRESERVED'
        diagnostics.update(source_id=SOURCE_ID,ouem_id=OUEM_ID,face_table=face_table,
            coordinates=dict(raw='EPSG:6697 lat/lon/H',horizontal='EPSG:6668 -> EPSG:6677 XY only',engine='explicit projected metric XYZ; north-up rows, eastward columns',Z='absolute source H; no DEM or vertical transform',standard_max_XY_error_m=max_xy,XY_tolerance_m=XY_TOLERANCE),
            triangulated=mesh_stats(raw_vertices,faces))
        repaired=watertight.make_watertight_mesh(raw_vertices.copy(),faces.copy(),voxel_size=1.)
        diagnostics['repair']=dict(method=repaired.method,watertight=bool(repaired.is_watertight),stats=mesh_stats(repaired.vertices,repaired.faces))
        require(repaired.is_watertight and repaired.method=='merge',"repair escalated beyond explained merge; stop before voxelization")
        diagnostics['repair']['correspondence']=repair_correspondence(raw_vertices,faces,repaired.vertices,repaired.faces)
        stages['GEOMETRY']='PASS_WITH_DOCUMENTED_MERGE'
        lo=np.floor(raw_vertices.min(axis=0))-1;hi=np.ceil(raw_vertices.max(axis=0))+1
        gp=voxelizer3d.Grid3DParams(int(hi[1]-lo[1]),int(hi[0]-lo[0]),int(hi[2]-lo[2]),float(lo[0]),float(hi[0]),float(lo[1]),float(hi[1]),float(lo[2]),float(hi[2]),1.)
        voxels=np.zeros((gp.n_rows,gp.n_cols,gp.n_z),dtype=np.int8);trace=[]
        original_repair=voxelizer3d.make_watertight_mesh
        original_occupancy=voxelizer3d._voxelize_by_occupancy
        original_surface=voxelizer3d._voxelize_single_mesh
        def traced_repair(*args,**kwargs):
            wt=original_repair(*args,**kwargs);trace.append('repair:'+wt.method)
            require(array_sha(wt.vertices)==array_sha(repaired.vertices) and array_sha(wt.faces)==array_sha(repaired.faces),"voxel repair differs from diagnosed stage")
            return wt
        def traced_occupancy(*args,**kwargs):
            ok=original_occupancy(*args,**kwargs);trace.append('occupancy:'+str(ok));return ok
        def forbidden_surface(*args,**kwargs):raise RuntimeError('sealed surface fallback forbidden in this diagnosed F profile')
        before=(array_sha(raw_vertices),array_sha(faces))
        try:
            voxelizer3d.make_watertight_mesh=traced_repair;voxelizer3d._voxelize_by_occupancy=traced_occupancy;voxelizer3d._voxelize_single_mesh=forbidden_surface
            import numba
            prior=numba.get_num_threads();numba.set_num_threads(2)
            try:voxelizer3d._voxelize_building_solid(raw_vertices,faces,gp,voxels,-3,True)
            finally:numba.set_num_threads(prior)
        finally:
            voxelizer3d.make_watertight_mesh=original_repair;voxelizer3d._voxelize_by_occupancy=original_occupancy;voxelizer3d._voxelize_single_mesh=original_surface
        require(before==(array_sha(raw_vertices),array_sha(faces)) and (voxels==-3).any() and not events,"input changed, empty occupancy or forbidden side effect")
        for name,array in dict(triangulated_vertices=raw_vertices,triangulated_faces=faces,repaired_vertices=repaired.vertices,repaired_faces=repaired.faces,voxels=voxels).items():
            np.save(output/(name+'.npy'),array,allow_pickle=False);require(np.array_equal(np.load(output/(name+'.npy')),array),'NPY readback differs')
        stages['VOXEL']='PASS_MESH_ONLY'
        diagnostics['voxel']=dict(shape=list(voxels.shape),building_voxels=int((voxels==-3).sum()),grid=gp.__dict__,sha256=array_sha(voxels),trace=trace,DEM='NOT_USED; no ground substitute',network_attempts=events,land_cover_canopy_water='NOT_USED',API='voxcitygml.voxelizer3d._voxelize_building_solid (pinned low-level private API)')
        require(all(sha(p)==h for p,h in inputs.items()),"input file changed")
    except Exception as exc:
        diagnostics['error']=f'{type(exc).__name__}: {exc}'
        diagnostics['P1-1b_READY']='BLOCKED'
    else:diagnostics['P1-1b_READY']='CONDITIONAL_REVIEW_REQUIRED'
    diagnostics.update(scientific_validation='NOT_VERIFIED',formal_acceptance='NOT_VERIFIED',terrain_integration_ready=False)
    write(output/'geometry_diagnostics.json',diagnostics)
    write(output/'manifest.json',dict(profile=diagnostics['profile'],status='BLOCKED' if 'error' in diagnostics else 'COMPLETED_EXPERIMENTAL',inputs={Path(p).name:h for p,h in inputs.items()},commits=dict(voxcitygml=GML_COMMIT,voxcity=VOX_COMMIT),implementation_sha256=sha(__file__),outputs={p.name:sha(p) for p in output.iterdir() if p.is_file()},stages=stages,P1_1b_READY=diagnostics['P1-1b_READY'],scientific_validation='NOT_VERIFIED',formal_acceptance='NOT_VERIFIED',terrain_integration_ready=False))
    return diagnostics


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('member','standard','audit-report','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=run(a.member,a.standard,a.audit_report,a.output)
    print(json.dumps(dict(stages=result['stages'],error=result.get('error'),P1_1b_READY=result['P1-1b_READY'])))
    return int('error' in result)


if __name__=='__main__':raise SystemExit(main())
