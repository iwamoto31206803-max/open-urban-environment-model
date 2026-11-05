# STEP 2-A Mixed-LoD Building-only Shadow E2E

**COMPLETED / EXPERIMENTAL**。PR #153マージ後main `21a5f5a` を基点に、GEEKOM-A6のWindows OUEM venvで実施した。 `terrain_integration_ready=false`。 [E1設計](../../planning/OUEM_Candidate_B_E1_Minimal_Shadow_Design.md) · [STEP 1](STEP1_COMPATIBILITY_PROBE.md) · [保存T5モデル](MIXED_LOD_CANDIDATE_B_T5_23.md)

## 入力と接続

Git管理外 `data/work/terrain-candidate-b/t5-23-02` の成功reportをSHA-256 `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` で固定した。63棟（LoD1 31、LoD2 32）、Processing Domain `[-22588,-39938,-22461,-39811]`、Evaluation AOI `[-22575,-39925,-22475,-39825]`、保存127×127×12配列を使用した。 `t5-3/voxels.npy` のSHAは `350e08696bf6b73cd26e8bebcea63f3e7208e2df28cf0ac13a8affbea35bd54d`。

STEP 1の読取マッピングを `compatibility_probe.load_candidate` に取り出し、既存STEP 1 launcherもこれを利用する。保存済み全出力のSHA、D0=23.959999084 m、原DEMと所有ID別平均地盤、XYZ中心、ROI、クラス・source_id対応、観測点を共通Probeで検査した。NPYはread-only mmapで読み、処理・出力の後にも元ファイルを再ハッシュした。今回のProbeはT5への数値handoff検証であり、RawからのConsumer再実行は含まない。

## 計算条件と実装範囲

固定VoxCity **1.7.0 / fa212656305328a9a657973bae26f352bfe813bc** をインストールメタデータで検証した。E0で確認した既存CPU関数 `voxcity.simulator.solar.kernels.compute_direct_solar_irradiance_map_binary` に全127×127×12配列を直接渡した。新しい光線追跡法、再Voxel化、追加Terrain処理は含まない。

- 太陽は真北起点の方位180°、高度45°。保存地理格子の軸0は真北に対し−0.145335°。地理的な格子方位を引いた光線ベクトルは約 `[-0.707104506,-0.001793627,0.707106781]`。軸0は南→北、軸1は西→東、軸2は上。
- 観測高さは0 m要求。最初の表面遷移の空気セル中心で、実座標はD0+k+0.5 m。地表面そのものの精度を保証する評価点ではない。屋根無効、全建物列を `any(voxels==-3,axis=2)` で対象外にした。
- `hit_values=(0,-1,1)`、`inclusion_mode=False`。建物だけを遮蔽物とし、地盤は観測点位置に反映する。TREEクラスは拒否した。API引数k=.6、LAD=1はTREEなしでは結果に影響しない。
- 計算後に保存中心座標のROIマスクで抽出。0=日陰、1=日向、255=対象外。予期しないNaN・非二値・不正開始点は拒否する。

## 実測結果

| 範囲 | 総セル | 日陰 | 日向 | 対象外（建物列） | 有効セル中の日陰率 |
|---|---:|---:|---:|---:|---:|
| Processing Domain | 16,129 | 3,197 | 7,585 | 5,347 | 29.6513% |
| Evaluation AOI | 10,000 | 2,270 | 3,608 | 4,122 | 38.6186% |
| 評価域外 | 6,129 | 927 | 3,977 | 1,225 | 18.9029% |

有効評価セルは5,878。その他対象外・予期しないNaNは0。評価域を50 m四方に分けると、NW/NE/SW/SEの日陰セルは471/557/583/659、有効セル中の日陰率は31.74/34.13/40.04/50.46%。出力GeoTIFFを北向きの分類図として確認し、建物の北側に日陰が伸びる分布を確認した。確認図はGit管理外の `data/work/terrain-candidate-b/step2a-review.png`。QGIS GUI検証は未実施。

## GeoTIFFと再現性

EPSG:6677、100×100、北向き1 m、Affine `(1,0,-22575,0,-1,-39825)`、NoData=255。実セル中心を座標で割当て、重複・未割当・範囲外は0。登録誤差の最大は **0.001436056 m**、設計上限0.01 m以内。出力は元のエンジン格子と完全に同じaffineではなく、検証した中心対応による公称1 m格子への分類値配置。入力の位置精度を保証する値ではない。

GeoTIFFの再読込で値・マスク・CRS・Affine・dtype・NoDataと四隅のセル中心、中央付近のセル中心を検証した。外接範囲も一致し、範囲中央は `[-22525,-39875]`。例として左上中心は `[-22574.5,-39825.5]`、右下中心は `[-22475.5,-39924.5]`。南北方向を座標で確認し、転置していない。

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_shadow `
  --source-run data/work/terrain-candidate-b/t5-23-02 `
  --output-dir data/work/terrain-candidate-b/step2a-repro
```

新規runのみ使用する。完了マーカー `report.json` はステージ内監査と入力再照合後に最後に公開し、失敗時は `failure.json` に理由を残す。部分ファイルは完了の証拠にしない。 `step2a-03` と `step2a-04` はreportと全出力SHAが一致した。各runの外側に同名 `.log` を保存した。

| 出力 | SHA-256 |
|---|---|
| report.json | `c968c8a754e2a9bc0eeb2fa4a4b24a165021c1a518f6d99e76643ad8a8af81af` |
| domain_classes.npy | `1f9a2be8b775613fe6a611eaa0fda03c59e50d510174592ab85fa8b210276305` |
| evaluation_classes.npy | `80b5559c500a0966738d10793c430846877cfdeb82a65049f30e5b90f78dac02` |
| evaluation_indices.npy | `ed870f042c979e15b08c747537151e366a49b505a9165cc58f811db1bf60a4e5` |
| evaluation_shadow.tif | `3a0cb2c88ad3a2dfcfe6f13e8b24215f53c30e4075845403e3e08dcee3703db4` |

## 検証と限界

合成・関連pytestは34件通過、Rasterioの将来の非推奨警告1件。南向き光線、回転格子、建物有無、全域計算後のROI抽出、建物除外、非正方形GeoTIFF、0/1/255、ハッシュ・クラス・観測点不正、入力不変、再現性、出力失敗を確認した。

共通reader抽出後のSTEP 1 launcher出力は、保存済み `step1-probe-a-final.json` とバイト一致した。回帰pytestでは今回のGVI実行禁止を優先し、`tests/test_b2_gvi.py`・`tests/test_b2_gvi_synthetic.py`・`tests/test_b2_gvi_qgis.py` を除外する。実行ログは `data/work/terrain-candidate-b/full-step2a.log`。最終結果はPR本文に記録する。

技術的E2Eの成立は、保存モデルから指定条件の分類と地理出力まで。Context Buildingsと領域外の遮蔽物、領域の十分性、1 m形状量子化、現実の日陰精度、鉛直基準のrealization・epoch・accuracy、正式Terrain統合は未検証。領域外へ抜けた光線はモデル内の遮蔽物がなければ日向となる。既存B1の樹冠差分・W/m²指標とは評価条件を区別する。
