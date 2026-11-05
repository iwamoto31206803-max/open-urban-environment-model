# Candidate B VoxCity 3D Voxel Integration — T4-B2

**COMPLETED / EXPERIMENTAL / NOT_FORMALLY_ACCEPTED**。候補Bの固定入力・40棟だけを対象とする。AOIはEPSG:6677、`[-22575,-39925,-22475,-39825]`、水平・鉛直mesh指定は1 m。AOI越境23棟のID・理由は出力レポートに保持した。 [T4-B1](MIXED_LOD_CANDIDATE_B_T4B1.md) · [T3](MIXED_LOD_TERRAIN_CANDIDATE_B_T3.md)

## 鉛直基準の判断履歴

| 入力 | 鉛直基準の根拠 |
|---|---|
| Mixed Standard Building | Source-HのEPSG:6697の鉛直成分EPSG:6695（JGD2011 gravity-related height）を保持。国土地理院は日本の標高基準を東京湾平均海面と説明する。 [Mixed Standard](MIXED_LOD_STANDARD_POC.md) · [国土地理院](https://www.gsi.go.jp/sokuchikijun/datum-main) |
| 多摩2023 | 配布元のT.P.明示を採用。 [T0の出典整理](../../planning/OUEM_Candidate_B_Terrain_Integration_Decision_Plan_v0.1.md#t0-conditional-vertical-assumption) |
| 区部2024 | 世田谷区ダウンロードメッシュの公式ビューア説明における点群T.P.表記はT0で利用者提供の証拠として記録済み。2024年10月31日の東京都報道発表は元点群と0.5 mグリッドを同事業の掲載データとして示し、公式カタログは0.50 m GeoTIFFを地盤点群から生成したと説明する。この系譜を根拠に、元点群のT.P.がDEMへ継承されたと推定する。個別TIFFへの直接宣言は確認できていない。 [東京都報道発表](https://www.metro.tokyo.lg.jp/information/press/2024/10/2024103126) · [公開データ一覧](https://www.metro.tokyo.lg.jp/documents/d/tosei/11_01_473) · [東京都カタログ（0.50 m）](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000024/resource/0129940e-e3dc-4a5e-9ac9-929bfebc6d11) |

T0からT4-B1までの `CONDITIONAL` を履歴として維持する。T4-B2では、明示された基準と公式系譜による継承推定を、候補Bの隔離実験で同一の公称鉛直基準を使うための根拠とし、適格性を **PASS提案** とする。測量時期の整合、datum realization、標高epoch、標高精度は未検証。鉛直変換・オフセット補正なし。 `terrain_integration_ready=false`。公式カタログの親ページは取得制限があり、製品別記述はカタログの公開索引でも照合した。 [東京都カタログの公開索引](https://search.ckan.jp/datasets/catalog.data.metro.tokyo.lg.jp__dataset%3At000029d0000000024)

## 実行と照合

GEEKOM-A6の通常Windows OUEM venvで実行。VoxCity 1.7.0の固定コミット `fa212656305328a9a657973bae26f352bfe813bc` をインストールメタデータで確認した。B1成功レポートと6格子のSHA、T4-A・Consumer・Mixed Standard・T3の固定SHAと入力の結合関係を確認した。生DEMはB1の10,000値を再利用し、補間・外挿なし。GPKGから元の最大Zを再確認し、A3の派生footprint処理と精密格子化でセグメントを再生成した。所有ID・高さ格子はB1と全値一致した。 `G_eff_abs` は所有セルの生DEM平均、`height=max(Z_abs)-G_eff_abs`、`min_height=0`。樹木なし、表面クラス1で固定エンジンの `Voxelizer.generate_combined` を実行した。

実配列は `(100,100,11)` のint8。南西を水平原点として第0軸は北、第1軸は東、第2軸は上。エンジンは生DEMの最小値を引き、所有IDごとに地盤を平均してから、処理後の最小値がゼロになるよう正規化する。今回の生DEM最小と処理後の絶対標高最小はいずれも24.1499996185 m。監査は地盤表面クラスの添字kに対して `Z=基準+k×1m` を使用し、建物の上端は最高占有添字で同様に比較した。A3方式の上面評価は最高占有添字に1層加え、別に集計した。 [A3受入記録](../../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)

| 実測項目 | 結果 |
|---|---:|
| 建物の所有列／単棟に帰属できる列 | 2,998／2,997 |
| 単棟に帰属できる占有を持つ建物 | 40/40（LoD1 19、LoD2 21） |
| 建物／地中／表面／空気のボクセル数 | 20,401／5,826／10,000／73,773 |
| 地盤表面と所有平均適用後DEMの最大絶対差 | 0.500000 m（許容0.500001 m） |
| 地盤表面と生DEMの最大絶対差 | 0.670000 m（内訳として所有平均による変更の最大絶対値は0.305165 m） |
| 全建物列のセグメント上端包絡に対する最大絶対差 | 0.953480 m（地盤と高さの丸めを合算、許容1.000001 m） |
| 単棟に帰属できる列のStandard最大Zとの差 | 最大絶対0.953480 m。A3上面方式では1.953480 m（許容2.0 m） |
| 地盤直上から離れた列・地盤への侵入・建物内部の空隙 | 各0（この代表高さモデルの格子上） |

これらは入力値と離散モデルの整合性の評価。元の建物底面の接地精度や測量成果間の標高一致は評価していない。

### 競合セル

`[48,83]`（EPSG:6677で約 −22491.500463, −39876.500087）の所有IDは35、適用地盤は24.615000 m。単棟の格子化でID 28の高さ5.059462 m、ID 35の高さ2.885000 mを確認し、全棟のセグメントと多重度込みで一致した。両者の下端は0 m、丸め後の範囲は順に `[1,6)` と `[1,4)`。最終クラス−3はk=1～5で、k=1～3は両セグメントが説明し、k=4～5は28のセグメントだけが説明する。最終配列は棟IDを保持しないため、この列を単棟屋根統計から除外した。

## 再現と出力

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_t4b2 `
  --building-run data/work/mixed-lod-standard/run-02 `
  --consumer-receipt data/work/mixed-lod-consumer/run-04/receipt.json `
  --terrain-run data/work/terrain-candidate-b/t3-02 `
  --b1-run data/work/terrain-candidate-b/t4b1-04 `
  --output-dir data/work/terrain-candidate-b/t4b2-repro
```

新規runのみ使用する。 `report.json` を最後に公開し、失敗時は `failure.json` にBLOCKEDと理由を保存する。既存runとAccepted A2/A3は読み取り専用の範囲に保った。入力のパス・SHAはレポートに記録し、公開直前に再検証した。 `data/work/terrain-candidate-b/t4b2-02` と `t4b2-03` は4ファイルとも同一バイト。実行ログは同じ親ディレクトリの `t4b2-02.log` と `t4b2-03.log`。

| 出力 | SHA-256 |
|---|---|
| report.json | `5105b192961e771cf24336ab2dc36ed84c1b3d14e2d591d140968634f67978b9` |
| voxels.npy | `44bc3982807aadd05b3676ae76b06c166b6eb050357ecd685697c79ae7d5e1d7` |
| effective_dem_abs.npy | `dccaf076bfd6c653219395b788968b2d711f2bea9b4c36474030223c9832a458` |
| segments.json | `c4d80de9e9d193c2cdbbbfdb562253fba35ececea01fb004bc9ab4d41ead8709` |

合成テストで、手作成の所有・セグメント・地盤格子、異常占有、欠落receipt、run再使用拒否を検証した。T4-A/B1を含む関連pytestは23件通過、5件警告。

次工程では、AOI越境23棟の扱いと、代表高さモデルで省略される屋根・地盤の局所形状を独立に評価する。競合セルを含む棟別の分析では、所有格子と併せてセグメントの証拠を保持する。

全体pytestはGEEKOM-A6の通常権限で1,247件通過、10件skip（GIS/QGIS専用Python 5件、Windows symlink権限5件）、345件警告。初回のサンドボックス内実行はWindowsのハードリンクなどの権限制限に当たり、通常権限で再実行した。ログは `data/work/terrain-candidate-b/full-t4b2-normal.log`。A2の原TIFF・再現Terrain、PR #134のNative・Standard・VoxCityレポート・VoxelのSHAは既存記録と一致した。旧A3の歴史的固定パスにある入力2点はT4-B1と同様にローカルで確認できず、直接ハッシュ照合の対象外。
