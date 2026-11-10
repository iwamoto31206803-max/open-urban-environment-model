# OUEM／VoxCityGML — 5モジュール責任分界とPoC-P1技術クロージング（レビュー草案）

- **確認日・基準**：2026-11-10、main `b9cbbe9addf6353935295f807c0083f66e19d0a7`（PR #175マージ後）。
- **状態**：文書統合のための**レビュー草案**。新しい正式設計、Standard、Adapter、Acceptanceの承認ではない。GitHub上のコード・文書・実験証拠と、別途保全された2026-11-06/07の設計草案を照合した。ローカル実データ・環境の再実行、科学的妥当性の新規検証、ライセンスの法的最終審査は行っていない。
- **数値・実行証拠の所有元**：[P1-0](../experiments/voxcitygml_p1/P1-0_REPORT.md)、[P1-1a](../experiments/voxcitygml_p1/p1-1a/P1-1a_REPORT.md)、[P1-1b](../experiments/voxcitygml_p1/p1-1b/P1-1b_REPORT.md)、[P1-1c](../experiments/voxcitygml_p1/p1-1c/P1-1c_REPORT.md)、[P1-2a仕様](../experiments/voxcitygml_p1/p1-2a/P1-2a_EXPERIMENT_SPEC_DRAFT.md)、[P1-2b結果](../experiments/voxcitygml_p1/p1-2b/P1-2b_REPORT.md)。歴史的記録の判定・数値をこの文書で上書きしない。

## 1. 設計レビューの出発点と変えない原則

OUEMの目的は3D樹冠・建物の生成自体ではなく、地形・建物・樹冠を統合し、都市に暮らす人が体感する樹木の環境機能を面的に評価することにある。出口はB1（Current／No-Canopyの日射・日陰）とB2（360°樹冠緑視）を中心とし、GISで扱える地図成果と科学的な解釈を重視する。

[Concept & Architecture v0.2](../OUEM_Concept_Architecture_v0.2.md)は正式登録の上位概念設計、[v0.1](../OUEM_Concept_Architecture_v0.1.md)は継承されたB1/B2の詳細、[Development Principles](../OUEM_Development_Principles_v0.1.md)は採用済みの開発原則である。今回の発見は目的変更ではなく、**OUEMが日本の多様なオープンデータの意味・品質・出典を保ち、解析エンジンへ接続することへ開発資源を集中する**という責任分界の具体化である。OSSが提供する汎用ジオメトリ・voxel・ray計算カーネルを、必要性の証拠なしに再実装しない。

基本境界は **Raw → Native → OUEM Standard → Engine／Analysis Adapter**。StandardはVoxCity専用形式にせず、詳細3D建物形状を**Primary**、高さラスタ・2.5Dを情報損失のある**Derived**として保持する。VoxCityGML発見前から、これらはv0.2の原則である。

## 2. 5モジュール横断機能とOUEM／OSSの役割

以下は2026-11-06の横断機能台帳（T01–T08、C01–C10、B01–B10、V01–V10、E01–E10）と11-07の第2次設計レビューの論点を**機能単位**に縮約したもの。**コードやリポジトリを必ず5分割する決定ではない**。OSSの実装存在、固定環境での検証、OUEMへの正式採用は別判定とする。

| 機能モジュール | OUEMが保持する責任 | 既存OSSの再利用・検証境界 |
|---|---|---|
| **① 地形データの前処理** | DEM/DTM、取得と鉛直根拠、NoData、時点・出典、建物・樹冠との高さ整合 | VoxCityの地盤/voxel処理を再利用。VoxCityGMLのCityGML TIN地形経路は候補だが**P1では未検証**。元建物Zを暗黙にDEMへ再アンカーしない |
| **② 樹木データの前処理** | 2D樹冠の存在・調査範囲、CHM/HAG、樹冠上端/下端絶対Z、推定Crown Ratio・不確実性、欠測と不存在の区別 | VoxCityの上端/下端TREE表現を利用。VoxCityGMLの3D植生・樹冠再適用は**完全なNo-Canopyが成立するか未検証**。セグメンテーションは上流の別リポジトリ |
| **③ 建物データの前処理** | PLATEAU／将来GSIの取得・Native/Standard、LoD・形状・ID・絶対Z・時点、3D Primaryと2.5D Derived | 既存VoxCity 2.5Dを維持。VoxCityGMLの詳細LoD2形状・merge-only mesh経路は**F/S/M/Cの4棟で限定実証**。GSI→OBJは将来候補 |
| **④ 地形・樹木・建物の統合とボクセル化** | 同一格子・D0・XY/Z・クラス・ID、干渉・優先順位、Current/No-Canopyの一致、モデル品質・再現性・資源QA | 汎用voxel/mesh処理をVoxCity/VoxCityGMLから再利用。P1の低位/private 3D voxel経路は成功したが、contact shell・格子位相・解像度に感度あり |
| **⑤ 日陰・緑陰等の都市環境解析** | B1/B2指標・比較条件、観測点、独立検証、科学的意味、GIS出力、自治体利用条件 | VoxCityのSolar/Shadow/Viewなど既存計算核を利用。P1-2bは**建物だけの二値日陰**であり、樹冠付きB1/B2の受入を意味しない |

**再利用と責任の要点**：

- **VoxCityGML**：CityGML詳細LoD2のメッシュ化・必要な補修・3D voxel化の**候補**。P1は特定の低位/private APIを固定して実行し、汎用高位pipeline・地形TIN・3D植生・橋梁を正式検証したわけではない。
- **VoxCity**：既存の2.5D Building Adapterとvoxel処理、B1/B2計算核、P1で同一条件比較に使った `trace_ray_generic` 等を提供する。ソース選定、物理的な高さの正しさ、指標の科学的妥当性を保証するものではない。
- **OUEM**：日本のデータの選定・意味・ID、Raw/Native/Standard整合、原絶対Hとエンジン相対Hの区別、時点・権利・品質・欠損、比較シナリオの同一条件、独立QA、成果物の説明責任を保持する。

## 3. 詳細3D経路とStandardの責任分界

```text
               Raw → Native → OUEM Standard
                  （形状・ID・CRS・絶対Z・QA）
                               │
                  Engine／Analysis Adapter
                   （正式な経路選択は未決）
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       詳細LoD2の3D経路                  既存2.5D経路
       VoxCityGML利用候補               VoxCity利用
       Standard形状起点または           外周線・高さDerived
       Standard照合済みRaw参照          （従来の限定Adapter）
               └───────────────┬───────────────┘
                               ▼
                共通条件の3Dモデル・解析
                          B1／B2
```

上図の詳細3D側は**Standardを迂回する許可ではない**。監査済みRawを参照する案でも、Standardとの形状・ID・LoD・Z対応を検証するAdapterが必要である。両経路の接続方法は今後の設計判断に属する。

P1では、元CityGML member、`source_id`／`ouem_id`、LoD2 polygon/ring、Native/Standard形状、元の絶対HをSHAと対応で監査したうえで、原データ参照の限定技術経路を使った。しかし、**原CityGMLからvoxelを作れたことと、正式なStandard準拠Adapterが完成したことは異なる**。

正式経路は次の二案から未選択である。

1. **Standard形状起点**：監査済みStandardの完全3D形状からエンジン用mesh等を作成する。
2. **監査済みRaw参照起点**：原CityGMLをStandardのSHA／ID／LoD／幾何／変換履歴・絶対Zに結び付け、Adapter経由で直接参照する。

どちらも未監査RawによるStandard QA迂回、根拠のないDEM再アンカー、north-up/south-upやD0の暗黙変更、欠測を不存在に変える処理を許容しない。既存[Building Standard](../OUEM_Standard_Building_v0.1.md)／[Terrain Standard](../OUEM_Standard_Terrain_v0.1.md)はPROVISIONAL、[Canopy Standard](../OUEM_Standard_Canopy_v0.1_Draft.md)はDRAFT、[正式VoxCity Adapter](../OUEM_VoxCity_Adapter_v0.1.md)は従来の限定2.5D経路として変更しない。

## 4. 当初PoC-P1仕様と実施結果の照合

2026-11-07の**正式設計としては未登録の独立PoC仕様草案**から、実際の実験では個別の条件確認・承認を経て工程名と番号が組み替わった。草案の正式登録状態と、後続PoC各段階の実施承認は別の判断である。実験記録を書き換えて番号を一致させない。

| 当初DRAFTのゲート | 実際の記録 | 到達状態 |
|---|---|---|
| P1-0：入力・環境・権利 | PR #170、独立環境構築 #171 | 選定ソース・実行APIは限定PASS。配布・商用に係るライセンス最終確認はCONDITIONAL |
| P1-1a：合成形状による較正 | #171–173の合成テスト、#173の独立solid-angle内外判定 | **部分充足**。当初の全較正ゲートを一括して完了したとは扱わない |
| P1-1b：Fの最小実験 | 実施名は **P1-1a／#171** | FのLoD2対応、水密merge、mesh-only voxel実証 |
| P1-2：S/M/C拡大・同条件A/B/C影比較 | #172–173形状/voxel、#174仕様、**#175実行** | 4棟の共通観測点・既存ray核の比較はPASS。**元LoD2三角形による独立ray–triangle shadow照合は未実施** |
| P1-3：再現性・運用評価 | 各PRの2run、#175の101出力SHA比較、#173の時間記録 | 限定再現性PASS。ピークメモリや最終権利条件は未確認 |

当初の「P1-3」は再現性・運用評価を指すため、本クロージングに**P1-3という新しい工程番号を付けない**。

[PR #175の結果](../experiments/voxcitygml_p1/p1-2b/P1-2b_REPORT.md)ではF/S/M/CすべてGate 1〜5 PASS。保存観測点5,088点に対するA/B計10,176判定の不一致0、Cによる観測点追加除外0、独立2runの101成果物のSHA一致を記録した。A＝代表上端2.5D、B＝セル別上端2.5D、C＝元LoD2 solid由来voxelで、**Cを真値としない**。FのB/C日陰差14セルにはvoxel上面の1m差が関係するが、実影精度の証明ではない。詳細数値・図・manifestは元レポートを参照し、ここで表を複製しない。

独立P1環境はPython 3.11.9／VoxCityGML 0.3.0（commit `19628c033b1cbbbdee80fe781f516672765d1eee`）／VoxCity 1.7.0（commit `fa212656305328a9a657973bae26f352bfe813bc`）。`_voxelize_building_solid`などprivate API依存は将来の保守リスク。元の大容量データ、NPY、仮想環境、cacheはGitに含まれず、Git cloneだけでは再実行できない。

## 5. 設計判断の残し方と未決事項

2026-11-07第2次レビューのD-01〜D-16を、P1の新事実に照らすと以下の整理になる。

- **既存の正式原則を維持（D-01〜03）**：OUEMの目的、Raw/Native/Standard/Adapter、詳細3D Primaryと2.5D Derived。
- **技術候補として継続（D-04〜05）**：VoxCityGML詳細3Dの限定成功を認め、既存2.5Dも軽量用途・比較対照として保持。**正式Adapter採用（D-11）ではない**。
- **後続の研究・データ調達候補（D-06〜08）**：GSI点群を用いた独自の詳細形状処理・OBJ等の本格実装は後段で検討する一方、RGB＋LiDARのlate fusionは樹冠情報を補完する**研究上の有力候補**として保持する。どちらもP1では検証しておらず、実装着手・正式採用を決定したものではない。
- **環境評価・広域の設計課題（D-09〜10）**：CityGML植生を含む全起源のNo-Canopy、3次メッシュ管理と解析タイル／halo／crop／mosaicの区別。
- **変更の承認が必要（D-11〜13）**：VoxCityGML正式採用、Standard schema・ロードマップ改定、Standard形状起点かRaw参照起点かの選択。P1結果だけで決めない。
- **横断QAの継続候補（D-14〜16）**：画像・点群／教師データ／学習済み重み／モデル実装／OSS／依存／成果物の権利区分、RGB・LiDAR・建物・DEMの観測時点差と時点不明、LandUse・水域・樹冠除去後の基底地表。いずれも実データ・用途に即した別判断が必要。

## 6. 保留する検証と樹冠統合への引き継ぎ

| 着手条件 | 未解決事項 |
|---|---|
| **正式な詳細3D Adapter採用前** | Standard形状起点／監査済みRaw参照起点の選択、ID/LoD/Z/幾何の固定、public/private APIと依存・権利の保守条件、地形・建物の鉛直整合 |
| **元LoD2に基づく独立の影精度を主張する前** | 元三角形と光線の独立交差照合、物理観測高、contact-shell・voxel離散化／格子位相と影の関係。P1-1cのsolid-angle **内外判定はshadow oracleではない** |
| **適用できる形状種・規模を広げる前** | 実際に穴のある建物、複雑な非merge修復、LoD混在、周辺障害物・halo、他解像度／太陽条件、ピークメモリと総運用コスト |
| **P1詳細3Dへ樹冠を統合する前** | 同一voxel格子・D0・地形・BUILDING/TREE・観測点XYZ、Current／No-Canopy全樹冠起源の制御。CityGML植生があればCHM由来TREEだけの除去では不十分。B1の光学・B2指標の意味は別途検証 |

**クロージング判定**：4棟限定の**technical executionはPASS**、当初独立仕様の**全面充足は主張しない**。`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`、`terrain_integration_ready=false`を維持する。詳細LoD2正式採用は別の設計判断だが、既存Height Envelope／TREE／B1/B2技術E2Eを使った次のCanopy検討を一律に止めない。

## 7. 原草案の来歴・GitHub反映方針

この文書は、下記の**正式設計としては未登録の歴史的DRAFT**を全文コピーせず、議論の重要な責任分界とPoC結果の対応を縮約して記録したもの。後続のPoC-P1は個別の条件確認・承認に基づいて実施されており、草案が未登録であることを実験の未承認と混同しない。SHAは原本との対応を示すが、原本がGit clone内で入手できることは意味しない。原本に記載された2026-11-06/07の実装状態・OSS機能一覧は**当時の調査スナップショット**であり、現在の正式仕様として採用しない。

| 原本（Git管理外） | SHA-256 |
|---|---|
| `OUEM_Function_Inventory_v0.1_DRAFT_20261106.md` | `93ec65f347ab898237c4dec3aacadd249ce9c8b572dd26616b46ad1b5d186421` |
| `OUEM_Architecture_Review_and_Design_Change_DRAFT_20261107.md` | `00431bb628f76c1272bd4651678de6c970bd0a8ba7b20983d22e38adb4b42321` |
| `OUEM_Architecture_Review_and_Design_Change_DRAFT_v0.2_20261107.md` | `ebb2df9deabe4d9f8cd6782b5c7da454b52c9b9fc64f3613da3547595da98502` |
| `OUEM_PoC_P1_Specification_DRAFT_v0.1_20261107.md` | `ccaa164c975ce6e03a4e32167ac71b858c7f2af6a0d86bad2d42c1f94336777e` |

本レビュー文書が設計経緯・P1対応関係の**単一の参照先**を担い、個別の実測値は保存P1レポート、現行案内は[README](../../README.md)と[Building Current State](../status/BUILDING_CURRENT_STATE.md)が担当する。正式Concept／Standards／VoxCity Adapter／Acceptance／旧実験記録・manifest・コードを変更しない。クロージング文書へのリンク追加をもって、正式Adapter採用や権利・科学的検証が完了したことにはしない。

**Documentation Impact**：新規レビュー文書1本と案内2か所のみ。コード・入出力・科学的条件に変更がないため、新規pytestや実データ再実行は行わない。相対リンク・変更ファイル・既存契約の不変性を確認してレビューに供する。
