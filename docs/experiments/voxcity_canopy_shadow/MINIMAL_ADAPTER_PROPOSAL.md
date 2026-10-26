# 未実装の最小Adapter・比較条件案

> 公開用整理: 2026-10-27。以下は2026-10-26の既存調査・提案の全文を保持した記録。調査結果と **CONDITIONAL** 判定は変更せず、今回新しいAPI実行・Adapter実装・voxel化・日射比較・pytestは行っていない。本文の「今回」「最新main」「commit／push／PR作成なし」は当時の調査実行を指し、本ドキュメントPRの提出操作とは区別する。
>
> ローカル証跡の基点（リポジトリ相対識別子）: `data/work/voxcity-canopy-shadow/komae-phase01-20261026-01/`。本文の `environment-and-api.json`、`input-evidence.json`、`source-index.json`、`source-snapshots/`、`inspect_inputs_and_api.py` は同run内の非公開ローカル証跡で、GitHubへ同梱しない。`.venv/Lib/site-packages/voxcity/` は調査したインストール環境内の相対位置。JSON内のローカル絶対パスは環境依存の監査情報であり、第三者の取得先ではない。本文のソース行は当時の保存ソースに対する位置。
>
> このPRは本ディレクトリのMarkdown 3件のみ。コード・テスト・入力データ・ローカルログ・未完成Adapterを含まず、Standard Canopy／既存VoxCity Adapter契約や正式受入記録を変更しない。実装・比較計算の開始を承認するものではなく、Draftとして独立レビューを待つ。
> 対応するローカル原本: `MINIMAL_ADAPTER_PROPOSAL.md`、SHA-256 `005e40bbf48d98da7effaeac2fc6c8df9feb85804e41b603edf424d4b0302e63`。原本は不変。

[調査結果](RESULTS.md) · [API調査](API_REVIEW.md) · [最小Adapter案](MINIMAL_ADAPTER_PROPOSAL.md)


**CONDITIONAL / 承認前の設計案**。既存APIだけで相対canopy voxelと植生減衰は処理できるが、絶対Height Envelopeを安全に渡す境界が未実装。ユーザー指示によりここで停止する。以下は観測値・受入済み設定ではない。

## 入力と小領域

元入力は `data/work/height-envelope/komae-exploratory-20261026-01/generated/` の3枚＋manifest。実Terrainは `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif`。input-evidence.jsonに実hash・上流manifest整合を保存。

候補の評価ROIはEPSG:6677 bounds **[-23320,-40760,-23256,-40696]**、64×64、1m。元Height Envelopeのrows[196:260]、cols[280:344]、中心lon/lat=(139.57620924243287,35.63262314968702)。樹冠が多い南東寄りの領域を選んだ。読取集計4096 valid、3842正厚さ、254ゼロ厚さ。上端22.97400093..44.95500183m、下端22.97400093..31.24499893m、中心nearestのDEM19.59000015..23.99600029m。存在範囲・本数判定ではない。

32m haloを付けた128×128入力領域の候補bounds **[-23352,-40792,-23224,-40664]** は既存AOI内。halo全セルの変換検証と太陽条件に対する長さの十分性は次工程。周辺未収録樹木・建物の遮蔽は保証できず、boundary-sensitive扱い。

## 最小構成案（既存契約外のローカルPoC）

1. Height Envelope manifest COMPLETED／hash／bridge、Terrain manifest／受入hash／source-declared T.P.、全格子・maskをgateする。各入力を読み取り専用とし、新runへAdapter manifestと派生配列を保存する。
2. 同じ1m cell centreで0.5m TerrainをnearestサンプルしてDを得る。元Height Envelope生成時に使ったnearest DEMと全セル比較する。相違するDEMへ無条件に置換しない。invalid/missing/outsideはzero fillせず停止。
3. `relative_top = top_abs - D`、`relative_bottom = bottom_abs - D`。state=1で有限、0≤bottom≤topを検証。保存済み絶対top/bottomのFloat32丸めを維持し、HAGやCRから再生成して置換しない。
4. state=1かつtop_abs>bottom_absを表示・変換上の正厚さセルとし、ゼロ厚さはAPI入力top=bottom=0で樹冠voxelを生成しない。ゼロ除外は実験上の操作であり、不存在の正式判定ではない。3m閾値なし。
5. **格子案:** EPSG:6677の既存1m格子をそのまま使い、Dとrelative上下端・state等をすべて同時にflipudしてsouth-upにする。低level Voxelizerとmodelsへ直接渡す。GridMetadata.crs/boundsは実EPSG:6677／実範囲を正直に記録する。高levelのlon/lat rectangle rasterizerを再使用して微妙に異なる格子を作らない。このengine-specific格子接続は既存Building Adapter契約へ適用しない。
6. 建物はA/Bとも除外。heights=0、ids=0、各min_heightsセルは独立の空list。land_cover_source='Standard'で全セルcode1(Bareland)を**観測でない共通のwalkable表面ラベル**として仮置きする。反射・地表被覆評価はしない。code0のままだと地表検出に支障があるため使わない。
7. Aはrelative上下端0、Bは上記relative配列。D・metadata・meshsize・landcover・太陽・観測点設定は同一。D0も同じ。A/B各Voxelizer.generate_combined後、Z配列長が異なればair=0だけで共通の上限までpaddingし、共通サイズで比較する案。これも次工程で検証し、地形／樹冠をpaddingで変えない。
8. CPU直達日射APIへ接続し、配列をnorth-upへ戻す際は同じ方向変換を用いる。模型座標のrotation_angleを記録する。ROI中心で投影格子の北向き10mをGeod方位へ変換した値は **-0.14979770792591632°**。真北と投影北が同一だと仮定せず、格子点による変化・signを次工程でfixture検証する。

## 比較する太陽・光学条件の候補

最小案は瞬時の**水平直達日射だけ**。全天日射・年間積算は別工程。

| 項目 | 候補と根拠 |
|---|---|
| 時刻 | 2026-06-21T12:00:00+09:00、Asia/Tokyoを明示。代表的な日中条件という実験選択で、当日の観測ではない |
| 太陽 | `get_solar_positions_astral`へtimezone-aware時刻とROI中心lon/lat。方位・高度の実結果は未計算。両ケース同一の計算値を使う |
| DNI | 800 W/m²の実験定数案。気象観測・晴天推定モデルの値ではない |
| 光学 | tree_k=0.6、tree_lad=1.0を明示（VoxCity既定値に合わせる案）。観測LAD・植生種・葉量を反映しない。expのlengthはmで、tree_k×tree_ladはm⁻¹に相当する実験減衰係数として記録。LAD物理単位の説明は別途根拠が必要 |
| 葉の状態 | 定数減衰という仮定。季節のleaf-on/offを自動表現したとしない |
| 観測高 | view_point_height=1.5m案。kernelでは1m格子でint(1.5)=1 voxelと中心補正が使われ、厳密な1.5m地上点という精度を主張しない |
| 屋上 | include_building_roofs=False。建物なし |

## 実装前に固定・レビューする検証

- 方位4方向・投影北の回転、north/south flip、同一cell centreを合成fixtureで照合。太陽azimuthへ独断で180°を加えない。
- `g=round(D-D0)+1`と相対top/bottomのroundを含むkernel通りのTREE半開区間を独立算定し、実voxelと全件照合。薄い冠の1層拡張とabsolute面誤差を報告し、黙って1m補正しない。
- AのTREE=0、BのTREE>0、全common terrain voxel一致、building=0、分類値・空間分布・共通配列shapeを確認。
- A/Bの観測点有効maskを照合し、NaNが違う地点は件数・理由を報告。共通finite領域でのみB−Aを集計し、無効を0日射へ変えない。
- 直達の単位W/m²を明記。A/B/差分図、分位点、変化セル、増加の有無を報告。既存kernelの透過率<0.01打切りも記録する。日陰はまず連続透過率・日射低下で示し、独断の二値日陰しきい値は導入しない。
- halo有無／辺からの距離で境界影響を別記。buffer32mを十分と無検証で確定しない。観測値がないため科学精度評価は不可。

実装許可後の最小作業は、ローカル `HeightEnvelope→relative grids→VoxCity` Adapterと上記fixture、既存CPU APIを呼ぶA/B runnerの作成。既存komae_canopy.py、Building Adapter、Standard契約、正式記録は変更しない。新規Standard Canopy契約を作らない。
