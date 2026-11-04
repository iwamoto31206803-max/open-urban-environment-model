# Candidate B Terrain T3 experimental preparation

**EXPERIMENTAL / NOT_FORMALLY_ACCEPTED**。T0 CONDITIONAL PASS、T1 PASS、T2 WARD_FIRSTは候補Bの隔離実験に限定して承認。T3実測は `COMPLETED`、`terrain_integration_ready=false`。基準mainはPR #142を含む `d1641cb`。 [統合判断設計](../../planning/OUEM_Candidate_B_Terrain_Integration_Decision_Plan_v0.1.md) · [入力実測](MIXED_LOD_TERRAIN_CANDIDATE_B_PREFLIGHT.md) · [T1接合診断](MIXED_LOD_TERRAIN_CANDIDATE_B_DIAGNOSTICS.md)

## 入力・実行

GEEKOM-A6の通常Windows OUEM venv（Python 3.11.9、Rasterio 1.4.4）で2026-11-05 00:18 JSTに実行した。PR #141の `run-03` に保存された4原TIFFを再利用し、固定SHA-256を処理前・読取時・公開前に照合した。再取得は不要。入力の個別ハッシュ、アフィン、NoData、元マスク情報はmanifestに記録する。

```powershell
.venv/Scripts/python.exe -m ouem.terrain_candidate_b_t3 `
  --input-run data/work/terrain-candidate-b/run-03 `
  --output-dir data/work/terrain-candidate-b/t3-repro
```

対象はEPSG:6677、bounds `[-22575,-39925,-22475,-39825]`、200×200、0.5 m。元TIFFの整列したセル中心と有効マスクを使用し、区部の有効値を優先する。区部が欠損・範囲外なら有効な多摩の原値を使う。有効な0 mを保持する。両ソース欠損、同一ソース内の有効タイル競合、格子・SHA不一致、出力NoData値との衝突は停止条件。

区部の水平CRSはT1で記録した条件付き解釈を使用。元ファイルのラベルは保持し、アフィンに追加のシフトを加えない。区部T.P.は点群の公式説明からの継承推定で、DEM自体の鉛直datum実現・標高epoch・測量間の精度一致は未確認。再投影、補間、平均化、平滑化、鉛直変換とオフセットは適用していない。

## 実測

| 出典ID | 元TIFF | 採用セル |
|---:|---|---:|
| 1 | 多摩2023 / 09LD3423 | 16,318 |
| 2 | 多摩2023 / 09LD3433 | 7,579 |
| 3 | 区部2024 / 09LD3423 | 13,682 |
| 4 | 区部2024 / 09LD3433 | 2,421 |

全 **40,000** セル有効。区部 **16,103**、多摩 **23,897**。標高範囲は24.141～25.499 m。再オープン監査で、全セルの原Float32ビット列、採用タイルID、格子、CRS、マスク、NoDataを照合した。独立確認では、AOI中心座標を各元TIFFの逆アフィンで行列へ戻し、4マスクから優先順に選択して出力と全セル一致した。

WARD_FIRSTの切替は284辺（東200・南84）。切替MAEは東0.043905 m、南0.030798 m、最大絶対ジャンプ0.172001 m。再オープンした標高の全切替辺のジャンプはT1と一致した。最大重複差は (−22512.75, −39870.75) の区部−多摩 −0.656000 m。採用値は区部09LD3423の24.549999 m。絶対差0.50 m超の47セルはすべて区部採用で、採用標高は24.490～24.590 m。切替辺の端点に該当するセルは0、最短の辺中点距離は1.601 m。全47セルの座標・採用標高・タイルID・重複差は `validation.json` に記録した。

## 出力と完了条件

Git管理外の `data/work/terrain-candidate-b/t3-02/` に保存した。

| 成果物 | 内容 | SHA-256 |
|---|---|---|
| `artifacts/terrain.tif` | 1バンドFloat32、NoData −32767、全セル有効 | `4b38efbfdca1535983a691cba4a18592fe332e87072f05b70d1bebff4759f193` |
| `artifacts/source_tile.tif` | 同じ格子のUInt8、NoData 0、ID 1～4をmanifestに対応付け | `7ee11d4b757c3b73b1d1467e76a02d6501cd8763274477e3f6a006a7c0962c5a` |
| `artifacts/validation.json` | 全セル照合、切替辺集計、外れ値詳細 | `f8e18193e225f94e9fd45cf721a948b47d11e97316b8ee5f4bc38e97a5adb936` |
| `manifest.json` | 完了マーカーと出典・入出力ハッシュ | `66c0c835a2a448140dbce905cf2be3af3942b809ce72788bb0e4c81be953b1ab` |

一時領域で検証後に成果物を移し、完了manifestを最後に公開する。失敗時は `BLOCKED` と原因を `failure.json` に記録。完了manifestを欠くrunの部分ファイルは利用対象外とし、再実行には別のディレクトリを使う。

関連pytestは44件通過、13件警告。新規合成テスト10件で欠損、符号付きゼロ、同一ソース競合、SHAと格子の不一致、書込失敗、再オープンでのビット改変検出、完了マーカー公開失敗とrun再使用を検証した。別集計コードとログは `data/work/terrain-candidate-b/audit-t3.py` と `audit-t3.log`。A2再現TerrainとA3 VoxCity配列は記録済みSHA-256と一致した。

全体pytestは1,224件通過、10件skip、341件警告（710.90秒）。skipは専用GIS/QGIS Python 5件とWindows symlink権限5件。ログは `data/work/terrain-candidate-b/full-t3.log`。

この実験用Terrainは既存の単一入力Standard Terrain契約の外に置く。正式な標準化、Mixed Buildingとの鉛直整合、VoxCityとT4判定は未実施。
