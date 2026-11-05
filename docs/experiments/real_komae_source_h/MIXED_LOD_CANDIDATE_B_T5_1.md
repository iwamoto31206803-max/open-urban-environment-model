# Candidate B T5-1 領域設計とDEM被覆

**COMPLETED / EXPERIMENTAL**。基点はPR #147マージ済みmain `1086193`。推奨領域は既存の4枚で全セルが有効で、追加取得は不要。T5-2での実格子検証へ進行可能と判定する。 `terrain_integration_ready=false`。 [T4-B2](MIXED_LOD_CANDIDATE_B_T4B2.md) · [T3](MIXED_LOD_TERRAIN_CANDIDATE_B_T3.md)

## 領域と対象

- **Evaluation AOI** はEPSG:6677の `[-22575,-39925,-22475,-39825]`。最終評価範囲の100 m四方。
- **Processing Domain** は元AOIと交差した63棟（LoD1 31、LoD2 32）の元3D形状と、A3方式で正規化した完全フットプリントを収める。最小包含矩形は `[-22586.607500,-39936.560000,-22462.440000,-39812.440000]`。T4-AとAOI内40棟・越境23棟のIDが一致した。各棟の元XY範囲、フットプリント範囲、東西南北の拡張距離はreport.jsonに記録した。
- **Source Coverage** は元DEMのマスクが有効で有限標高を持つネイティブ0.5 mセルの集合。DEMファイルの外接矩形とは別に集計した。

Evaluation AOIの格子原点を基準に境界を1 mの外側へ丸め、0.5 mの元格子にも整列させた。推奨はさらに四辺に1 mの余裕を加えた候補。意図は境界に接する建物と処理格子端を離すこと。日陰解析のバッファは、太陽条件と遮蔽物を踏まえて別途設計する。拡張域に新たに入るContext Buildingsは今回の63棟に加えず、将来の遮蔽物として別の選択・出典管理を行う。

| 候補 | EPSG:6677 bounds | 幅×高さ | Terrainセル数 | VoxCity想定セル数 |
|---|---|---:|---:|---:|
| 格子整列した最小範囲 | `[-22587,-39937,-22462,-39812]` | 125×125 m | 62,500 | 15,625 |
| 推奨、四辺に1 m追加 | `[-22588,-39938,-22461,-39811]` | 127×127 m | 64,516 | 16,129 |

VoxCityの値はmesh指定1 mでの公称値。T5-2では実際の原点・向き・寸法・中心座標と有効DEMセル中心の被覆を検査し、範囲外参照は拒否する。全63棟の所有セルとゼロ所有・競合も確認する。

## 有効被覆

| 候補 | 区部有効 | 多摩有効 | 両方 | どちらも無効 | 同一ソース内重複 |
|---|---:|---:|---:|---:|---:|
| 最小 | 26,823 | 41,073 | 5,396 | 0 | 0 |
| 推奨 | 27,771 | 42,225 | 5,480 | 0 | 0 |

| 元DEM | 最小 有効／採用 | 推奨 有効／採用 |
|---|---:|---:|
| 多摩2023 09LD3423 | 26,219／22,390 | 26,797／22,924 |
| 多摩2023 09LD3433 | 14,854／13,287 | 15,428／13,821 |
| 区部2024 09LD3423 | 21,610／21,610 | 22,288／22,288 |
| 区部2024 09LD3433 | 5,213／5,213 | 5,483／5,483 |

不足セルとその外接範囲は両候補ともなし。WARD_FIRSTで区部の有効値を優先し、欠損のみ多摩で補完する選択をメモリ上で確認した。既存T3と重なる全40,000セルは格子、採用値のFloat32ビット、出典IDが一致した。区部の水平・鉛直解釈は従来の条件付き根拠を継承する。補間・外挿・ゼロ充填・鉛直補正は適用していない。格子化、ボクセル化、正式Terrain生成は今回の検証範囲外。

## 再現と証跡

GEEKOM-A6のOUEM Windows venvで実行。新規runを指定する。

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_t5_1 `
  --building-run data/work/mixed-lod-standard/run-02 `
  --consumer-receipt data/work/mixed-lod-consumer/run-04/receipt.json `
  --terrain-run data/work/terrain-candidate-b/t3-02 `
  --t4a-report data/work/terrain-candidate-b/t4a-02/report.json `
  --input-run data/work/terrain-candidate-b/run-03 `
  --output-dir data/work/terrain-candidate-b/t5-1-repro
```

入力は固定SHA-256で照合し、公開前に再確認した。

| 入力 | SHA-256 |
|---|---|
| building_manifest | `9789d443e0286ad0c5da57156d7ba10ed19adafba5e42cec068e9deeead0f789` |
| consumer_receipt | `1f9de8a7bdd7c92fd455f7c3897f45d8280dff05da90634f2aa677a86298e415` |
| terrain_manifest | `66c0c835a2a448140dbce905cf2be3af3942b809ce72788bb0e4c81be953b1ab` |
| building_gpkg | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |
| terrain | `4b38efbfdca1535983a691cba4a18592fe332e87072f05b70d1bebff4759f193` |
| source_tile | `7ee11d4b757c3b73b1d1467e76a02d6501cd8763274477e3f6a006a7c0962c5a` |
| terrain_validation | `f8e18193e225f94e9fd45cf721a948b47d11e97316b8ee5f4bc38e97a5adb936` |
| t4a_report | `7fdc8839f785b54467dd6b67db5090caa34d9286a36a798cfae0d1ec0a5005d9` |
| tama/09LD3423 | `8b92f4ce3cb72f6084858df629b0cc676cd7cd45e6973942f0a9cf0c793b34ca` |
| tama/09LD3433 | `491defd8c37fb52241d73ae4bd2142c605056133b51a320a750aeddfb9018d92` |
| 23ku/09LD3423 | `62b98534376827a0906b6703522764356e20eb5c2d8ef53ac36b1ea3e3e6b8b8` |
| 23ku/09LD3433 | `66190876d0baab6aa25fb518a6e4827d45b78286a2e3fa385e0fe9b61f7eb18c` |

出力はGit管理外の `data/work/terrain-candidate-b/t5-1-01` と `t5-1-02` に保存した。2回のSHA-256は下記の通り一致。マスク配列は北から南の行、西から東の列。各ビットの重み1、2、4、8は上表のタイル順（多摩2枚、区部2枚）。値0はどの元タイルにも有効値がないセル。標高ラスタは書き出さない。

| 出力 | SHA-256 |
|---|---|
| report.json | `2b832f2c3a146812e3e77a4363e80058b33996c6b80e62eb9f141cbd540832b9` |
| aligned_minimum_tile_validity.npy | `a78e3ca6f2f11b3c30c02bbdfccb9f59ad15f8a87e0849d1211c2f742cd412f4` |
| one_mesh_margin_tile_validity.npy | `843af5e7e920cd69e0d9955428b5511c68e221867a6a4a67feeca8f4014fc703` |

関連pytestは23件通過。合成検証では負座標での外丸め、境界、ゼロ標高、マスク欠損、ソース優先順位、同一ソース内重複を確認した。T3・T4-Aは固定入力として、T4-B1/B2の代表出力は保存済みハッシュで照合した。旧A3の歴史的固定パスは前回と同様に直接照合の対象外。
