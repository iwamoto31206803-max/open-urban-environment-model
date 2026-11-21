# 国立市 09LD1122 — A2 Terrain個別受入審査資料

**審査状態 — REVIEW_PENDING。** 対象は下記SHA-256のStandard TIFF一件。技術QAは確認済み。正式な個別受入、科学的妥当性、CHMとの互換性は未判定。[実行報告](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/215#issuecomment-7056325500)・[報告の独立レビュー](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/215#issuecomment-7056353682)・[今回の作業承認](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/215#issuecomment-7056374303)

## 原本と処理来歴

- 東京都 Tokyo Digital Twin Tama ground grid 0.50m / 09LD1122。保存先は `data/raw/terrain/tokyo_tama_dem_050m/kunitachi-preflight-20261030-01/`。取得receiptが原本を特定する。[国立市事前調査](../planning/OUEM_Kunitachi_Data_Source_Preflight_v0.1.md)
- GEEKOM-A6、Windows、既存OUEM venv Python 3.11.9。実行HEADは `7d9249ae1a09bca4ea7f308063f6dcfe76e593c0`、比較したGitHub mainは `5df4337ff652664cf80608d2c02d2f8d721ab047`。Native／Standard実装、両CLI入口、Study Area loader、国立市2 km設定、TerrainテストのGit blobが一致。
- 既存 `ouem.native.terrain` でRAWを参照するmanifestを登録し、`ouem.standardize.terrain` を既存 `kunitachi_2km.yaml` で実行。出力は原タイル全体。今回の審査準備では既存成果を再読込し、再生成は行っていない。

| 保存ファイル | SHA-256 |
| --- | --- |
| RAW `09LD1122.tif` | `1d5591dacef1da49193c7e3fc22d55c7b7f19c425ad00b1e4b70e99ba9b02c27` |
| RAW `download-receipts.json` | `047d6844f76d2b086f04379c81d5823e606ffefaf93b9d8e25b22a455819f381` |
| `native.json` | `a3f4c0b116766dabae559bc4c54b2287b90c52c13f51c3ed1d12b2a3586d333e` |
| `standard.tif` | `e361663312a7d2c72308ba6a97bbf67411b7d0fffdefa871301684821147c124` |
| `standard.tif.manifest.json` | `b7bafcf13d66e2991f7cc1fce364b116149cde4aaa83474d68b4b43bee54840b` |

出力3ファイルは `data/work/kunitachi-terrain-09ld1122-0ae94113b7/` に保存。RAWと出力はいずれもローカルデータ。上記5ファイルは今回の再読込の前後で同一SHA。

## 技術QAと個別審査の論点

- 既存Native loaderで原本SHA・メタデータを照合。直接開いたRAW・Standardでも、EPSG:6677、800×600、単バンドFloat32、0.5 m、Affine `[0.5,0,-35200,0,-0.5,-33600]` を確認。有効480,000点、欠測0、全有効値とマスクが完全一致。標高範囲72.212–76.342 m。NoData宣言は `1.701410009187828e38` から `-9999.0` に正規化。
- 鉛直は提供元宣言の `source-declared` T.P. (Tokyo Peil / Tokyo Bay mean sea level)。Native、Standardタグ、manifestの名称・状態とmanifestの出典参照が整合。[東京都多摩データカタログ](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020)・[Terrain契約](../OUEM_Standard_Terrain_v0.1.md)
- 候補 `[-35032,-33782,-34968,-33718]` の北上1 m格子で4,096中心が有効、RAWとStandardの値が一致。エンジン実格子の確認は後続工程。
- 既存 `tests/test_standard_terrain.py` を再実行し9件合格。Rasterio/AffineのPendingDeprecationWarningが8件。これは同一性・構造・変換の技術検証。

独立レビューでは、上記の原本来歴、提供元の標高宣言、正確なStandard出力SHA、値・格子・マスクの保存を根拠として、**この出力一件**を個別受入とするか判断する。既存の[狛江A2記録](OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)は書式・審査観点の参照。測量精度、T.P.実現・時点、他地域への適用、CHM推定地盤との整合は未確認。正式受入とHeight Envelope用のcompatibility reviewは別の判断。
