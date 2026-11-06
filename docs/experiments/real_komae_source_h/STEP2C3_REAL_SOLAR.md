# STEP 2-C3 Mixed-LoD Real Solar / Canopy Difference PoC

**実データSolar E2E COMPLETED / EXPERIMENTAL**。2026-11-06（JST）、GEEKOM-A6のOUEM Windows venvで、保存C2 Current/No-Canopyペアの共通観測点から直達日射差分を計算した。
`terrain_integration_ready=false`、`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`。
GVI、建物・Terrain・Canopyの再生成は行っていない。
[STEP 2-A baseline](STEP2A_BUILDING_SHADOW_E2E.md) · [STEP 2-C2入力](STEP2C2_REAL_CANOPY_INTEGRATION.md)

## 実装とAPI監査

[candidate_b_solar.py](../../../src/ouem/candidate_b_solar.py) が保存ペアの監査・共通観測点QA・2ケース計算・座標出力を所有する。
B1 [real_komae_solar.py](../../../src/ouem/real_komae_solar.py) の `solar_pair()` 内にあった単一ケース計算を `direct_solar_at_saved_grid()` に取り出して共有した。
既存B1の既定太陽135°/35°、DNI=800、光学条件・5回の診断呼出・出力と判定は維持する。B1全runは複製しない。
今回は同じ下位公開API `get_direct_solar_irradiance_map()` を **Current/No-Canopyの2回だけ** 全Processing Domainで呼び、ROI抽出は後段で行う。不要なTerrain-only・crop Controlは追加しない。

固定VoxCity 1.7.0／commit `fa212656305328a9a657973bae26f352bfe813bc` のインストール済みsourceを監査した。
公開APIは `compute_direct_solar_irradiance_map_binary()` の透過率にDNIと太陽方向Z成分を掛ける。
関数名にbinaryとあるが、TREEがある場合の値は0/1限定ではなく、**水平面直達日射 W/m²** である。散乱日射・反射・時間積分・実気象データを含まない。

| 条件 | 両ケース共通値 |
|---|---|
| 太陽 | 真方位180°、高度45°（人工的固定条件） |
| DNI | 800 W/m²（B1と同じ仮定） |
| 障害物なしの水平面直達日射 | `800×sin(45°)` = 565.685424949238 W/m² |
| 光学条件 | tree_k=0.6、tree_lad=1.0、未較正の均質仮定 |
| API | view_point_height=1.5、include_building_roofs=false、show_plot=false |
| 通過・遮蔽 | hit_values=(0,)、inclusion_mode=false。AIRのみ通過、TREEは減衰、建物・地盤・表面等は不透明 |
| TREE経路 | `exp(−tree_k×tree_lad×TREE内経路長m)` の積。透過率<0.01でhitとなり出力0 |

モデル軸はaxis 0南→北、axis 1西→東、axis 2上。保存格子の真北に対する方位は約−0.145335°。
既存 `candidate_b_shadow.sun_direction()` で保存地理基底から方位を再監査し、真方位から格子方位を引く。
sunward光線は約 `[-0.707104506,-0.001793627,0.707106781]`。
汎用orientation docstringのfrom/toward注意書きを日射APIへ機械的に転用せず、実際のSolar APIが直接渡す **太陽へ向かう180°** として扱う。180°の追加反転はしない。
独立した合成壁テストで北側に影、南側は日向、45°の幾何的到達範囲より遠い北側は日向となることを確認した。

## 入力・観測点監査

以下の保存データのみを読む。全ファイルをSHA・sizeで照合し、C2 manifestの全40出力と全upstream入力rootをたどってT5・STEP 2-A・C1・Raw CHM・取得/HAG evidence・snapshotを再照合した。
計算・出力後に全Watchを再照合し、入力配列・nested building segmentsもメモリ上で比較した。

| 入力マーカー | SHA-256 |
|---|---|
| `step2c2-canopy-final-a/manifest.json` | `1160efdb4a8e689f2b5cb0baf8c6f829d83d88463e8a9e4de332d86392692b45` |
| `t5-23-02/report.json` | `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` |
| `step2a-03/report.json` | `c968c8a754e2a9bc0eeb2fa4a4b24a165021c1a518f6d99e76643ad8a8af81af` |

T5は共通readerで元DEM→所有ID別平均地盤、D0、占有・source ID・地理座標・ROIを再検証した。
Canopyを除いた配列は保存T5 baseと一致し、Currentとの差はTREEだけ。共通Z容量127×127×12、D0=23.959999084472656 mを維持する。
建物高さ・セグメント・相対Canopy区間は保存値を使用し、再生成しない。

`b2_gvi.observers()` は観測点の独立幾何診断だけに使用し、GVIは計算しない。
Current/No-Canopyのindexとvalid maskが全値一致し、全建物列が除外されることを要求する。
APIと同じ最初のAIR/TREE遷移を選び、`k=surface_index+1+int(1.5/1m)=surface_index+2`、中心絶対Zは `D0+k+.5`。

**1.5 mはAPI要求値であり、実効地盤から測った高さ1.5 mを保証しない。**
表面・遷移セルと整数化を含むB1の既存規則をそのまま使い、地盤へ高さを補正しない。
今回の観測indexは2～4、絶対Zは26.459999084～28.459999084 m。
保存XYZとT5実効地盤から求めた実際の高さ差は約2.000999451～3.0 m。この量子化を現地測量精度と解釈しない。

| 範囲 | 総列 | 共通有効観測点 | 建物除外 | TREE内観測点 |
|---|---:|---:|---:|---:|
| Processing Domain | 16,129 | 10,782 | 5,347 | 647 |
| 評価ROI | 10,000 | 5,878 | 4,122 | 540 |

TREE内観測点もAIRと同じindex・XYZを維持し、そのセル内の残り経路から減衰を数える。有効数・位置は変わっていない。
合成テストでは観測点自身にTREEを置き、半セル対角経路 `sqrt(.5) m` に対する `exp(−.6×sqrt(.5))` と一致した。

## 実データ結果と数値QA

差分は **No-Canopy − Current**。以下の平均・中央値・割合は、建物を0として混ぜず、各範囲の共通有効観測点（低減0も含む）で集計する。
低減ありの閾値と負差分の許容範囲は **1e−9 W/m²**。結果はclampしない。

| 指標 | Processing Domain | 評価ROI | 評価ROI外 |
|---|---:|---:|---:|
| 有効観測点数 | 10,782 | 5,878 | 4,904 |
| Current平均 W/m² | 386.555290 | **323.615837** | 461.995360 |
| No-Canopy平均 W/m² | 420.093044 | **374.557277** | 474.672823 |
| 低減量平均 W/m² | 33.537754 | **50.941440** | 12.677462 |
| 低減量中央値 W/m² | 0 | **0** | 0 |
| 低減量最大 W/m² | 565.685425 | **565.685425** | 553.260848 |
| 低減あり観測点数 | 937 | **753** | 184 |
| 有効観測点中の割合 | 8.690410% | **12.810480%** | 3.752039% |

両ケースの有効値は0～565.685424949238 W/m²、無効観測点はNaN。
負の日射は拒否する。今回、負の低減量0点、許容値を超える増加0点、最大増加0 W/m²。
NaN/finite支持が共通maskと完全一致し、TREEなしのNo-Canopy値は0または障害物なし値であることも検査した。
TREEなしの同一ペアが全値一致することは合成テストで確認した。実データで同じControlを追加計算していない。
計算中に建物・地盤・Canopy区間・両ボクセル配列が変わっていないこと、保存NPYのdtype/shape/値の再読込一致も確認した。

## STEP 2-Aとの比較可能性

同じ保存建物・地盤・格子と180°/45°の太陽方向を持つため、形状と日陰方向の診断baselineに使える。
ただしSTEP 2-Aは要求高さ0 mの最初の遷移セル中心、二値0/1、地盤・表面を通過させる `hit_values=(0,-1,1)`。
今回は要求1.5 m・水平面直達日射W/m²・`hit_values=(0,)`。観測高さも遮蔽条件も異なるのでセル完全一致は受入条件にしない。

| 範囲 | STEP 2-A二値日陰 | 今回No-Canopyで日射0 | Aの日陰→今回日向 | Aの日向→今回日射0 |
|---|---:|---:|---:|---:|
| Processing Domain | 3,197 | 2,775 | 422 | 0 |
| 評価ROI | 2,270 | 1,986 | 284 | 0 |

この比較では高さ効果と地盤遮蔽条件を分離して推定していない。Canopy減衰量に二値分類やこの不一致数を流用しない。
今回のNo-Canopyそのものが同条件の建物・地盤Controlであり、Canopy差分の成立に別Control呼出は不要と判断した。

## 地理出力・再現性

`data/work/terrain-candidate-b/step2c3-solar-final-b/` を引き継ぎ対象、`step2c3-solar-final-c/` を独立再実行として保存。
両runの **12 NPY・4 GeoTIFF・manifestはすべてバイト一致**。
`step2c3-solar-01` と `step2c3-solar-final-a` は実装確認用の先行runで、引き継ぎ対象外。
reproducibility SHA: `82b17bf70c465f3b3ee657f1b346e1cc6f1d8960f8b44cbe146ea783efe81e94`。

Processing DomainのCurrent/No-Canopy/reduction、観測index・valid・XYZ、表面index、両ケースの観測点クラス、ROI、実中心、分類maskをNPY保存した。
NPYはVoxCity軸、GeoTIFFはEPSG:6677北向き100×100、公称1 m、Affine `[1,0,-22575,0,-1,-39825]`。
実中心をinverse-affine floorで配置し、重複・欠落・範囲外0、登録誤差最大 **0.001436055367 m**（既存上限0.01 m以内）を検証した。
単純な転置・反転によるラスタ化ではない。公称北向きpixel中心とのmm程度の差は記録し、元座標を補正していない。

日射3ラスタはFloat64、NoData=−9999、単位タグW/m2。Float32へ丸めず元値と一致させた。
observer maskはuint8、NoData=255、**0=建物除外・1=AIR内観測点・2=TREE内観測点**。除外0自体はmask内の有効分類値。
CRS・Affine・shape・dtype・NoData・単位・全値・mask、四隅と中央付近のpixel中心および対応元実中心を再読検証した。
左上pixel中心は `[-22574.5,-39825.5]`、右下は `[-22475.5,-39924.5]`。全座標検査をmanifestに記録した。

| 成果物 | SHA-256 |
|---|---|
| current.npy | `7fd8300b74248bde095bad69e544e2b83d3e79849ab8bc52b2a58b6f3167a454` |
| no_canopy.npy | `4a122d0d8ea6874a68e81f5ac64e7599fe258c139225a33f3fd260a71b46ba9c` |
| reduction.npy | `93e507fd66731b99769107bb59e8f3d2ea0f6ac3237213bc4ddbb2e6c9451b62` |
| evaluation_current.tif | `1df3fe4b91a309d0939983d2756a2e6cfdbb32108f6bce92f0e3357b1e9b9c9c` |
| evaluation_no_canopy.tif | `e58b15f83413694e4a217909532e1575d9d0a3bde29f990e3732b497febcadd2` |
| evaluation_reduction.tif | `5e158d22332c3fe38899bb40c73cc3fd4cab756bdbebef7da931a6fde358d031` |
| evaluation_observer_mask.tif | `17b4f8020220a5c61ac37c9183d20fe47a69524e934254c59dadc565ce440fa8` |
| manifest.json | `afefa79524efbf911f0019f663235a3115b8158cd79efcd1da67cea18122cfb7` |

manifestには全入力root・identity・SHA、実装SHA、VoxCity PEP 610/RECORD来歴、計算設定・観測点・全出力SHA・QAを記録した。
実行時HEADはPR #158マージ後 `0488fa7d22df67e31ddc5e31ef5dc7c12fde3bbe`。Solar helperは未commit変更、adapterは未追跡状態だったため、実行バイトSHAも記録している。
adapter SHA `d93a6befddc20bfc69645dfc74fb8562fcb43d03f91f6fdadc47ad4f7fa41428`、Solar helper module SHA `dd62776512bfbc047174b6f05219f10eccbc850d5d63d7afb8210371709261fb`。
環境はWindows-10-10.0.26300-SP0、OUEM Python 3.11.9、NumPy 2.4.6、Numba 0.68.0（16 threads）、rasterio 1.4.4／GDAL 3.10.3、pyproj 3.7.2。
PEP 610と136 source filesのRECORD整合は確認したが、upstream Git treeとの独立バイト比較ではない。

## 実行・テストと未解決事項

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_solar `
  --pair-run data/work/terrain-candidate-b/step2c2-canopy-final-a `
  --source-run data/work/terrain-candidate-b/t5-23-02 `
  --step2a-run data/work/terrain-candidate-b/step2a-03 `
  --output-dir data/work/terrain-candidate-b/step2c3-solar-new-run

.venv/Scripts/python.exe -m pytest -q -ra tests/test_candidate_b_solar.py tests/test_candidate_b_shadow.py tests/test_real_komae_solar.py tests/test_shared_vertical_domain.py
```

合成テスト通過後に実データを計算。最終関連pytestは **65 passed、skip/deselect 0、17 warnings**（既存rasterio/Affine PendingDeprecationWarning）。
観測点・太陽方向・TREE内透過率・TREEなし一致・物理範囲/負差分許容・入力不変・保存SHA・非正方形地理出力・部分出力/公開失敗・再現性を検証した。
既存B1 `solar_pair()` の5呼出・crop/terrain診断を含む関連回帰も通過。GVI専用テストは実行していない。
ログは `data/work/terrain-candidate-b/step2c3-related-final.log`。
ローカル全体pytestは繰り返さず、既存Windows/Ubuntu Actionsを全体回帰ゲートとする。CI・テスト選択・合格条件、PR #156のpip cache・`--durations=30` は維持。結果はDraft PR本文に記録する。

入力監査はSolar・出力作成より前。新規runのみ使用し、出力/入力再照合後にmanifestを最後に公開する。
入力監査失敗は出力未作成で非zero終了。その後の失敗はBLOCKED manifestまたは公開失敗のfailure.json。
部分NPY/TIFFやpendingファイルは完了を示さず、並行writer/resumeは非対応。
T5・STEP 2-A・C1・C2、B1/B2 Accepted成果物は変更していない。正式Terrain受入条件も維持する。

樹冠実在、CR、k/LAD、鉛直基準realization/epoch・精度、1 m形状量子化、領域外遮蔽物と領域十分性、現地日射精度は未検証。
今回の結果は固定太陽・仮定DNIの技術PoCであり、実際の日・年間積算や科学的精度・正式Acceptanceを主張しない。GVIは次工程。
