# Candidate B T5-2 / T5-3 拡張TerrainとVoxCity統合

**Gate 1 PASS / Gate 2 PASS / EXPERIMENTAL**。PR #148を取り込んだmain `bb50bfd` を基点にGEEKOM-A6のWindows OUEM venvで実行。 `terrain_integration_ready=false`。T4の鉛直基準の留保を継承する。区部T.P.は点群からの継承推定であり、測量時期の整合、datum realization、標高精度は未検証。 [T5-1](MIXED_LOD_CANDIDATE_B_T5_1.md) · [T4-B2](MIXED_LOD_CANDIDATE_B_T4B2.md)

## Gate 1 — T5-2

Processing DomainはEPSG:6677の `[-22588,-39938,-22461,-39811]`。原GeoTIFF 4枚を固定SHAで照合し、T3の有効マスク・WARD_FIRST選択処理を再利用した。0.5 mの254×254全セルで元値を採用し、再読込したFloat32標高と出典IDを検証した。既存T3と重なる40,000セルは両方とも完全一致。区部27,771セル、多摩36,745セル。Terrainと出典のNoData宣言は−32767と0。補間、外挿、鉛直補正なし。

VoxCity 1.7.0の固定コミット `fa212656305328a9a657973bae26f352bfe813bc` で実格子を計算した。実寸法127×127、南西原点 (139.583915791715°, 35.639760221126°)、第0軸は北、第1軸は東。調整間隔は約1.000094 m。全16,129中心が領域とDEMの有効セル中心凸包の内側にあり、UTMで独立に確認した最近傍値とエンジンのDEMが全値一致した。最大最近傍距離0.353514 m。A3派生フットプリントと元3DのXY範囲はいずれも処理域内で、元形状・絶対Zを保存した。

元Evaluation AOIと交差する63棟（LoD1 31、LoD2 32）に決定的な数値IDを割り当てた。**全63棟が5,347セルを所有**（棟別4～231セル）。ゼロ所有、再割当、単棟候補外の所有は0。精密格子は2回で所有が収束し、最終再格子化でもIDと高さが一致した。競合は1セル。ゼロ所有や棟のフラグはREVIEW_REQUIRED、所有の不収束や格子不整合、被覆外参照などはFAILとし、いずれもGate 2はNOT_RUNとする。

T4の40棟について、source_id・ouem_id・絶対上端Zは全数一致した。T4の全中心から新格子の最近傍への最大距離は0.000325 m。T4の所有2,998列のうち2,997列で同じsource_idが所有した。各棟の有効地盤平均と相対高さの最大差はともに0.001194 m未満。数値IDは新しい63棟の集合で割り当てた。

## Gate 2 — T5-3

Gate 1のPASS後に固定エンジンの `Voxelizer.generate_combined` を実行した。出力は **127×127×12**。Z基準は23.959999084 m。所有IDで地盤を平均した後、代表高さ `max(Z_abs) − G_eff_abs` と `min_height=0` を適用する。T4-B2と同じ監査で実クラスと地盤・全セグメントの占有を照合し、全63棟に単棟帰属可能な建物ボクセルを確認した。

| 項目 | 結果 |
|---|---:|
| 建物ボクセル | 36,405 |
| 地盤表面と有効DEMの最大絶対差 | 0.500000 m |
| 地盤表面と生DEMの最大絶対差 | 0.650002 m |
| セグメント包絡と再構成上端の最大絶対差 | 0.797600 m |
| 棟別Standard上端との差、A3上面方式 | 最大1.763479 m（許容2.0 m） |
| 浮き・地盤侵入・占有中の空隙 | 各0列 |

競合セル `[61,96]` はT4の `[48,83]` と地理的に対応する。新ID 45と55の高さセグメントはそれぞれ5.059462 mと2.885000 m、所有IDは55。占有はk=2～6で、k=5～6はID 45のセグメントだけが説明する。競合列は棟別屋根誤差から除外した。T4との地理比較で、同一source_idの非競合2,996列の絶対屋根高を比較し、最大差は0.809999 mだった。地盤の量子化と領域別のZ基準を含む離散モデル上の差。

Evaluation AOI `[-22575,-39925,-22475,-39825]` はEPSG:6677の中心座標を半開区間で判定して10,000列を抽出し、元格子の添字と中心座標を保存した。62棟が評価域内で所有列を持ち、うち22棟が越境棟。残る越境棟 `bldg_eeed3575-1ab7-487f-bccb-56714e1daf78` は処理域内で72セルを所有し、その所有セル中心はすべて評価域外だった。評価域の離散化に起因するため、建物の追加、除外、形状クリップは行っていない。Context Buildingsは今回の対象外。

## 再現と検証

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_t5 `
  --building-run data/work/mixed-lod-standard/run-02 `
  --consumer-receipt data/work/mixed-lod-consumer/run-04/receipt.json `
  --terrain-run data/work/terrain-candidate-b/t3-02 `
  --input-run data/work/terrain-candidate-b/run-03 `
  --preflight data/work/terrain-candidate-b/t5-1-01/report.json `
  --old-grid data/work/terrain-candidate-b/t4b1-04 `
  --old-voxel data/work/terrain-candidate-b/t4b2-02 `
  --output-dir data/work/terrain-candidate-b/t5-23-repro
```

新規runのみ使用する。T5-2とT5-3の出力は別ディレクトリに置き、両Gateの状態と入力・出力SHAを最後の `report.json` に記録する。中断時は完了レポートなし、失敗時の出力は診断用として扱う。再実行 `t5-23-02` と `t5-23-03` で出力SHAとレポートが一致。レポートSHAは `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f`。ログと生成物はGit管理外の `data/work/terrain-candidate-b/` に保存。

| 出力 | SHA-256 |
|---|---|
+| `t5-2/building_height.npy` | `133076e8455c3f69edf93882a44048637a0f1f6d59475b292b58887e8ddd1afd` |
| `t5-2/building_ids.npy` | `aff4a3da1d709749d43d373cb5e4cd0c01885ddcad555fb9291c617c79022eea` |
| `t5-2/centres_xy.npy` | `a477bc6700c45f032308948a7e1754c9ff0a15cfa2d888a0ca655480d5ef8ffc` |
| `t5-2/dem.npy` | `1e140b13690380e0750ad8a614cf8575ede315d9ae35d521bcb4c7f8b0602464` |
| `t5-2/evaluation_mask.npy` | `07f9245c6e8fcaabbdaaaaff348ddd0b81875db567008d4c93d1675a6ccdf922` |
| `t5-2/isolated_claim_count.npy` | `ac96fe514dccf833f72fe6dff6c9623b78788ab657562b18877de40549285925` |
| `t5-2/source_tile.tif` | `2db8434d2aaf3297c33de1696971021a42f434f917027f010efd1453c096c1ad` |
| `t5-2/terrain.tif` | `ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2` |
| `t5-2/terrain_row_col.npy` | `9146b38591204bd1be35958c6a134e5ee717bec3545bd8535120967f7d85716f` |
| `t5-3/effective_dem_abs.npy` | `afc46253022b203eda78aa0026ad36cb5d6c4d4f34d8d07d6d3d22d487778853` |
| `t5-3/evaluation_centres_xy.npy` | `0314d07aaf3a0fea006b171a74bb58aa5b6d11dbc17d7dda576d9e99acbaccce` |
| `t5-3/evaluation_indices.npy` | `ed870f042c979e15b08c747537151e366a49b505a9165cc58f811db1bf60a4e5` |
| `t5-3/evaluation_voxels.npy` | `8864ba127c9f618cd004e84ecb30250eb58b2fe5ff0c611be86cc6c7ed0b40fb` |
| `t5-3/segments.json` | `9b5b567a6782bcbe090334ebda1eef3d60b3a3aa57c3a5b5c80eaa21555e783c` |
| `t5-3/voxels.npy` | `350e08696bf6b73cd26e8bebcea63f3e7208e2df28cf0ac13a8affbea35bd54d` |

関連pytestは28件通過。合成検証は中心座標での境界抽出、ゼロ所有のレビュー判定、不正入力時のボクセル化停止、source_idと座標によるT4比較を含む。固定済みT3/T4の入力は実行前後にハッシュ照合した。共有DEMサンプリングhelperに明示的な領域引数を追加し、T4-B1の既定値は従来のEvaluation AOIを維持する。
