# 国立市 09LD1122 — Standard Terrain v0.1 個別受入

| 項目 | 決定 |
| --- | --- |
| Status | **ACCEPTED** |
| Standard output SHA-256 | `e361663312a7d2c72308ba6a97bbf67411b7d0fffdefa871301684821147c124` |

2026-11-21のプロジェクトオーナー判断Aに基づく。対象は保存済み東京都多摩地盤タイル09LD1122から生成された上記SHAのStandard TIFF一件。鉛直宣言は提供元の `source-declared` T.P. (Tokyo Peil / Tokyo Bay mean sea level)。受入は原本来歴、値・格子・マスクの保存とTerrain v0.1の技術適合性に限定する。測量精度、鉛直基準の実現・時点、CHM推定地盤との互換性、他成果・他地域への適用は未検証。[オーナー判断](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/215#issuecomment-7056776092)・[東京都提供元](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020)

- 入力RAW `09LD1122.tif` は `1d5591dacef1da49193c7e3fc22d55c7b7f19c425ad00b1e4b70e99ba9b02c27`、取得receiptは `047d6844f76d2b086f04379c81d5823e606ffefaf93b9d8e25b22a455819f381`。出力側のNative manifestは `a3f4c0b116766dabae559bc4c54b2287b90c52c13f51c3ed1d12b2a3586d333e`、Standard manifestは `b7bafcf13d66e2991f7cc1fce364b116149cde4aaa83474d68b4b43bee54840b`。保存出力は `data/work/kunitachi-terrain-09ld1122-0ae94113b7/`。
- CodexがGEEKOM-A6で再ハッシュ、Native再読込、全480,000セルの標高値とマスクの一致を確認。EPSG:6677、800×600、0.5 m、Float32、Affine `[0.5,0,-35200,0,-0.5,-33600]`、欠測0、NoData宣言は−9999.0へ正規化。Native／Standard manifestの鉛直宣言とStandard TIFFタグを照合。独立レビュアーは報告証拠をレビューした。
- 元の変換はWindows、Python 3.11.9、ローカルHEAD `7d9249ae1a09bca4ea7f308063f6dcfe76e593c0`。当時のmainと関連Terrain blobが一致し、今回main由来 `7b0ce79b11f2c50346a2b94312a784877bcf972e` でも保存データを再検証。元のローカルTerrainテストは9件合格、警告8件。追加ローカル回帰は未完了。審査資料PRのUbuntu・Windows CIは成功。[準備履歴](OUEM_A2_Standard_Terrain_Kunitachi_09LD1122_Review_Draft.md)・[CI](https://github.com/iwamoto31206803-max/open-urban-environment-model/actions/runs/44860760257)

狛江A2と独立の個別記録。CHM＋DEM技術シナリオは別決定に従う。