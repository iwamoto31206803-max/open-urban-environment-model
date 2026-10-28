"""Test-only synthetic chain factory; CLI bytes are dummy identities, never executed."""
import xml.etree.ElementTree as ET
from pathlib import Path

from test_source_h_ingestion import plan as fixture_plan, db, blob, refresh, G, B
from ouem.native.building.source_h import ingest_source_h
from ouem.standardize.building.source_h import standardize_source_h
from ouem.native.building.provenance import SOURCE_H_PROFILE
from ouem.adapters.source_h_synthetic import FlatSyntheticTerrain


def build_chain(root):
    """Reuse the existing small synthetic chain; relocate its second authored box.

    Not the unchanged historical Converter-executed fixture. Its two IDs are
    retained as labels; synthetic_niigata is deliberately moved near the first
    box for this test, not a real Niigata dataset or measurement.
    """
    root = Path(root)
    plan = fixture_plan.__wrapped__(root)  # existing pytest fixture's pure factory
    xml = ET.parse(root/'raw.gml')
    ns = {'gml':G,'bldg':B}
    for building in xml.getroot().findall('.//bldg:Building',ns):
        if building.get('{'+G+'}id')=='synthetic_niigata':
            for pos in building.findall('.//gml:posList',ns):
                values = list(map(float,pos.text.split()))
                for i in range(0,len(values),3):
                    values[i] += 35.63-37.12
                    values[i+1] += 139.5703-138.28
                    values[i+2] -= 89.875
                pos.text = ' '.join(map(repr,values))
    xml.write(root/'raw.gml',encoding='utf-8',xml_declaration=True)
    all_xy = []
    with db(root/'converter.gpkg') as conn:
        for building in xml.getroot().findall('.//bldg:Building',ns):
            faces = []
            for surface in building.findall('bldg:boundedBy',ns):
                for polygon in surface.findall('.//gml:Polygon',ns):
                    rings = []
                    for pos in polygon.findall('.//gml:posList',ns):
                        values = list(map(float,pos.text.split()))
                        ring = tuple((values[i+1],values[i],values[i+2]) for i in range(0,len(values),3))
                        rings.append(ring)
                        all_xy.extend(p[:2] for p in ring)
                    faces.append(tuple(rings))
            conn.execute('UPDATE "bldg:Building" SET geometry=? WHERE id=?',
                         (blob(faces),building.get('{'+G+'}id')))
        conn.execute('UPDATE gpkg_contents SET min_x=?,min_y=?,max_x=?,max_y=?',
                     (min(p[0] for p in all_xy),min(p[1] for p in all_xy),
                      max(p[0] for p in all_xy),max(p[1] for p in all_xy)))
    refresh(plan,root,'raw');refresh(plan,root,'converter')
    ingest_source_h(plan,artifact_root=root)
    config = root/'area.yaml'
    # Authored 64x64m domain enclosing both entire boxes.
    bounds = (-23860.,-41025.,-23796.,-40961.)
    config.write_text('study_area:\n  id: synthetic-flat-25d\ncrs:\n  epsg: 6677\nextent:\n'
        f'  xmin: {bounds[0]}\n  ymin: {bounds[1]}\n  xmax: {bounds[2]}\n  ymax: {bounds[3]}\n')
    standard = standardize_source_h(profile=SOURCE_H_PROFILE,native_manifest='native-run/native.gpkg.manifest.json',
        artifact_root=root,output='standard-run/standard.gpkg',study_area_config=config)
    terrain = FlatSyntheticTerrain(bounds,1.,10.25,'EPSG:6695','gravity_related_height','metre',
        'Authored synthetic H=10.25m, declared same EPSG:6695 meaning as both synthetic Buildings; not survey evidence.')
    return standard,config,terrain
