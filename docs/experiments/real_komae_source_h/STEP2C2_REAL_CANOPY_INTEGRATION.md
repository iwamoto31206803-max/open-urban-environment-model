# STEP 2-C2 Candidate B Real Canopy Voxel Integration

**COMPLETED / EXPERIMENTAL**。2026-11-06（JST）、GEEKOM-A6のWindows OUEM venvで保存済み63棟Mixed-LoDモデルと推定Canopyを統合した。
`terrain_integration_ready=false`、`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`。
Solar/GVI、PLATEAU/Terrainの再生成、高さ分布モデルは実行していない。
[STEP 2-B](STEP2B_CANOPY_FEASIBILITY.md) · [STEP 2-C1](STEP2C1_EXPERIMENTAL_HEIGHT_ENVELOPE.md)

後続Solar PoCは [STEP 2-C3](STEP2C3_REAL_SOLAR.md)。以下はSTEP 2-C2完了時点の記録として維持する。

## 実装と保存入力

[candidate_b_canopy_run.py](../../../src/ouem/candidate_b_canopy_run.py) は保存入力の復元・A/B比較・QA・新規run公開を所有する。
既存 `candidate_b_canopy.integrate`、B1 `integrate_canopy`、固定VoxCityの公開 `Voxelizer.generate_combined` を再利用し、これらの既存関数を変更していない。
保存高さ・セグメントをそのまま読み、建物の再ラスタ化や高さ再推定はしない。

| 入力 | SHA-256 |
|---|---|
| T5 `t5-23-02/report.json` | `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` |
| T5 `t5-3/voxels.npy` | `350e08696bf6b73cd26e8bebcea63f3e7208e2df28cf0ac13a8affbea35bd54d` |
| T5 `t5-3/segments.json` | `9b5b567a6782bcbe090334ebda1eef3d60b3a3aa57c3a5b5c80eaa21555e783c` |
| T5 `t5-2/terrain.tif` | `ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2` |
| Meta Raw CHMv2 `1330021123.tif` | `6313f286dca3b9f760be95d998e9648d0dd77b0a9305081b67422150340af862` |
| C1 `step2c1-envelope-final-a/height_envelope_manifest.json` | `544c526ce7078c72b89da6757662c4ec6b13924598458c5ae95ac57f88cab7ef` |
| 保護対象STEP 2-A `step2a-03/report.json` | `c968c8a754e2a9bc0eeb2fa4a4b24a165021c1a518f6d99e76643ad8a8af81af` |

`compatibility_probe.load_candidate` でT5 reportと全15成果物のSHAを照合した。
対象には `building_height.npy`、`building_ids.npy`、`dem.npy`、`effective_dem_abs.npy`、`centres_xy.npy`、`evaluation_mask.npy` を含む。
セグメントJSONは127×127、5,348区間。row/column数、cell/list、各pairの長さ、JSON数値型（bool/string不可）、有限性、`0≤low<high`、所有IDとのsupportを検証して復元した。
実データの下端はすべて0。元の複数区間・順序・値を維持し、公開API呼出後にもnested segmentの不変性を照合した。

C1の全GeoTIFFと元CHM・DEM・取得記録・HAG evidence・出典snapshotも固定SHAで照合した。
STEP 2-Aはreport・全4出力のSHAと、report内の全T5入力identityを照合した。
全入力を処理後にも `Watch.unchanged()` で再照合し、入力・保存成果物を変更していない。
正式Terrain validator、B1/B2のAccepted成果物、既存Acceptanceは変更していない。

## A/Bサンプリングと採用

**A** はC1のnorth-up EPSG:6677・1 m top/bottom/state GeoTIFFを保存T5実中心でnearest sample。
**B** は同じRaw HAG・実験DEMをその実中心で直接sampleし、既存 `sample_raster`・`calculate`・`ConstantCR(.60)` で計算した。
いずれもinverse-affine floor、元mask尊重、位置補正・鉛直offsetなし。
C1 north-up中心での計算も再実行し、Aのtop/bottom/stateが対応セルの値と全値一致することを確認した。

| 項目 | A | B |
|---|---:|---:|
| valid | 16,129 | 16,129 |
| 欠測／範囲外／不正state | 0／0／0 | 0／0／0 |
| 有効ゼロ厚 | 13,819 | 13,819 |
| TREE候補 | 2,310 | 2,310 |
| 保存T5 DEMと異なるサンプル数 | 13,986 | **0** |
| top範囲 m | 23.950000763–33.720001221 | 23.959999084–33.739997864 |
| bottom範囲 m | 23.950000763–28.319999695 | 23.959999084–28.340000153 |
| 実効地盤下の正厚候補 | 0 | 0 |
| 実効地盤下の有効ゼロ厚 | 6,752 | 2,369 |
| 建物優先後の予想TREEボクセル | 3,456 | 3,451 |

候補の位置とstateは全値一致。元CHMサンプルは1セルで異なり、DEMは13,986セルで異なる。
`B−A` はtop −0.950000763～+0.309999466 m、bottom −0.350000381～+0.309999466 m。
top・bottomとも13,986セルで差がある。これはC1で確認した中心の最大約1.81 mmの差がnative DEMの0.5 m画素境界等をまたぐためで、暗黙に位置を合わせた結果ではない。
ベクトル化した独立QA oracleで、ボクセル化後のTREE差は **6列・7ボクセル**（評価ROI内は3列）と予想した。
これはAを公開Voxelizerで生成した実測ではなく、同じ丸め・建物優先規則による比較予測である。公開Voxelizerの実行対象はB。

保存T5 DEMとの全値一致を根拠に **Bを採用**。
別profile `ouem-candidate-b-actual-centres-derived-envelope/v0.1` を明示し、C1とAの値は上書きしない。
top=`DEM+CHM`、bottom=`DEM+(1−.60)×CHM`、CHMはlocal groundからのHAG m。
`selection` と `sampling_profiles` にA/Bそれぞれの元ファイルSHA、実中心SHA、計算方法と採用理由を記録した。

実効地盤は所有IDごとの保存raw DEM平均で再検証。Bの有効ゼロ厚で最大約0.40127 m地盤下となるものは、元raw DEMと所有ID平均地盤の差であり、TREE候補ではない。
ゼロ厚区間も有効のまま保存し、平均地盤に吸着させず、不存在の観測とも解釈しない。
T.P.継承はあくまで **working assumption**。adapterの `vertical_reference="T.P."` は今回明示採用した条件付き計算座標であり、datumの検証済み宣言ではない。
realization・epoch・精度、CHMモデル地盤とDEMの差、時点差、位置誤差、CR誤差は未解決のままmanifestへ引き継いだ。

## 公開API統合と占有QA

| QA | 結果 |
|---|---:|
| Processing Domain | 127×127 m／16,129列 |
| 評価ROI | 100×100 m／10,000列 |
| Current／No-Canopy shape | 127×127×12 |
| D0 | **23.959999084472656 m**（維持） |
| TREE占有 | **3,451ボクセル／1,851列** |
| 評価ROI内TREE | 2,861ボクセル／1,461列 |
| 建物列にあるCanopy候補 | 464列 |
| 建物優先によるTREE候補除去 | **677ボクセル** |
| 地盤下の正厚区間除外 | 0列 |
| 欠測／範囲外／不正state | 0／0／0列 |
| 薄い区間の既存丸め規則による拡張 | 7列 |
| 丸め後に消滅した区間 | 0列 |
| 必要TREE end index／非建物observer用層数 | 11／5 |
| 上部AIR追加 | **0層** |

公開Voxelizerは16層を割り当てたが、保存12層より上の4層はすべてAIRであることを既存helperが確認して除いた。占有の切捨てや容量不足の修復はない。
既存B1 scalar QAに加え、workflowのベクトルQAで下端・上端の整数化、thin-crown規則、建物優先、必要end容量とTREE maskを独立照合した。
TREEは元の建物・地盤・表面を上書きしない。CurrentからTREEをAIRへ戻すとNo-Canopyと全値一致。
No-Canopyは保存T5 baseと **NPYバイトSHAまで一致**（今回Z拡張なし）。建物ID、地盤、原点、地理座標、ROIも維持した。

丸め前Hとの区間edge差（遮蔽前）は、bottom +0.100000381～+1.899999619 m、top +0.5～+1.539999008 m。
実際に残ったTREE占有edgeとの差（建物優先後）はbottom +0.104999542～+4.600000381 m、top +0.500999451～+1.5 m。
大きい下端差には建物による下側TREEの除去が含まれる。この占有差を、元の推定bottom値の変更や鉛直精度の保証と混同しない。

## 保存・再現性・実行手順

Git管理外の `data/work/terrain-candidate-b/step2c2-canopy-final-a/` と `step2c2-canopy-final-b/` に保存。
両runの **40個のNPYとmanifestすべてがバイト一致**。初回確認run `step2c2-canopy-01` は引き継ぎ対象外。
manifestには実入力root・SHA・ファイルidentity、実装SHA、VoxCity来歴、出力SHA・dtype・shape、A/B比較、採用判断と残課題を含む。
reproducibility SHA: `879a922fe6d68f7ab34272a800c1bc6541c28ada5eba719115944706a4494ade`。

| 主成果物 | SHA-256 |
|---|---|
| current.npy | `63ce14fab104861a1283c3fc272a08c1faa5a06a8d9a9509b2fb2467099ffdf4` |
| no_canopy.npy | `350e08696bf6b73cd26e8bebcea63f3e7208e2df28cf0ac13a8affbea35bd54d` |
| tree_mask.npy | `5a6892075cb90b5362369f3b858c2b858373335690115be5e7e19a75caeb2100` |
| manifest.json | `1160efdb4a8e689f2b5cb0baf8c6f829d83d88463e8a9e4de332d86392692b45` |

`A/`・`B/` にそれぞれtop/bottom/state、source CHM/DEM、missing/outside/valid/candidate、zero_depth_valid、below_ground、active、nonempty、rounded_empty、thin_expanded、uncertainを保存。
`uncertain` はsourceが不明・無効なセルのmask（今回すべてfalse）であり、生態学的信頼度の検証済みmaskではない。全樹冠は推定である。
`B/relative_top`・`relative_bottom`、実中心、評価mask、A/B予想差列も保存した。
NPYはEPSG:6677実中心に結び付くVoxCity軸（axis 0南→北・axis 1西→東）であり、north-up GeoTIFFとして解釈しない。

実行環境はGEEKOM-A6／Windows-10-10.0.26300-SP0、OUEM Python 3.11.9、NumPy 2.4.6、rasterio 1.4.4／GDAL 3.10.3、pyproj 3.7.2。
VoxCity 1.7.0、commit `fa212656305328a9a657973bae26f352bfe813bc`、numba経路。
PEP 610・136 source filesのRECORD整合を検証したが、upstream Git treeとの独立バイト比較ではない。
実行時HEADはPR #157マージ後 `8cfa0f1e4fbca316d7d63422985558fff36040d1`。
workflowは未追跡状態で実行したため、自身のSHA `6da5df08d2eefce2687ddfc39a6d0999c57c3e650b2bdbd40d30174453eaeb22` と既存helper/adapter等のSHAも記録した。

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_canopy_run `
  --source-run data/work/terrain-candidate-b/t5-23-02 `
  --envelope-manifest data/work/terrain-candidate-b/step2c1-envelope-final-a/height_envelope_manifest.json `
  --chm data/raw/canopy/meta_chmv2_komae_acquisition_20261025/1330021123.tif `
  --acquisition-record data/work/meta_chmv2_komae_acquisition_20261025/acquisition-record.json `
  --chm-evidence data/work/height-envelope/komae-exploratory-20261026-01/inputs/source-evidence.json `
  --step2a-run data/work/terrain-candidate-b/step2a-03 `
  --output-dir data/work/terrain-candidate-b/step2c2-canopy-new-run

.venv/Scripts/python.exe -m pytest -q -ra tests/test_candidate_b_canopy_run.py tests/test_candidate_b_canopy.py tests/test_candidate_b_envelope.py tests/test_compatibility_probe.py tests/test_shared_vertical_domain.py --deselect=tests/test_shared_vertical_domain.py::test_expanded_solar_uses_same_observers_and_pair_grid
```

新規runのみ。出力・全QA・入力再照合後に `.pending` をrenameして `manifest.json` を最後に公開する。
失敗時はBLOCKED manifestまたは公開失敗の `failure.json`。部分NPYと `.pending` は完了の根拠にしない。並行writer・resumeは非対応。
関連pytestは **96 passed、skip 0、1 deselected、42 warnings**（既存rasterio/Affine PendingDeprecationWarning）。
Solarを実行する1件のみ明示除外。正常/不正セグメント、画素境界のA/B差、欠測/0/範囲外、保存ペア、再現性、SHA不一致、入力改変、占有改変、書込・公開失敗を新規テストで確認した。
既存adapter/Probe/Z-domainテストで建物優先、D0/地盤不整合拒否、容量不足拒否、丸め・薄い区間、上部AIR拡張を再確認した。
ログは `data/work/terrain-candidate-b/step2c2-related-final.log`。
ローカル全体pytestは繰り返さず、既存GitHub Actions Windows/Ubuntu全体回帰を受入ゲートとする。
PR #156のpip cache・`--durations=30`、テスト選択・合格条件は維持する。CI結果はDraft PR本文に記録する。

この完了は実験的ペア生成と数値QAに限られる。日射・緑視率の評価、樹木の現地検証、科学的精度・正式Acceptanceは別工程である。
