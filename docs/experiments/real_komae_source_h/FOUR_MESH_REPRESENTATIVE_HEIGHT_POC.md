# Komae four-mesh LoD2 representative-height VoxCity PoC

調査・実行日: 2026-10-30 JST。基準main: `b9af043`（PR #133 merged）。
状態: 探索的な実データ技術PoC。正式Acceptance・既存Baselineの更新ではない。
Source-H eligibilityはNOT_ESTABLISHED、formal acceptanceはNOT_VERIFIEDのまま。

結果: **373棟の探索的3D Standard生成・独立検証を完了し、371棟が実1m格子のownerとなり、
300×400×30のBuilding/Terrain voxel生成を完了した**。残る2棟はAOI境界の部分支持が
precise採用閾値に届かず、Standardへ保持したまま欠落理由を記録した。
旧173棟の面/ring/XYZ/属性は同値だが、面順序の厳密一致とは区別する。

## 対象と責任分界

[Preflight](../../planning/OUEM_Komae_Mixed_LOD_Preflight_v0.1.md)で特定した4メッシュの
**LoD2のみ**を使用する。LoD1 fallbackやMixed-LODは実装していない。
[既存Source-H](README.md)のRaw照合・Native・Standard・独立Consumerを再利用する。
Standard Buildingは絶対Hを持つ3D面集合のまま、XYのみ6668→6677へ変換する。
Adapterの2D footprintと代表高さは派生物であり、Standardを平坦化・上書きしない。

既存runnerへの変更は明示的な`members`キーワード引数のみ。既存CLIの既定2メンバー、
LoD2 profile・検証・公開方法は不変。独立した
[`ouem.komae_four_mesh_poc`](../../../src/ouem/komae_four_mesh_poc.py)が4メンバーを固定指定する。
accepted AdapterのCLI・manifest whitelist・契約には変更しない。
新しい入口のprofileは`exploratory-komae-four-mesh-representative-height/v0.1`。

## 入力と実行領域

- Study Area: [komae_09LD3451.yaml](../../../config/study_areas/komae_09LD3451.yaml)、
  EPSG:6677、`[-23600,-40800,-23200,-40500]`、400×300m。
- 既存ZIP: `data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip`。
  1,192,172,043 bytes、SHA-256
  `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555`。
- 出典・取得条件: [2026-10-27取得記録](../voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md)。
  [公式配布](https://assets.cms.plateau.reearth.io/assets/6c/9c8c10-16b2-4a21-b971-c9330d4c20f4/13219_komae-shi_pref_2025_citygml_1_op.zip)、
  [CKAN](https://www.geospatial.jp/ckan/dataset/plateau-13219-komae-shi-2025)。今回は再取得・規約再照会なし。
- Converter: 固定nusamai 0.1.19 / `ce7766df9788ce391b149c55df16d33082d0bc72`。
  binary SHA `0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b`。
  `--sink gpkg --epsg 6697 -t use_lod=lod2`、split_components=False。
- Terrain: `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif`。
  SHA `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a`。
  800×600 / 0.5mの既存source-declared T.P.標高。
  [A2出典訂正](../../acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)で
  追跡された既存再現成果物を読取使用し、旧A3の凍結Terrain bytesと同一とは主張しない。
- 比較用173棟: `data/work/real-komae-source-h/run-20261028-04/standard/standard.gpkg`。
  SHA `a23829bbcb689a3e830535b7654f0c5b892554b0ad26e0222eaf146e5b9aca3c`。
- 新規Run parent: `data/work/real-komae-source-h/`。既存Runへの上書き・再開は不可。

| ZIP内 udx/bldg/ メンバー | SHA-256 |
|---|---|
| 53393455_bldg_6697_op.gml | `07245d14727d83c769a7809e3b135bf651ace6c3a18293b35c6a7ffe33b45b1f` |
| 53393456_bldg_6697_op.gml | `eaff3868a122e28e8c23810a45165675591ddfa72e1077a1948aa04bd0d89c30` |
| 53393465_bldg_6697_op.gml | `32f8912b2c3f8b09a2c76211b8ea22c9402f5b1357d36843dcfd5c93616ff613` |
| 53393466_bldg_6697_op.gml | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |

## モデルと格子

現在のAdapter helperを再利用し、正面積XY面のrepair/union、EPSG:4326境界変換、
必要時のpost-CRS repair、決定的numeric ID、`maxZ-G_eff_abs`と`min_height=0`を維持する。
独立Consumerの実行後、検証した入力群をWatchで再bindし、消費後にも不変性を確認する。
Terrain manifest/hash/宣言とVoxCity metadata pinを確認してからengineをimportする。

旧A3 workerは建物群の外接範囲でrectangleを作る。今回は指示どおり**Study Areaの4隅**を
6677→4326へ水平変換してrectangleにする。過去と同じ格子原点・セル配列であるとは扱わない。
1mはVoxCityのnominal meshsize。実寸調整値、uv軸、shapeはローカルreportへ記録する。
GeoTIFF DEMはVoxCityの公開rasterizer（dem_interpolation=False）で実engine格子にサンプリングする。
Standard Terrainの作り直しではない。

precise rasterizer（overlapping_footprint=True）の実ownerセルの**raw DEM平均**から
各棟のheightを求め、最大8回でowner-gridの収束を確認し、最終heightでも再rasterizeする。
同一セルに複数segmentがあってもID gridは単一owner、voxelの-3には個体IDがない。
従ってowner IDとsegment/roof envelopeの診断を分ける。
ゼロowner棟はG_effを推定せず理由を記録し、Standardに保持したまま次engine passから除外する
探索的方針である。既存accepted Adapterのゼロowner時エラー仕様は変更しない。
欠落を小面積・境界・競合のどれかと自動断定しない。

Voxelizerにはbareland=1、tree=0の最小入力を与える。樹冠、日射、GVIは対象外。
標準のground+1セルと高さの丸めを変更せず、roof envelope誤差は診断値として記録する。
測量精度、鉛直datum realization、物理的な屋根高の正しさを検証するものではない。

## 再現手順

普通のWindows terminalでOUEM venvを明示する。QGIS/OSGeo4W child runtimeは使用しない。
固定binaryは既存手順どおりOUEM外に配置し、artifact-rootで追跡する。
新規run名に置換する。既存directoryへの実行は失敗する。

```powershell
.venv/Scripts/python.exe -m ouem.komae_four_mesh_poc `
  --artifact-root C:/dev `
  --run-dir data/work/real-komae-source-h/<new-four-mesh-run> `
  --zip data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip `
  --converter C:/dev/plateau-gis-converter/target/x86_64-pc-windows-msvc/release-lto/nusamai.exe `
  --terrain data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif `
  --study-area config/study_areas/komae_09LD3451.yaml `
  --previous-standard data/work/real-komae-source-h/run-20261028-04/standard/standard.gpkg
```

Raw取得の代わりに既存ZIPから4メンバーとcodelistsだけを新Runへ抽出する。
作業領域にはConverter logs/run receipt、plan/evidence、Native/Standardとmanifests/receipts、
Consumer結果、入力SHA・不変性とTerrain診断を含む`report.json`を保存する。
VoxCity段階は別の`voxcity/report.json`に記録する。Raw→StandardのCOMPLETEDだけで
VoxCityも完了したとは判断しない。
`voxcity/`の出力はbuildings.geojson、building_ids.npy、heights.npy、terrain_H.npy、
effective_dem.npy、voxels.npy、segments.json、multi-segment-cells.json。
NPYはengineのuv配列であり、GIS row/columnへ無断transposeしていない。
実データ・生成物はGit管理外。生成3D配列は別のID gridとmappingを併用する。

## 実行結果・検証

### Raw → Native → Standard

4メンバー全体のLoD2は12,332 ID（Raw全Building 12,847のうちLoD1-only 515を除く）。
ConverterとNativeは各12,332行、AOI交差選択後のStandardは373行。
AOI内訳はmesh55=89、56=53、65=111、66=120。
境界建物は3D全形状を保持し、AOIでgeometryをclipしていない。
Source-Hの厳密検証は面・ring・XYZ・ID照合、NativeへのBLOB保持、XY変換とHの完全保持、
AOI選択、独立Consumer検証を実施する。CityGML全XSD・manifold性・測量精度の検証ではない。

### 実行環境

ordinary OUEM venv Python3.11.9 / Windows10.0.26300 AMD64。
NumPy2.4.6、GeoPandas1.2.0、Shapely2.2.0、PyProj3.7.2、Rasterio1.4.4、
SciPy1.17.1、Numba0.68.0、VoxCity1.7.0。依存更新なし、GIS Pythonとの統合なし。
環境snapshotは`data/work/four-mesh-runtime-20261030.json`。

### 実行試行と制限

`run-four-mesh-20261030-01`はNativeの検証後のhardlink公開でWinError5となりFAILED。
input_unchanged=true。失敗Run/report/logを保持した。公開の原子性や検証を緩める実装変更はしない。
同じ入力を新しい`run-four-mesh-20261030-02`で通常実行権限により再試行した。
初回はStandard/VoxCity未実施であり、成功回数には含めない。



`run-four-mesh-20261030-02`のRaw→StandardはCOMPLETED、独立ConsumerはPASS。
373棟、71,824頂点。NativeのID/XYZ/構造順序/BLOB保持とRaw LoD2対応がPASS、
StandardのH exact（許容差0）・構造/順序/ID/属性・独立XYがPASS。
独立XY最大誤差は0m（既存検証許容差1e-7m）。入力不変性true。
Raw→Standardの実測wall timeは669.03秒（11:18:35.994→11:29:45.027 UTC）。
Terrain診断は全形状の部分被覆56棟、TOP_BELOW_DEM=0、BOTTOM_OFFSET_OVER_3M=0。
後者3mは既存の探索的flagであり、Acceptance許容差ではない。

同RunのVoxCity段階は旧173棟とのordered-tree比較で停止した。
調査では173/173棟の**面の並び順**が異なったが、面ごとのring構造/順序/全XYZの
multiset（重複数を含む）と属性、外側geometry typeは173/173棟で完全一致した。
点集合だけの一致や2D equalsで代用していない。Converter再実行間の表現順序差として記録し、
どの内部処理が順序を変えるかは追跡していない。Native→Standardの同一Run内の
厳密な順序保持検証は変更していない。既存173棟のファイル/受入記録も変更していない。
この停止RunはVoxCity成功に数えない。

Cross-run比較はordered差と上記の完全な面/ring/XYZ差を別々に報告するようにし、
座標袋が同じでもring接続が変わった場合をFAILとするテストを追加した。
`run-four-mesh-20261030-03`は`--prepared-standard-run`により-02のStandardを読取再利用し、
新しい出力領域で独立Consumer/Watch/hashを再検証する。source-reference.jsonが
元reportをSHAで結び、Native/Standardや失敗したvoxcity/reportを上書きしない。
再現時は前掲コマンドのrun名を変更し、必要なら以下を追加する。

```powershell
--prepared-standard-run data/work/real-komae-source-h/run-four-mesh-20261030-02
```

## 旧111棟・173棟との比較の限界

旧173棟は同じ2025配布物の東側2メンバーであり、Source IDを主キーに比較する。
373棟化でnumeric IDが再採番され得るため、古いID gridの数値を同じ建物の識別子とは扱わない。
旧111棟は[A3受入記録](../../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)の
凍結成果物で、当該GPKGはこの環境に現存せず、全ID/形状/H/格子の直接比較は未実施。
記録上は111/111 ID保持・1mの代表高さvoxel化が受入済みであるが、今回373棟の成功を
そこへ加算せず、同じ入力版・格子原点・評価範囲とも仮定しない。
一部mesh65の件数111が一致することだけで同一データとは認定しない。

## 次のMixed-LODへの示唆

本PoCはLoD2のみであり、LoD1 readerやfallback、Mixed-LODのNative/Standard/Consumerを
検証したことにはならない。次工程では選択profile・欠損/壊れたLoD2の扱い・Solid対応・
LoD/ID/Hのprovenanceを明示し、LoD1/LoD2/両方/欠損の合成fixtureから検証する。
今回の面順序差も、同一Run内の保持と再実行間の同値性を区別する必要性を示す。
高さ分布モデル、樹冠、日射/GVI、測量・写真比較、鉛直精度、正式Acceptanceは対象外のまま。


## VoxCity実測結果（run-four-mesh-20261030-03）

状態COMPLETED、Consumer再検証PASS、input_unchanged=true。
同じface/ring/XYZ/属性の旧173棟がすべて含まれ、追加200 ID。
ordered-record差は173件、形状/ring/XYZ/属性差は0件。
再検証・rasterize・voxelize・出力を含むこの段階のwall timeは**207.31秒**。
この値をVoxelizer単体の処理時間とは解釈しない。

| 項目 | 実測 |
|---|---:|
| Standard / grid owner / ownerなし | 373 / 371 / 2 |
| engine grid (u, v) | 300 × 400 |
| voxel grid (u, v, up) / dtype | 300 × 400 × 30 / int8 |
| nominal mesh / adjusted horizontal mesh | 1m / 1.0000930367, 1.0000931727m |
| ownerセル数 | 35,861 |
| Building (-3) voxel数 | 316,734 |
| 地下 (-1) / bareland (1) / air (0) | 495,582 / 120,000 / 2,667,684 |
| TREE (-2) voxel | 0（入力なし） |
| height 最小 / P05 / 中央値 | 1.896585 / 2.365392 / 7.596099m |
| height P95 / 最大 | 10.275477 / 23.495370m |
| raw engine DEM 最小 / 最大 | 19.586000 / 25.266001m H |
| `ground_eff_abs+height-maxZ` 最大絶対差 | 0m（371棟） |
| ownerごとBuilding voxel数>0 | 371 / 371 |
| 背景ID=0セル内のBuilding voxel | 0 |
| 複数segmentセル / 関係する建物ID数 | 43 / 43（各セル最大2棟） |

uvはapproximately north / eastで、通常のGIS north-up row/columnとは異なる。
origin lon/latは`[139.5727665710906,35.631966761568215]`。
cell centreは`origin+(i+0.5)*du*u_vec+(j+0.5)*dv*v_vec`。
ベクトル・rectangle・実寸調整はvoxcity/report.jsonに保存した。
元Terrainは600行×800列、480,000/480,000有効、NoData=0。
engine gridは同じRasterそのものの配列コピーではなく、その格子への公開APIによるサンプルである。

bootstrap → 実height → owner安定の3回と、最終heightでの再rasterizeを実行した。
各回ownerは371、最初だけownerなし2。以後のowner-gridは収束し、最終再rasterizeでも一致した。
371棟のheightはすべて正。`process_grid`の平坦化地盤とraw owner DEM平均の対応も確認した。
地盤平均との差による元のbottom H offsetは、相対heightの補正には使っていない。

### ownerを持たない2棟

| source_id | 今回numeric ID | 全footprint / AOI交差面積(m²) | 単独ownerセル | 最大cell交差率 |
|---|---:|---:|---:|---:|
| bldg_a43dc7f6-88e5-499f-a9a7-707fd434fd4b | 173 | 196.210706 / 0.333804 | 0 | 0.2932108841 |
| bldg_14cc3f2e-58e4-4837-8693-f81476fe8bfc | 298 | 49.751295 / 0.008214 | 0 | 0.0064828561 |

1件目は西端、2件目は北端で、全体が小建物だから落ちたとは扱わない。
同じrectangle/precise APIへ各棟を単独投入しても0セル。
engine geometryに対し、bbox周辺の実cell polygonとShapelyで交差率を計測した。
固定版`buildings_precise.py`の採用条件はcell面積比 **>0.3** であり、両棟は届かない。
他棟との所有競合だけで消えたものではなく、AOI境界の小さな平面支持とセル採用閾値が
原因と整合する。欠落を隠すための拡張AOI・閾値変更・resolution変更は行わない。
両棟のheight/G_effは算出せず、null相当のmissing診断として残した。
373棟すべての正height・voxel反映が成功したとは主張しない。

### 所有競合・roof envelope

43複数segmentセルで、実cellと各footprintの交差率>0.3から参加IDを再計測した。
全セルで参加数とsegment数が一致し、owner IDは参加集合内だった。
ID gridは単一値であり、複数segmentのどれかをすべて同じ建物に帰属させない。
-3 voxelにも建物IDはないため、per-owner voxel数はそのownerセル内の総Building数であり、
各segment由来の個体別体積の証明ではない。

cell roof envelopeは`D0+effective_dem+max(segment top)`と、-3の最上セルの名目上端
`D0+k_max+1`を比較した。絶対誤差の中央値1.003820m、P95 1.577161m、最大1.877490m。
これは既存Voxelizerのground+1層とroundingを含む診断値で、Z補正・改善や測量精度の証明ではない。
今回のCOMPLETEDは処理完了を意味し、Formal Acceptanceの新しい誤差条件ではない。

### 保存物の同一性

| 保存物 | SHA-256 |
|---|---|
| -02 Native GPKG (111,562,752 bytes) | `aa96cfad953abb044dd5521b2e5eec54aec9fd09167d5ef2d0ddf4793a7926c4` |
| -02 Standard GPKG (2,330,624 bytes) | `2c8f46374a1ec41ecc31bca44e622466d9a1797daf49a934ead354f8d39ef97a` |
| -03 voxcity/report.json | `5f3b9be6a6229f01235bba8dddd1feb1703006ebd91e5b93197e7d4b696b48d0` |
| -03 voxcity/voxels.npy (3,600,128 bytes) | `9054ecc6c8cf0d328ec0ba2e46e245b5c47c31458af3b975eb20af3819f39581` |

全配列・GeoJSON・segmentsのhashはlocal report、multi-segment/reportを含めた追加一覧は
`data/work/four-mesh-post-diagnostics-20261030.json`に保存した。
追加診断scriptは`data/work/four-mesh-post-diagnostics-20261030.py`、SHA
`e35b6cdb50181d9cb6149292dc2100ab1ecd08ddc53415b3aca34fd321b3b686`。
そのJSONのSHAは`6498f61ea52e63025003db8eb34c9bb9f9ce77fe816579852d8b1f59a5d27139`。
所有競合の各cell/参加IDは`data/work/four-mesh-cell-competition-20261030.json`。
既存保護対象9ファイル（ZIP、旧GML、旧Converter/Native/Standard/report、Terrain、設定）は
Preflight時のhashと終了時も一致した。旧RunのmtimeやAcceptanceを更新していない。

## 検証結果と残る制約

旧173 IDのうち今回のownerは172、北端の`bldg_14cc3f2e-58e4-4837-8693-f81476fe8bfc`は
前掲の境界欠落となった。旧173棟のStandard保存と今回の格子残存数は別の数である。
新規追加200 IDのうちownerは199。旧173棟でengineがどうなっていたかを再実行したものではない。

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_komae_four_mesh_poc.py tests/test_real_komae_source_h.py
.venv/Scripts/python.exe -m pytest -q -ra tests/test_building_provenance.py tests/test_source_h_xlink.py tests/test_source_h_ingestion.py tests/test_source_h_standard.py tests/test_source_h_consumer.py tests/test_voxcity_adapter.py tests/test_voxcity_post_crs_repair.py
.venv/Scripts/python.exe -m pytest -q -ra
```

- 最終の追加・変更テスト: **13 passed / 3 warnings / 1.72秒**。
  2/4メンバー指定、owned DEMだけからのheight、ゼロowner、負height拒否、XYZ/ring接続検査、
  面順序差、Consumer失敗記録、既存出力拒否、prepared Run読取参照を検証。
- 関連既存テスト: **269 passed / 1 warning / 64.32秒**。
- 全体pytestの最初のsandbox実行: **1 failed / 1092 passed / 10 skipped / 336 warnings / 914.13秒**。
  既存`test_cli_prints_path_and_areas`のGDAL一時GPKG作成がunable to open database file。
  通常権限で同じテストは1 passed（7.90秒）。失敗を成功へ読み替えずログを残した。
- 最終本番コードでの通常権限の全体pytest: **1095 passed / 10 skipped / 336 warnings / 520.27秒**。
  全体collection後に追加したprepared-runテスト1件は前掲13件のtargeted実行に含む。
  skipはGIS/QGIS専用Python未指定5件とWindows symlink権限5件。
  warningsは既存Rasterio/Matplotlibのdeprecation、Agg非対話表示、stat/fstat ctime診断。
- ログ: `data/work/four-mesh-{related-tests,full-pytest,full-pytest-normal}.log`。
  文書リンク/相対path、付録と実行scriptの一致、差分範囲、`git diff --check`を確認。

QGIS GUI確認、旧111棟の直接再比較、独立したdatum/測量精度、LoD1/Mixed-LOD、
高さ分布、日射/GVI実データ、科学的妥当性、Formal Acceptanceは未実施。
既存Source-Hのeligibility/gates・Standard契約・accepted Adapter whitelist・Acceptanceは不変。
preparedモードではzip/converter引数で再変換せず、参照Runに記録されたchainを再検証して用いる。
このbounded入口はKomaeの373棟・指定AOI向けであり、一般的な自治体CLIへ昇格させていない。

## 付録: 追加の読取診断の再現

以下はlocal診断scriptの実行内容そのもの。完了Runには書き込まず、新しいJSON名へ変更して再実行する。

```python
"""Read-only supplemental QA of completed four-mesh PoC outputs."""
import json
from pathlib import Path
import numpy as np
import geopandas as gpd
import rasterio
from shapely.geometry import box
from ouem.adapters import voxcity as a
from ouem.real_komae_source_h import digest
from voxcity.geoprocessor.raster import create_building_height_grid_from_gdf_polygon as raster
from voxcity.geoprocessor.raster.core import compute_cell_center_coords, create_cell_polygon
root=Path("data/work/real-komae-source-h")
out=root/"run-four-mesh-20261030-03/voxcity"
r=json.loads((out/"report.json").read_text(encoding="utf-8"))
b=gpd.read_file(root/"run-four-mesh-20261030-02/standard/standard.gpkg",layer="building")
aoi=box(-23600,-40800,-23200,-40500)
original_ids=b.ouem_id.tolist()
qa={"boundary_crossing_buildings":0,"missing":[],"output_hashes":{p.name:digest(p) for p in out.iterdir() if p.is_file()}}
for row in b.itertuples():
    fp,_=a.build_normalized_footprint(row.geometry,row.ouem_id)
    qa["boundary_crossing_buildings"]+=int(not aoi.covers(fp))
geom=compute_cell_center_coords(r["rectangle_vertices_lonlat"],1.)
for missing in r["missing"]:
    sub=b[b.ouem_id==missing["ouem_id"]].copy()
    oid=missing["ouem_id"]
    fp,stats=a.build_normalized_footprint(sub.geometry.iloc[0],oid)
    sub=a._set_normalized_footprints(sub,{oid:(fp,stats)})
    sub["id"],sub["height"],sub["min_height"]=missing["voxcity_id"],1.,0.
    sub=a._to_voxcity_building_crs(sub)
    sub,_=a._repair_post_crs(sub,{oid:(fp,stats)})
    _,_,single_ids,_=raster(sub,1.,r["rectangle_vertices_lonlat"],overlapping_footprint=True)
    g=sub.geometry.iloc[0]
    xmin,ymin,xmax,ymax=g.bounds
    margin=2*(np.abs(geom["u_vec"])+np.abs(geom["v_vec"]))
    candidates=((geom["lons"]>=xmin-margin[0])&(geom["lons"]<=xmax+margin[0])&
                (geom["lats"]>=ymin-margin[1])&(geom["lats"]<=ymax+margin[1]))
    fractions=[]
    for i,j in np.argwhere(candidates):
        cell=create_cell_polygon(geom["origin"],int(i),int(j),geom["adj_mesh"],geom["u_vec"],geom["v_vec"])
        fractions.append(g.intersection(cell).area/cell.area)
    qa["missing"].append(dict(**missing,footprint_area_m2=float(fp.area),
        aoi_intersection_m2=float(fp.intersection(aoi).area),footprint_bounds=list(fp.bounds),
        single_building_owned_cells=int((single_ids==missing["voxcity_id"]).sum()),
        max_candidate_cell_intersection_fraction=max(fractions,default=0.)))
ids=np.load(out/"building_ids.npy",allow_pickle=False)
vox=np.load(out/"voxels.npy",allow_pickle=False)
qa["background_building_voxels"]=int((vox[ids==0]==-3).sum())
qa["occupied_cells"]=int((ids>0).sum())
qa["owner_count"]=int(len(set(ids.ravel())-{0}))
with rasterio.open("data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif") as dem:
    grid=dem.read(1,masked=True)
    qa["source_dem_valid_cells"]=int(grid.count())
    qa["source_dem_nodata_cells"]=int(np.ma.getmaskarray(grid).sum())
    qa["source_dem_shape"]=list(grid.shape)
qa["standard_unmodified"]=b.ouem_id.tolist()==original_ids
path=Path("data/work/four-mesh-post-diagnostics-20261030.json")
with path.open("x",encoding="utf-8") as f:json.dump(qa,f,indent=2,allow_nan=False)
print(json.dumps({k:v for k,v in qa.items() if k!="output_hashes"},indent=2))
```
