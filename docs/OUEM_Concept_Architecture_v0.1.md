# Open Urban Environment Model（OUEM）

## Concept & Architecture v0.1

**日本語名:** オープン都市環境モデル\
**Version:** v0.1\
**Status:** Concept / Architecture Baseline\
**作成日:** 2026-09-28

------------------------------------------------------------------------

## 1. 目的

Open Urban Environment
Model（OUEM）は、オープンな地理空間データ等から地形・建物・樹冠を統合した3D都市環境モデルを構築し、都市に暮らす人が体感する樹木の環境機能を面的に評価するためのモデル／ワークフローである。

OUEM
v0.1では、樹木の機能のうち特に人が体感しやすく、都市計画・緑地計画等への応用が想定しやすい次の2領域をPhase
Bの対象とする。

-   **B1：日射・日陰評価** --- 「樹木がどれだけ日差しを遮るか」
-   **B2：緑視評価** --- 「人からどれだけ樹冠が見えるか」

OUEMは「3D樹冠を作ること」自体を最終目的としない。2D樹冠情報やLiDAR等を3D都市環境モデルへ変換し、その3D構造から人間スケールの環境機能を評価する。

------------------------------------------------------------------------

## 2. 基本アーキテクチャ

``` text
Open / Available Geospatial Data
            │
            ▼
Phase A — 3D Urban Environment Model Construction
3D都市環境モデル構築
            │
            ▼
Terrain + Buildings + Canopy
3D Urban Environment Model
            │
      ┌─────┴─────┐
      ▼           ▼
     B1           B2
Solar & Shade   Green View
日射・日陰評価   緑視評価
      │           │
      ▼           ▼
日陰マップ      緑視率マップ
```

Phase AとPhase Bは疎結合とする。Phase
Aは都市を解析可能な3D空間として構築し、Phase
Bはその共通3Dモデルから環境機能を算定する。

------------------------------------------------------------------------

## 3. Phase A --- 3D Urban Environment Model Construction

### 3D都市環境モデル構築

Phase Aでは、DEM、建物、樹冠等を統合し、VoxCityを中心としたsemantic 3D
voxel cityを構築する。

### A1 --- Tokyo Reference / 東京リファレンス

高品質な東京都・自治体データを利用する最初のReference Model。

-   樹冠XY / CHM：自治体提供樹冠データ、東京都LP点群等
-   樹冠上端：LP点群等
-   樹冠下端：Crown Ratio等による推定
-   DEM：東京都等の公開DEM / LP点群由来地形
-   建物：東京都の公開3D建物モデル等
-   建物高さ：公開3DモデルまたはLP点群等

A1はGround
Truthではなく**Reference**である。最初の実装対象とし、実業務での有用性確認とA2/A3の評価基準に利用する。

### A2 --- National Baseline / 全国ベースライン

現在利用可能な全国規模データによる、比較的容易に展開できるBaseline。

-   樹冠 / CHM：Meta系1 m CHM
-   樹冠存在判定：CHMを基本とし、最低樹高閾値等をA1との比較で検証
-   樹冠下端：Crown Ratio等
-   DEM：国土地理院DEM
-   建物：高さ付き利用現況調査等を優先。必要に応じOSM等を検討。高さ情報が信頼できない場合は無理に推定しない選択肢も持つ。

目的は最高精度ではなく、**現在のデータ環境で全国展開可能なBaseline**を確立すること。

### A3 --- GSI-LiDAR National Target / 国土地理院LiDAR全国ターゲット

GSI
LiDAR、GSI建物外周線、商用利用可能な樹冠抽出モデル等を組み合わせ、ライセンス・時期整合・全国展開性を改善する将来Target。

``` text
                    GSI LiDAR
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
         RGB            Z           DTM
          │             │            │
     CC BY対応          │            └── DEM
     OAM-TCD等           │
          ▼             │
      Tree Mask ────────┤
                        ▼
                    3D Canopy

GSI建物外周線 ─────── × LiDAR Z
                        ▼
                   3D Building
```

狙いは、樹冠・建物・地形の高さ情報を同一LiDAR観測へ近づけること、時期不整合の低減、商用利用可能なデータ・コード体系、全国展開可能な入力パイプラインである。A3は完成形と決め打ちせず**National
Target**とする。

------------------------------------------------------------------------

## 4. VoxCityの役割

VoxCityは入力データの真偽を推論するデータ融合AIではなく、整理済みの地形・建物・canopy
top/bottom等を受け取り、解析可能なsemantic 3D
cityへ変換する基盤と位置づける。

``` text
【OUEM Input Preparation Layer】
DEM / Building / Canopy / Land cover
        │
        ▼
【VoxCity】
Semantic voxelization
        │
        ▼
3D Urban Environment Model
        │
        ▼
【OUEM Phase B】
Environmental Assessment
```

観測時期、精度、ライセンス、入力間競合等はOUEM側で管理する。

------------------------------------------------------------------------

## 5. Phase B --- Urban Environmental Assessment

### 都市環境評価

v0.1ではB1とB2に限定する。SVF、MRT、風環境、熱収支、生態系サービス等は、具体的な業務上の必要性が生じた場合に将来モジュールとして検討する。

------------------------------------------------------------------------

## 6. B1 --- Solar & Shade Assessment

### 日射・日陰評価

### 6.1 目的

現況（Current）と樹冠のみを除去した反実仮想（No-Canopy
Counterfactual）を同一条件で比較し、既存樹冠による日陰形成・日射低減効果を面的に定量化する。一般向けには**「日陰マップ」**として説明する。

### 6.2 基本計算

3D都市形状、太陽位置、EPW等の日射・気象情報、直達・散乱日射、樹冠透過、評価点高さを組み合わせる。

樹冠透過の概念式：

\[ T = `\exp`{=tex}(-k `\cdot `{=tex}LAD `\cdot `{=tex}L) \]

-   T：樹冠透過率
-   k：extinction coefficient（消散係数）
-   LAD：Leaf Area Density
-   L：樹冠内部の光路長

LAD・kは既往文献・社内知見を踏まえて設定し、必要に応じ感度分析を行う。

### 6.3 Current / No-Canopy

``` text
Current Scenario             No-Canopy Counterfactual
Terrain : same               Terrain : same
Building: same               Building: same
Surface : same               Surface : same
Weather : same               Weather : same
Time    : same               Time    : same
Canopy  : present            Canopy  : removed
```

地表土地被覆は原則として変更しない。

### 6.4 Output Tiers

**Tier 1 --- Primary Outputs / 主要成果指標**

1.  **Current Solar Exposure / 現況日射曝露量**
2.  **Tree-induced Solar Reduction / 樹冠による日射低減量**
3.  **Tree-induced Shade Duration / 樹冠による日陰形成時間**

\[ `\Delta `{=tex}Q\_{tree} = Q\_{no-canopy} - Q\_{current} \]

**Tier 2 --- Analytical Outputs / 分析用成果指標**

-   No-Canopy Solar Exposure / 樹冠なし想定日射曝露量
-   Tree Solar Reduction Rate / 樹冠による日射低減率
-   Current Sunlight / Shade Duration / 現況日照・日陰時間
-   No-Canopy Sunlight / Shade Duration / 樹冠なし想定日照・日陰時間

**Tier 3 --- Diagnostic Outputs / 検証・診断用成果指標**

-   Direct Solar Irradiance / 直達日射量
-   Diffuse Solar Irradiance / 散乱日射量
-   Canopy Transmittance / 樹冠日射透過率
-   Time-specific Solar / Shade / 時刻別日射・日陰
-   Solar Geometry / Model Parameters /
    太陽位置・日射幾何条件／モデルパラメータ

### 6.5 評価期間

指標と評価期間を分離して管理する。例：夏季昼間（7--9月、10--16時）、EPW代表気象、評価高さ1.5
m。

### 6.6 タイル処理

市町村全域は**Tile + Buffer + Crop + Mosaic**を基本とする。Output
Tile周囲まで3D化・計算し、中央のみ保存して次Tileへ進む。Buffer幅は理論値だけで固定せず、小範囲一括計算との収束試験で決める。

重い3D voxelは中間生成物とし、主要成果はGeoTIFF等の2D GIS
rasterとして保存する。

------------------------------------------------------------------------

## 7. B2 --- Green View Assessment

### 緑視評価

### 7.1 目的と正式指標

Phase
Aで構築した3D樹冠について、歩行者視点からどの程度視覚的に認識できるかを面的に評価する。

正式な主要指標：

**360° Green View Index (Canopy) / 360°緑視率（樹冠）**

普段の会話・説明では単に**「緑視率」／「緑視率マップ」**と呼ぶ。

### 7.2 「緑視率（樹冠）」とする理由

日本の一般的な緑視率では樹木に加えて草地、芝生、壁面緑化等を含み得る。一方OUEM
B2ではPhase Aの**3D樹冠**を対象とし、草地・農地等は原則Green
Viewに含めない。この対象範囲の違いを正式名称で明示する。

### 7.3 基本算定

1.  地表から歩行者高さ（例：1.5 m）に観測点を置く
2.  周囲の多数方向へrayを飛ばす
3.  各rayが3D樹冠を視認するか判定
4.  評価方向全体に占める樹冠可視割合を算定

概念式：

\[ GVI\_{canopy} = `\frac{N_{canopy\ rays}}{N_{evaluated\ rays}}`{=tex}
\]

写真ベース緑視率とは計測方法が異なるが、「視線のうちどの程度が緑を捉えるか」という基本思想は共通する。

### 7.4 360°評価

正式指標は特定方向の写真ではなく、観測地点の**周囲360°**を対象とする。道路方向の任意性を避け、交差点、公園、広場等でも同一ルールで面的評価できるためである。上下方向の視野角・ray
sampling等はモデルパラメータとして明示する。

### 7.5 Output Tiers

**Tier 1 --- Primary Output / 主要成果指標**

-   **360° Green View Index (Canopy) / 360°緑視率（樹冠）**

**Tier 2 --- Analytical Outputs / 分析用成果指標**

-   Directional Green View Index (Canopy) / 方向別緑視率（樹冠）
-   View-direction / Elevation Components / 方位・仰角別樹冠可視割合

**Tier 3 --- Diagnostic / Validation Outputs / 検証・診断用成果指標**

-   Virtual-camera GVI (Canopy) / 仮想カメラ緑視率（樹冠）
-   Canopy Visibility / Ray Classification / 樹冠可視判定／視線分類
-   View Geometry / Model Parameters / 視点・視野角・Ray
    Sampling・LAD等のモデルパラメータ

### 7.6 日本の写真式緑視率との関係

大阪府の緑視率調査や国総研のAI緑視率等の写真ベース手法を置き換えるものではなく、**3Dモデルから市域全体へ面的に推定する補完的手法**と位置づける。

検証時には、同一地点の実写真による樹冠相当緑視率とOUEM Virtual
Cameraを比較し、検証後に360°緑視率（樹冠）を市域へ展開する。

------------------------------------------------------------------------

## 8. OUEM v0.1 全体ツリー

``` text
Open Urban Environment Model（OUEM）
オープン都市環境モデル
│
├── Phase A — 3D Urban Environment Model Construction
│   3D都市環境モデル構築
│   ├── A1 — Tokyo Reference / 東京リファレンス
│   ├── A2 — National Baseline / 全国ベースライン
│   └── A3 — GSI-LiDAR National Target / 国土地理院LiDAR全国ターゲット
│
└── Phase B — Urban Environmental Assessment
    都市環境評価
    │
    ├── B1 — Solar & Shade Assessment / 日射・日陰評価
    │   ├── Tier 1 — Primary Outputs / 主要成果指標
    │   │   ├── Current Solar Exposure / 現況日射曝露量
    │   │   ├── Tree-induced Solar Reduction / 樹冠による日射低減量
    │   │   └── Tree-induced Shade Duration / 樹冠による日陰形成時間
    │   ├── Tier 2 — Analytical Outputs / 分析用成果指標
    │   │   ├── No-Canopy Solar Exposure / 樹冠なし想定日射曝露量
    │   │   ├── Tree Solar Reduction Rate / 樹冠による日射低減率
    │   │   ├── Current Sunlight / Shade Duration / 現況日照・日陰時間
    │   │   └── No-Canopy Sunlight / Shade Duration / 樹冠なし想定日照・日陰時間
    │   └── Tier 3 — Diagnostic Outputs / 検証・診断用成果指標
    │       ├── Direct Solar Irradiance / 直達日射量
    │       ├── Diffuse Solar Irradiance / 散乱日射量
    │       ├── Canopy Transmittance / 樹冠日射透過率
    │       ├── Time-specific Solar / Shade / 時刻別日射・日陰
    │       └── Solar Geometry / Model Parameters / 太陽位置・日射幾何条件／モデルパラメータ
    │
    └── B2 — Green View Assessment / 緑視評価
        ├── Tier 1 — Primary Output / 主要成果指標
        │   └── 360° Green View Index (Canopy) / 360°緑視率（樹冠）
        ├── Tier 2 — Analytical Outputs / 分析用成果指標
        │   ├── Directional Green View Index (Canopy) / 方向別緑視率（樹冠）
        │   └── View-direction / Elevation Components / 方位・仰角別樹冠可視割合
        └── Tier 3 — Diagnostic / Validation Outputs / 検証・診断用成果指標
            ├── Virtual-camera GVI (Canopy) / 仮想カメラ緑視率（樹冠）
            ├── Canopy Visibility / Ray Classification / 樹冠可視判定／視線分類
            └── View Geometry / Model Parameters / 視点・視野角・Ray Sampling・LAD等
```

------------------------------------------------------------------------

## 9. 認識済みの主要Engineering / Validation Issues

### Phase A

-   VoxCity入力adapter設計
-   樹冠下端（Crown Ratio等）
-   LiDAR / CHM / 樹冠ポリゴンの観測時期整合
-   建物と樹冠の競合
-   Meta CHM最低樹高閾値
-   OAM-TCD等の樹冠抽出精度
-   GSI LiDARの点密度・RGB品質・全国整備状況
-   LiDARによる建物高さ付与
-   入力データのライセンス管理

### Phase B1

-   LAD / extinction coefficient
-   Crown Ratio × LAD × k の感度
-   EPW / representative weather
-   評価期間・時間帯・評価高さ
-   Direct / Diffuse
-   Tile buffer幅
-   Current / No-Canopyの再現性
-   CPU / GPU benchmark
-   計算点mask / sampling
-   GIS出力検証

### Phase B2

-   360°評価時の仰角範囲
-   ray sampling密度
-   樹冠透過
-   B1とのLAD等パラメータ整合
-   日本の写真式緑視率との比較
-   Virtual Camera validation
-   「樹冠のみ」を対象とする定義の明示

------------------------------------------------------------------------

## 10. v0.1で採用しないもの

現時点では主要実装対象としない。

-   SVF / 天空可視率
-   MRT等の人体熱収支評価
-   WBGTそのものの推定
-   風環境
-   詳細な都市熱収支
-   CO₂固定
-   雨水流出
-   生態系サービス全般
-   新規植樹最適配置

具体的な業務上の問いが生じた場合にB3以降として検討する。

------------------------------------------------------------------------

## 11. v0.1 実装方針

構想をさらに広げるより、**A1 Tokyo Reference → B1 /
B2を小範囲でend-to-endに通すこと**を優先する。

最初の節目：

1.  A1入力データをVoxCityへ接続
2.  小範囲で3D Urban Environment Modelを生成
3.  3D geometryを目視・定量確認
4.  B1の瞬間Solar / Shadeを算定
5.  Current / No-Canopy比較
6.  B1 Tier 1の2D raster生成
7.  B2 360°緑視率（樹冠）算定
8.  B2 Tier 1の2D raster生成
9.  QGIS等で両成果を確認
10. 計算時間・RAM・GPU必要性等をbenchmark
11. 問題点をOUEM v0.2へ反映

------------------------------------------------------------------------

## 12. OUEM v0.1の短い説明

> **OUEM（Open Urban Environment
> Model）は、オープンな地理空間データ等から地形・建物・樹冠を統合した3D都市環境モデルを構築し、都市に暮らす人が体感する樹木の環境機能を面的に評価するためのモデル／ワークフローである。**

v0.1の主要な出口は、

-   **B1：日陰マップ**
-   **B2：緑視率マップ**

同じ3D都市環境モデルから、

-   **太陽から都市を見る → 日射遮蔽機能**
-   **人から都市を見る → 視覚的な樹冠機能**

を評価する。

------------------------------------------------------------------------

## 13. v0.1 Design Principles

1.  **Reference ≠ Truth** ---
    A1は高品質Referenceであり絶対的な正解ではない。
2.  **3D is an analytical intermediate** --- 重い3D
    voxelは解析中間物とし、利用成果は可能な限り軽量な2D GISへ戻す。
3.  **Phase A and Phase B are loosely coupled** ---
    入力改善と環境評価を独立して発展させる。
4.  **Open / reproducible workflow** ---
    出典、ライセンス、モデルパラメータ、評価条件を明示する。
5.  **Human-scale functions first** ---
    計算可能な指標を無制限に増やさず、日陰・緑視から始める。
6.  **Model pragmatically** ---
    目的・空間スケールに応じた合理的な簡略化を許容する。
7.  **Validate before nationwide scaling** ---
    A1で価値と限界を確認してからA2/A3へ展開する。

------------------------------------------------------------------------

**End of OUEM Concept & Architecture v0.1**
