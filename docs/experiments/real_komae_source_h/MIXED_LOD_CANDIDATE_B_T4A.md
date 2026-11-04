# Candidate B Building / Terrain Compatibility — T4-A

**COMPLETED (read-only diagnostic) / EXPERIMENTAL / NOT_FORMALLY_ACCEPTED**。`terrain_integration_ready=false`。基準main `670be74`。 [Mixed Consumer #140](MIXED_LOD_CONSUMER_POC.md) · [Terrain設計 #142](../../planning/OUEM_Candidate_B_Terrain_Integration_Decision_Plan_v0.1.md) · [T3 #144](MIXED_LOD_TERRAIN_CANDIDATE_B_T3.md)

## 再現と入力境界

GEEKOM-A6の通常Windows OUEM venvで実行した。入力manifestとConsumer receiptは実行コードの固定SHA-256に照合する。隣接GPKG、Terrain・タイルID GeoTIFF、T3検証JSONはそれぞれハッシュ連鎖を照合し、処理後にも再ハッシュする。Consumer receiptの検証対象SHA・AOI・CRSを確認し、GPKGから全ID・LoDと3D BLOBを読み直す。Raw→StandardのConsumer全工程は再実行していない。T3を実験profileとして開き、6677・200×200・0.5 m・アフィン・NoData・全有効・出典IDを検査する。

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_t4a `
  --building-run data/work/mixed-lod-standard/run-02 `
  --consumer-receipt data/work/mixed-lod-consumer/run-04/receipt.json `
  --terrain-run data/work/terrain-candidate-b/t3-02 `
  --output-dir data/work/terrain-candidate-b/t4a-repro
```

入力異常は `BLOCKED` と原因を新規runのJSONに記録する。実測は `data/work/terrain-candidate-b/t4a-02/report.json`、SHA-256 `7fdc8839f785b54467dd6b67db5090caa34d9286a36a798cfae0d1ec0a5005d9`。全建物のID・LoD・Z・面積・地盤統計・出典内訳と入力SHAを含む。

鉛直判定は **CONDITIONAL**。BuildingはEPSG:6695の重力関連Hを保持し、T3は多摩のT.P.宣言と区部のT.P.継承推定を含む。精密なdatum実現・epoch・測量精度の一致は未確認。宣言欠落や矛盾は停止する。高さ変換・補正は適用しない。

## 診断方法と結果

元3Dの各面をXYへ投影し、有効な正面積面をunionする。垂直面などゼロ面積の投影は除外する。不正な正面積面は修復せず件数を記録し、フットプリント診断を要レビューとする。AOI内外面積は集計用の交差・差分で求め、元形状はそのまま。閉じたフットプリントに入るT3ネイティブ格子のセル中心を対象とする。重複フットプリントでは同じ地盤セルを複数棟が独立に参照し得る。平均・標準偏差は等重みで、VoxCityの所有セルは使わない。

Z最小・最大・範囲は全3D頂点の記述統計。接地の参考には、中心を覆う正面積面のうち、平面フィット残差が1 µm以内の面の下側包絡を使う。平面性の数値条件は測量許容差ではない。包絡は構造上の底面や接地を認定せず、独立のZ最小値と区別する。地盤と上端の関係、下側包絡が全対応セルで地盤より高いケース、有効中心欠損を診断する。

| 実測項目 | LoD1 | LoD2 |
|---|---:|---:|
| 棟数 | 31 | 32 |
| スクリーニング指摘なし | 19 | 21 |
| フットプリントがAOI外に延びる | 12 | 11 |
| 地盤を参照できない棟（上段の内数） | 1 | 0 |
| 有効中心数の範囲 | 0–543 | 14–792 |
| 棟内地盤標高の標準偏差の範囲（m） | 0.016–0.087 | 0.014–0.133 |
| 多摩・区部の両方を参照する棟 | 2 | 0 |
| 最小の上端−地盤（有効中心のある棟、m） | 1.910 | 2.015 |

正面積の不正投影は0棟。有効中心のある62棟では上端が全対応地盤標高より高く、全サンプルで下側包絡が地盤より高い棟は0。包絡−地盤の全体範囲はLoD1が約 −0.390～+0.130 m、LoD2が −0.544～+0.068 m。局所差は記録したが、鉛直整合や建物の異常を確定する許容値は設定していない。

AOI内の形状・地盤スクリーニングで指摘のない40棟が次工程の初期候補。23棟はAOI外の地盤が未評価で、うちLoD1の `bldg_eeed3575-1ab7-487f-bccb-56714e1daf78` は全65.618 m²のうちAOI内0.069 m²（約0.105%）で、有効なT3が全面にあっても対応中心がない。VoxCityでの採否・実際の統合可否は全63棟で未判定。

## T4-Bに向けた変更候補

既存A3は3D面のXY投影から、必要時の修復・正規化・決定的unionでフットプリントを作り、エンジン境界で4326へ変換する。変換後の不正形状にも条件付き修復がある。正規化、修復要否と変形量の再確認は将来のエンジン側診断で行う。A3は `ouem_id` の字句順で1始まりの一意IDを付与し、VoxCity 1.7.0の精密 `overlapping_footprint=True` を用いる。ローカルGeoTIFFから `dem_interpolation=False` で、エンジンの矩形とmeshに対応するDEM格子を作る。 `G_eff_abs` はその生DEMのうち建物ID格子が同じIDを持つセルの平均で、`height = Z_top_abs - G_eff_abs`。通常の `min_height=0.0` を用い、Z最小値から浮上量を推定しない。 [A3 Adapter仕様](../../OUEM_VoxCity_Adapter_v0.1.md)

T4-Bでは別の実験profileでMixed Consumer・T3の固定SHAと条件付き鉛直判断を明示して受け付ける。既存A3が要求するAccepted manifestとT.P.の `verified`／`source-declared` 条件を緩めない。実験の矩形・格子原点・解像度・変換後のDEM有効性を先に定義し、AOI外へ延びる23棟の扱いをレビューする。既存A3の建物外接矩形を使うと、100 m四方のT3範囲を超え得る。範囲拡張・対象の限定・境界条件のいずれかは別途承認が必要。小さな交差、所有競合、ID欠落、DEM格子の行列・向き、地盤平均・屋根Zの再構成は、ピン済みVoxCityを使う別工程で検証する。

## テストと保護対象

関連pytest 43件通過、警告2件。新規合成テスト8件で、LoD1/2、垂直面とZ最小の違い、AOI越境・中心欠如、無効地盤、上下異常、鉛直の矛盾・未解決、manifest欠落／SHA差、決定的な再実行を確認した。VoxCityやAcceptedの書込経路は呼び出さない。

全体pytestは1,232件通過、10件skip（専用GIS/QGIS Python 5件、Windows symlink権限5件）、341件警告。ログは `data/work/terrain-candidate-b/full-t4a.log`。実データ再実行 `t4a-03` のJSONは `t4a-02` と同一バイト。A2再現TerrainとPR #134 VoxCity配列は記録済みハッシュと一致した。
