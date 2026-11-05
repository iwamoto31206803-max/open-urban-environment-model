# STEP 1 Compatibility Audit

2026-11-05、main `8093eba`（PR #151・#152反映）を監査基点とする。Candidate B E1の独立runnerは保留。区部DEMのT.P.継承推定による限定実験は継続可能で、`terrain_integration_ready=false` は正式Standard Terrain統合の未承認を示す。realization、epoch、標高精度は未検証。 [現在の設計判断](OUEM_Candidate_B_Terrain_Integration_Decision_Plan_v0.1.md) · [T5総括](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_T5_4_CLOSURE.md)

## 接続の分類

REUSE_AS_ISは該当関数の数値条件が満たされる場合、SMALL_ADAPTERは明示的なメタデータ・入力マッピング、KEEP_SEPARATEは異なる意味または来歴の境界、NOT_VERIFIEDは実行・証拠が不足している項目を指す。数値的適合の確認は、実データ環境評価を再実行した証拠にはならない。

| 項目 | 分類 | 実装の根拠と接続条件 |
|---|---|---|
| 配列・クラス | REUSE_AS_IS | `real_komae_voxel.audit_voxels:60`、`b2_gvi.load_run:86`。int8、axis0=概ね北、axis1=概ね東、axis2=上。0空気、−1地中、1仮Bareland表面、−3建物、−2TREE。Candidate Bの127×127×12とB1の128×128×27/26は固定形状を共有しない。 |
| 水平格子 | SMALL_ADAPTER | `real_komae_voxel.execute_model:153`のgridと中心配列、`candidate_b_t5.grid_phase`のengine_grid・centres_xyを明示的に対応付ける。真北への回転と公称1 m・調整間隔は別。原点とu/vベクトルから地理中心を復元し、EPSG:6677中心を照合する。 |
| Terrain sampling | KEEP_SEPARATE | `real_komae_voxel.sample_dem:27`は元ピクセルを含む位置で採取。Candidate B `candidate_b_t4b1.sample_dem:48`は固定エンジンのUTM最近傍を独立照合。似た中心・解像度でも同一採取法とは扱わない。 |
| D0・絶対H・地盤 | SMALL_ADAPTER | `real_komae_voxel.effective_ground:51`は所有ID別平均後の最小値をD0とする。B1はeffective_demがD0相対、Candidate Bのeffective_dem_absは絶対H。生DEM最小D0_rawとは一般に異なる。Probeは両表現を絶対Hへ明示的に対応させて照合する。 |
| 鉛直添字・屋根誤差 | KEEP_SEPARATE | B1 `audit_voxels:67`のground_indices=gは最初の建物／空気セルで、表面はg−1。Candidate B `candidate_b_t4b2.audit_voxels:40`はground_k=g−1。B1の屋根上面はD0+last_k+1、Candidate BにはD0+last_kと上面方式の両指標がある。同じ変数名で比較しない。 |
| ID・競合・セグメント | SMALL_ADAPTER | A3 `numeric_id_mapping:37`はouem_idから決定的に割当。ただし母集合変更で数値IDは変わる。B1 `execute_model:207`はセル寄与棟を独立照合、Candidate Bは孤立単棟と全棟のセグメント多重度を照合。source_idで対応し、−3占有は匿名であることを保持する。 |
| ROI／処理域／被覆 | SMALL_ADAPTER | `b2_gvi.roi_window:76`は矩形ROIだけを許容。B1は各runの評価域とcontext、Candidate Bは評価100 m・処理127 m。全域計算後に中心で抽出する。Source CoverageをROIと混同しない。 |
| 観測点抽出 | REUSE_AS_IS | `b2_gvi.observers:54`で最初の有効表面遷移、int(height/mesh)、開始クラスとZ範囲を検査できる。B1の保存observer_index_kと一致。Candidate Bは保存観測点がなく、B2定義での再構成として報告する。 |
| Solar核・観測条件 | SMALL_ADAPTER | `real_komae_solar.solar_pair:149`は人工太陽・1.5 m要求・DNI、共通No-Canopy対照・地盤対照を持つ。Candidate Bはその対照とCanopyなし。低水準日陰核はE0で確認済みだが、B1 runner全体をそのまま適用しない。 [E0](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_E0_SHADOW.md) |
| GVI核 | REUSE_AS_IS | `b2_gvi.calculate:171`は配列と矩形メタデータを受け、固定CPU generic、TREE-only、k=.5、LAD=1、120×20方向、仰角±30°、高さ1.5 m。入力配列とfigureの保護あり。Candidate Bでの計算実行はNOT_VERIFIED。 |
| Canopyの意味 | KEEP_SEPARATE | `real_komae_solar.integrate_canopy:47`は推定Height EnvelopeとCR、TREE以外の不変、共通Z容量・D0・地盤を検証。Candidate BはTREEなし。GVIがゼロとなる計算条件を、樹木不存在の観測証拠に使わない。B1のcanopy_missing/outsideも保持する。 |
| ファイル読込・来歴 | KEEP_SEPARATE | `gis_visualization.inspect_run:47`と`b2_gvi.load_run:86`は凍結B1 config/receipt/出力・上流SHAを要求。Candidate BのT5 manifest/profileは別系統。正式A3 whitelist・vertical gateを緩めない。 |
| GeoTIFF | SMALL_ADAPTER | `real_komae_voxel.export_outputs:266`、`real_komae_solar.export:379`、`b2_gvi.raster:222`は地理座標のexact affineと南北反転、転置なし。Candidate BのEPSG:6677中心は非線形変換結果で、完全な北向き1 m affineとは別。B1の地理affine経路を優先して照合する。 |
| 解像度・気象・外部遮蔽物 | NOT_VERIFIED | 1 m量子化の精度、Context Buildings、外部境界収束、気象時系列、写真GVIとの比較は対象実験で未検証。B1/B2 Technical E2Eと科学検証・Acceptanceの範囲を分ける。 |

## Probeの境界と再利用

`src/ouem/compatibility_probe.py::inspect` は既存`b2_gvi.observers`、`real_komae_voxel.effective_ground`を再利用し、明示的に対応付けた数値snapshotを検査する。新しいStandardや共通計算APIではない。格子軸・shape・dtype・クラス、原点と中心、D0、地盤クラス配置、source_id対応、ROI、観測点のXY/Hを拒否条件として持つ。LoDや高さモデルは関数の分岐に使わず、下流占有・観測点・座標が判断基準。

`scripts/work/step1_compatibility_probe.py` はB1の既存readerとWatchを再利用し、Candidate Bは明示SHAで固定したT5レポートとその出力だけを検証する。Candidate BのRaw→Native→Standardを新規に再監査する機能は含まない。共通幾何・観測点の合成テストは、共有helperの誤りを丸ごと検出する独立Consumerの代替にはならない。 [今回の実測と実行方法](../experiments/real_komae_source_h/STEP1_COMPATIBILITY_PROBE.md)

重大な矛盾として修正が必要な実験結果は確認していない。一方、D0と添字の命名差、GVIのTREEなし解釈、B1 readerとT5 profileの境界は、明示的接続なしに互換と宣言できない。 [H0とSTEP 2/3](OUEM_H0_Height_Distribution_Design_Audit_v0.1.md)
