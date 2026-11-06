# STEP 2-C4 Mixed-LoD Real GVI PoC

**実データGVI E2E COMPLETED / EXPERIMENTAL**。2026-11-06（JST）、保存C2モデルとC3観測点・地理座標から既存B2のCPU weighted first-TREE view indexを計算した。
STEP 2の保存Mixed-LoDモデル→Solar/GVIの実験的な数値評価接続を確認したもので、科学的・正式受入ではない。
`terrain_integration_ready=false`、`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`。
[C2モデル](STEP2C2_REAL_CANOPY_INTEGRATION.md) · [C3 Solar](STEP2C3_REAL_SOLAR.md) · [既存B2](../b2_gvi/README.md)

## 実装・入力・設定

[candidate_b_gvi.py](../../../src/ouem/candidate_b_gvi.py) はCandidate B固有の保存handoff、負荷receipt、EPSG:6677出力を所有する。
既存 [b2_gvi.py](../../../src/ouem/b2_gvi.py) の `calculate()`・`SETTINGS`・`observers()`・`check_result()`・計測を再利用し、B1/B2実装・既存結果を変更していない。
C3の読取専用loaderを使うが、Solar計算関数は呼ばない。建物・Terrain・Canopyの再生成もない。

| 固定入力 | manifest/report SHA-256 |
|---|---|
| `step2c2-canopy-final-a` | `1160efdb4a8e689f2b5cb0baf8c6f829d83d88463e8a9e4de332d86392692b45` |
| `step2c3-solar-final-b` | `afefa79524efbf911f0019f663235a3115b8158cd79efcd1da67cea18122cfb7` |
| `t5-23-02` | `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` |

C3の全16成果物とC2の全40成果物、全upstream bindingをSHA・sizeで照合した。
T5・STEP 2-A・C1・Raw CHM・取得記録・HAG出典snapshotも既存reader/Watchで再照合し、計算・出力後に不変性を確認した。
入力をread-only mmapで読み、B2の計算中バイトdigestでもCurrentのTREE・建物・地盤の不変性を検査した。

| 条件 | 値 |
|---|---|
| エンジン | VoxCity 1.7.0 / `fa212656305328a9a657973bae26f352bfe813bc` |
| 指標 | **CPU weighted first-TREE view index**、無次元0～1 |
| mode / targets / inclusion | None / (-2,) TREEのみ / True |
| optics | tree_k=0.5、tree_lad=1.0（未較正の既存B2仮定） |
| 観測点 | view_point_height=1.5、建物屋根除外 |
| 方向標本 | azimuth 120 × elevation 20 = **2,400光線/観測点** |
| 方位・仰角 | 全周0～357°の3°刻み、仰角−30～+30°（両端を含む等間隔20点） |
| 実行 | CPU **2 threads**、fast_path=False、ray_sampling=grid、OBJ off |

全光線の平均で、最初にhitしたTREE区間の寄与は `1−transmittance`。建物・地盤などの不透明物に遮られ、TREE targetに到達しなければ寄与0。
周囲すべての樹冠を透過積分した量や、写真の緑色画素割合ではない。等角度標本の既存平均をそのまま使い、新しい立体角補正・光線エンジンは導入しない。
方位標本はB2 APIのモデル格子基準で、Solarの単一太陽方向や追加の180°反転を流用しない。
Solarのk=.6とGVIのk=.5は、それぞれの既存実験条件であり、同じ光学指標とは解釈しない。

## Solarとの観測点・空間整合

Current/No-Canopyから再判定したobserver index、valid、XYZ、surface index、origin classをC3保存NPYと全値照合した（除外XYZのNaNも対応）。
B2設定での独立observer判定も一致。D0=23.959999084472656 m、共通Z容量127×127×12、index=2～4、絶対Z=26.459999084～28.459999084 mを維持した。
1.5 mはAPI要求値であり、実効地盤上の実高さはC3で記録した約2.001～3.0 mのまま。暗黙の高さ補正・TREE内観測点の移動はない。

| 範囲 | 総列 | 共通有効観測点 | 建物除外 | AIR内 | TREE内 |
|---|---:|---:|---:|---:|---:|
| Processing Domain | 16,129 | 10,782 | 5,347 | 10,135 | 647 |
| 評価ROI | 10,000 | 5,878 | 4,122 | 5,338 | 540 |

ROI・実セル中心もC3と完全一致。保存Solar GeoTIFFを読み取り専用で開き、EPSG:6677・Affine・shapeを確認した。
出力後の独立再読で、GVI/Solarの全finite mask、observer origin分類、validityも一致した。
同じ観測点・地理的位置でSolarとGVIの分布を比較できるが、相関・因果関係は今回は計算・科学検証していない。

## 実行可能性確認と性能

合成テスト通過後、同じ2,400光線・2 threadsで、5×7×6合成Currentを2回、TREEなし合成No-Canopyを1回、保存モデルの16×16×12部分域を2回計算した。
部分域は保存ROIの南西端 `u[13:29], v[13:29]`、有効78点。**部分域結果は負荷probeだけで、評価結果には使っていない。**
既存B2の推定式 `first subset wall + repeat wall × full/subset observers × XY diameter比` で、全域推定は **38.59146秒**。
測定peak working setは308.145 MiBで、既存の推定600秒/pass・2 GiB未満の負荷gateを通過した。推定は厳密な上限ではない。

| API呼出 | wall秒 | process CPU秒 | sample peak MiB |
|---|---:|---:|---:|
| 合成Current初回 | 0.091111 | 0.140625 | 305.980 |
| 合成Current反復 | 0.030041 | 0.062500 | 306.145 |
| 合成No-Canopy | 0.070200 | 0.125000 | 307.453 |
| 保存部分域1回目 | 0.027276 | 0.031250 | 307.984 |
| 保存部分域2回目 | 0.035148 | 0.062500 | 308.145 |
| **Current全域1回目** | **1.379458** | **2.703125** | **305.828** |
| **Current全域2回目** | **1.394213** | **2.781250** | **306.215** |

計測は既存B2の公開API呼出範囲（JIT/cache loading・map・Agg plot/showを含み、Python importsは除く）。メモリは0.1秒間隔のworking set標本であり、OSの絶対peak保証ではない。
既存Numba cacheが利用可能な環境での初回呼出で、純粋なJITコンパイル時間やcacheなし性能は分離測定していない。初回−反復差をコンパイル時間と断定しない。
固定plot overhead等も倍率に入るため、部分域推定は今回の実測全域時間より大きかった。別モデル・機器の性能保証ではない。
全域1回目が600秒または2 GiBを超えた場合は2回目へ進まない実装だが、今回は両方十分に基準内だった。
B2はNumbaを呼出内だけ2 threadsにし、終了後に元の16 threadsへ戻す。manifestの環境16とtiming内の実計算2を区別する。

## GVI数値結果とTREE内部の解釈

全127×127のProcessing Domainを計算してからROIを抽出した。GVIはFloat64、全有効値が0～1、全無効点がNaNであり、欠測を0に置き換えていない。
以下の割合の分母は建物を除いた有効観測点。指標の平均値を「現地の緑色割合」として百分率へ読み替えない。

| 指標 | Processing Domain | 評価ROI | ROI外 |
|---|---:|---:|---:|
| 有効点 | 10,782 | **5,878** | 4,904 |
| 平均GVI | 0.042383367 | **0.057891889** | 0.023794645 |
| 中央値GVI | 0.007210385 | **0.008453815** | 0.006003998 |
| 最大GVI | 0.256848725 | **0.256848725** | 0.255775402 |
| GVI>0の点 | 10,187 | **5,490** | 4,697 |
| GVI>0の割合 | 94.481543% | **93.399115%** | 95.778956% |
| 有効な0の点 | 595 | **388** | 207 |

| 観測点層 | ROI点数 | 正の点数 | 平均 | 中央値 | 最大 |
|---|---:|---:|---:|---:|---:|
| AIR内部 | 5,338 | 4,950（92.731360%） | 0.037873699 | 0.006472900 | 0.256848725 |
| TREE内部 | 540 | 540（100%） | 0.255775402 | 0.255775402 | 0.255775402 |

全域647個のTREE内部点も、すべて0.2557754022082587だった。
観測点自身のセルが全方位で最初のTREE targetとなるため、その先の周辺景観よりも、単位セル中心から最初の境界までの経路とk/LADが寄与を決める。
独立した解析式 `mean(1−exp(−.5×L))`、`L=.5/max(|dx|,|dy|,|dz|)` を同じ2,400方向で評価すると0.2557754022082607、実測との差は最大約2.1e−15だった。
この定数値を「樹冠内は常に同じ現実の緑視率」と解釈しない。ROIのTREE内部点は有効点の約9.19%を占め、AIR内部より高い平均を持つため、統合集計だけでなく別層を残した。

## No-Canopy：公開API実測と導出値の区別

合成5×7×6のTREEなし公開API呼出では、34個の有効点がすべて厳密に0、建物除外点はNaNだった。
監査した `trace_ray_generic()` はTREEなしではtarget=(-2,)へのhitを返さず、`compute_vi_generic()` のTREE寄与和は0となる。
保存No-CanopyにTREEがないことと、Current/Solarと同じ観測点・validを確認したため、No-Canopy全域API計算は省略した。

`no_canopy_theoretical_zero.npy` は **数学・実装上の導出0**（有効点0、除外NaN）であり、全域を計算した実測出力ではない。
manifestの `no_canopy.full_public_api_calculated=false` と負荷receipt内の合成公開API証拠で区別する。
これを実世界の樹木不存在の証拠とも扱わない。

## 地理出力と再現性

成果物はGit管理外 `data/work/terrain-candidate-b/step2c4-gvi-final-01/`。
10 NPY・3 GeoTIFFとmanifestを保存した。`evaluation_gvi.npy` はROIの元UV軸配列（南→北）で、GeoTIFFは実中心で対応させた北向き配列。
既存B2のEPSG:4326 exporterは呼ばず、C3と同じEPSG:6677・100×100・Affine `[1,0,-22575,0,-1,-39825]` にinverse-affine floorで登録した。
重複・欠落・範囲外0、最大登録誤差 **0.001436055367 m**。CRS・Affine・shape・NoData・単位・全値・maskと、C3に保存された四隅＋中央のpixel/実中心を再読照合した。
さらにROI全10,000点をGeoTIFFからsampleし、元全域NPYと全値一致（除外は−9999）を確認した。

- GVI TIFF：Float64、無次元unit=1、NoData=−9999。有効な0を保持。
- validity TIFF：uint8、0=除外、1=有効、NoData=255。
- origin class TIFF：uint8、0=除外、1=AIR、2=TREE、NoData=255。0は有効な分類値。
- raw origin class NPY：int8、0=AIR、−2=TREE、127=除外。valid maskと併用する。

同一プロセス・同一入力・同一2-thread設定で **2回の全域公開API計算** を実施した。
全値（NaN支持を含む）が一致し、`gvi.npy` と `repeat_gvi.npy` は **ファイルSHAも一致**。
計測値を含むmanifest自体のバイト再現性や別プロセスcold-cache再現性は主張しない。

| 成果物 | SHA-256 |
|---|---|
| gvi.npy / repeat_gvi.npy | `ce2b9db49c557e096f60fc667a09c26fd11cf4238914052474238efde8802261` |
| evaluation_gvi.tif | `234eef31e92767b152ef2472ae46079fa652a76f6f3baa77ca4754c7a6c9b072` |
| evaluation_observer_valid.tif | `c8c261c16da65dc78d8cd98fad161f8d72319171aa00b9b92c6cbc1185902ee5` |
| evaluation_observer_origin_class.tif | `02c2ca7ad6b2f5a57a4643a633c7ab36a0cf6fb0d2e42f2c912917e750f83497` |
| no_canopy_theoretical_zero.npy | `8b6c94bb34c17e17d6ecac95f8126df0fbbdc4a390f314c1bf4ce89ceffa8e2c` |
| manifest.json | `7718aaeb6014cc3505c98d71a1817800ca5a311b32f7613e3fd441d15d488081` |
| step2c4-gvi-benchmark-01/manifest.json | `db1d4ea0ddcc7e5e012624dcb5c4710384ebff0aee9c5bb02e1e9c83497899c1` |

実行環境はGEEKOM-A6／Windows-10-10.0.26300-SP0、OUEM Python 3.11.9、NumPy 2.4.6、Numba 0.68.0、rasterio 1.4.4／GDAL 3.10.3、pyproj 3.7.2。
HEADはPR #159マージ後 `0f43c329bb32da1105937017dee331a61098566e`。adapterは未追跡状態で実行したため、実バイトSHA `f669ca6a423ac40e9db0a2a81763c009ad1577daf6a82cddc3efb3309ea2c566` も記録した。
既存B2 SHAは `fa71402d6026c044167a4510628e62aae5409214dfe7b6445a7634c89d75575d` で変更なし。
VoxCity PEP 610と136 Python source filesのRECORD整合を確認したが、upstream Git treeとの独立バイト比較ではない。

## 実行と検証

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_gvi `
  --pair-run data/work/terrain-candidate-b/step2c2-canopy-final-a `
  --solar-run data/work/terrain-candidate-b/step2c3-solar-final-b `
  --source-run data/work/terrain-candidate-b/t5-23-02 `
  --output-dir data/work/terrain-candidate-b/step2c4-gvi-new-benchmark --benchmark

.venv/Scripts/python.exe -m ouem.candidate_b_gvi `
  --pair-run data/work/terrain-candidate-b/step2c2-canopy-final-a `
  --solar-run data/work/terrain-candidate-b/step2c3-solar-final-b `
  --source-run data/work/terrain-candidate-b/t5-23-02 `
  --benchmark-report data/work/terrain-candidate-b/step2c4-gvi-new-benchmark/manifest.json `
  --output-dir data/work/terrain-candidate-b/step2c4-gvi-new-run

.venv/Scripts/python.exe -m pytest -q -ra tests/test_candidate_b_gvi.py tests/test_b2_gvi.py tests/test_b2_gvi_synthetic.py
```

新規runのみ。負荷receiptは同じ入力identity・設定・実装に結び付いている必要があり、code/HEAD変更後のreceiptは再利用しない。
入力監査失敗は計算・出力前に非zero終了。後段失敗はBLOCKED、公開失敗はfailure.json。部分NPY/TIFF/pendingは完了を示さず、並行writer/resumeは非対応。
初期関連テストでreceiptのtuple/list正規化不備による2件の失敗を検出し、SHA・設定照合を緩めず修正した。
最終関連pytestは **74 passed、skip/deselect 0、43 warnings**（既存rasterio/Affine、VoxCity/matplotlib非推奨とAgg非対話show警告）。
正常/不正handoff、SHA・観測点不一致、解析的TREE内値、TREEなし公開API、負荷receipt・過大負荷停止、値域、部分書込/公開失敗、入力改変、全域2回→ROIの順序を検証した。
CI結果はDraft PR本文へ記録する。ログは `data/work/terrain-candidate-b/step2c4-related-final.log`。
ローカル全体pytestは繰り返さず、既存Windows/Ubuntu Actionsを全体回帰ゲートとする。PR #156のpip cache・`--durations=30`・既存合格条件は維持。

樹冠実在・CR、光学仮定、鉛直基準realization/epoch・精度、観測点の実眼高、角度・格子の収束、領域外遮蔽物、現地GVI精度は未検証。
Solarとの共通位置は確認したが、GVIと日射低減量の相関・因果関係を検証したとはしない。
