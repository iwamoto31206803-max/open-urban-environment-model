# 狛江市 Mixed-LOD Building 実装準備 v0.1

状態: **設計提案・読取Preflight**。正式な契約・受入条件ではない。
基準main: `466c6846d8828ea666e4c27f00d2fc47a74c3423`（PR #134 merged）。
調査日: 2026-10-30 JST。既存Reader/Converter/Native/Standard/Consumer/Adapter、
既存設定・Acceptance・Baseline・完了Runは変更しない。新設定も本PRでは登録しない。
本番Mixed-LOD実装、Converter変換、Native/Standard生成、VoxCity voxel化は未実施。

## 1. 結論: 狛江市内のMixed実証AOIは未確定

**今回の4メッシュでは、LoD1-only 515棟はすべて他自治体コードだった。**
Rawの`uro:BuildingIDAttribute/uro:city`とZIP付属codelistを追加確認し、
LoD1-onlyは調布市13208が28棟、世田谷区13112が487棟、狛江市13219は0棟だった。
LoD2 12,332棟はすべて13219。全12,847 IDにcity値があり、値の欠落は0。
配布物が「狛江市2025」であることは、内包する全建物が狛江市所属である証明ではない。
PR #133の515という値は配布物内の件数であり、市内LoD1-onlyの件数ではなかった。

このため、以下の100m候補は**city属性上で複数自治体を含む、市境横断の条件付き候補**であり、「狛江市内」という依頼条件を
満たしたAOIとして採用・設定登録しない。先に地理だけで選んだ候補をcity確認後に保留へ戻した。
行政境界polygonとの独立した位置照合は未実施であり、city値だけで各footprintの全頂点が
市外にあると証明するものでもない。少なくとも本入力から狛江市内のfallbackを確定できない。

設計・合成試験は進められるが、実データ段階へ進む前に次のどちらかをレビューする必要がある。

- **狛江市限定を維持**: 別release/提供物・公式行政境界を別Preflightで確認し、
  市内LoD1-onlyの有無から調べ直す。本PRで追加取得や存在の保証はしない。
- **市境横断を明示的に許可**: 下記の63棟候補を狛江市・世田谷区のMixed実験として別途承認し、
  追加Terrainを用意する。既存狛江市Baselineや受入範囲には追加しない。

Rawのcity値を理由に現行Standardの行filterを黙って増やすものではない。
市内という検証対象の適合確認と、LoD選択・幾何AOI判定は別の責任とする。

### 既存成果との関係

[PR #133 Preflight](OUEM_Komae_Mixed_LOD_Preflight_v0.1.md)の4メッシュと同じRawを再調査した。
[PR #134 PoC](../experiments/real_komae_source_h/FOUR_MESH_REPRESENTATIVE_HEIGHT_POC.md)は
373 LoD2 Standard → 371 grid ownerの探索的成功であり、LoD1 fallbackや科学的妥当性、
Formal Acceptanceを検証した結果ではない。
既存400×300m AOIは全373棟にLoD2があるため、その範囲の変更でMixed成功を装わない。

### 位置分布とTerrain

| Raw member | LoD1-only | Raw city / ZIP付属codelist | LoD1-only footprint外接範囲（6677、m） |
|---|---:|---|---|
| 53393455 | 0 | — | — |
| 53393456 | 0 | — | — |
| 53393465 | 28 | 13208 / 東京都調布市 | [-24558.14,-40297.15,-24468.49,-39718.71] |
| 53393466 | 487 | 13112 / 東京都世田谷区 | [-22551.63,-40406.31,-22242.90,-39720.86] |

4メッシュのユニーク親Building IDは12,847。候補規則でLoD2=12,332、LoD1=515。
Raw LoD2は既存のstrict reader、LoD1はPR #133のcorpus限定読取診断で検査した。
この読取用の面集合をNative/Standardに登録したわけではない。

既存Terrainは`data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif`。
実boundsは[-23600,-40800,-23200,-40500]、EPSG:6677、600×800、0.5m、
480,000/480,000有効。515棟との交差は0。
最も近いLoD1-onlyは`bldg_34d2a239-01fe-438f-94c1-f0a04417fe66`（mesh66）、
選択全形状からTerrain矩形まで840.677502m。
今回候補はすべて既存Terrainとの重なり0で、追加Terrainなしに代表高さは計算できない。
Raw terrain inventoryには旧狛江09LD3451と国立Preflightの別地域tileがあるが、
国立tileをこのAOIへ適用したり、未調査tileの被覆を推定したりしていない。

### 小矩形候補の比較（すべて市内確定条件を満たさず保留）

LoD1-onlyのrepresentative point周辺を25m単位で探索し、辺50/100m、4種類のoffsetで
得た217個のユニークな混在矩形を比較した。全平面に対する最適AOIの証明ではない。
LoDを決めた後の選択**全形状**の2D交差で数え、メッシュ矩形・中心点で件数を代用しない。

| 候補 | 6677 bounds [xmin,ymin,xmax,ymax] | 面積 | LoD1 / LoD2 | 境界棟 | Terrain距離 |
|---|---|---:|---:|---:|---:|
| A: 近接100m | [-22525,-40225,-22425,-40125] | 10,000m² | 4 / 38 | 15 | 728.869m |
| B: 混在均衡100m | **[-22575,-39925,-22475,-39825]** | **10,000m²** | **31 / 32** | **23** | **849.264m** |
| C: 小50m | [-22475,-40200,-22425,-40150] | 2,500m² | 2 / 12 | 11 | 784.618m |

距離は候補**矩形**と既存Terrain矩形の距離であり、最寄りLoD1建物までの840.678mとは別。
AはLoD1の4棟すべてが境界にかかる。Cは14棟中11棟が境界である。
**市境横断が承認された場合に限る**技術上の推奨はB。
全63棟がmesh66で、LoD1-only31棟は13112、LoD2の32棟は13219だった。
LoD1 19棟・LoD2 21棟が完全包含され、境界は各12/11棟。
両LoDが十分な棟数で混在し、31棟を単なる境界sliverだけで検証することを避けられる。
地理的な外接範囲はlongitude/latitude [139.584056174,35.639877696,139.585163169,35.640781346]。
このBBoxが市境のどちら側かを行政境界データで確定したという意味ではない。

### Bの境界・1m採用可能性（幾何診断だけ）

各棟の全Raw選択面をXY投影してAOI交差を確認し、正面積面の派生footprintでも
63 IDの交差が一致した。canonical geometryの修復/clipではない。
矩形完全包含は`rectangle covers bbox(all selected coordinates)`で判定した。
線分で構成される形状と軸平行矩形の包含に対して同値であり、ゼロ面積壁面への
GEOS coversエラーを避ける。凸包/正面積だけへRawを置換したわけではない。

EPSG:6677の1m正方形、原点=(xmin,ymin)、各footprintのcell交差面積>0.3m²で
**個別の幾何支持**を測定した。LoD1は30/31、LoD2は32/32、計62/63棟に支持セルがある。
支持なしは境界のLoD1 `bldg_eeed3575-1ab7-487f-bccb-56714e1daf78`で、
AOI内footprint面積0.0691735m²。31棟すべてが1m格子に残るとは仮定しない。
複数棟が支持されるセルは1個、最大2棟であり、owner競合の検証ケースにも使える。

これはVoxCityの地理uv格子・優先順位によるrasterizeではなく、投影格子の事前診断。
同じ0.3という閾値でも実engine格子では結果が変わり得る。
DEM/G_eff/height/voxelは計算していない。62棟がVoxCity ownerになると確定した値ではない。


## 2. 選択仕様案（未実装）

仮profile名: `ouem-native-building/plateau-mixed-lod-source-h/v0.1`。
名前・manifest schemaは次の仕様PRでレビューし、旧Source-H profileのaliasにはしない。
source release + 入力member集合内の親`bldg:Building/@gml:id`を選択単位にする。
BuildingPart・複合entityは最小profileでは非対応として明示エラーとする。

| Raw状態 | 提案する結果 / reason |
|---|---|
| LoD2が存在し有効（LoD1有無に無関係） | 2 / `LOD2_PRESENT_VALID` |
| LoD2 branchが**存在しない**、LoD1が有効 | 1 / `LOD2_ABSENT_USE_LOD1` |
| LoD2が存在するがempty / 不正 / 未対応表現 | **Runを停止** / `LOD2_INVALID`。LoD1に落とさない |
| LoD2なし、LoD1が存在するが不正 | **Runを停止** / `LOD1_INVALID` |
| 両方なし | 出力から除外、`NO_SUPPORTED_LOD1_OR_LOD2`をID付きで記録 |
| 同一Building IDが複数member/同一XMLで重複 | **Runを停止** / `DUPLICATE_BUILDING_ID`。同形状でもdeduplicateしない |

LoD2の存在判定はConverter出力や「有効なfacesが得られたか」から逆算せず、Raw branchの
存在を先に分類する。空のLoD2、壊れたxref、非対応Solid-only等をABSENTへ読み替えない。
最小案はfail-closedであり、隔離して残りだけ公開するモードは含めない。
LoD3/4があっても「最大LoD」を選ばず、2→1の規則だけで選ぶ。対応外LoDの存在を記録し、
両対象LoDなしは除外する。特にLoD1+LoD3、LoD1+LoD2+LoD3を合成試験に含める。

**LoD選択→選択branchの形状検証→XY変換→AOI交差**の順序を固定する。
選択LoD2がAOI外、LoD1がAOI内でもLoD1に変更しない。
AOI判定は全選択形状の2D `intersects`で、境界接触を含む既存選択意味を保ち、
全3D形状はclipしない。接触のみ/微小交差による格子脱落をStandard欠損へ読み替えない。
本番化時にはゼロ面積投影面を含む判定の安全性も合成検証する。

### 形状と鉛直座標

- LoD1: 本corpusの`lod1Solid/Solid/exterior/CompositeSurface/surfaceMember/Polygon`。
  **Polygonのinterior ring**を保存する。`Solid/interior`という内側shellは別概念であり、
  最小profileでは非対応エラー。Solidの体積・水密性を保証する契約にはしない。
- LoD2: `lod2MultiSurface`のinline facesと同一Building内のSolid参照を既存の厳密仕様で照合。
  同じ面をSolidとMultiSurfaceで二重登録しない。xrefの外部/別Building参照・重複等を拒否する。
- 共通の派生表現は3D面集合。Raw branch/shell/ringの対応表を保持し、LoD1 Solidを
  LoD2 MultiSurfaceに呼び替えない。Standardを2D footprintや押出高さへ置換しない。
- 提供元宣言はEPSG:6697の緯度・経度・H（JGD2011/T.P.、Hは重力関連絶対標高m）。
  取得時の宣言証拠は[Preflight](OUEM_Komae_Mixed_LOD_Preflight_v0.1.md)を参照。
  Native格納はlongitude,latitude,H。StandardはXYだけ6668→6677へ変換し、Hはbit/値として
  exactに保つ。鉛直変換、ジオイド補正、EPSG:4979、高さの相対化を導入しない。
- LoD1の平坦上面とLoD2詳細形状の最高点はモデルの意味が異なる。
  maxZ比較を精度の優劣や補正量と解釈しない。宣言の一致は測量精度・datum realizationの検証ではない。

### ID・provenanceの最小記録

各Buildingで`source_id`、LoDに依存しない既存UUIDv5規則の`ouem_id`、`source_lod`（1/2を明示）、
選択reason、両branchのpresence/validation状態、Raw ZIP SHA、member名/SHA、release、
geometry branch（親ID下のnamespace-aware locatorとpolygon ID/ordinal）、元H宣言を記録する。
AOI適合の監査証拠としてRaw city値・codeSpaceとそのcodelist hashも保持する案とするが、
これを汎用Standardの暗黙の自治体filterにはしない。
同じsource IDに`:lod1`等のsuffixを加えて別建物化しない。異release間の同一建物照合は未解決。
原geometry byte hashと構造/座標の意味的digestは別名で記録し、canonicalizationの規則も版管理する。

NativeにはどのConverter出力・feature・LoDからgeometry BLOBを採ったかを記録し、Standardには
Native artifact/receipt/hashと選択表を引き継ぐ。nullableな既存`source_lod`を後から埋めず、
新profileでの必須の意味を定義する。GPKG列とmanifestのLoD/ID集合が一致することを検査する。

## 3. Converterの成立性と変換方式案

固定Converter: `ce7766df9788ce391b149c55df16d33082d0bc72` / nusamai0.1.19。
CLI SHA `0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b`。
ローカルcheckout HEAD・clean status・対象3ソースの固定commitとの差分なしを読取確認した。

既存の[合成実行証拠](../experiments/plateau_converter/CLI_SYNTHETIC_EXECUTION_20261027.md)は、
固定LoD2の各EPSGと`use_lod=lod1` controlの成功を示す。LoD1 controlは両LoDを持つ2棟に
対する独立したXYZ/ring検査であり、LoD1-only/実Mixed出力が検証済みという意味ではない。
今回はConverterを再実行していない。

ソースの`nusamai/src/transformer/selection.rs:LodSelection`、`setting.rs:build`、
`transform/lods.rs:FilterLodTransform::transform/find_lods/edit_tree`を確認した。
実CLIの最大指定は`use_lod=max_lod`、内部modeはHighest。
単一LoD指定`lod1/lod2`は単一mask、maxはobject treeで見つかる最大LoDを採り、
対象LoDがなければentityを出さない。Raw上の「LoD2が壊れている」を業務的な欠損と区別する
選択validatorにはならない。`use_lod=highest`を実在するCLI optionとして案内しない。
LoD3/4、descendant、空/不正branchを考えるとmaxは提案規則の代替ではない。

**最初の実装候補は2回の明示変換**:

1. 先にRaw selectorで全ID・presence・選択LoD・有効性を確定し、不正は変換前に停止する。
2. 同じimmutable Raw member集合を`--epsg 6697 -t use_lod=lod2`と`...use_lod=lod1`で
   別々の新規GPKGに変換する。split_components=False、binary/argv/stdout/stderr/hashを各々記録。
3. Raw選択表で各出力のID/面/ring/全XYZを照合する。LoD1変換に両LoDありの建物が含まれても、
   LoD2を選択したIDはNativeへLoD1から入れない。
4. 新Mixed Native writerが、同じ格納CRS/encodingを確認した上で選択branchのBLOB/属性を
   コピーし、全IDをちょうど1回だけ登録する。全体ID集合・構造・XYZ・BLOB対応を再検証して公開。

これは**未実装・未実行の案**であり、二つのGPKGを単純appendする方式ではない。
旧provenance validatorはConverter output1個、requested_lod=2等を要求するため、
旧schemaを偽装して2 branchを通さず、新profileのgraph/schemaで2実行と1選択Nativeを表現する。
追加実行コストと新Native結合writerが必要だが、Raw XMLを切り貼りせず、branch出典を検証しやすい。
代案のmax_lod利用は、全Raw LoD範囲・object tree・不正branch検出・出力選択一致を独立に証明した
限定profileでのみ検討する。本計画で同義と認定しない。Converter本体patch/依存更新は提案しない。

## 4. 実装境界と既存経路の保護

| 境界 / 現在の所有コード | 新profileで必要な最小変更案 |
|---|---|
| [LoD2 Reader](../../src/ouem/native/building/source_h_lod2.py): `read_lod2/compare_lod2` | 既存入口は不変。別のMixed presence/selectorとLoD1 Solid限定decoder。XML安全性・座標/ring primitiveは再利用可能だが、LoD2 absentとinvalidを潰さない |
| [provenance](../../src/ouem/native/building/provenance.py): `validate_source_h_record` | 旧requested_lod=2・use_lod=lod2・単一Converter graphは不変。新profile/schema/receiptと選択表・二branch graphを別に検査 |
| [Native](../../src/ouem/native/building/source_h.py): `ingest_source_h` | 旧LoD2照合は不変。選択BLOBを持つ新writer/validatorと原子的新規公開。ring/XYZ・ID・source branchを照合 |
| [Standard](../../src/ouem/standardize/building/source_h.py): `validate_native/standardize_source_h` | 旧profileのLoD2再照合・selected_lod_by_id=2は不変。新NativeからXYのみ変換、3D/H・選択metadata保持、選択後のAOI判定 |
| [geometry helper](../../src/ouem/standardize/building/source_h_geometry.py): `read_attributes/audit_standard` | 既存LoD2/null認識や旧manifest意味を変更せず、新profileでは明示1/2・reasonとRaw branch対応の厳密検査を追加 |
| [独立Consumer](../../src/ouem/consumers/source_h_standard.py): `manifest_format/_validate` | 旧selected_lod=2固定を緩めない。別ConsumerがRaw presenceから選択とAOI集合を独立再計算し、producerの選択関数・PASS dictをoracleにしない。Watch/hash・読取専用性は再利用 |
| [accepted Adapter](../../src/ouem/adapters/voxcity/__init__.py): `adapt_standard_to_voxcity` | whitelist/CLI不変。Mixed candidateを受け付ける別探索的入口が、Consumer・Terrain・CRS/鉛直宣言を検査してから既存pure helperを利用 |
| [PR #134入口](../../src/ouem/komae_four_mesh_poc.py) | 373棟固定・旧LoD2 Consumer/profile・既存CLIは不変。Mixed用のAOI/入力は独立入口へ。必要時だけ共有helperの抽出を別PRで回帰検証し、丸ごとforkしない |

Native/Standardの公開は検証後、新規directoryに限り、失敗Runと証拠を保持する。
同一Run内のNative→Standardの構造/順序/H保存は厳密に検証する。
別Converter実行間の面順序差はPR #134同様、全XYZを含む各face/ring multisetとordered差を
分離して報告する。点の袋だけ/2D equalsで形状同値を証明しない。

## 5. 合成テスト仕様（今回未実装）

既存fixtureや期待値を変更せず、独立した小さなMixed fixture群を新設する案。
手で記述したXYZ・外周/内周・branch ID・期待選択JSONをoracleにする。
Converter出力、producer selector、同じ変換関数の戻り値から期待値を作らない。

| ID | 合成条件 | 独立した期待結果・検証境界 |
|---|---|---|
| M01 | 同じIDでLoD1/2あり。tops例18/20m H | 1行、LoD2/reason2、LoD2全faces/XYZのみ。LOD1+2+3でも2、LoD3最大値を使わない |
| M02 | LoD1のみ、base10/top18m H | 1/reason fallback、Solidの全face/ring/Hを保持。LoD1+3でも1 |
| M03 | LoD2のみ | 2、LoD1なしをエラーにしない、Solid参照とMultiSurfaceを二重計上しない |
| M04 | 両方なし（LoD0/3だけの例も） | `NO_SUPPORTED_LOD1_OR_LOD2`の明示除外、geometry/heightを補完しない |
| M05 | 有効LoD1 + empty/破損LoD2、欠損/外部/別Building xref | Run FAIL、LoD1出力なし、未検証成果物を公開しない。真のabsentとは別state |
| M06 | 同一/別memberの重複Building ID、同形状でも重複、重複XML ID | fail-closed。相殺・last-winsやLoD別suffixによる重複回避はしない |
| M07 | LoD1の屋根/底面にcourtyard interior ring、内壁あり | exterior/interior区別と閉鎖・順序・XYZ・重複数を保持。穴を埋めない。別fixtureのSolid/interior shellは非対応FAIL |
| M08 | 同じIDでLoD1のみAOI内、LoD2のみAOI外／逆、境界接触 | 選択2→交差判定。前者除外・後者2で採用。LoDをAOI都合で替えない。選択全形状をclipしない |
| M09 | 2D/非有限/未閉鎖、EPSGや軸/単位/H宣言不整合 | 元Hを推測補正せずFAIL。縦基準が宣言されても正しい実現かは別検証。XYだけの既知制御点とliteral Hを比較 |
| M10 | Native→Standard、外周/内周/3D壁/offsetのないH | XYは独立制御点で1e-7m以内という既存検証水準を出発案に、H exact=0差、構造・ID・属性/BLOB選択対応。閾値の正式契約化は別レビュー |
| M11 | producerが2ありを1と偽装、選択reason/LoD列/Raw hash/geometry/Hを改ざん、古いPASS流用 | ConsumerがRawから選択を独立再構成してFAIL。再hashした偽receiptも検出。manifest/GPKG/Rawの同じID集合・選択LoDを検査 |
| M12 | 旧LoD2のfixtures/CLI・PR #134 bounded入口 | 旧profileの許可/拒否境界・2メンバー既定・373制約・accepted whitelistを維持。Mixedは旧入口で拒否される。旧Runへ書込みなし |
| M13 | 複数出力から選択、LoD1/2の両GPKGに同じID | Nativeに1回だけ、選択branchのBLOB/属性を採る。Converter省略/余分ID/予期しないLoD/exit非0はFAIL |
| M14 | 別実行でface並び順だけ違う／同じ点袋でもring接続を変更 | 前者をordered差として報告、各face/ring/XYZ同値を確認。後者は必ずFAIL。Run内の順序保持は別に厳密検査 |
| M15 | 公開前/消費中に入力変更、既存directory、失敗後の再試行 | hash/identity再検査、成功を宣言しない。旧成果物と失敗Runを残し、新Runのみ公開 |
| M16 | 市名付き配布物に他自治体codeのLoD1を含む | Preflightで市内と誤認しない。市内適合の未確認を記録する。汎用Standardの無断filter追加や、LoD選択のすり替えはしない |

M01–09でRaw selectorを先行、M10/M13で固定Converter+新Native/Standard接続、
M11で独立Consumerの否定テストを完了してから実Mixed AOIへ進む。
Voxelizerテストはその後。セル交差率>0.3・ownerなし・複数segment・roundingはAdapter側の
別診断であり、Standardの建物ID集合を縮める条件にはしない。

## 6. 推奨する実装PRの分割

| 順序 | PR内容 / 完了条件 | 前提・リスク |
|---|---|---|
| P1 (Small–Medium) | profile/selection tableのレビュー、手作りfixture、bounded LoD1 decoderと純粋selector、M01–09/M14 | 本提案の承認。旧Reader挙動不変。Solid inner ringとinner shellの境界を確定 |
| P2 (Medium) | 固定Converter二branchの合成実行、Mixed Native graph/receipt・選択BLOB writer、M13/M15 | P1。単一旧graphを流用しない。新GPKGのCRS/header/属性コピーを検証。既存binary/pin不変 |
| P3 (Medium) | Mixed Standardと独立Consumer、M10–12、次いで対象地域を承認したAOIのBuilding-only実データ新Run | P2と市内条件/市境横断の範囲レビュー。H exact、選択後AOI、source_lod/reason必須。TerrainやVoxCityなしでもRaw→Standardは検証可能 |
| P4 (Separate scope) | 追加Terrainの出典/被覆/鉛直宣言をPreflightし、新規成果物を生成 | AOIに合うTerrainが必要。旧Terrain拡張/外挿/平坦面で穴埋めしない。未取得tileを確定扱いしない |
| P5 (Medium) | 新Mixed探索的Adapterから代表高さ実行、実owner/欠落/複数segmentを診断 | P3+P4と別実行承認。旧A3/PR #134入口不変。高さ分布・科学的妥当性/正式受入は含めない |

P1の最小selector仕様、P2の二branch graph、LoD1 unsupported表現の拒否範囲がレビュー事項。
これは設計決定の提案であり、本PRで正式契約を改定した扱いにはしない。

## 7. 出典・再現手順・検証の限界


### 入力の出典と保存先

2026-10-27取得の既存PLATEAU Komae2025 ZIPを再利用し、新規ネットワーク取得なし。
出典URL・ライセンス確認は[既存取得記録](../experiments/voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md)と
[PR #133](OUEM_Komae_Mixed_LOD_Preflight_v0.1.md)に依拠し、現時点の配布条件を再照会していない。
ZIP: `data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip`、
1,192,172,043 bytes、SHA `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555`。
入力GMLはPR #134の新Runに展開済みの
`data/work/real-komae-source-h/run-four-mesh-20261030-02/extracted/udx/bldg/`の4メンバー。

| メンバー | SHA-256 |
|---|---|
| 53393455_bldg_6697_op.gml | `07245d14727d83c769a7809e3b135bf651ace6c3a18293b35c6a7ffe33b45b1f` |
| 53393456_bldg_6697_op.gml | `eaff3868a122e28e8c23810a45165675591ddfa72e1077a1948aa04bd0d89c30` |
| 53393465_bldg_6697_op.gml | `32f8912b2c3f8b09a2c76211b8ea22c9402f5b1357d36843dcfd5c93616ff613` |
| 53393466_bldg_6697_op.gml | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |

cityはnamespace `https://www.geospatial.jp/iur/uro/3.2`、codeSpaceは
`../../codelists/Common_localPublicAuthorities.xml`。
ZIP内の`codelists/Common_localPublicAuthorities.xml`と展開済みcodelistのhash一致を確認。
SHAは`18b2baadea829417703a9d44796cf3812c487b94c056f75eabcd043741dd61dd`。
全IDのcity fieldsをlocal JSONに保存し、515件だけの抜取確認に留めていない。

### ローカル証拠（Git対象外）

`data/work/komae-mixed-lod-design/20261030-01/`は初回失敗のscan.py/logと既存pytest log。
3D壁面のXY投影を含むGeometryCollectionに対しcoversが
`IllegalArgumentException: Cannot compute the quadrant for point (0,0)`で失敗した。
未検証の結果を成功扱いせず、次の新directoryで診断をやり直した。

成功した読取診断は`data/work/komae-mixed-lod-design/20261030-02/`。
`scan.py/summary.json`が全域分布・候補比較、`refine.py/balanced-details.json`がBの全63 ID・
選択LoD・H範囲・境界・投影格子支持、`city_audit.py/city-audit.json`が全12,847 IDのcity確認。
`city-fields.json`はB63棟の初回city調査。地図用の`lod1-distribution.geojson`（515棟）と
`balanced-coverage.geojson`（候補B/63棟）もEPSG:6677で保存した。QGISでの実表示は未確認。
GeoJSONに市内確認済み/正式Study Areaという意味を持たせない。

| 証拠 | SHA-256 |
|---|---|
| scan.py | `258ebbd1bf0c4a2ec6cf75a80854c125eaf85e0045894a3f18525db32bddc8ec` |
| summary.json | `31846f26be055f03643be0cd42d6df75384da4b9d8785e851fe9113f2206b76f` |
| refine.py | `3b7efe37880a6c9ccf300835beaadd47f83894748efa5a6474b987f8ff27fc01` |
| balanced-details.json | `2d277024a41e10b5254f4d61c9a183421b4e962b298c421ec96c59711affa64b` |
| city_audit.py | `06278eb9b07a5637b63822667019fd6be50bc9b15f327ceccf86518418ecd2c3` |
| city-audit.json | `41e1b98ec3e8853ce542ed8c09c333926991528fa219c84f147e7f3ba1aaeef0` |

### 再現方法

ordinary Windows OUEM venv Python3.11.9、NumPy2.4.6、Shapely2.2.0、PyProj3.7.2、
Rasterio1.4.4。依存更新・GIS Python subprocess・Converter・engine raster/voxel実行なし。
付録の3つの診断を**新しい同一作業directory**に各ファイル名で保存し、順に実行する。
終了済みworkのJSONはopen(x)で上書きを拒否する。原データは読取専用である。

```powershell
.venv/Scripts/python.exe data/work/<new-mixed-lod-preflight>/scan.py
.venv/Scripts/python.exe data/work/<new-mixed-lod-preflight>/refine.py
.venv/Scripts/python.exe data/work/<new-mixed-lod-preflight>/city_audit.py
```

scan/refineはPR #133の限定`lod1_records`診断だけをASTで再利用し、旧script全体を実行しない。
そのscriptが無い環境では、[Preflight付録](OUEM_Komae_Mixed_LOD_Preflight_v0.1.md)の
「実行した読取診断コード」を新workの別ファイル`prior/diagnose_mixed_lod.py`へ復元し、
scan/refineの`OLD`だけをその新しいprior directoryへ向ける。
GML/codelistが無い場合は上記ZIPの4メンバーとcodelistsを新しい入力directoryに選択抽出し、
診断3ファイルの入力pathを置換して表のSHAと一致を確認する。Converter再実行は不要。
付録は実行済み診断のテキストで、本番Readerや新profileの実装ではない。
Windows改行等でscript byte hashが変わる場合も、入力byte hashと選択条件を区別して記録する。

### 検証結果と未確認

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_study_area.py tests/test_source_h_xlink.py tests/test_source_h_ingestion.py tests/test_source_h_standard.py tests/test_source_h_consumer.py tests/test_building_provenance.py tests/test_komae_four_mesh_poc.py tests/test_real_komae_source_h.py tests/test_voxcity_adapter.py
```

**280 passed、4 warnings、68.41秒、失敗/skipなし**。
warningsは既存stat/fstat ctime診断1件とRasterio/Affine pending deprecation3件。
新規本番コード・テスト変更なしの文書PRなので全体pytestは再実行していない。
scan入力6件の前後hash、旧Preflightの保護入力9件、PR #134 Standardとvoxelの記録済みhashが
終了時も不変であることを確認した。tracked差分は本新規文書のみ。
文書リンク/相対path、付録と実行scriptの一致、`git diff --check`を確認する。

未確認は公式行政境界による幾何照合、市内LoD1-onlyを持つ別入力の存在、追加Terrainの
tile番号/被覆/取得条件、Mixed Converter/Native/Standard/Consumerの実動作、
VoxCity実owner・height・voxel、高さ分布・科学的妥当性・正式Acceptance。
本PRの完了は設計・制約の可視化であり、**狛江市内Mixed AOI選定の成功ではない**。


## 付録: scan.py（読取Preflight）

```python
"""Read-only AOI search; not a Mixed-LOD Reader/Native/Standard implementation."""
import ast
from collections import Counter
import hashlib,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from pyproj import Transformer
import rasterio
import shapely
from shapely.geometry import box,mapping
from ouem.native.building.source_h_lod2 import read_lod2,_ring
from ouem.standardize.building.source_h_geometry import as_shape
from ouem.adapters.voxcity import build_normalized_footprint

W=Path(__file__).resolve().parent
OLD=Path('data/work/komae-mixed-lod-preflight/20261030-01')
G='{http://www.opengis.net/gml}'
B='{http://www.opengis.net/citygml/building/2.0}'
X='{http://www.w3.org/1999/xlink}href'
SRS='http://www.opengis.net/def/crs/EPSG/0/6697'
# Reuse the exact previously executed corpus-specific diagnostic function only.
original=ast.parse((OLD/'diagnose_mixed_lod.py').read_text(encoding='utf-8'))
function=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='lod1_records')
exec(compile(ast.Module(body=[function],type_ignores=[]),'prior-diagnostic-function','exec'))
transform=Transformer.from_crs(6668,6677,always_xy=True)
paths=sorted(Path('data/work/real-komae-source-h/run-four-mesh-20261030-02/extracted/udx/bldg').glob('*.gml'))
assert len(paths)==4
protected=paths+[Path('config/study_areas/komae_09LD3451.yaml'),Path('data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif')]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
before={str(p):digest(p) for p in protected}
records=[]
seen=set()
for path in paths:
 two,excluded=read_lod2([path])
 one,forms=lod1_records(path)
 assert not (seen & one.keys())
 seen.update(one)
 assert two.keys()|set(excluded)==one.keys()
 for sid,faces1 in one.items():
  lod=2 if sid in two else 1
  faces=two.get(sid,faces1)
  assert faces
  tree=('GeometryCollection',tuple(('Polygon',face) for face in faces))
  # Diagnostic XY only. Raw H is retained/checked independently, not sent to PROJ.
  geom=shapely.transform(as_shape(tree),transform.transform,interleaved=False)
  fp,diag=build_normalized_footprint(geom,sid)
  hs=[p[2] for face in faces for ring in face for p in ring]
  records.append(dict(source_id=sid,source_lod=lod,member=path.name,geometry=geom,footprint=fp,
                      h_min=min(hs),h_max=max(hs),vertices=len(hs),footprint_area_m2=fp.area))
 print(path.name,dict(Counter(r['source_lod'] for r in records if r['member']==path.name)),flush=True)
 geoms=None
with rasterio.open(protected[-1]) as ds:
 terrain=box(*ds.bounds)
 terrain_info=dict(bounds=list(ds.bounds),crs=ds.crs.to_string(),shape=list(ds.shape),valid=int(ds.read(1,masked=True).count()))
one=[r for r in records if r['source_lod']==1]
assert len(one)==515 and len(records)==12847
geoms=np.array([r['geometry'] for r in records],dtype=object)
index=shapely.STRtree(geoms)
def evaluate(bounds):
 area=box(*bounds)
 positions=index.query(area,predicate='intersects')
 selected=[records[int(i)] for i in positions]
 n=Counter(r['source_lod'] for r in selected)
 return dict(bounds=list(bounds),area_m2=area.area,lod1=n[1],lod2=n[2],total=len(selected),
             boundary=sum(not area.covers(box(*r['geometry'].bounds)) for r in selected),
             terrain_overlap_m2=area.intersection(terrain).area,
             terrain_distance_m=area.distance(terrain),
             terrain_covered=terrain.covers(area))
candidates={}
for r in one:
 c=r['footprint'].representative_point()
 for side in (50,100):
  x=math.floor(c.x/25)*25
  y=math.floor(c.y/25)*25
  for dx,dy in ((0,0),(-25,0),(0,-25),(-25,-25)):
   bounds=(x-side/2+dx,y-side/2+dy,x+side/2+dx,y+side/2+dy)
   if bounds not in candidates:
    value=evaluate(bounds)
    if value['lod1'] and value['lod2']:candidates[bounds]=value
mixed=list(candidates.values())
assert mixed
near=min((r for r in mixed if r['area_m2']==10000 and min(r['lod1'],r['lod2'])>=3),key=lambda r:(r['terrain_distance_m'],-r['terrain_overlap_m2'],r['total'],r['bounds']))
balanced=min((r for r in mixed if r['area_m2']==10000),key=lambda r:(-min(r['lod1'],r['lod2']),r['total'],r['bounds']))
small=min((r for r in mixed if r['area_m2']==2500),key=lambda r:(r['terrain_distance_m'],-min(r['lod1'],r['lod2']),r['total'],r['bounds']))
closest=min(one,key=lambda r:r['geometry'].distance(terrain))
summary=dict(terrain=terrain_info,total=len(records),selected_lod_counts=dict(Counter(r['source_lod'] for r in records)),
 per_member={p.name:dict(Counter(r['source_lod'] for r in records if r['member']==p.name)) for p in paths},
 lod1_only_bounds=list(shapely.union_all([r['footprint'] for r in one]).bounds),
 lod1_only_intersect_terrain=sum(r['geometry'].intersects(terrain) for r in one),
 closest_lod1_only=dict(source_id=closest['source_id'],member=closest['member'],distance_m=closest['geometry'].distance(terrain),bounds=list(closest['geometry'].bounds)),
 candidate_search=dict(alignment_m=25,sides_m=[50,100],unique_mixed_candidates=len(mixed)),
 candidates=dict(near=near,balanced=balanced,small=small),input_sha256=before)
chosen=box(*near['bounds'])
selected=[records[int(i)] for i in index.query(chosen,predicate='intersects')]
for r in selected:
 r['boundary']=not chosen.covers(box(*r['geometry'].bounds))
 r['aoi_footprint_m2']=r['footprint'].intersection(chosen).area
assert before=={str(p):digest(p) for p in protected}
summary['input_unchanged']=True
with (W/'summary.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
with (W/'selected.json').open('x',encoding='utf-8') as f:json.dump([{**{k:v for k,v in r.items() if k not in ('geometry','footprint')},'geometry_wkb':r['geometry'].wkb_hex,'footprint_wkb':r['footprint'].wkb_hex} for r in selected],f,indent=2)
with (W/'lod1-distribution.geojson').open('x',encoding='utf-8') as f:json.dump(dict(type='FeatureCollection',crs=dict(type='name',properties=dict(name='EPSG:6677')),features=[dict(type='Feature',properties=dict(source_id=r['source_id'],member=r['member']),geometry=mapping(r['footprint'])) for r in one]),f)
print(json.dumps(summary,indent=2))
```

## 付録: refine.py（読取Preflight）

```python
"""Read-only detailed validation of the balanced candidate; no engine rasterization."""
import ast,json,math
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import shapely
from shapely.geometry import box,mapping
from pyproj import Transformer
from ouem.native.building.source_h_lod2 import read_lod2,_ring
from ouem.standardize.building.source_h_geometry import as_shape
from ouem.adapters.voxcity import build_normalized_footprint
W=Path(__file__).resolve().parent
OLD=Path('data/work/komae-mixed-lod-preflight/20261030-01')
G='{http://www.opengis.net/gml}';B='{http://www.opengis.net/citygml/building/2.0}'
X='{http://www.w3.org/1999/xlink}href';SRS='http://www.opengis.net/def/crs/EPSG/0/6697'
original=ast.parse((OLD/'diagnose_mixed_lod.py').read_text(encoding='utf-8'))
function=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='lod1_records')
exec(compile(ast.Module(body=[function],type_ignores=[]),'prior-diagnostic-function','exec'))
summary=json.loads((W/'summary.json').read_text(encoding='utf-8'))
bounds=summary['candidates']['balanced']['bounds']
aoi=box(*bounds)
xy=Transformer.from_crs(6668,6677,always_xy=True)
geo=Transformer.from_crs(6677,6668,always_xy=True).transform_bounds(*bounds,densify_pts=21)
rawbox=box(*geo)
path=Path('data/work/real-komae-source-h/run-four-mesh-20261030-02/extracted/udx/bldg/53393466_bldg_6697_op.gml')
two,excluded=read_lod2([path]);one,_=lod1_records(path)
rows=[]
for sid,faces1 in one.items():
 lod=2 if sid in two else 1
 faces=two.get(sid,faces1)
 xyz=[p for face in faces for ring in face for p in ring]
 xs,ys=zip(*[(p[0],p[1]) for p in xyz])
 if not rawbox.intersects(box(min(xs),min(ys),max(xs),max(ys))):continue
 tree=('GeometryCollection',tuple(('Polygon',face) for face in faces))
 geom=shapely.transform(as_shape(tree),xy.transform,interleaved=False)
 if not geom.intersects(aoi):continue
 fp,diag=build_normalized_footprint(geom,sid)
 # A projected diagnostic grid, not a VoxCity generator or ground/height model.
 support=[]
 imin=max(0,math.floor(fp.bounds[0]-bounds[0]));imax=min(99,math.floor(fp.bounds[2]-bounds[0]))
 jmin=max(0,math.floor(fp.bounds[1]-bounds[1]));jmax=min(99,math.floor(fp.bounds[3]-bounds[1]))
 for i in range(imin,imax+1):
  for j in range(jmin,jmax+1):
   cell=box(bounds[0]+i,bounds[1]+j,bounds[0]+i+1,bounds[1]+j+1)
   if fp.intersection(cell).area>.3:support.append([i,j])
 hs=[p[2] for p in xyz]
 rows.append(dict(source_id=sid,source_lod=lod,member=path.name,boundary=not aoi.covers(box(*geom.bounds)),
  footprint_intersects=fp.intersects(aoi),full_area_m2=fp.area,aoi_area_m2=fp.intersection(aoi).area,
  h_min=min(hs),h_max=max(hs),vertices=len(hs),interior_rings=sum(len(face)-1 for face in faces),
  support_cells=support,footprint=mapping(fp)))
assert len(rows)==summary['candidates']['balanced']['total']
assert Counter(r['source_lod'] for r in rows)=={1:31,2:32}
cell_members={}
for row in rows:
 for i,j in row['support_cells']:cell_members.setdefault((i,j),[]).append(row['source_id'])
report=dict(bounds=bounds,area_m2=aoi.area,total=len(rows),selected_lod_counts=dict(Counter(r['source_lod'] for r in rows)),
 boundary_lod_counts=dict(Counter(r['source_lod'] for r in rows if r['boundary'])),
 fully_contained_lod_counts=dict(Counter(r['source_lod'] for r in rows if not r['boundary'])),
 supported_lod_counts=dict(Counter(r['source_lod'] for r in rows if r['support_cells'])),
 zero_support=[dict(source_id=r['source_id'],source_lod=r['source_lod'],aoi_area_m2=r['aoi_area_m2']) for r in rows if not r['support_cells']],
 competing_cells=sum(len(v)>1 for v in cell_members.values()),max_competitors=max(map(len,cell_members.values())),
 footprint_vs_full_geometry_selection_equal=all(r['footprint_intersects'] for r in rows),
 geographic_bounds=list(geo),source_member=path.name,
 meaning='Projected EPSG6677 1m squares, origin=(xmin,ymin), >0.3m2 individual support; no owner priority, DEM, VoxCity raster/voxel call or scientific height validation.')
with (W/'balanced-details.json').open('x',encoding='utf-8') as f:json.dump(dict(report=report,buildings=rows),f,indent=2)
with (W/'balanced-coverage.geojson').open('x',encoding='utf-8') as f:json.dump(dict(type='FeatureCollection',crs=dict(type='name',properties=dict(name='EPSG:6677')),features=[dict(type='Feature',properties=dict(role='study_area'),geometry=mapping(aoi))]+[dict(type='Feature',properties={k:v for k,v in r.items() if k not in ('footprint','support_cells')},geometry=r['footprint']) for r in rows]),f)
print(json.dumps(report,indent=2))
```

## 付録: city_audit.py（読取Preflight）

```python
import json,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
W=Path(__file__).resolve().parent
ids={x['properties']['source_id'] for x in json.loads((W/'lod1-distribution.geojson').read_text(encoding='utf-8'))['features']}
G='{http://www.opengis.net/gml}'
rows=[]
base=Path('data/work/real-komae-source-h/run-four-mesh-20261030-02/extracted')
for path in sorted((base/'udx/bldg').glob('*.gml')):
 for _,node in ET.iterparse(path,events=('end',)):
  if node.tag.endswith('}Building'):
   sid=node.get(G+'id')
   fields=[dict(tag=e.tag,text=(e.text or '').strip(),attributes=e.attrib) for e in node.iter() if e.tag.split('}')[-1]=='city']
   rows.append(dict(source_id=sid,lod1_only=sid in ids,member=path.name,city_fields=fields))
   node.clear()
  elif node.tag.endswith('}cityObjectMember'):node.clear()
assert len(rows)==12847 and len({r['source_id'] for r in rows})==len(rows)
assert sum(r['lod1_only'] for r in rows)==515
summary={}
for label,items in [('all',rows),('lod1_only',[r for r in rows if r['lod1_only']]),('lod2',[r for r in rows if not r['lod1_only']])]:
 summary[label]=dict(Counter(e['text'] for r in items for e in r['city_fields']))
 summary[label+'_missing_city']=sum(not r['city_fields'] for r in items)
summary['per_member_lod1_only']={p.name:dict(Counter(e['text'] for r in rows if r['lod1_only'] and r['member']==p.name for e in r['city_fields'])) for p in sorted((base/'udx/bldg').glob('*.gml'))}
code_spaces={e['attributes'].get('codeSpace') for r in rows for e in r['city_fields']}
summary['code_spaces']=sorted(code_spaces)
summary['code_names']={}
for space in code_spaces:
 path=(base/'udx/bldg'/space).resolve()
 assert path.is_file()
 root=ET.parse(path).getroot()
 for definition in root.iter():
  name=definition.find(G+'name');desc=definition.find(G+'description')
  if name is not None and name.text in ('13219','13112','13208'):
   summary['code_names'][name.text]=dict(description=desc.text if desc is not None else None,codelist=str(path))
with (W/'city-audit.json').open('x',encoding='utf-8') as f:json.dump(dict(summary=summary,buildings=rows),f,indent=2,ensure_ascii=False)
print(json.dumps(summary,indent=2,ensure_ascii=False))
```
