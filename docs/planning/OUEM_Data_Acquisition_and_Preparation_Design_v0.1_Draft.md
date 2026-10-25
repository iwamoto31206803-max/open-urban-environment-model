# OUEM Data Acquisition & Preparation Design v0.1 — Draft

- 作成日：2026-10-25
- 状態：**DRAFT / 設計レビュー待ち / 実装・受入未実施**
- 位置付け：OUEM Concept & Architecture v0.2の下位に置くデータ取得・準備の設計案
- 根拠：2026-10-25までの本チャットの設計協議、PR #60の実装・データ取得インベントリ
- 注意：この文書は既存のStandard Building v0.1、Standard Terrain v0.1、VoxCity Adapter v0.1、狛江市受入記録を**自動変更しない**。実際のデータ提供URL、ライセンス、取得版、鉛直基準、変換手順は、独立確認が必要な項目を含む。

## 1. 目的と適用範囲

OUEMの地形・建物・樹冠を、東京都の高品質データおよび全国の地域別に利用可能なデータから、再現可能な手順で構築する。対象はデータソース選択、取得、Raw登録、Native生成、Standardへの受入、来歴管理、品質管理まで。VoxCity固有の格子化とB1/B2解析はAdapter以降の責任範囲。

全国版は**レイヤー別最適データ選択（B案）**を採用する。A1 Tokyo Reference、A2 National Baseline、A3 GSI-LiDAR National Targetは**構築プロファイル**であり、既存の実装工程A1 Building／A2 Terrain／A3 VoxCity Adapterとは別概念。各プロファイルは既定候補を与えるが、レイヤーごとの明示的なソース変更を認める。初期版で自動最適選択は実装しない。

## 2. 全体フローと責任分界

```text
AOI / profile / required layers
    ↓
Source Catalog → source suitability review → explicit source selection
    ↓
Acquisition Recipe → manual or optional automated acquisition
    ↓
Raw (original distribution units) + Dataset Manifest
    ↓
Work (temporary transformations, point processing, mosaics)
    ↓
Native (provider-specific accepted representation + existing native receipts)
    ↓
OUEM Standard (source-independent geometry, elevation, QA, provenance)
    ↓
Engine Adapter → VoxCity / B1 / B2
```

- Raw：配布元のZIP、CityGML、GML/XML、GeoTIFF、LAS/LAZ、画像等。可能なら元ファイルを保持。保持状態`retained` / `external` / `removed`等を記録。
- Work：展開、形式変換、HAG、ラスタ化、タイル結合、モデル推論等の再生成可能な中間物。保存は必要性に応じて選択。
- Native：ソース固有の主要成果物。単一主要ソースを原則とし、補助DEM等の利用は許容。
- Standard：必要に応じ複数主要ソースを統合。絶対標高Z、共通水平CRS、レイヤーの共通意味とQAを保証することを目指す。
- Adapter：VoxCity等の解析エンジン固有の解像度、ボクセル、干渉、解析範囲を扱う。

## 3. データソース・構築経路

以下は**採用候補・優先経路**であり、各配布元の現在の利用条件、カバー範囲、版を確認する前の正式採用ではない。

### 3.1 Terrain

| プロファイル・条件 | 候補ソース | Raw | Native/Work | Standard |
|---|---|---|---|---|
| A1 東京 | 東京都公開DEM、対応する点群由来DTM | 元GeoTIFF/点群 | 格子・標高・鉛直基準検査。必要時に地盤抽出 | 共通地盤絶対Z GeoTIFF |
| A2 全国 | GSI基盤地図情報DEM（地域で利用可能な1m/5m/10m等） | 元ZIP・GML/XML | GeoTIFF化、必要時に座標変換、NoData/格子検査 | 同上 |
| A3 LiDAR | GSI DEM、適合するDEMがなければGSI点群由来DTM | 元DEM/点群 | 地盤点分類・DTM生成・QA | 同上 |

既存DEMを優先。ただし点群との測量時期・鉛直整合を確認し、適切なDEMがない場合は地盤点からDTMを生成する。5m DEMを1mへリサンプリングしても実効解像度が1mに向上するわけではない。元解像度と出力解像度を別記録する。

### 3.2 Building

| 経路 | 入力 | 加工 | 出力の意味 |
|---|---|---|---|
| BLD-1 | PLATEAU CityGML | 既存Converter等→Native→Standard。LoD・Z保持検査 | 詳細3D形状をPrimary、必要な上端ZラスタをDerived |
| BLD-2 | GSI基盤地図情報「建築物の外周線」＋LiDAR＋DEM | 外周線復元、屋根上端抽出、地盤標高付与 | 上端Z分布をPrimary、簡略3D形状をDerived |
| BLD-3 | GSI建築物外周線＋推定高さ＋DEM | 明示した推定方法で簡略化 | Estimatedと明記した暫定3D |

PLATEAUを優先候補とするが、地域・版・LoDの適格性で選択する。GSI外周線は全国向けの基礎候補だが、線データから閉じた建物ポリゴンへの再構成、屋根縁と壁面の差、欠損・位相QAが必要。高さ情報のない場合に無根拠な高さを捏造しない。狛江市で残る元CityGML→Converter→建物Zの高さ不整合疑義は独立の未解決事項。

### 3.3 Canopy：3つのNative経路

| 経路 | 水平範囲 | 高さソース | Native生成 |
|---|---|---|---|
| CAN-1 | Meta CHMから閾値・連結領域等で抽出 | Meta CHMをそのまま相対樹高として使用 | 元CHM、樹冠候補領域、品質・版を記録 |
| CAN-2 | 自治体提供樹林・樹冠ポリゴン | 東京都・自治体・GSI等のLiDAR | ポリゴンとLiDAR由来CHMを統合 |
| CAN-3 | GSI航空写真をOAM-TCDで推論 | LiDAR由来CHM | 推論ポリゴンとLiDAR由来CHMを統合 |

CAN-2の「樹林区域」は実際の樹冠外縁とは限らない。CAN-3はGSI画像の解像度・撮影時期とモデルのスケール適合、重みの商用利用条件を事前確認する。既存のOAM-TCD試行は全国適用可能性の証明ではない。CAN-1の「そのまま」は**CHM高さ値を再推定しない**意味であり、樹冠ポリゴン抽出、地盤との整合、絶対Z化は必要。Meta CHMの高さは**モデルによる推定値**であり、LiDARで直接観測した高さとは区別し、モデル版・推定の来歴・不確実性を記録する。

Standard Canopyの基本情報は、**樹冠ポリゴン、上端絶対Zラスタ、下端絶対Zラスタ**。下端は初期候補としてCrown Ratio（CR）推定を用い、係数・観測/推定根拠・適用範囲を記録。点群で直接推定できる場合は別手法を許容。高さ不明の樹冠と樹冠不存在は区別する。**CHMは樹冠上端の候補情報**であり、有効なCHM値だけで樹冠の存在・樹種を確定しない。樹冠下端Zは地盤基準、推定方法、適用範囲を明示し、上端Zとの大小関係に加えて地盤との関係も検査する。

## 4. CAN-2/3共通LiDAR HAG→CHM処理

1. **Preflight**：LAS/LAZ等のファイル完全性、水平CRS、鉛直基準、測量時期、点密度、点分類、RGBの有無、AOI+Bufferの被覆を検査。
2. **Ground reference**：対応する既存DEM/DTMを優先。適合性が確認できなければ点群の地盤分類・DTM生成。地盤分類済みでも、地盤点の妥当性、補間セル、観測密度、測量時期差を検査する。
3. **HAG**：各点の相対高さ`HAG = point_absolute_Z - ground_absolute_Z`を計算。鉛直基準が整合しない場合は停止または明示的な保留。
4. **Canopy candidate points**：高さ・分類・外れ値を検査。樹冠ポリゴンだけで非樹木点を完全排除できるとはみなさない。
5. **Unmasked CHM**：ポリゴン適用前にセル統計を生成。初期候補は1m、最大HAG。点数とP95を診断用に記録。P99や別解像度は実データで比較。
6. **Masking**：CAN-2自治体ポリゴンまたはCAN-3推論ポリゴンを適用。マスク前後を区別し、ポリゴンの時期・座標ずれ・過不足を診断。
7. **Native QA**：点数、NoData、外れ値、タイル継ぎ目、ポリゴン整合、地盤点・非樹木点・補間セル・建物・電線混入疑義、点群・ポリゴン・DEM間の測量時期差を検査。ポリゴンマスクとは独立して、CHMの非樹木点と観測欠損を診断する。
8. **Standardization**：共通地盤Zと整合する上端Zを生成し、下端Z推定と根拠を付与。`Z_top = Z_ground + H_CHM`、`Z_bottom <= Z_top`に加え、`Z_bottom`と地盤Zの関係を、推定手法と適用範囲に照らして検査する。式の成立だけで樹冠の存在や高さの真値性を保証しない。

1m/最大値/P95は**PoC初期候補であり確定した全国Standard契約ではない**。セルに点がない場合、樹冠が観測上存在しない場合、異常値、AOI外を区別する。欠損セルを無条件に0mへ変換しない。点密度不足のときは2m等への変更を許容し、比較・QAを必須とする。巨大なHAG点群は再生成可能なら任意保存とし、入力・設定・出力ハッシュを残す。

## 5. Source Catalog / Recipe / Manifest / Run Record

**4種類の記録を分離する。** 新管理体系は既存Native/Standard manifest・receipt・acceptanceを置換しない。

| 記録 | 目的 | 最小項目 |
|---|---|---|
| Source Catalog | 取得可能なソースの定義 | `source_dataset_key`, provider, official landing URL, access mode, format, coverage, release policy, license reference, verification status |
| Acquisition Recipe | 取得からNative候補生成までの再現可能な手順 | `recipe_id`, version, supported source, prerequisites, manual/automated steps, tools/versions, settings, expected inputs/outputs, QA, known limitations |
| Dataset Manifest | **実際に取得した**配布物の同一性 | `dataset_id`, source key, provider release, acquired_at, URL/selection, license evidence, spatial/vertical metadata, files, SHA-256, retention status, verification status |
| Run Record | **実際に実行した**変換の履歴 | `run_id`, recipe/version, code revision, environment, inputs/manifest IDs+hashes, parameters, AOI/buffer/grid, outputs+hashes, QA, warnings, execution status |

既存Buildingのフィーチャー属性`source_id`と台帳のデータソース識別子を混同しないため、台帳は`source_dataset_key`を採用する案とする。`dataset_id`は版・取得範囲を識別し、`artifact_id`は成果物、`area_id`はAOI、`mesh_id`は3次メッシュ、`run_id`は実行を識別する。文字列IDは人間可読でもよいが、同一性は版情報とSHA-256で確認する。具体的なID構文は既存実装照合後に決定。

取得操作が手動であっても、取得日時・クリックした配布ページ/選択条件・元ファイル名・配布版・ライセンス確認結果・ハッシュを記録する。URL不明・ライセンス未確認は`unverified`として残し、確認済みと装わない。Rawを保存できない場合は外部所在・再取得可能性・保持状態を記録する。Rawを保持しない場合は、元配布物の変更・削除・アクセス権変更により**完全な再実行ができない可能性**を明示し、残存する入力のハッシュと再取得の依存条件を記録する。

### 5.1 記録の関係

次の図は関係の概念図であり、**一対一の処理連鎖を要求しない**。

```text
Source Catalog ── references ── Acquisition Recipe
      │                                │
      └───────── Dataset Manifest(s) ─┘
                      │  ▲
           reused by  │  │ references multiple inputs
                      ▼  │
                  Run Record(s)
                      │
                      ├── Work / Native artifact(s)
                      └── Standard artifact(s) → existing QA/acceptance
```

**一つのDataset Manifestは複数のRunから再利用でき、一つのRunは複数のDataset Manifestを入力として参照できる。一つのRunが複数の成果物を生成することも許容する。** Dataset Manifestは取得物の同一性を、Run Recordは処理実行と入出力の関係を管理する。取得イベント、配布版、取得範囲、ファイル単位のSHA-256を識別できるようにする。具体的なID構文と参照スキーマは実装前に確定する。

レイヤー間の組合せもRunとStandard provenanceで追跡する。新管理層は既存manifestやreceiptを参照するだけで、受入済みファイルの意味や構造を無断で変更しない。

## 6. 保存・更新・識別

```text
data/
  raw/{terrain,building,pointcloud,imagery,canopy}/<provider-or-dataset>/...
  work/<run_id>/...
  native/{terrain,building,canopy}/...
  standard/{terrain,building,canopy}/...
  model/...
  output/...
metadata/                     # 提案・未確定。既存manifestは移動しない
  sources/ recipes/ datasets/ runs/ areas/
```

- Rawは**元の配布単位**で保存し、異なるAOIから再利用する。3次メッシュに切断してRawを改変しない。
- Standardの更新・管理は原則**3次メッシュ×レイヤー**。建物および樹冠の原形状はメッシュ境界で分割しない。地物には重複しない**所有メッシュ**を一つ設定し、交差する他メッシュからも空間索引で参照可能とする。所有メッシュは保存・更新の責任単位、交差メッシュは検索・解析の対象範囲として区別する。重複集計を防ぎ、分割された派生物から原形状IDへ追跡できるようにする。所有メッシュの厳密な決定規則と境界例外は実装前に定義する。
- `area_id`と`mesh_id`は別概念。複数自治体にまたがるメッシュ、複数メッシュにまたがるAOIを許容する。
- 同一地域の異なる年度・ソース・版・runを共存させ、QA受入後にCurrent参照を切り替える。旧版と採用したレイヤー組合せを保持する。
- ローカル絶対パスを可搬な同一性キーにしない。既存Terrain manifestにある絶対パスは互換維持し、将来のポータブル参照方式は別途仕様化する。
- `metadata/`の採用、JSON/YAMLの選択、命名規則、Currentポインタの実体は**未確定**。既存契約との照合後に決める。

## 7. データ選択・フォールバック

1. AOI、Buffer、必要レイヤー、構築プロファイル、解析用途を入力。
2. Catalogから対象地域を覆う候補を抽出。
3. **適格性ゲート**：利用条件、取得可能性、AOI+Bufferの被覆、水平/鉛直基準の変換可能性、必要な品質・時期。
4. 適格な候補を品質、測量時期、解像度、処理負荷で順位付け。
5. 初期実装では**ユーザーが採用ソースを明示的に確定**。自動で黙って切り替えない。
6. 選択理由と不採用理由（未整備、取得不可、条件不適合、時期不整合、品質不足等）を**実行前に保存可能なSource Selection Record**に残し、後続のRun Recordから参照する。Run未実施でも選択判断を追跡できるようにする。

フォールバックは必ずしも品質低下ではない。樹林ポリゴンの時期が古い場合、CAN-3の方が適切な場合もある。CAN-1/2/3は地域に応じて選び、全地域で一律の経路を強制しない。

## 8. AOI、Buffer、水平CRS、鉛直、格子

- **AOI**：GeoPackage/GeoJSONの任意ポリゴンを初期入力とする。`analysis_aoi`、`processing_extent`（Buffer込み）、`storage_mesh`、`output_extent`を区別する。
- **Buffer**：用途・工程ごとに設定。B1の日陰とB2の視線範囲で必要距離は異なる。幅を全国一律に固定しない。周辺データ不足は地物不存在と区別する。
- **水平CRS**：地域に適した平面直角座標系（m）に統一。狛江市既存EPSG:6677は地域固有の受入条件であり全国固定ではない。CRS境界を跨ぐAOIは未決。
- **鉛直**：Standardは統一された**絶対標高Z（m）**。地盤相対HAGや建物高さとは区別。元データの鉛直基準、変換根拠、処理を記録。不明・不整合なら正式受入を保留し、CRSラベルの付け替えで解決しない。
- **格子**：CRS・地域・解像度ごとの共通原点とセル配置。セル中心で3次メッシュ所属を決定。Native元格子・元解像度を保持可能。1mは候補であり未確定。再サンプリング方法は標高/高さ/マスク/カテゴリ値ごとに選ぶ。
- **欠損・推定**：`valid canopy`、`observed non-canopy`、`no observation`、`invalid`、`outside AOI`、`estimated`を概念的に区別する。CHMの有効値だけで樹冠の存在・樹種を確定しない。未観測・地物不存在・無効・推定の具体的な符号化、受入条件は**将来のStandard Canopy契約**で定義する。

## 9. QA・受入と記録

| 段階 | QAの責任 | 主な検査 |
|---|---|---|
| Source/Raw | 取得・登録 | 出典・利用条件・版・配布ファイル・SHA-256・取得日時 |
| Native | ソース別処理 | CRS・鉛直・点群分類・点密度・形状・ラスタ・NoData・ソース特有の異常 |
| Standard | 共通表現 | 絶対Z・共通格子・ID・top/bottom関係・原形状・来歴・欠損区別 |
| Adapter | エンジン依存 | ボクセル、干渉、解像度、解析入力、用途適合性 |

**処理状態**（未実施・実行中・保留・完了・失敗など）と**QA判定**は独立して管理する。QA未実施や判定保留を`FAIL`や`CONDITIONAL PASS`と同一視しない。QA判定は実際に評価した対象に限って`PASS` / `CONDITIONAL PASS` / `FAIL`とする。`CONDITIONAL PASS`は無制限な解析利用を認めない。必須の鉛直基準・ライセンス・ファイル同一性等が不明な場合は、判定対象と保留理由を明記し、PASSにしない。未整備・未取得と品質不良を区別。閾値（点密度、NoData率、CHM外れ値、屋根/樹冠Z誤差等）は実データで校正し、設計段階で根拠なく確定しない。

## 10. 既存実装・受入との互換性

- 現行のBuilding Native manifest/receipt、Terrain Native manifest、Standard manifests、Adapter acceptanceはそのまま維持。
- 新しいDataset Manifestは**Raw取得と元データの同一性**を管理し、Run Recordは**変換実行の来歴**を管理する。既存のレイヤー別受入記録とは役割が異なる。
- PR #60のインベントリは**静的調査**であり、ソースURL・ライセンス・実ファイル・新PC実行の独立確認をしていない。
- 狛江市のBuilding Native→Standard、Terrain Native→Standard、VoxCity Adapterには限定条件下の既存受入があるが、Raw再取得からの完全再現、Standard Canopy、全国展開、B1/B2の受入を意味しない。
- 概念設計の決定だけを根拠に既存のコード、パス、manifest schema、受入記録を一括変更しない。新契約は別途レビュー・テスト・移行計画を必要とする。

## 11. 未決事項と実証計画

### 11.1 仕様化前の確認

1. Source Catalog/Recipe/Manifest/Run Recordの正式なJSON schema、ID構文、保存場所、既存manifestとのリンク方式。
2. 3次メッシュIDとRaw配布単位の索引、Current参照の切替と履歴保持。
3. 地域別の平面直角CRS選定と境界跨ぎ、共通ラスタ原点・解像度・再サンプリング。
4. データソース別の鉛直基準と変換手段、特にPLATEAU CityGML→ConverterのZ整合。
5. 各公式ソースの実際のダウンロード経路、配布版、カバー範囲、ライセンス、利用制限、更新周期。
6. CAN-1 Meta CHMの公式配布経路・版・ライセンスと、CAN-3 OAM-TCDモデル重みの利用条件。

### 11.2 実データで検証して決定

1. 狛江市LiDAR：HAG最大値、P95/P99、1m/2m格子、点数、NoData、タイル境界、地盤整合を比較。
2. CAN-2自治体樹林ポリゴン：樹冠外縁との違い、街路樹欠落、建物・道路混入。
3. CAN-3 OAM-TCD：GSI画像解像度と推論スケール、位置精度、モデルライセンス、実用性。
4. CAN-1：Meta CHMの樹冠ポリゴン抽出、元DEMとの整合、観測年の違い。
5. CR推定：樹冠下端の係数・分類・不確実性。
6. GSI建築物外周線：線→ポリゴン復元とLiDAR建物高さ推定。

### 11.3 段階的実装の推奨（未承認）

- **P0**：既存狛江Raw取得の公式経路・ライセンス・Converter設定・Z診断を確定し、元データとRun来歴を登録。
- **P1**：最小Catalog/Recipe/Manifest/Run schemaを、既存契約非破壊で追加。狛江Terrain/Buildingを新PCで再取得・再実行。
- **P2**：LiDAR HAG→CHM共通処理とCAN-2小範囲実証。CAN-1の配布・provenance確認。
- **P3**：CAN-3日本向け推論・樹冠QA、全国の別地域でGSI DEM/外周線/LiDAR経路を検証。
- **P4**：3次メッシュ×レイヤー更新、複数AOI、より自動的な候補提示と運用。

## 12. 文書レビューで確認してほしい事項

1. Concept & Architecture v0.2の責任境界、Standard絶対Z、Primary/Derived、観測/推定、AOI/メッシュ原則との整合。
2. 既存Standard Building/Terrain、VoxCity Adapter、狛江市の受入証跡を無断で改変しないこと。
3. CAN-1/2/3の入力・生成物・ライセンス/モデルの不確実性が明示されていること。
4. Catalog/Recipe/Manifest/Run Recordの役割重複・欠落がないこと。
5. 鉛直基準、格子、QA数値、公式ソースURL等を未検証のまま確定していないこと。
6. 文書承認と実装・データ受入の区別が維持されていること。

## 参照文書

- `docs/OUEM_Concept_Architecture_v0.2.md`（正式登録の上位概念設計）
- `docs/planning/OUEM_v0.2_Implementation_Inventory_20261025.md`（PR #60、静的実装棚卸し）
- `docs/planning/OUEM_Data_Acquisition_and_Reproducibility_Inventory_20261025.md`（PR #60、取得・再現性棚卸し）
- `docs/OUEM_Standard_Building_v0.1.md`、`docs/OUEM_Standard_Terrain_v0.1.md`、`docs/OUEM_VoxCity_Adapter_v0.1.md`
- 狛江市Building / Terrain / Adapter / Contained E2Eの各受入記録

---

**状態確認：本書は設計ドラフトであり、コード変更、実データ取得、QA受入は未実施。PR #61について独立設計監査（CONDITIONAL PASS）が実施され、指摘事項を本文へ反映した。修正後の再確認およびマージは別途実施する。**
