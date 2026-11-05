# Candidate B E1 最小日陰評価設計

**DESIGN / EXPERIMENTAL**。E0で検証した固定VoxCityのCPU核を使う。 `terrain_integration_ready=false`。 [E0](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_E0_SHADOW.md) · [T5-4](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_T5_4_CLOSURE.md)

## 入力と実行

1. T5-2/T5-3の成功reportを既知SHA-256で照合し、両GateがPASSのrunから `t5-3/voxels.npy`、`t5-2/centres_xy.npy`、`t5-2/building_ids.npy`、保存済み評価域マスクを読み取り専用で開く。各SHAをreportと照合し、127×127×12、クラス集合 `{-3,-1,0,1}`、1 m、EPSG:6677、軸順、座標配列との対応、固定VoxCityバージョンとcommitを確認する。Terrain・建物・ボクセルの再生成は不要。 [固定入力とハッシュ](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_T5_23.md)
2. 方位180°、高度45°、`view_point_height=0`、屋根無効で実行する。方位は観測点から太陽へ向かう角度。T5の格子ベクトルとEPSG:6677中心差分を使い、軸0負・軸2正を確認し、真北に対する格子回転を評価して使用角度を記録する。E0で確認した方位変換と低水準核を使い、`hit_values=(0,-1,1)`、`inclusion_mode=False` とする。地表面は評価点の選定に使用し、光線の遮蔽は建物のみ。日時からの太陽位置計算は後続に分離する。
3. 建物占有は `any(voxels == -3, axis=2)` を使う。所有格子だけに依存せず、建物列は屋根・地表とも評価対象外。建物以外の各列で最初の表面遷移と開始添字を照合し、開始点の範囲外を拒否する。対象外と予期しないNaNを別に集計し、後者は完了判定を保留する。許容する計算値は0と1。
4. **Processing Domain全127×127×12を入力に光線追跡**する。計算後に元の100 m四方のEvaluation AOIを中心座標で半開区間抽出し、T5のマスクと照合する。AOI外の対象建物は光線遮蔽に寄与し得る。

## GeoTIFFと品質条件

- EPSG:6677の北向き1 m GeoTIFFを作る。目標Affineは `(1,0,-22575,0,-1,-39825)`。実中心を座標でピクセルに割り当て、重複・空き・範囲外がないことと公称中心との差を測る。初期PoCの登録上限は0.01 mとし、超過時は座標設計を再レビューする。位置精度の保証値には使わない。
- 行は北→南、列は西→東。VoxCityの第0軸は南→北、第1軸は西→東。北向きのこの出力では座標照合上の南北反転が必要。無条件の転置や、別のuv affine向け変換は使わない。非正方形の合成マーカーと再読込四隅・中心座標で検証する。
- uint8の0=日陰、1=日向、255=対象外（NoData）。建物、その他対象外、予期しないNaNを個別に記録する。対象域の全セルを重複なく集計し、有効数=日陰数+日向数を検証する。GeoTIFFと分類配列を再読込し、クラス・CRS・Affine・NoData・中心の対応を監査する。
- 新規実験runに入力SHA、コードとエンジン識別、環境、角度・高さ・許可クラス、格子・マスク、結果件数と出力SHAを保存する。同一入力で分類・マスク・統計・出力を再現してから完了と判定する。

領域外へ出た光線は、モデル内に遮蔽が無ければ日向を返す。外部遮蔽物とContext Buildingsは未収録で、地盤・樹冠・気象・全天日射・暑熱はこの初期条件の評価外。E1の技術成立は指定条件における分類と地理出力まで。必要な日陰処理域、実測精度、鉛直基準のrealization・epoch・accuracy、正式Terrain統合は別途検証する。
