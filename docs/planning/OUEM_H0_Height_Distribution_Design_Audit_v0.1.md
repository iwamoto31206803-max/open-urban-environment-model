# H0 建物高さ分布の設計監査

**DESIGN CANDIDATE / IMPLEMENTATION NOT_STARTED**。監査基点main `8093eba`。代表高さと高さ分布は併存し、LoD1/LoD2という取得情報の違いとは独立した選択軸とする。上位方針はConcept v0.2 §3・§4.2。今回の候補は正式Standardの変更を伴わない。 [Concept](../OUEM_Concept_Architecture_v0.2.md) · [接続監査](OUEM_STEP1_Compatibility_Audit_v0.1.md)

## PLATEAU経路

既存Standardは3D face、外周・内周ring、頂点XYZ、ID、source_lod、selection_reason、measured_heightの原値とnullable解析値を保存する。`standardize/building/mixed_lod.py::run:173`・`audit:131`はXY変換とHの完全保持を分け、独立Consumer `consumers/mixed_lod.py::audit_standard:319`は元形状・順序・全H・XYを照合する。GPKGのPolygon集合だけから屋根種別、閉じたSolid、水密性を推定しない。Raw branchへの参照は出典の追跡に使えるが、全意味属性がStandardの各面に複製されているとは限らない。

LoD1 Solidの上端は元の押出し表現に由来し、実屋根勾配の再現を保証しない。LoD2 MultiSurfaceは保持された屋根等の斜面情報を使える一方、ReaderがLOD2を選択したことだけで屋根面の完全性や測量精度を保証しない。`adapters/voxcity.build_normalized_footprint:131`は正面積のXY投影面を集めるため、屋根面の分類器としては使えない。

セル上端Zの初期実装前に、次を設計レビューで選ぶ。

| 論点 | 最小候補とQA |
|---|---|
| 採用範囲 | footprint全形状と処理域、共通格子原点・CRS・resolutionを固定。形状のAOI clipは派生サンプリング範囲と区別。 |
| セル評価法 | セル中心の上端交点と、セル内の最大上端は異なる。前者は細い庇や境界を欠測し得る。後者はセル全体を高くする。初期候補は中心サンプル、境界セルにcoverage fractionと不確実フラグを併記。採用前に両者の合成比較が必要。 |
| 斜面・非平面 | 三角形分割、法線、投影面積、平面性の誤差予算を定める。垂直壁は単独で正面積の屋根支持を作らない。非平面を黙って平面補正しない。内周は穴として保持。 |
| 複数面・庇 | 上端は同じセルで有効な最高の絶対Z。下側面・重なり数・寄与face locatorを保存。上端だけではピロティや空洞を表現できないため、全体の鉛直占有を捏造しない。初期2.5D押出しは別profileとする。 |
| ID・競合 | 1 source_idに複数セル、1セルに複数候補を許す中間表。数値ownerはエンジン側派生。セルごとの上端winnerだけを保存すると他棟の段差と鉛直セグメントを失う。 |
| 来歴 | Standard/manifest SHA、Raw branch・face/ring対応、XY変換履歴、grid SHA、採用規則・コード版・LoD、元形状を追跡。元3Dは保持し、Derivedが代替しない。 |

## 将来のGSI点群＋外周線経路

データ取得・分類法は未実装。配布製品ごとのCRS、鉛直意味、観測時期、点分類、精度・ライセンスを先に確認する。単なるXYZまたはGeoTIFFの読込可能性を利用適格性としない。

| 技術要件 | 必要な証拠・欠測時の扱い |
|---|---|
| 建物帰属 | 外周線の安定IDと出典SHA、時点、境界上点の規則、複数棟候補と未帰属点数。最近隣だけで他棟へ帰属しない。 |
| 水平位置合わせ | 点群と外周線のCRSとXY変換を記録し、重なり・ずれを診断。位置補正は別の承認されたDerivedとして記録。 |
| 上端推定 | セル内の建物由来点から上端Zを推定。最大値・分位値・面フィットは別手法でありパラメータ、外れ値判定、支持点数を記録。 |
| 汚染 | 地盤、植生、外れ点・飛点を製品分類と局所構造で識別。樹木が屋根上にある場合の誤認率を評価し、未判定を残す。 |
| 密度・精度 | 有効点密度、走査・入射条件、分散・誤差推定、屋根面の検証点を保持。十分な点が無いセルは欠測。補完の有無・元欠測マスクと手法を別記。 |
| 高さ | 絶対標高ZとHAGを別属性にし、DEM ID・SHA・セルと地盤処理を固定してHAGを導出。HAGを絶対Zへ無根拠で読み替えない。 |

## 共通のDerived入力候補

上流の屋根解析法を共通化せず、両経路から次の候補を出せるようにする。

- GridはEPSG・原点・二つの軸ベクトル・shape・XY/Z単位・resolution・セル評価法・処理域／評価域を明示する。VoxCity格子への再採取と元Derived格子を区別する。
- セル×source_idの表はabsolute_top_Z、支持面積、source_lod（点群ではnullable）、height_method、source_dataset、根拠SHA、face/point参照、quality、推定誤差を持つ。
- stateは建物不存在、上端既知、建物有り上端欠測、競合、補完済みを区別する。NaNと高さ0を同一視せず、複数寄与棟の多重度を保持する。
- モデル選択はrepresentativeまたはdistribution。原形状・原DEM・Standardを変更せず、同じsource_idで比較可能な別Derivedを出す。地盤参照IDと実効地盤の選定法を必須とする。

正式スキーマ名・属性型・保存形式は次PRで小さい探索的profileとしてレビューする。性能要件と利用者が決まる前に汎用APIへ昇格させない。

## 固定VoxCityの接続可能性と限界

後続の限定実行検証は現行
[STEP 3-B synthetic voxelization](../experiments/height_distribution/STEP3B_SYNTHETIC_VOXELIZATION.md)
を参照。以下は監査時点の静的所見であり、合成の限定成立は実データや正式契約の
適合性を意味しない。地表面indexと最上位層の上面／下面の区別も同記録に明示する。

インストール済み1.7.0、commit `fa212656305328a9a657973bae26f352bfe813bc` の `generator/voxelizer.py::generate_combined:158–245` は、セルごとのheight配列と複数の[low,high]セグメントを受け取る。ループは各セルのセグメントを整数化して占有を書き込む。**静的な受け口は確認できるが、新しい高さ分布での実行適合性はNOT_VERIFIED**。

- `height_grid` はZ容量確保に使われ、実占有はsegment配列が決める。各セルの最大highとheight_gridの不整合で上端を切り捨て得る。NaNの代替値設定があるため、OUEM側は渡す前に未解決欠測を拒否する。
- `geoprocessor/raster/core.py::process_grid:48–89`は単一owner IDごとに地盤を平均し、最小値を引く。絶対上端Zからhighを導く時の地盤は、元DEMやsource別の地盤と別。複数棟のセグメントもセルownerの地盤に置かれるため、競合の各寄与上端を別に再構成する。
- `_flatten_building_segments:91`、`_voxelize_kernel:39`は上下端を1 m単位へ丸め、地表面の直上から相対位置を加える。D0は平均後地盤の最小、surfaceの上面と最初の建物indexは1層分の定義を持つ。H0では既存の規則に合わせて端点を定義し、オフセットで過去結果を補正しない。
- 屋根下空間を扱うには上端だけでなくlowと複数占有区間が必要。現在のB1/Candidate B監査はlow=0かつ連続占有を前提としており、そのままピロティモデルの検証には使えない。
- 最終−3クラスは匿名。source_idとセル寄与・セグメントを別保存する。代表高さと分布高さを同じSolar/GVI核へ渡す条件は、軸、D0、地盤、ROI、観測点、TREE条件と境界、クラスの意味を一致させること。

## STEP 2 / STEP 3への引継ぎ

現行STEP 3-Aの限定合成実装・検証は
[Synthetic Building Height Distribution PoC](../experiments/height_distribution/STEP3A_SYNTHETIC_HEIGHT_DISTRIBUTION.md)
を参照。中心／セル最大の正式採用、実データ処理、VoxCity接続は未確定・未実施。
本設計監査の履歴上の候補・表を、その実装結果と混同しない。

**工程番号に関する履歴注記（2026-11-06）：** 以下の番号はH0設計監査時点の
局所的な提案ラベルであり、後に実施したCandidate Bの現行STEP番号とは一致しない。
実施済みの現行STEP 2-Aは[建物日陰](../experiments/real_komae_source_h/STEP2A_BUILDING_SHADOW_E2E.md)、
STEP 2-Bは[Canopy成立性](../experiments/real_komae_source_h/STEP2B_CANOPY_FEASIBILITY.md)、
STEP 2-C1〜C4は[Envelope](../experiments/real_komae_source_h/STEP2C1_EXPERIMENTAL_HEIGHT_ENVELOPE.md)、
[実データTREE統合](../experiments/real_komae_source_h/STEP2C2_REAL_CANOPY_INTEGRATION.md)、
[Solar](../experiments/real_komae_source_h/STEP2C3_REAL_SOLAR.md)、
[GVI](../experiments/real_komae_source_h/STEP2C4_REAL_GVI.md)である。
次の現行STEP 3は建物高さ分布の合成PoCであり、以下の古い提案行は実施済みの
高さ分布実験を意味しない。設計上の論点を保持するため、元の表は変更しない。

| 順序 | 最小PR単位 | 実施条件と受入候補 |
|---|---|---|
| STEP 2-A | 既存配列を扱う小さい数値handoff接続 | 既存readerは維持し、Candidate Bのgrid・D0・観測点を明示的に写像。source_id、出力affine、全域計算後のROI抽出、入力不変を検証。E1 runnerの保留解除と実データ計算の範囲は別に承認する。 |
| STEP 2-B | H0のセル評価規則とDerived候補の合成PoC | 斜屋根・壁・庇・穴・複数棟・欠測の手作成fixtureで、中心／セル最大を比較。絶対Z・state・寄与を保持し、エンジン手前まで。 |
| STEP 3-A | PLATEAUの限定実データ高さ分布 | 新規run、固定Standard SHA、面／ringの来歴、代表高さとの差をsource_idと地理セルで測る。選んだ規則と誤差予算にレビュー合意後に実施。 |
| STEP 3-B | 固定VoxCityへの分布入力と核の再利用検証 | high容量一致、単棟斜面と競合多区間、D0、屋根・地盤・匿名占有を合成で先に検証。同一観測点を保証して環境指標を比較。 |
| 後続 | GSI製品・外周線の入力監査 | 製品の被覆・基準・点密度・属性・権利を確認後、帰属と欠測のPoC。PLATEAUと同じDerived候補へ独立変換。 |

ユーザーレビューを要する論点は、中心かセル最大か、欠測補完の可否と手法、地盤の代表値かセル値か、庇・空洞の対象範囲、数値許容差、評価用Contextの範囲。今回の監査では確定しない。
