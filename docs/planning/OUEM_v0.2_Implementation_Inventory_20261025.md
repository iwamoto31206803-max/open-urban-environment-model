# OUEM v0.2 実装インベントリ（2026-10-25）

## 1. 調査基準と読み方

調査基点はmain `526cd57fa7f5ecf2aa78dca59a82c08342f8e77f`。[Concept & Architecture v0.2](../OUEM_Concept_Architecture_v0.2.md)を要求の基準とし、追跡対象のsrc / scripts / config / testsと文書を静的調査した。実行テスト、実データの取得・生成・加工、個人PC上の入力ファイルの存在確認は実施していない。以下のテスト欄は対応する既存テストを示し、今回の合格結果ではない。

文書の正式登録、コードの存在、合成テスト、実データ受入は別の軸である。v0.2は上位概念設計であり、現行Standard / Adapter契約と受入記録を自動変更しない。設計決定01〜36と未決事項は変更しない。構築プロファイルA1/A2/A3と実装工程A1 Building / A2 Terrain / A3 Adapterは別体系である。

| 状態 | 本文での意味 |
|---|---|
| Implemented | 記載した限定機能の実装がある。受入・全国適用を意味しない |
| Partial | v0.2要求の一部、特定入力、PoC経路のみを実装 |
| Not Implemented | 調査した追跡コードに該当処理がない。空のnamespaceや上流エンジンの存在は実装に数えない |
| Unverified | 実装・資料はあるが、当該性質を確定する実データ・証拠が不足 |

優先度は本調査の**推奨・未承認**。P0は個人PC再実行の前提、P1は樹冠／B1/B2移行前、P2は一般化時。順序の提案であり契約の確定ではない。

## 2. 現行契約と受入の台帳

| 記号 | 根拠 | 確認できる範囲／限界 |
|---|---|---|
| C-B | [Standard Building v0.1](../OUEM_Standard_Building_v0.1.md) | PROVISIONAL。絶対T.P. Z、狛江EPSG:6677、3D形状、5メタデータ項目 |
| C-T | [Standard Terrain v0.1](../OUEM_Standard_Terrain_v0.1.md) | PROVISIONAL。EPSG:6677・Float32・north-up、既存格子保持、NoData -9999、鉛直根拠は別管理 |
| C-A | [VoxCity Adapter v0.1](../OUEM_VoxCity_Adapter_v0.1.md) | VoxCity 1.7.0固定。2D footprint、相対高さ、数値ID、precise rasterization、条件付きpost-CRS repair |
| E-B | [Building受入](../../experiments/a1_e2e_pilot/README.md) | Native 3,637棟→交差選択Standard 111棟、Z差0、QGIS確認。全自治体への互換性を証明しない |
| E-T | [A2正式受入 2026-10-06](../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md) | 09LD3451、800×600、0.5 m、全480,000セル有効、source-declared T.P.、入力／出力hash |
| E-A | [A3正式受入 2026-10-05](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md) | 固定入力111棟、1 mボクセル生成までACCEPTED。屋根誤差最大1.7814643352673158 m、許容2 m。入力hashは記録なし |
| E-C | [contained E2E 2026-10-18](../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md) | 92棟、2反復、レビューPASS within reviewed evidence。artifact acceptanceはPENDING_LOCAL_REVIEWのまま。当該出力のQGIS目視は未実施 |
| E-V | [建物鉛直診断](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md) | UNRESOLVED。CityGML→Converterの数値変化と原因を区別。約37 mずれは仮説 |
| E-H | [樹冠エンジン調査](../research/OUEM_VoxCity_1.7.0_Canopy_Contract_Verification.md) | pinned sourceと合成配列の検証。CHM／狛江実データの受入ではない |
| E-PC | [GEEKOM A6環境記録](../development/OUEM_Windows_Development_and_Remote_Setup_20261025.md) | 環境のみscope-limited ACCEPTED。400 passed / 5 skipped / 128 warnings等は過去記録。個人PCの実データE2Eは未実施 |

[Phase A実装設計](../Phase_A_Implementation_Design_v0.1.md)はCurrent-status noteを先に読む。歴史的なpending記述だけで未実装と判定しない。

## 3. ライフサイクルと空間基準の対応

表内のコード・テストパスはリポジトリルート相対。関数名は現行実装の追跡点である。

| 要求／v0.2節 | 実装ファイル・関数・CLI | 対応テスト | 受入・検証範囲 | 状態 | ギャップ | 推奨対応・優先度 |
|---|---|---|---|---|---|---|
| 元データ取得 §2,6 | `src/ouem/acquire/__init__.py`はnamespace。Converter GUIは外部手動 | 専用取得テストなし | E-B/E-Tは取得済み入力が前提 | Not Implemented | Source Catalog、ダウンロード／解凍recipe、ライセンス証拠がない | 取得元・版・条件を先に確認 P0。自動取得は任意 P2 |
| Raw→work→Native Building §2 | `src/ouem/native/building/plateau.py::ingest_converter_geopackage`、`_plateau_gdal_worker.py::_ingest`、`ouem-plateau-buildings`。`scripts/work/plateau_komae_local_acceptance.cmd` manual/gis/ouem | `tests/test_plateau_building.py`, `test_runtime.py` | E-B：3,637棟、Z付き形状・属性・CRS・QGIS | Partial | Converter操作はOUEM外。Rawからの変換履歴・鉛直操作の記録が不足。汎用providerなし | 手動設定と入力同一性を記録 P0 |
| Raw→Native Terrain §2 | `src/ouem/native/terrain/__init__.py::inspect_dem, accept_native_terrain, load_native_manifest`、`ouem-accept-terrain` | `tests/test_standard_terrain.py`（hash改変検出、鉛直根拠） | E-T：元TIFFをhashで参照するmanifest受入 | Implemented | データを複製しない限定経路。汎用Native LiDAR派生処理はない | 元TIFFとmanifestを一組で再作成 P0 |
| Native→Standard Building §2,4.2 | `src/ouem/standardize/building/__init__.py::standardize_native_buildings, deterministic_ouem_id`、`_gdal_worker.py::_horizontal_transform, _restore_z, _run`、`ouem-standardize-buildings` | `tests/test_standard_building.py`（intersection/no clipping、ID、horizontal-only、Z） | C-B/E-B：3,637→111、Z保持、UUIDv5 | Implemented | 現行契約の範囲のみ。v0.2の全建物表現や他CRSは未対応 | 既存結果を回帰基準として保持 P0 |
| Native→Standard Terrain §2,3 | `src/ouem/standardize/terrain/__init__.py::validate_terrain_input, standardize_native_terrain`、`ouem-standardize-terrain` | `tests/test_standard_terrain.py`（grid/value保持、NoData、決定性） | C-T/E-T | Partial | EPSG:6677 Float32入力のみ。再投影・再サンプルせず入力全格子を保持。AOI cropや共通1 m格子ではない | 0.5 m原格子を変えず再実行 P0。汎用仕様は別途検討 P2 |
| Standard→Adapter→engine §2 | `src/ouem/adapters/voxcity/__init__.py::adapt_standard_to_voxcity, _run_voxcity_grids, build_normalized_footprint, _repair_post_crs`、`ouem-adapt-voxcity`、`scripts/work/voxcity_komae_a3_acceptance.py` | `tests/test_voxcity_adapter.py`, `test_voxcity_post_crs_repair.py`, `test_komae_repair_acceptance.py` | C-A/E-A/E-C。2D GeoJSON EPSG:4326、正数ID、height/min_height、manifest | Partial | 建物・地形の限定Adapter。汎用engine interfaceやCFD未実装 | 固定VoxCity pin・precise経路・修復診断を維持 P0 |
| 統合・work境界 §2,6 | `src/ouem/komae_integration.py::run, input_paths, verify_inputs`、`scripts/work/run_komae_contained_e2e.cmd` | `tests/test_komae_integration.py`, `test_komae_contained.py` | E-C：独立2反復。既存Nativeを入力、ingestは再実行しない | Partial | work内の隔離PoCはCurrentへの昇格ではない。MODEL/OUTPUT一般管理はnamespace中心 | 新run IDを用い既存証拠を保全 P0 |
| 水平CRS §3 | `src/ouem/study_area.py::load_study_area`、Building horizontal transform、Adapter `_to_voxcity_building_crs` | `tests/test_study_area.py`, `test_standard_building.py`, `test_voxcity_adapter.py` | 狛江EPSG:6677→engine EPSG:4326 | Partial | 地域別CRS選定、CRS境界AOIは未実装・未決 | 他地域を狛江設定だけで処理しない P2 |
| 鉛直意味と互換性 §3,8.1 | Adapter `check_vertical_compatibility, derive_attributes`。`src/ouem/komae_vertical_provenance.py`, `komae_height_diagnostics.py`, `komae_vertical_exploratory.py` | `tests/test_voxcity_adapter.py`, `test_standard_building.py`, `test_standard_terrain.py`, `test_komae_vertical_provenance.py`, `test_komae_height_diagnostics.py`, `test_komae_vertical_exploratory.py` | E-BはNative以降のZ保持、E-Tはprovider宣言、E-Aはengineとの不変式。E-Vは原因未確定 | Unverified | NativeのEPSG:4979ラベルとアプリ上のT.P.解釈、Converterの数値操作を独立検証できていない。2024成果への変換なし | 元CityGMLとConverter設定・同一地物全Zを照合 P0。定数差引やCRS付替えはしない |
| AOI・範囲・buffer §3 | `study_area.py`の矩形YAML、Adapter `--aoi XMIN YMIN XMAX YMAX`、`komae_integration.py::coverage`、`komae_contained.py::select, validate_selection` | `tests/test_study_area.py`, `test_komae_contained.py`, `test_komae_integration.py` | E-Bは交差111棟、E-Cはcoversで92棟／19棟除外 | Partial | 任意GPKG/GeoJSONポリゴン、工程別buffer/crop、入力・解析・出力AOIの一般管理なし。contained選択は19棟問題の一般解ではない | 再実行対象が111か92か明示 P0。AOI設計は別途 P1 |
| 3次メッシュ管理 §3,6 | `config/study_areas/komae_09LD3451.yaml`に400×300 m矩形。メッシュ割当処理は見当たらない | 専用テストなし | 09LD3451はDEM識別子。3次メッシュ所属を証明しない | Not Implemented | セル中心帰属、建物代表点、樹冠分割・再結合、メッシュ更新なし | DEM番号と3次メッシュを混同しない。規則候補を別途検討 P2 |
| 共通ラスタ配置 §3,8.3 | Terrainは入力格子保持、`src/ouem/komae_canopy.py::convert_chm`はengine実セル中心でnearest sampling | `tests/test_standard_terrain.py`, `test_komae_canopy.py`（回転格子・位置合わせ） | E-Tの0.5 m、E-Hのengine配列。実CHM整合受入なし | Partial | 地域／解像度ごとの共通原点規則はない。1 mはPoC engine設定でStandard確定値ではない | 原格子・engine格子・未決標準格子を区別 P1 |

## 4. レイヤー・品質・運用・Phase Bの対応

| 要求／v0.2節 | 実装ファイル・関数・CLI | 対応テスト | 受入・検証範囲 | 状態 | ギャップ | 推奨対応・優先度 |
|---|---|---|---|---|---|---|
| 建物のPrimary/Derived・根拠 §4.1–4.2 | C-Bの詳細3D、`deterministic_ouem_id`と5属性。Adapter footprintは派生 | `tests/test_standard_building.py`, `test_voxcity_adapter.py` | E-B/E-A。measured_heightはnullableコピーでheightの代替ではない | Partial | 代表高さ／高さ分布の併存、上端絶対Z raster、A3点群＋外周線モデル、根拠分類なし | 高さ疑義の解消前に表現変更しない P0。別表現は将来仕様 P2 |
| 地形・欠損 §3,4.1 | `native/terrain::inspect_dem`、`standardize/terrain`のmasked値とNoData正規化、integration coverage | `tests/test_standard_terrain.py`, `test_komae_contained.py`（NoDataでblock） | E-TはNoData 0。補間受入ではない | Partial | 共通DEM融合・欠損補完Derived・補完maskなし | 欠損をゼロ標高へ変換しない P0。補間規則を勝手に追加しない |
| 樹冠Standard §4.3 | `src/ouem/native/canopy/__init__.py`, `standardize/canopy/__init__.py`, `model/canopy/__init__.py`はnamespaceのみ | 正式樹冠Standardのテストなし | 正式契約・受入記録なし | Not Implemented | polygon＋絶対上端Z／下端Z、観測／推定根拠、汎用mesh、ID／欠損仕様なし | PoC配列をStandardと呼ばない。契約候補レビュー P1 |
| Meta CHM opt-in PoC §4.3,7 | `src/ouem/komae_canopy.py::validate_provenance, convert_chm, scenario_arrays`、`scripts/work/run_komae_meta_chm_e2e.cmd` | `tests/test_komae_canopy.py`、`test_real_pinned_engine_overlap_and_component_preservation`等 | E-Hは合成engine実験。実データformal canopy acceptanceなし | Partial | HAG入力をengineへ渡す限定経路。3 m閾値・bottom=0.4×topはPoC固定値でCRの検証済み係数ではない。Standard絶対Z／polygon経路なし | 出所・hash・HAG証拠と全セル有効性を確認、別runで評価 P1 |
| 樹冠可視化 §4.3,5 | `src/ouem/komae_canopy_qgis_export.py`、`scripts/work/export_komae_canopy_qgis.cmd` | `tests/test_komae_canopy_qgis_export.py` | scripts/work READMEのsaved-array再構成手順。QGIS 4.2実表示の確認は未完了と記載 | Unverified | voxel spanの派生表示は元CHM精度や正式mesh受入ではない | 新規exportのhash・2D/3D関係を現地確認 P1 |
| Standard QA / Adapter QA §5 | Native/Standard validators、Adapter geometry/vertical checks、`komae_integration.py::adapter_quality, contained_repair_quality, a3_checks`、`komae_preflight.py::preflight` | `tests/test_standard_building.py`, `test_standard_terrain.py`, `test_voxcity_adapter.py`, `test_komae_preflight.py`, `test_komae_repair_acceptance.py` | E-B/T/A/Cの限定指標。qualityとreproducibilityは独立 | Partial | PASS/CONDITIONAL PASS/FAILの汎用dataset運用や全国QA閾値は未整備。AUTOMATED_PASSはformal acceptanceではない | preflight→隔離run→目視／根拠レビューを分離 P0 |
| Provenance §6 | `plateau.py::write_manifest`、receipt SHA、Terrain manifest、Adapter inputs/output SHA、`komae_integration.py::fingerprint, voxcity_provenance, environment` | `tests/test_plateau_building.py`, `test_standard_terrain.py`, `test_komae_integration.py`（lineage、pin integrity） | E-Tに明示hash、E-Aはhashなし、E-Cはlocal report参照 | Partial | 取得URL・利用条件・release・Converter設定の完全なchainなし。絶対パス依存あり | 再取得時点の証拠を記録、旧入力と新入力を同一視しない P0 |
| Run Log §6 | `komae_integration.py::execute, checkpoint, run`、各repeat logとintegration-report、配列hash、入力改変検知 | `tests/test_komae_integration.py`（失敗log保持、checkpoint、変更検知） | E-Cは2反復9比較項目true。元reportはlocal | Partial | 限定runnerのrun記録。取得／Converter GUIのログ、全プロセス共通schemaではない | 新run ID・新reportでPC別の実績を記録 P0 |
| 保存・版更新・Current §6 | `data/raw,native,standard,model,output,work`慣例、runner既存run拒否。`src/ouem/model/*`はnamespace中心 | `tests/test_komae_integration.py`, `test_komae_contained.py`（既存出力拒否） | 既存記録はlocal artifactをGit外へ保持 | Partial | mesh×layer版管理、Current切替、retained/external/removedの汎用台帳なし | 新旧証拠を隔離 P0。Catalog/Manifest案は別冊参照 P2 |
| Phase B1 §7,7.1 / v0.1 §6,9 | Current/No-Canopy配列までは`scenario_arrays`。OUEMの日射／日陰指標CLIは追跡コードにない | canopyシナリオ比較テストのみ。B1 Tier指標のテストなし | E-Hは占有配列。日射・気象・精度受入なし | Not Implemented | EPW等気象、時刻、太陽位置、透過/LAD、評価点、Tier出力、buffer収束なし | v0.1継承仕様に従い小範囲計画と必要入力を確認 P1 |
| Phase B2 §7,7.1 / v0.1 §7,9 | OUEMの360°Canopy GVI／ray評価CLIなし | B2専用テストなし | formal acceptanceなし | Not Implemented | 視点高・仰角・ray sampling・写真比較・Tier出力なし | canopyの前提確認後に計画 P1。上流の機能存在をOUEM実装扱いしない |
| 他地域・構築profile §2.1,8 | 狛江矩形configのみ。A3 profile用GSI点群・外周線providerなし | 狛江／合成のテストのみ | E-B/T/A/Cは狛江限定 | Not Implemented | profile既定値＋override、GSI全国target等は未実装 | 工程A3成功を構築profile A3成功と呼ばない P2 |

## 5. 既存記録の不整合・未解決点（変更せず報告）

1. **建物鉛直の根拠不足**：C-BはNative EPSG:4979のZを絶対T.P.として扱う一方、E-VはConverterによる鉛直数値変換を未確定としている。Native以降のZ保存とengine不変式のPASSだけでは、元CityGMLに対する屋根の正しさを証明できない。既存受入は撤回・拡張せず、個人PCでの新規検証項目とする。
2. **受入fieldとレビュー判定の差**：E-CはレビューPASS、reportはPENDING_LOCAL_REVIEW。E-Tの生成manifestには歴史的pending文字列が残る。正式記録で説明済みの差であり、値を編集して解消しない。
3. **実データ間のhash連続性**：10/06 A2出力と10/05 A3入力の同一bytesは未証明。E-Aに入力hashはない。A2のhashをA3のhashとして転載しない。
4. **研究文書と後続実装の時点差**：E-H末尾は後続CHM実装を将来として記述するが、現行mainには`komae_canopy.py`等がある。これはコードの不存在を意味しない。一方、後続PoCの存在も研究文書の未検証点を受入済みに変えない。
5. **手順文書の時点差**：scripts/work READMEにcompany-PC実行・レビュー待ちやAfter review/mergeが残る。E-PCの個人PC環境受入へ読み替えない。GIS Python 3.12.14（旧受入）と3.12.15（A6）は別環境の観測値であり単一のlockではない。
6. **幾何修復の差異**：E-CのPR #42/#45のMultiPolygon/Polygon差異は未説明。当該runのQGIS目視も未実施。今回原因を確定しない。

## 6. 個人PC再実行への推奨順序（未承認）

- **P0**：データ取得・利用条件・版を確認し、CityGML／DEMを新規取得する準備を行う。必要入力と経路は[データ取得・再現性インベントリ](OUEM_Data_Acquisition_and_Reproducibility_Inventory_20261025.md)を参照。
- **P0**：E-PCに従いOUEM/GISを分離。GIS snapshotはローカルで再確認する。環境受入と実データ受入を区別する。
- **P0**：Converterの版・LOD・CRS／鉛直設定と元CityGMLの同一性を記録し、全Z比較・代表建物の地盤／屋根整合を確認する。疑義が残る場合は結果を限定・保留する。
- **P0**：Native・Standardとmanifestを揃え、preflightの対象と111/92棟の違いを確認してから、別途認可された新runを実行。新PCの結果を既存受入とは別記録にする。
- **P1**：hash付きCHMとHAG根拠、NoData／coverage、CR推定の限界を確認してopt-in canopy評価。B1/B2はその後の独立した実装・検証計画とする。
- **P2**：AOI一般化、3次メッシュ、profile、共通格子、版管理はv0.2未決点をレビューしてから進める。

本調査ではコード・テスト・設定・既存契約・受入記録を変更せず、実データを処理していない。GEEKOM A6での所要時間・最大RAM・新規入力の品質・同一版再取得可否は未確認。
