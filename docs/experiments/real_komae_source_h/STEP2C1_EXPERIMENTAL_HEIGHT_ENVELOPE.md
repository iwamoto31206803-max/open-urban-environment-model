# STEP 2-C1 Candidate B Experimental Height Envelope

**COMPLETED / EXPERIMENTAL**。2026-11-05、GEEKOM-A6のWindows OUEM `.venv` で生成・入力出力QAを実施した。
`terrain_integration_ready=false`、`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`。
[STEP 2-B](STEP2B_CANOPY_FEASIBILITY.md) の旧Envelope範囲外を解消する新規成果物であり、TREE統合・Solar・GVI・高さ分布モデルは実行していない。

## 実装と入力の境界

後続の [STEP 2-C2実データCanopy統合](STEP2C2_REAL_CANOPY_INTEGRATION.md) は保存実中心のA/B比較と別Derived profileによる統合を扱う。C1の成果物・値・QA記録は維持する。

[candidate_b_envelope.py](../../../src/ouem/candidate_b_envelope.py) が限定profile
`ouem-candidate-b-experimental-height-envelope/v0.1` を所有する。
既存 `GridSpec`、`ConstantCR`、`sample_raster`、`calculate`、`write_verified`、
`compatibility_probe.load_candidate`、`Watch` を再利用した。
正式 `height_envelope.validate_sources()`、B1/B2、Standard Terrain・Acceptanceの条件は変更しない。
入力identityは以下の保存記録に固定し、差異を拒否する。新規ダウンロードはない。

| 入力 | SHA-256 |
|---|---|
| Raw Meta CHMv2 `1330021123.tif` | `6313f286dca3b9f760be95d998e9648d0dd77b0a9305081b67422150340af862` |
| CHMv2取得記録 `meta_chmv2_komae_acquisition_20261025/acquisition-record.json` | `c4c4a842a2271c12a29f62672ee57632f2a7bcea10b79806cafdd761777c98a7` |
| 既存HAG evidence `source-evidence.json` | `afdf8560ac1d7a94cf599ffaa7fe17bbba29df5fca7a61df994052cdc04bf6a9` |
| 保存T5 `t5-23-02/report.json` | `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` |
| T5 `t5-2/terrain.tif` | `ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2` |

CHMはEPSG:3857、32768×32768、uint8、公称投影画素幅約1.194328567 m。
NoData値指定なし、per-dataset maskを尊重する。バンド単位タグは未指定だが、保存済みMeta公式HAG出典snapshotの文言・SHAによりlocal groundからの高さmという意味を結び付けた。
取得記録は旧AOIのcrop記録だが、今回使うのは記録中のRaw tileそのもの。旧crop・旧DEMへの限定適合性レビューを新DEMへ転用していない。

実験用TerrainはEPSG:6677、0.5 m north-up、254×254、Float32、NoData **−32767**、
Affine `[0.5,0,-22588,0,-0.5,-39811]`。単位タグ未指定の標高mはT5の実験的来歴に基づく。
T5のWARD_FIRST/Tama・23区ソース混在選択と全保存出力のSHAを共通readerで検証した。
区部DEMのT.P.継承は **working assumption**。realization・epoch・精度は未確定であり、EPSG:6677を鉛直根拠にしていない。
CHMとDEMの時点差、CHMモデル地盤とDEMの差、位置誤差、CR誤差も未解決。

## 生成規則と実データQA

Processing Domain全体 `[-22588,-39938,-22461,-39811]` にEPSG:6677の北向き1 m格子
127×127を作成。Affine `[1,0,-22588,0,-1,-39811]`。
`top=DEM+CHM`、`bottom=DEM+(1−CR)×CHM`、CR=0.60（B1との比較用仮定）。
出力は絶対標高mの推定であり、鉛直offset・地盤吸着・補完はない。
CHM=0とtop=bottomを有効として保持し、樹木不存在の観測とは解釈しない。

| QA | 北向きEnvelope中心 | 保存T5実中心で元入力を直接sample |
|---|---:|---:|
| 全セル／valid | 16,129／16,129 | 16,129／16,129 |
| CHM=0 | 13,819 | 13,819 |
| TREE候補（state=1かつtop>bottom） | 2,310 | 2,310 |
| missing／outside／invalid | 0／0／0 | 0／0／0 |
| top範囲 m | 23.950000763–33.720001221 | 23.959999084–33.739997864 |
| bottom範囲 m | 23.950000763–28.319999695 | 23.959999084–28.340000153 |

両入力の全domain外縁被覆（101点densify変換によるbounds）と両中心集合の有効性を検査した。
元マスク・非有限値・範囲外を区別し、両中心集合で `DEM≤bottom≤top`、有限値を確認。
Float32最大丸め誤差はtop約1.91e−6 m、bottom約7.63e−7 m。
浮動出力NoDataは−9999、state自体はNoData指定なし。
state=1は有効、error bitはmissing CHM/DEM=2/4、invalid CHM/DEM=8/16、outside CHM/DEM=32/64、model/Float32不正=128（OR結合）。
既存writerでCRS・Affine・shape・dtype・NoData・単位・鉛直タグ・配列・maskを再読照合した。

### 実中心との座標対応とSTEP 2-C2への引き継ぎ

保存T5はaxis 0が南から北、axis 1が西から東の実VoxCity中心を持ち、north-up格子と同一ではない。
保存されたEPSG:6677中心をそのまま使い、Envelopeのinverse-affine floorでrow/colを求める。
16,129中心は全て異なるEnvelopeセルに入り、対応セル中心までの最大距離は **0.001808639 m**。
ただしnative DEM 0.5 m画素の境界付近にあるため、北向き中心のサンプルと実中心での直接サンプルは
DEM **13,986セル**、CHM **1セル**で異なる。直接サンプルとのtop最大差は **0.950000763 m**、bottom最大差は **0.350000381 m**。
実中心で直接読んだDEMは保存T5 `dem.npy` と全値一致した。位置を暗黙に補正した結果ではない。

生成済みtop/bottom/stateも実中心で再サンプリングし、全16,129がvalid、missing/outside=0、対応するEnvelopeセル値と一致した。
**次工程では3ラスタを同じ実中心でnearest（inverse-affine floor）サンプリングする。単純なreshape/flipを位置対応の代用にしない。**
北向きEnvelope値は実中心で元入力から再計算した値とは同一でない。
STEP 2-C2はこの差に加え、所有ID別平均地盤、D0=23.959999084 m、地盤下区間の拒否、元DEM SHAを再確認すること。
今回の成果物だけで既存canopy adapterへの適合やTREE統合可能性を認定しない。

## 成果物と再現性

Git管理外の `data/work/terrain-candidate-b/step2c1-envelope-final-a/` と `step2c1-envelope-final-b/` に保存。
2回の全GeoTIFF・manifestはバイト一致した。reproducibility SHAは
`e21aceaff9a2f611617cfadb7c16318067be1bfb328f6dec1c165b50fac31c8b`。
実行時HEADはPR #156マージ後 `8d8dd0f`、生成moduleは未追跡状態だったため、manifestにはmodule自体とhelperのSHAも記録した。
Python 3.11.9、NumPy 2.4.6、rasterio 1.4.4／GDAL 3.10.3、pyproj 3.7.2。
VoxCity 1.7.0／固定commit `fa212656305328a9a657973bae26f352bfe813bc` のPEP 610・RECORD整合を確認したが、エンジンによるボクセル生成は行っていない。

| 成果物 | SHA-256 |
|---|---|
| canopy_top_z.tif | `589fde0f3be88aad75a27269434a1c2dbb53d95eb9458f3dfe4a3b5061b51a74` |
| canopy_bottom_z.tif | `530f11a9b41e621a185a6c9ab4790a2c32248a432d14ffe8af0197086e1e9bb7` |
| height_envelope_state.tif | `4cb3a98a88793e375f23570fa1df18f3d0d42fffecfe17c121e08c8ba344d3d0` |
| height_envelope_manifest.json | `544c526ce7078c72b89da6757662c4ec6b13924598458c5ae95ac57f88cab7ef` |

入力は処理前後でSHA・ファイルidentityを再照合。T5のreport・全成果物を保護した。
STEP 2-A `step2a-03` のreport SHA `c968c8a754e2a9bc0eeb2fa4a4b24a165021c1a518f6d99e76643ad8a8af81af`、
shadow TIFF SHA `3a0cb2c88ad3a2dfcfe6f13e8b24215f53c30e4075845403e3e08dcee3703db4` も既存記録と再照合した。
出力先は新規かつ入力bundle外を要求し、全TIFF QA・入力再照合後にmanifestを最後にrenameして公開する。
失敗・中断時の部分TIFFや `.pending` は完了ではない。並行writerは非対応であり、runを再利用しない。
初回試行では実験TerrainのNoDataと正式Terrainの値の相違を検出し、入力を変更せずprofileを修正した。
`step2c1-envelope-01` はhardlink公開がWindowsで拒否され `failure.json` を保存。rename公開へ変更して再検証した。
`-02`～`-04` は実装確認用で、引き継ぎ対象は `final-a`／`final-b` のみ。

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_envelope `
  --source-run data/work/terrain-candidate-b/t5-23-02 `
  --chm data/raw/canopy/meta_chmv2_komae_acquisition_20261025/1330021123.tif `
  --acquisition-record data/work/meta_chmv2_komae_acquisition_20261025/acquisition-record.json `
  --chm-evidence data/work/height-envelope/komae-exploratory-20261026-01/inputs/source-evidence.json `
  --output-dir data/work/terrain-candidate-b/step2c1-envelope-new-run

.venv/Scripts/python.exe -m pytest -q -ra tests/test_candidate_b_envelope.py tests/test_compatibility_probe.py tests/test_height_envelope.py::test_exact_komae_grid_centres_and_half_metre_dem_sampling tests/test_height_envelope.py::test_invalid_constant_cr_blocks tests/test_height_envelope.py::test_replaceable_spatial_cr_model_and_float32_overflow
```

関連pytestは **38 passed、skip 0、45 warnings**（既存rasterio/AffineのPendingDeprecationWarning）。
新規合成fixtureで数値期待値、0/欠測/範囲外、保存後の格子、再現性、入力SHA不一致、入力変異、保存DEM不一致、被覆不完全、書込・公開失敗を検証した。
既存Height Envelopeファイル全体を含む試行はGitの全未追跡ファイル走査で停滞したため中断し、上記のhelper関連テストへ絞った。テストや合格条件は変更していない。
ローカル全体pytestは依頼どおり省略。全体回帰は既存GitHub Actions Windows/Ubuntu CIが受入ゲート。
PR #156のpip cache・`--durations=30`、テスト選択・CI設定は維持する。
