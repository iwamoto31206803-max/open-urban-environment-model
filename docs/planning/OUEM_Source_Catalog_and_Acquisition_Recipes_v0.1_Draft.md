# OUEM Source Catalog & Acquisition Recipes v0.1 — Draft

- 作成日：2026-10-25
- 状態：**DRAFT / 独立監査前 / 実装・取得・QA受入未実施**
- 上位設計：`docs/OUEM_Concept_Architecture_v0.2.md`
- 関連設計：`docs/planning/OUEM_Data_Acquisition_and_Preparation_Design_v0.1_Draft.md`（PR #61の修正反映版を参照。マージ状態は独立確認）
- 対象：全国版B案「レイヤー別最適データ選択」に基づくSource Catalog、Acquisition Recipeの**設計候補**。既存Building/Terrain/Adapter契約、受入記録、パスを変更しない。

## 1. 設計原則と境界

1. Terrain、Building、Canopyは**レイヤーごと**に最適なソースを明示選択する。自動フォールバックは初期実装しない。
2. Source Catalog（候補の知識）、Source Selection Record（実行前の選択理由）、Acquisition Recipe（手順）、Dataset Manifest（実取得物）、Run Record（実処理）は異なる。単純な一対一連鎖ではなく、Dataset Manifestは複数Runに再利用でき、Runは複数Dataset Manifestから複数Artifactを生成できる。
3. Rawは元の配布単位を可能な限り保持する。Rawが外部所在のみの場合は再取得不能リスクを記録する。Workは再生成可能な中間物。Native/Standardの既存manifest・receipt・acceptanceを置換しない。
4. 公式サイトの存在と、個別配布ファイルの利用条件・版・CRS・鉛直基準の検証完了を混同しない。**この文書に記載したURLやS3 prefixは実ダウンロード・ライセンス受入の証拠ではない。**
5. Source Selectionの承認と、Run実行状態と、各段階のQA判定（PASS / CONDITIONAL PASS / FAIL）は別管理。未実施・保留はQA FAILと同義ではない。
6. Standardは共通水平CRS、絶対標高Z、原形状・来歴・品質区別を目標とする。Canopyの正式契約・符号化は未確定。メッシュ所有と交差検索は区別し、原形状を境界で切らない。

## 2. Source Catalog候補

以下の`source_dataset_key`は**仮のカテゴリ識別子**。正式なID構文、ソースごとの版・範囲・取得イベントは実装前に別途定義する。

| 仮キー | 提供元・候補データ | 用途 | 取得経路の候補 | 現段階の確認境界 |
|---|---|---|---|---|
| SRC-T01 | GSI 基盤地図情報 数値標高モデル（DEM1/5/10等） | Terrain | https://service.gsi.go.jp/kiban/ | 具体的な種別、測地成果、配布版・ファイルは未検証 |
| SRC-T02 | 東京都・自治体DEM / LiDAR由来DTM | Terrain | 地方公共団体の公開窓口（地域別） | 個別配布先・権利・高さ基準未検証 |
| SRC-B01 | PLATEAU CityGML | Building | https://www.mlit.go.jp/plateau/open-data/ | 都市・年度・LoD・個別配布物は未検証 |
| SRC-B02 | GSI 基盤地図情報 建築物の外周線 | Building | https://service.gsi.go.jp/kiban/ | 閉合・ポリゴン化の成立と版は未検証 |
| SRC-C01 | Meta/WRI Canopy Height Map v2（CHMv2） | Canopy | https://registry.opendata.aws/dataforgood-fb-forestsv2/ | S3のタイル索引・配布版・利用条件は実取得時に検証 |
| SRC-C02 | 自治体樹林・樹冠ポリゴン | Canopy | 自治体オープンデータ等（地域別） | 「樹林区域」と実樹冠外縁の意味の差に注意 |
| SRC-C03 | GSI空中写真・地理院タイル | Canopy | https://maps.gsi.go.jp/development/ichiran.html | 元解像度・撮影年・タイル利用条件を確認 |
| SRC-L01 | GSI航空レーザ点群 | Building/Canopy | GSIの点群提供窓口（別途確認） | 提供・購入条件、LAZ版、測地成果、分類は未検証 |
| SRC-L02 | 東京都・自治体航空レーザ点群 | Building/Canopy | 自治体配布窓口（地域別） | 個別地域の配布版・利用条件・鉛直基準は未検証 |

Catalog最小項目案：`source_dataset_key`, `provider`, `dataset_name`, `official_landing_url`, `access_method`, `format`, `coverage`, `resolution_or_density`, `horizontal_crs`, `vertical_reference`, `license_reference`, `license_verification_status`, `metadata_verification_status`, `last_checked_at`, `notes`。不明値は明示的にunknownとし、推測値で埋めない。

## 3. 共通Recordの責任

| 記録 | 作成時点 | 主な内容 |
|---|---|---|
| Source Catalog | 取得前 | ソースの所在、提供条件、対象範囲、検証状態 |
| Source Selection Record | **実行前** | AOI、レイヤー、候補、適格性、採否・理由、確認者、判断時点 |
| Acquisition Recipe | 取得前 | 手順版、必要入力、ツール、変換、QA、既知の制約 |
| Dataset Manifest | **実取得後** | `dataset_id`、取得イベント、配布版、取得範囲、元ファイル名・サイズ・SHA-256、保持状態、元CRS/鉛直、利用条件証跡 |
| Run Record | **処理実行時** | `run_id`、Recipe版、code revision、環境、複数入力Dataset IDs、設定、複数出力Artifact IDs・SHA-256、処理状態・QA参照 |

`source_dataset_key`とBuilding featureの`source_id`を混同しない。正式なID構文・JSON Schema・既存manifest参照方法・保存パスは**実装前に決定**する。ファイル単位のハッシュは同一性の検証であり、出典・ライセンスの正当性を単独で証明しない。

## 4. Acquisition Recipe共通インターフェース案

- 入力：`area_id`、`analysis_aoi`、`processing_buffer`、必要レイヤー、承認済みSelection Record、入力Dataset Manifest IDs、Recipe version、パラメータ。
- 出力：元Rawの参照、Work、Native候補、QA診断、Artifact IDとSHA-256、Run Record。Standardへの昇格は**既存の別途受入手続き**。
- 記録：ソフトウェア版（GDAL/PDAL/Converter/モデル等）、コードrevision、CRS変換・鉛直変換根拠、元解像度、出力格子、NoData、測量/撮影時期。
- ゲート：ライセンス・取得可否・AOI+Buffer被覆・水平/鉛直適合・データ品質。必須の鉛直基準や利用条件が未確認なら正式受入PASSにしない。
- 同一Recipeの再実行は新しいRun Recordで表し、Rawを重複登録する必要はない。失敗・保留Runも診断可能な範囲で記録する。

## 5. 個別Recipe設計

### T-01 — GSI DEM → Native Terrain

1. AOI+Bufferから必要配布メッシュを計算。DEM1/5/10等の利用可能性、元精度・測量時期・測地成果の世代で明示選択。
2. 公式基盤地図情報サービスでZIP/GMLを**当面手動取得**し、元配布単位・ファイル名・取得時刻・SHA-256を記録。
3. JPGIS/GMLの格子定義、原点、間隔、標高値、NoDataを解析しWork GeoTIFFへ変換。単純なXYZ点群として誤解釈しない。
4. 元CRS/鉛直基準を検証し、Native Terrainへ。必要時に正式な座標・鉛直変換を経て共通格子へ変換。
5. QA：ZIP完全性、被覆率、格子原点・解像度、NoData、異常標高、境界、鉛直整合。5m→1mの再標本化は実効精度向上を意味しない。

**実装前の確認**：GMLパーサ仕様版、測地成果の扱い、複数DEMの接合と優先規則、既存Terrain manifestとのリンク。

### B-01 — PLATEAU CityGML → Native Building

1. 都市・年度・CityGML配布版・LoDを選び、配布ZIPとハッシュを登録。
2. PLATEAU GIS Converterの版・設定・入力座標参照を固定してWork GeoPackage生成。
3. 既存Building IngestでNative Buildingを作成し、既存Standardizerへ接続。
4. QA：ID、建物数、LoD、形状、水平CRS、元Z・変換後Z・Standard Zの同一建物トレース。

**Blocking unresolved**：狛江市で指摘されたCityGML→Converterの約37mのZ不整合疑義。CRSラベル付け替えで解決したとみなさない。既存受入を自動的に取り消すものでもない。

### B-02 — GSI建築物外周線 → 簡略Building

1. 配布GMLから外周線を読み込み、閉合・結合・位相検査を経てポリゴン候補生成。
2. LiDARと適合DEMがある場合は屋根点・地盤点を分離して高さ推定（BLD-2）。
3. LiDARがない場合は根拠ある推定モデルを明示し、Estimated属性付きの暫定建物（BLD-3）。
4. QA：閉合率、自己交差、建物対応、壁面/屋根縁の違い、地盤・屋根の上下関係、推定根拠。

**未決**：線のポリゴン化アルゴリズム、屋根抽出、推定モデルと許容用途。

### C-01 — Meta/WRI CHMv2 → Native Canopy候補

1. 公式公開索引・配布仕様からAOI+Bufferと交差するタイルを特定。**S3 prefixの存在だけでタイル索引・ライセンスを検証済みとしない**。
2. 元CHMタイルを取得・ハッシュ登録。モデル版、データ版、撮影/推定時期、CRS、元解像度、NoDataを記録。
3. モザイク・切出し、異常値とNoData診断。CHMから**樹冠候補**ポリゴンを抽出し、独立した樹冠存在判定・誤検出診断を行う。
4. 適合DEMから`Z_top = Z_ground + H_CHM`を生成。下端ZはCR等の推定法・適用範囲・地盤との関係を明記。
5. QA：モデル推定値とLiDAR直接観測の区別、樹冠以外の混入、元格子・時期差、地盤Z整合、NoData、上下端と地盤の関係。

**未決**：樹冠閾値・連結領域、タイル索引の実装、モデル推定誤差、Standard Canopyの符号化・受入条件。CHM有効値だけで樹冠や樹種を確定しない。

### L-01 — LiDAR → HAG → CHM（共通Work）

1. LAS/LAZのファイル、点密度、分類、水平CRS、鉛直基準、測量時期、AOI+BufferをPreflight。
2. 適合DEM/DTMまたは検査済み地盤点から地盤基準を作り、`HAG = point_Z - ground_Z`を計算。
3. 非樹木点・外れ値・地盤点・補間セル・時期差を検査。**ポリゴンマスク前**のCHM・点数・NoData診断ラスタを作成。
4. 初期比較：1m/2m、最大HAG/P95/P99。これらはPoC候補であり全国固定の閾値ではない。
5. QA：分類、建物・電線混入、タイル境界、点密度、空隙、鉛直整合。未観測セルを無条件に高さ0へ変換しない。

### C-02 — 自治体樹林ポリゴン + L-01 CHM

1. 樹林区域・樹冠外縁などの元データの意味、作成時期、形状を確認。
2. CHMと独立にポリゴンの位置・被覆・街路樹欠落・道路建物混入を評価。
3. ポリゴンマスクとCHMを統合し、絶対Z・下端Z推定・来歴・QAを付与。

**未決**：樹林区域と樹冠の差の補正、自治体間の仕様差。

### C-03 — GSI航空写真 + OAM-TCD + L-01 CHM

1. 空中写真の撮影年、元解像度、ライセンス、タイル出典を確認。
2. モデル重みの利用条件・版を検証し、GSI画像のスケールに適合させて推論。
3. 推論マスクをポリゴン化し、独立QAの後L-01 CHMと統合。
4. QA：画像/点群時期差、位置ずれ、分類精度、樹冠の過不足、非樹木混入。

**Blocking unresolved**：商用利用可能な重みと日本向け性能の検証。既存PoCは全国性能の証明ではない。

## 6. 3次メッシュ、格子、欠損

- Rawは配布単位。Standardは原則3次メッシュ×レイヤーで保存・更新。建物/樹冠の原形状は境界で分割しない。
- 各地物に重複しない所有メッシュを与え、交差するメッシュは空間索引で検索する。派生物は原形状IDへ追跡可能とする。
- `analysis_aoi`、`processing_extent`、`storage_mesh`、`output_extent`を区別。狛江市EPSG:6677は全国固定ではない。
- `observed non-canopy`、`no observation`、`invalid`、`estimated`、`outside AOI`を区別。正式な符号化・受入条件はStandard Canopy契約で別途定義。

## 7. 実装順序・受入境界

1. **P0設計・証拠確認**：CatalogとRecipeのID/Schema、公式取得経路・利用条件・鉛直基準を確定。PR #61のマージ・独立監査状態を確認。
2. **P1 T-01**：GSI DEMのRaw登録、GML変換、Native QA、既存Terrain契約への非破壊接続。
3. **P2 B-01**：PLATEAUのRaw→Converter→Nativeの再現性・Z診断。
4. **P3 C-01**：CHMv2のタイル取得・モデル来歴・樹冠候補・QA。Standard Canopy契約を別途策定。
5. **P4 B-02/L-01/C-02/C-03**：GSI建物外周線、LiDAR、自治体樹冠、OAM-TCDを段階導入。

初期実装地域は狛江市を既存比較基準とし、PLATEAU未整備等のフォールバックを別地域で検証する。**この文書のレビューやマージは、実データ取得、ライセンス・鉛直基準の検証、Standard改訂、実装・QA受入を意味しない。**

## 8. 独立監査で確認する事項

1. Concept v0.2、PR #61の修正設計、既存Standard/Adapter/狛江市受入との整合。
2. Source CatalogとRecipeの責任境界、Source Selectionの実行前保存、Dataset/Runの多対多関係。
3. ソースURLと個別ファイルの検証状態、ライセンス・測地成果・鉛直基準の未決事項。
4. C-01の推定CHM、L-01の点群QA、欠損・非樹冠・推定値の意味。
5. 3次メッシュ所有と原形状保持、QA状態と処理状態の分離。
6. P1着手前に必須の決定と、実データ検証まで保留できる事項。

**状態確認：設計ドラフト。取得・実行・独立監査・受入は未実施。**
