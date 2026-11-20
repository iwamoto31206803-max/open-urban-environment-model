# M2限定技術終了記録 — 保存済み狛江市Phase 3C A

**`M2_LIMITED_TECHNICAL_EXIT=ACHIEVED` — 保存された有限3D計算モデルとその観測点に限る。**
固定CPU経路で、B1の人工太陽条件におけるモデル上の瞬間水平面直達日射低減と、B2のCPU weighted first-TREE view indexを再現可能な形で技術評価した。科学的妥当性と正式Acceptanceはいずれも **NOT_VERIFIED**。全用途でのM2完了はこの記録の対象外とする。

2026-11-20にユーザーがこの限定文言を採択した。[Concept v0.4 §7](../OUEM_Concept_Architecture_v0.4.md#7-phase-b既存ossによる環境指標)を上位設計とし、[Integrated Roadmap M2](../planning/OUEM_Integrated_Roadmap_v0.1.md#m2--樹冠環境機能の再現可能な技術評価)の用途別出口案に照合した。[M2-E準備判定](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/210#issuecomment-7042213992)、[独立レビュー](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/210#issuecomment-7042549930)、[ユーザー承認](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/210#issuecomment-7042630787)、[文書化の範囲](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/211)を区別して記録する。

## 固定した用途と出口条件

B1の保存runは `data/work/shared-vertical-domain/phase3c-20261029-01/outputs/komae-a-3c-20261029-01/`、B2の派生runは `data/work/b2-gvi-phase3-20261030-01/a/`。両方ともローカルのGit管理外成果で、cloneには含まれない。PR #99の最終run、狛江B、Mixed-LoDは別の実験証拠として扱う。

| 出口条件 | 固定用途に対する証拠と判定 |
| --- | --- |
| 指標の意味・単位・API・固定版・設定 | **SUPPORTED**。VoxCity 1.7.0 CPU、`fa212656305328a9a657973bae26f352bfe813bc`。B1は `get_direct_solar_irradiance_map`、人工方位135°・高度35°・DNI 800 W/m²、k=0.6／LAD=1。No-Canopy − Currentの正値がモデル上の低減を表す。A ROIの履歴平均（Current／No-Canopy／低減）は2.251779／427.916993／425.665214 W/m²。B2は `get_view_index(mode=None, hit_values=(-2,), inclusion_mode=True, fast_path=False)`、k=0.5／LAD=1、120×20等重み方向、仰角−30°〜+30°。最初のTREE交差区間の減衰寄与を用いる無次元指標で、写真式・二値GVI、全樹冠透過率、GPU同等性は対象外。B2は保存Currentの分布を評価し、両指標は別々に報告する。[B1 Phase 3C](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst)・[B2実行結果](../experiments/b2_gvi/RESULTS.md) |
| 入力来歴とB1対照 | **SUPPORTED**。凍結設定→receipt→Voxel/Solar report→B2 preflight/reportを結合。B1の対は地盤・建物・格子・観測点・太陽条件を共有し、全442,368位置の差はTREE→AIR 95,735個。B2入力のCurrent SHAは同じAの保存Currentに一致。#209は33ファイルの実バイトを照合し、独立レビューは報告を精査した。[保存照合](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/209#issuecomment-7041599997)・[独立レビュー](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/209#issuecomment-7041664574) |
| 計算点XYZ、D0、格子、採否 | **SUPPORTED**。128×128×27、名目1 m、`uv_m/SOUTH_UP`、D0=19.586000442504883 m。ROIは両軸 `[32:96)` の64×64。保存中心XY、有効点の共通k、中心H=D0+k+0.5 mで計算点を特定。有効マスク・ROIはB1/B2で一致。要求高さはボクセル表面から1.5 m、ROIの保存計算点はDEM+約2.001〜3.000 m。物理的な歩行者目線高と歩道位置は未検証。[B1観測点診断](../experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md)・[保存照合](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/209#issuecomment-7041599997) |
| 計算域・ROI・halo・外部遮蔽物 | **SUPPORTED（範囲と制約の記録）**。全域計算後にROIを抽出。32 m haloは、既知高さの到達距離39.1801 m＋2 m余裕に対する等方十分性を満たさない。最短太陽方向退出距離45.8419 mの判定は固定太陽・既知高さに限り条件付きで成立。ROIだけに切り出すと861セルでCurrent日射が増加した。未知の外部遮蔽物とB2全方位の領域十分性は **NOT_VERIFIED**。[Phase 3C領域診断](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst) |
| 再現性と数値QA | **SUPPORTED**。B1 AはPR #107 Aとの保存NPY・GeoTIFF値等の一致を記録。B2の独立CPUチェックポイントと最終NPYはNaNを含め一致。B2有限値は0–1、ROI切出しと全域が対応。#209は保存バイトと配列関係の照合で、再実行は行っていない。[B1 Phase 3C](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst)・[B2再現性](../experiments/b2_gvi/RESULTS.md)・[保存照合](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/209#issuecomment-7041599997) |
| 空間QAとGIS成果 | **SUPPORTED**。EPSG:4326の元回転affine（全域のTIFF行=127−u、列=v）とROI変換を保持。EPSG:6677は投影参照・QGIS表示。実行記録にGIS成果、再読込とGUI確認があり、#209ではB2の2 TIFFが公開SHAに一致。QGIS Identifyは表示格子を参照し得るため元セルは既存の原ファイル照会を使用する。[B1 GIS記録](../experiments/real_komae_solar/README.md)・[B2 GIS記録](../experiments/b2_gvi/RESULTS.md) |

### 観測点の報告方針③

全valid点と元の値を保持する。AIR／TREE起点と除外を分け、単一の主集計や新たな分母は採用しない。B2では有効ゼロと除外のNaNを区別する。次の件数は保存配列の既存kから得た。[保存配列の照合](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/209#issuecomment-7041599997)

| 範囲 | 有効 | AIR起点 | TREE起点 | 除外・B2 NaN | B2有効ゼロ |
| --- | ---: | ---: | ---: | ---: | ---: |
| 全域 | 12,638 | 12,305 | 333 | 3,746 | 63 |
| 評価ROI | 3,722 | 3,685 | 37 | 374 | 12 |

## 証拠の継承と未検証事項

- [B1 Closeout](B1_TECHNICAL_MILESTONE_CLOSEOUT.md)と[B2 Closeout](B2_TECHNICAL_MILESTONE_CLOSEOUT.md)はM0の元実証として保全する。[M1樹冠経路の保存TREE一致](CANOPY_CURRENT_STATE.md)は樹冠入力経路の技術証拠。M2で追加したのは、[Bの証拠対応](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/207#issuecomment-7034976344)、[Cの用途・来歴整理](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/208#issuecomment-7039265272)、[Dの33ファイルと観測点起点の照合](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/209#issuecomment-7041599997)、[Eの出口準備判定](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/210#issuecomment-7042213992)である。
- 推定CHMv2・CR、簡略2.5D建物、未校正のk／LADを使用した。現地での放射・日陰、写真式緑視、物理的な観測点、測量・形状精度、実気象・季節、暑熱便益、広域での再現性は未検証。Building／TerrainはPROVISIONAL、CanopyはDRAFT、Source-H適格性はNOT_ESTABLISHED、混在経路の正式AcceptanceはNOT_VERIFIED、Phase 5はOPENのまま。[B1保留事項](../planning/OUEM_B1_Deferred_Validation_Backlog.md)・[B2保留事項](../planning/OUEM_B2_Deferred_Validation_Backlog.md)

## M3への引き継ぎ

最初に、主張ごとに独立した参照データが利用可能かを調べる。候補は実測等に基づく樹冠の存在・形状、地盤と歩道・物理観測点、現地の日陰・放射、全天球／街路写真。時点、範囲、品質、座標、利用許諾を確認する。現時点で候補の存在・利用可能性は未確認であり、この記録は取得や評価を承認しない。領域感度・光学校正は対象用途に応じて検討する。市町村全域級の被覆・運用性能はM4、権利・第三者利用はM5に引き継ぐ。[Integrated Roadmap M3–M5](../planning/OUEM_Integrated_Roadmap_v0.1.md#m3--科学的妥当性と不確実性の検証)
