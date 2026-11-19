# Open Urban Environment Model（OUEM）
## Concept & Architecture v0.4 Draft — M2環境指標の設計改定案

- 草案日：2026-11-19
- 状態：**レビュー草案（未承認・未登録）**。正式な上位概念設計は[Concept v0.3](OUEM_Concept_Architecture_v0.3.md)。
- 改定の根拠：[Roadmap M2-A Issue #205](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/205)。

## 文書の位置付けと適用範囲

v0.3を基に、Phase B1/B2の指標選定とv0.1からの継承範囲を見直す案である。正式登録、実行条件の変更、契約変更、科学的検証、データセット受入にはそれぞれの承認を要する。

- 現行の具体的な契約・動作は、[Standard Building v0.1](OUEM_Standard_Building_v0.1.md)、[Standard Terrain v0.1](OUEM_Standard_Terrain_v0.1.md)、[VoxCity Adapter v0.1](OUEM_VoxCity_Adapter_v0.1.md)を参照する。ライフサイクルと実装境界は[Phase A Implementation Design v0.1](Phase_A_Implementation_Design_v0.1.md)のCurrent-status noteと現行契約を併せて参照する。
- 本書の一般化されたNative / Standard / Adapterの記述、空間基準、表現・QA・運用方針と現行契約の差分は、今後の仕様化・実装・検証で扱う。本書だけを根拠に現行スキーマ、処理条件、データ配置を変更しない。
- 受入の根拠は[Building受入記録](../experiments/a1_e2e_pilot/README.md)、[A2 Terrain正式受入記録](acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)、[A3 VoxCity正式受入記録](acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)とする。受入は記録されたデータセット・環境・条件に限られ、Standard契約のFINAL化、全国適用、樹冠統合やB1/B2の受入を意味しない。
- 2026-10-25のv0.2に対する文書監査結果CONDITIONAL PASSは、当時の文書監査判定であり、v0.3の設計登録・データセット受入とは別である。第8章の未決・要検証事項と第9章の未承認提案は、その状態を維持する。

## 1. 目的・対象
OUEMは、利用可能な地理空間データから地形・建物・樹冠を統合した3D都市環境モデルを構築し、都市に暮らす人が体感する樹木の環境機能を面的に評価するモデル／ワークフローである。3D樹冠生成そのものを最終目的としない。

- **Phase A**：3D都市環境モデル構築
- **Phase B1**：日射・日陰評価（現況とNo-Canopy反実仮想の比較）
- **Phase B2**：既存OSSの視認指標による樹冠の面的評価

B1/B2では目的に合う既存OSSの公開機能を選び、指標の意味、設定、適用範囲を記録する。v0.1からの継承範囲は§7.1に示す。CFD・風環境等は将来の応用先であり、現段階の実装対象ではない。

## 2. 基本アーキテクチャ

```text
Source acquisition (manual or optional automated)
       ↓
Raw → Native → OUEM Standard → Engine / Analysis Adapter
                      │                   │
                      │                   └→ VoxCity → B1 / B2
                      └→ Other adapters (future, e.g. CFD)
```

- **Raw**：取得した元データ。手動取得を常に許容。
- **Native（Step 1）**：原則として単一の主要データソースに対する変換・正規化・派生処理。複数段階の中間成果物を許容する。補助的な変換グリッドやモデルの利用は妨げない。
- **Standard（Step 2）**：必要に応じ複数の主要データソースを統合し、共通の地形・建物・樹冠の意味・座標・品質条件を満たす表現へ変換する。単一ソースからの受入も可能。
- **Adapter**：エンジン固有の解像度・ボクセル・水密性・干渉解消・解析領域等を処理する。StandardをVoxCity固有仕様にしない。

### 2.1 構築プロファイル
- **A1 Tokyo Reference**：東京都等の高品質データによるReference（Ground Truthとはみなさない）。
- **A2 National Baseline**：Meta CHM・GSI DEM等を活用するベースライン。
- **A3 GSI-LiDAR National Target**：GSI点群・建物外周線等を活用するターゲット。

A1/A2/A3は固定的なデータセット構成ではなく**代表的な構築プロファイル**。レイヤー単位でデータソースを選択・変更できる。初期段階ではプロファイル既定値＋手動オーバーライドとし、自動最適選択は実装しない。

### 2.2 既存実装工程との名称の区別

本書の構築プロファイルA1/A2/A3と、既存実装・受入記録の工程A1/A2/A3は**異なる名称体系**であり、番号の一致は同じ範囲や受入状態を意味しない。

| 番号 | 本書の構築プロファイル | 既存実装工程・受入記録での名称 |
|---|---|---|
| A1 | Tokyo Reference | PLATEAU Buildingの取込・Native-to-Standard処理 |
| A2 | National Baseline | Standard Terrain処理 |
| A3 | GSI-LiDAR National Target | Standard-to-VoxCity Adapterとボクセル生成までの接続 |

既存工程の根拠は前掲の実装設計と受入記録を参照する。例えば工程A3の狛江受入は、構築プロファイルA3のGSI-LiDAR全国ターゲットが実装・受入済みであることを示さない。第4.2章や第9章のA1/A3は構築プロファイルを指す。

## 3. 空間基準と処理範囲
- **管理・保存の基本単位**：日本の3次メッシュ。ただし地物や解析領域をメッシュ境界に強制的に閉じ込めない。
- **水平CRS**：対象地域に適切な平面直角座標系（m）を用い、同一解析地域では統一。CRSの正確なコード・変換履歴を記録する。
- **鉛直**：Standardの3D形状・地形DEM・上端／下端面は、統一した基準の**絶対標高Z（m）**。建物高・樹高・HAGは地盤相対値として区別。元データの鉛直基準を記録し、根拠のないCRSラベル変更を禁止する。2024年標高成果への整合は有力候補だが、採用範囲・変換手段は要検証。
- **地形**：共通DEMを地盤基準とするが、元の建物・樹冠形状を機械的にDEMへ吸着させない。調整は派生処理として明示。
- **ラスタ**：地域・CRS・解像度ごとに共通の原点とセル配置を使用。標準解像度を設定し、高解像度版の追加保持を許容。1mは候補であり未確定。
- **ラスタの3次メッシュ所属**：セル中心で判定。ファイルの矩形外接範囲と正式所属セルを区別する。
- **建物ベクトル**：メッシュ境界で分割しない。建物内部の代表点で一つの所属メッシュを定め、他メッシュからは空間参照する。
- **樹冠ベクトル**：原形状は保持。メッシュ単位の派生物のみ分割を許容し、元IDとの対応・再結合性を維持する。
- **AOI**：任意ポリゴンを基本とし、初期入力はGeoPackage / GeoJSON。AOI、データ処理範囲、解析計算範囲、最終出力範囲を概念上区別する。
- **処理**：3次メッシュ処理を基本とし、必要に応じAOI一括処理。工程ごとのBuffer→処理→Crop/Assignを認め、幅は固定しない。周辺データ不足は不存在と区別し、可能な範囲で処理する。

## 4. Standardの共通データ原則

### 4.1 表現と根拠は別軸
- **Primary / Derived**：Standard内の表現上の位置付け。品質の優劣や直接観測を意味しない。
- **Observed / Estimated / Interpolated等**：値の根拠・生成方法。単純な二値分類に限定しない。
- 欠損と地物の不存在を区別する。補完前の情報を保持し、補完結果は別のDerivedとし、補完セルを識別可能にする。

### 4.2 建物
- **代表高さモデル**と**高さ分布モデル**を許容し、同一建物で併存可能。
- 建物上端ラスタは**絶対標高Z**を格納する。地盤相対高さHAGは、利用DEMを明記して導出する。
- **A1**：元の詳細3D建物形状をPrimaryとし、ラスタ化した上端ZをDerivedとして保持可能。
- **A3**：点群と外周線から構築した建物上端ZラスタをPrimary、簡略3D建物をDerivedとする。
- 簡略3D建物の底面は**建物単位の水平代表地盤標高**を基本とする。地形追従形状は必要に応じ派生生成。代表地盤標高の算定法は未確定。
- 3D形状からの上端ラスタ化は情報損失を伴うため、元の詳細3Dを代替しない。

### 4.3 樹冠
- 基本情報：**ソースプロファイルに応じた樹冠の水平存在情報と判定可能範囲、樹冠上端Zラスタ、樹冠下端Zラスタ**。樹冠厚は上端Z−下端Z。存在判定の根拠、元データ、鉛直基準、位置合わせ、欠測・品質・来歴を保持する。水平情報と高さ情報の妥当性は別々に管理する。
- **水平範囲の基準はソースプロファイルに応じる。** CHM・2D推定マスク主体では、出典・推定手法を明示したモデル上の樹冠存在情報と判定可能域を、ラスタ格子上の水平判定の基準とする。CHMの元値・マスクは維持する。有効なCHMサンプルから導出する場合はDerivedとして扱い、入力・格子・判定規則を記録し、判定と判定可能域を再現できるようにする。別ファイルとしての保存・公開の要否と具体的なスキーマはStandard／実装レビューで決める。元の樹冠ポリゴンを持つプロファイルでは、その原形状を維持し、該当ソースの水平基準とする。Primary／Derivedは情報表現上の位置付けであり、観測／推定や独立した科学的真偽とは区別する。
- **樹冠あり・モデル上の樹冠なし・判定不能を区別する。** 樹冠の存在推定と高さ・DEMの有効性は独立に管理し、存在推定が陽性でも高さ不明ならNoDataを許容する。CHM=0、推定マスク陰性、未判定、調査済み不存在を同一視しない。モデルの判定可能範囲は、独立に調査された生態学的coverageを意味しない。異なる時点やソース間の不整合を隠さない。
- 初期の樹冠下端推定は**簡易Crown Ratio（CR）モデル**。CR値・区分・パラメータは要検証。推定アルゴリズムをStandard仕様へ固定しない。
- 点群由来の上端ZとCR推定の下端Zでは、観測／推定の根拠を別々に記録。点群の高さ候補を、樹冠判定や妥当性検証なしに樹冠CHMと同一視しない。
- **VoxCity解析の主経路**は、共通の高さ・樹冠存在情報・上下端ZからAdapterでTREE voxelへ接続する。**2D樹冠ポリゴンの生成や3Dメッシュ化を、解析の必須中間工程にはしない。** エンジン固有の格子、voxel丸め、建物優先、観測点、haloおよび解析可否の判断はAdapter側で扱い、元の存在・欠測の意味を黙って変更しない。
- **外部出力用の2D樹冠ポリゴン・汎用3D表面メッシュ**は、共通樹冠情報から用途に応じて生成するDerivedとする。既存の原ポリゴンは派生物で置換しない。派生物は原入力・GridSpec・生成条件・近似／欠測・QA・出典を追跡可能にし、生成しなければVoxCity解析できない構成にはしない。具体的な生成規則・ファイル形式・受入条件は各Standard／export仕様で別途決める。
- LAD・透過率など樹冠内部特性は初期Standardでは**未設定**。後から追加できる余地だけ残す。未設定は透過率ゼロを意味しない。
- 建物と樹冠の2D重複を許容。3D干渉の処理は後段へ委ねる。

## 5. QAと受入
- **Standard QA**：CRS・鉛直意味・水平存在情報と判定可能域の根拠・高さ有効性・上下端の大小・欠損状態などの基本整合性。出典・来歴を含む樹冠の共通QAは、幾何の派生出力の有無にかかわらず適用する。
  - **Primaryの原樹冠ポリゴン**：水平基準としてStandardに受け入れる時点で、派生出力の有無にかかわらず原形状と識別子の妥当性を検証する。
  - **任意の派生樹冠ポリゴン・3Dメッシュ**：生成または利用する場合に幾何固有のQAを行う。このQAをラスタ／Height EnvelopeからVoxCityへの解析経路の前提条件にしない。
- **Adapter QA**：エンジン固有の水密性・3D干渉・ボクセル欠損・解析格子など。
- データセット受入判定は **PASS / CONDITIONAL PASS / FAIL**。個別の品質指標・制約・対象IDを別に記録。
- CONDITIONAL PASSは用途無制限の利用許可を意味しない。解析への適合性はAdapterで再判定。
- QA閾値は実データで検証して設定する。

## 6. データ運用と記録
- 全国を事前に一括整備するのではなく、**必要なAOIだけをオンデマンド処理**する。全国適用可能な仕様を目指す。
- 更新は原則 **3次メッシュ×レイヤー**を単位とし、旧版を保持、新版をQA受入後Currentへ切り替える。広域解析は利用した版の組合せを記録する。
- 自動取得は任意の拡張。手動取得を常に許容し、取得手段とRaw→Native変換を疎結合にする。
- Rawは保存推奨だが必須ではない。`retained` / `external` / `removed` 等で状態を記録。再取得できないデータの保全を優先。
- Nativeは再利用価値の高い主要成果物を保存推奨、一時中間ファイルは削除可能。削除後も履歴を保持。
- **Provenance**（データの由来）と**Run Log**（実行履歴）を区別し、必要最小限のJSON等で自動記録する。複雑なDBは導入しない。
- Standardは**レイヤー別**に整理し、関連は軽量メタデータで記録。具体的なフォルダ階層は実装時に確定。

### 6.1 形式
| 対象 | 初期基本形式 |
|---|---|
| 2D建物ポリゴン | GeoPackage |
| 原樹冠ポリゴン（ソースにある場合）・派生2D樹冠ポリゴン（生成時） | GeoPackage（樹冠経路に応じる） |
| DEM・建物上端・樹冠上下端ラスタ | GeoTIFF |
| 樹冠の水平存在・判定可能範囲のラスタ | GeoTIFF（ファイル化する場合の候補。別ファイルの保存・公開要件とスキーマは未決） |
| 3D建物・樹冠メッシュ | 要検証・未決（樹冠は任意の派生出力） |
| Provenance・QA・Run Log | JSON |

## 7. Phase B：既存OSSによる環境指標

用途ごとに公開API、バックエンド、バージョンとコミット、設定、指標の定義と単位を指定する。用途に適した機能があればOSSの計算を利用する。公開APIのカスタム対象クラスは設定として扱い、既定モードと区別して記録する。APIの存在、限定条件での技術E2E、現地での科学的妥当性、正式受入は別の判断とする。

M2の初期参照経路は **VoxCity 1.7.0 CPU**（`fa212656305328a9a657973bae26f352bfe813bc`）。GPUは別実装として、利用を具体的に検討する時点で関数と設定を指定して評価する。バックエンド間の同等性と指標名の共用には根拠を要する。

| 対象 | 技術実証と候補 |
| --- | --- |
| B1 日射・日陰 | **限定実証済み**のCPU `get_direct_solar_irradiance_map` は水平面の瞬間直達日射強度（W/m²）。狛江の実証は人工太陽条件（方位135°、高度35°、DNI 800 W/m²）と未校正の `k=0.6`・`LAD=1.0` を使用した。CPUの散乱・全球日射、累積・EPW経路は候補。GPU `get_sunlight_hours` のPSH（EPWによる気象条件）・DSH（晴天仮定）、建物面・体積のGPU日射は別途評価する候補。日照時間（h）や期間積算、実気象や光学精度の検証は未実施。[B1技術記録](status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md)・[CPU公開API](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator/solar/__init__.py)・[CPU直達計算](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator/solar/radiation.py)・[GPU公開API](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator_gpu/solar/integration/__init__.py)・[GPU日照時間](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator_gpu/solar/integration/ground.py) |
| B2 樹冠の視認 | **限定実証済み**のCPU weighted first-TREE view indexは `get_view_index(mode=None, hit_values=(-2,), inclusion_mode=True, fast_path=False)`。無次元で、通常の第一TREE交差区間の寄与は `1−exp(−k·LAD·L)`。試験設定は `k=0.5`、`LAD=1.0`、水平360°の等間隔120方位、仰角−30°〜+30°の等間隔20方向（両端含む）で、2,400レイを等重み平均する。二値ヒット率、樹冠全体を積分した透過率、写真式緑視率は別の測定量として扱う。CPU `mode='green'` は `(-2, 2, 5, 6, 7, 8)` を対象とし、TREEを含む対象集合に対するスコア規則と実行経路を確認してから使う。Sky View Factorも用途に応じた候補。GPUの地上視認経路ではTREE対象ヒットに1を加える分岐があり、CPUと同じスコアは前提にできない。[B2技術記録](status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md)・[B2 API監査](planning/OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md)・[CPU API](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator/visibility/view.py)・[CPU汎用スコア](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator/common/raytracing.py)・[GPU API](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator_gpu/visibility/integration.py)・[GPUカーネル](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/simulator_gpu/visibility/view.py#L407) |

B1では、同じOSS指標の **No-Canopy − Current** をOUEMの派生量として記録する。地形・建物・気象・時刻・観測点・計算領域を固定し、樹冠だけを変える。差分の単位と符号は選んだ指標とともに示す。

両評価で実観測点XYZと有効マスク、D0、格子の向き・回転、樹冠と建物の優先順位、観測点の採否、出力の有効ゼロとNaN、ROI／計算域・halo・外部遮蔽物、光学・時刻条件と来歴を記録する。要求値 `view_point_height=1.5` の狛江例では、実際の位置はボクセルの観測点規則に従う。観測点は座標で確認し、32 m haloの十分性は利用する方向・領域ごとに評価する。[B1観測点記録](experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md)

VoxCityGML 0.3.0（`19628c033b1cbbbdee80fe781f516672765d1eee`）は統合・形状経路の候補であり、日射・視認はVoxCityの機能を呼ぶ。VoxCity 1.8.0で導入された既定の建物下樹冠マスクは将来の互換性評価事項とし、現行1.7.0の配置・建物と樹冠の重複根拠の扱いは§4.3に従う。[VoxCityGML固定版](https://github.com/kunifujiwara/VoxCityGML/tree/19628c033b1cbbbdee80fe781f516672765d1eee)・[OUEM P1記録](reviews/OUEM_VoxCityGML_P1_Architecture_Closeout_20261110.md)・[VoxCity 1.8.0変更履歴](https://github.com/kunifujiwara/VoxCity/blob/v1.8.0/CHANGELOG.md)

### 7.1 v0.1からの継承と改定範囲

- [B1のv0.1第6章](OUEM_Concept_Architecture_v0.1.md#6-b1-----solar--shade-assessment)から評価目的、Current／No-Canopyの比較、評価期間・気象の明示、タイル・余白・切り出し・GIS成果の原則を継承する。本案の§7が基本計算と指標の選定を規定し、旧§6.4のTier 1一式（日陰形成時間を含む）をM2の必須出力とする規定を置き換える。各出力の役割は選んだOSS指標と用途に応じて定義する。
- [B2のv0.1第7章](OUEM_Concept_Architecture_v0.1.md#7-b2-----green-view-assessment)から、歩行者視点での樹冠評価の目的、水平範囲と上下視野・レイ設定の明示、写真式緑視率との関係を記録する原則を継承する。本案の§7が旧§7.1–7.5の正式名称・対象クラス・二値算定・360°の固定要件・指標別Tierの一律指定を置き換える。写真・現地観測との対応の科学的評価はM3で扱う。
- [v0.1第9章](OUEM_Concept_Architecture_v0.1.md#9-認識済みの主要engineering--validation-issues)の気象・時間帯、観測高さ、透過パラメータ等の検証課題を継承する。既存記録と未決事項は[B1 backlog](planning/OUEM_B1_Deferred_Validation_Backlog.md)と[B2 backlog](planning/OUEM_B2_Deferred_Validation_Backlog.md)を参照する。

## 8. 未決・要検証（決定事項ではない）
1. 日本の鉛直基準・標高成果の具体的な採用範囲、PLATEAU / LiDAR / DEM間の変換と検証方法。
2. 水平CRSの地域選定ルール、CRS境界を跨ぐAOIの扱い。
3. 標準ラスタ解像度（1m候補）、原点規則、セル境界・NoDataの細則。
4. 建物の代表地盤標高の算定方法、屋根上端ラスタ化の定義。
5. CR区分・係数、樹冠下端の品質指標、欠損補完方法。
6. 3Dメッシュの保存形式、形状の生成・検証方法。
7. QA閾値、各プロファイルの実際のソース一覧と利用条件。
8. VoxCity Adapterの入力仕様とB1/B2の小範囲end-to-end検証。
9. 既存GitHub実装との差分と、過去の建物高さ不整合の原因検証（未確定）。

## 9. 初期実装の優先順位（提案・未承認）
1. **A1小範囲での鉛直基準と建物高さの整合確認**。原因未確定の高さ不整合を、元データ・変換・Standard・表示の各段階で切り分ける。
2. **最小Standard**：共通CRS・DEM・建物・樹冠、基本QA、最小Provenance / Run Log。
3. **VoxCity Adapterで小範囲end-to-end**：3D表示→選定したB1指標のシナリオ比較→選定したB2指標（§7）。
4. **A3の小範囲PoC**：GSI点群と建物外周線による上端Z・簡略3D建物、樹冠上下端。

上記は実装計画の**提案**であり、設計決定01〜36と同じ確定度ではない。

## 10. v0.1からの主要変更（v0.2から継承）
- VoxCity中心の入力準備を、**VoxCity非依存のOUEM Standard＋Adapter**へ明確化。
- Raw / Native / Standardの責任境界と、単一ソース処理・複数ソース統合を整理。
- 建物・樹冠のPrimary / Derivedおよび観測・推定根拠を独立管理。
- 絶対標高Zを共通3D表現とし、HAG・樹高等を区別。
- 3次メッシュを管理の基本としつつ、AOI・処理・出力・原形状を分離。
- QA・欠損・更新・ファイル保持・履歴を軽量に管理。
- A1/A2/A3を代表プロファイルとして、レイヤー別のソース選択を許容。

### 10.1 v0.2からの変更（2026-11-14／上位概念として承認）
- §4.3：一律「ポリゴンを水平基準」から、ソースプロファイル依存の水平存在情報へ変更。モデル判定域／独立調査coverage、高さ有効性、推定／真値を区別。
- §4.3：VoxCity主経路はラスタ・高さ情報からのAdapter接続とし、2Dポリゴン／3Dメッシュは必要時の独立派生出力へ分離。
- §5・§6.1：共通QAと幾何出力固有QAを分け、水平判定ラスタの形式を追加。具体的なCanopy Standardスキーマ、コード値、受入条件は未確定。
- 変更しない事項：v0.1からのB1/B2継承、CRの暫定性、鉛直根拠、Raw／Native／Standard／Adapter、過去の実行・Acceptance証拠、既存GSI／Meta実装。

---

### 10.2 v0.3からの変更案（M2-A／未承認）

§1、§7、§7.1および§9のB1/B2参照を、既存OSS指標を選ぶ方針に合わせる。§10.1はv0.3登録時点の履歴である。正式設計と登録の判断は[Concept v0.3](OUEM_Concept_Architecture_v0.3.md)および[文書ガバナンス](OUEM_Documentation_Governance_v0.1.md)を参照する。
