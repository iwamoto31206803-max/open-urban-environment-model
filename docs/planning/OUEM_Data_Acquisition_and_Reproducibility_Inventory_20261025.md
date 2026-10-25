# OUEM データ取得・再現性インベントリ（2026-10-25）

## 1. 調査範囲と証拠

基点main：`526cd57fa7f5ecf2aa78dca59a82c08342f8e77f`。リポジトリのREADME、config、scripts、src、契約、受入・研究・環境記録の静的調査である。実データ・外部Webページは取得していない。URLはリポジトリ中で確認できた文字列のみを転載し、到達性・現在の公開状況・利用条件は再検証していない。記載がないURL・license・手順は「未確認」とする。入力のローカル存在・サイズ・実際のhashは今回検査していない。

主な根拠：

- [ルートREADME](../../README.md)、[Windows手順](../../scripts/work/README.md)、[狛江config](../../config/study_areas/komae_09LD3451.yaml)、[CLI定義と依存pin](../../pyproject.toml)。
- [Building受入](../../experiments/a1_e2e_pilot/README.md)、[A2 Terrain受入](../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)、[A3 Adapter受入](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)、[contained E2E記録](../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md)。
- [建物鉛直診断](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)、[樹冠engine調査](../research/OUEM_VoxCity_1.7.0_Canopy_Contract_Verification.md)、[CHM handoff provenance](../local_handoff/komae_test_standard.tif.provenance.json)。
- [GEEKOM A6環境記録](../development/OUEM_Windows_Development_and_Remote_Setup_20261025.md)、[runtime境界](../architecture.md)。

実装との差分は[実装インベントリ](OUEM_v0.2_Implementation_Inventory_20261025.md)を参照。以下の「必要」は将来の再実行に必要という意味であり、今回の取得・処理許可ではない。

## 2. 必要データの全体像

| 区分 | データ | 用途 | 現行再実行での位置付け |
|---|---|---|---|
| 建物・地形PoC必須 | PLATEAU Building CityGML、Converter GeoPackage | Building Native作成。元CityGMLは鉛直診断にも必要 | 統合runner自体は既存Nativeから開始するため、Raw→Converter→ingestを別途再構築する |
| 建物・地形PoC必須 | 東京都0.5 m bare-earth DEM `09LD3451.tif` | Native Terrain→Standard Terrain→Adapter地盤 | Native manifestからRAW絶対パスとhashを参照。TIFF単体では不足 |
| 派生成果・補助必須 | Native Building / Terrain、Standard Building、adjacent manifests、study-area YAML、GIS runtime snapshot | integration / preflightの入力 | Git管理されるconfigと、Git外で作成される実データ・snapshotを区別 |
| 次段階opt-in | Meta CHM GeoTIFFとhashに結合したprovenance JSON | Current / No-Canopy canopy voxel PoC | 現在の建物・地形受入に必須ではない。正式樹冠Standardでもない |
| 将来候補 | 東京LP・樹冠polygon、GSI LiDAR／外周線／DEM、気象EPW、B2比較写真等 | 構築profileやPhase B | 狛江の受入済み入力として特定されていない。実データrecipe未確認 |

現行A3 acceptance runnerのland coverは`np.ones`によるminimal bareland配列（`scripts/work/voxcity_komae_a3_acceptance.py::main / once`周辺）であり、公開土地被覆データを取得した証拠ではない。OSM等を追加必須データと推測しない。

## 3. PLATEAU Building：狛江固有の証拠

| 項目 | 確認できた内容 |
|---|---|
| 提供機関・データセット | PLATEAU CityGML建物。個別releaseの配布主体・自治体年度・版は未確認。根拠はStandard Building契約とBuilding受入記録 |
| 目的・layer | 3D Building。Converterの`bldg:Building`からNative `building`。非null String `id`をStandard `source_id`へ対応。診断ではCityGML `gml:id`との対応を確認 |
| 元ファイル識別子 | `53393465_bldg_6697_op.gml`（Windows手順と鉛直診断の入力例）。これだけで元配布archiveや年度を一意に同定できるとは限らない |
| 範囲 | Native 3,637棟。StandardはEPSG:6677の`[-23600,-40800,-23200,-40500]`と交差する111棟。contained PoCは全形状が矩形に含まれる92棟、境界横断19棟除外 |
| 取得先URL | **未確認**。リポジトリに当該CityGML配布先の具体URLが見当たらない。既知の外部サイトを推測で追加しない |
| 手動download既知部分 | CityGMLを入手することが前提。配布サイトでの選択、年度、archive名、解凍階層、必要隣接tileの選び方は未確認 |
| 利用条件・license | **未確認**。該当releaseのlicense名・条件・帰属表示の保存記録なし。OUEM本体のLICENSEとは別 |
| Raw保存先 | `data/raw/building/plateau_komae/53393465_bldg_6697_op.gml`。配布archiveの保存名・hashは未確認 |
| work中間 | `data/work/building/plateau_komae/53393465_bldg_6697_op_convert.gpkg`。Converter出力でありNativeではない |
| Native | `data/native/building/komae.gpkg`、layer `building`、adjacent `.manifest.json`、ingest再利用用`.receipt.json` |
| Standard | `data/standard/building/komae.gpkg`と`.manifest.json`。111棟、3D Multi Polygon、EPSG:6677、絶対T.P. Zを保持する契約 |
| ツール | PLATEAU GIS Converter GUI、QGIS/OSGeo4W GDAL/OGR子worker、OUEM venv。Converterの正確なバージョンは未確認 |
| 再現性証拠 | Building受入記録の3,637→111、Z差0、ID決定性。コードのConverter source SHA receiptとNative/Standard manifest。元CityGML・元archiveの既存hash値は記録から未確認 |
| 未確認事項 | release年度・元archive・全入力tile、ConverterのLOD/CRS/鉛直変換の正確な設定、元CityGMLからConverterまでの数値Z保存。EPSG:4979ラベルだけでT.P.保存を証明できない |

### 3.1 狛江の既知処理経路

```text
CityGML（raw）
 → PLATEAU GIS Converter GUI（manual、maximum LOD、3D/Z保持設定）
 → Converter GeoPackage（work）
 → ouem-plateau-buildings + GIS snapshot
 → Native Building + manifest / receipt
 → ouem-standardize-buildings + study-area YAML + GIS snapshot
 → Standard Building + manifest
 → ouem-adapt-voxcity + Standard Terrain
 → engine GeoJSON / manifest / grids / voxels（隔離PoC）
```

正確なコマンドと引数は[Windows手順](../../scripts/work/README.md)のmanual / gis / ouem / standardを参照し、重複した代替手順をここで確定しない。元CityGML直接GDAL変換は、試験時に`POLYHEDRALSURFACE Z EMPTY`となったため採用経路ではない。Converter後のNative ingestはreprojection／修復を行わず、Standardizerが水平のみ変換してZを復元・照合する。

### 3.2 他地域に再利用できる部分と変更点

再利用可能なのは手動Converter→明示runtime→Native→Standardという責任境界、Z／属性／feature数のQA、source_idに基づくID規則である。別地域では元release・tile・layer・source dataset・path、期待件数、study-area矩形とCRS、鉛直根拠を確認し直す。現行Building Standardizerは受入済みNative EPSG:4979→狛江EPSG:6677の制約があるため、YAMLのEPSGと件数を変えるだけで全国適用できるとは扱わない。containedの92/19はコードに固定されており一般化パラメータではない。

## 4. Tokyo DEM：狛江固有の証拠

| 項目 | 確認できた内容 |
|---|---|
| 提供機関・dataset | Tokyo Metropolitan Government、Tokyo 0.50 m bare-earth DEM、区部点群・地盤データに関する公開資料。狛江ファイルの根拠はA2受入記録 |
| 使用目的 | terrain絶対標高。DSMやCHMではない。A3のeffective ground算出とvoxel生成 |
| 使用ファイル・範囲 | `09LD3451.tif`、EPSG:6677、800×600、0.5×0.5 m、400×300 m、extent `[-23600,-40800,-23200,-40500]` |
| 記録内URL | [東京都Open Data Portal](https://portal.data.metro.tokyo.lg.jp/)、[区部の3次元点群公開release](https://www.metro.tokyo.lg.jp/information/press/2024/10/2024103126)、[公共基準点・水準基標](https://www.kensetsu.metro.tokyo.lg.jp/jimusho/tech/04-kijyun/kijyunsetu)。Standard Terrain契約とterrain launcherに存在 |
| URLの意味 | 案内・公開情報・鉛直意味の根拠。特定tileの直接download URL、archive、最新選択画面は**未確認**。これらURLだけで元bytes再取得を保証しない |
| 手動download既知部分 | 対象DEMを取得して下記Rawパスへ置く。tile選択・解凍・版指定の具体操作は未確認 |
| 利用条件・license | **未確認**。リポジトリの出典リンクはT.P.宣言の根拠であり、license確認の代用ではない |
| Raw | `data/raw/terrain/tokyo_23ku_dem_050m/komae/09LD3451.tif` |
| work | 必須work変換段階なし。入力TIFFをそのままNative manifestで登録 |
| Native | `data/native/terrain/komae_09LD3451.json`。RAW絶対パス、SHA、格子・統計・鉛直情報を保持 |
| Standard | `data/standard/terrain/komae_09LD3451.tif`と`.tif.manifest.json`。Float32、NoData -9999、入力格子・有効値保持。再投影・再サンプルなし |
| 必要CLI | `ouem-accept-terrain` → `ouem-standardize-terrain`、手順は`terrain_komae_local_acceptance.cmd`。Rasterio/NumPyはOUEM venv |
| 鉛直 | `source-declared` T.P.。水平EPSG:6677から鉛直datumを推論しない。独立測量によるverifiedではない |
| 未確認 | 新規取得版が2026-10-06入力と同一bytesか、現在の配布構成・license、他tileの欠損・datum・適合性 |

### 4.1 記録されたhashと品質

[A2正式記録](../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)の値：

- source SHA-256：`c747f2ae2ee30f67da98c1c90961f6a094fa0fca8ba3f15a1131c09783d73824`
- Standard SHA-256：`0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a`
- 有効セル480,000、NoData 0、標高19.577999114990234〜25.29599952697754 m。
- 使用main：`e1037dc4b01b4b091e30a8f3806b363d5ef12cc0`。現在の環境・依存一式を凍結したlockではない。

新規取得hashが違う場合は新版／異なる入力として調査し、上記値やmanifestを書き換えて一致させない。10/05 A3の入力hashは記録がなく、10/06 A2出力と同一bytesとは証明されていない。

### 4.2 他地域への再利用範囲

manifestでRAWを登録し、source hash／格子／標高を検査する方法は再利用候補。別地域ではtile・path・provider・source dataset・datum evidence・AOIを変える必要がある。ただし現行Terrain契約はEPSG:6677・Float32・north-up・有限NoData等に限定され、異CRSを自動再投影しない。取得後に勝手な再サンプルを挟まず、非適合入力は別の仕様検討対象とする。

## 5. Meta CHM：次段階PoCの入力候補

| 項目 | 確認できた内容 |
|---|---|
| 提供者・dataset名 | handoff JSONの宣言は「Meta and World Resources Institute (2026), Version 2 High Resolution Canopy Height Maps (CHMv2), DINOv3 global CHM v2 ml3」。一次提供releaseとの独立照合は未確認 |
| 用途 | canopy HAGをengine top/bottom配列へ変換しCurrent/No-Canopyを比較。正式樹冠Standardの絶対Z rasterではない |
| 狛江ファイル・範囲 | JSON名は`komae_test_standard.tif.provenance.json`。対応raster自体・元tile ID・取得範囲・前処理方法・取得先は未確認。名前にstandardがあってもOUEM Standard受入を意味しない |
| 記録内URL | [rslearn Meta canopy-height参照](https://allenai.github.io/rslearn/reference/data_sources/meta_canopy_height/)（handoff JSONのcitation）。元rasterの直接download URLではない |
| 手動download手順 | developer-local GeoTIFFと隣接`.tif.provenance.json`を用意する、という前提のみ。取得・mosaic・crop等の具体recipeは未確認 |
| 利用条件・license | **未確認**。citationとHAG宣言は利用許諾の証拠ではない |
| Raw保存先 | 現行の固定canonicalパスなし。launcherは明示ローカルpathを要求。将来の置き場所候補を決定済みと記載しない |
| 処理経路 | 指定CHM＋provenance→`komae_canopy.convert_chm`→engine cell中心nearest sampling→scenario arrays→隔離work。正式Native／Standard canopyを経由しない |
| CLI・tools | `.venv`のRasterio/NumPy/PyProj/pinned VoxCity。`run_komae_meta_chm_e2e.cmd <fresh-run-id> <CHM-path>`が既存contained runnerを起動 |
| 再現性証拠 | handoff JSON raster SHA：`cbfdd7ad7da9c9027203dff97ca435b111071f4423cdba39669725285470f315`。コードは実raster hashとJSONの一致、`height_above_ground_m`、source/citation/height statementを要求。今回一致検査なし |
| 数値・coverage条件 | 1 band、宣言CRS・有効transform、全target中心をcoverage、NoData/非有限/負値はBLOCK。pixel間隔は最初のtarget中心で正・有限かつ2 m以下。3 m未満はno-canopy、bottom=0.4×top。これらは1 m PoC設定で精度受入済みの標準値ではない |
| 受入・未確認 | 正式な狛江canopy受入記録は調査範囲にない。CHM精度、下端推定、全域位置整合、元配布版、QGIS実表示、shade/GVI性能は未確認 |

別地域ではcoverage・CRS・transform・HAGの根拠・source release・hashを再確認する。現行launcherは狛江92棟contained経路専用であり、CHM path変更だけで他地域を受け入れない。元CHMにNoDataがあれば補完は現行recipeに含まれず、勝手にゼロ化しない。

## 6. 将来データ：受入済み狛江入力とは分離

| 将来候補 | v0.2上の用途 | 取得・再現性の現状 |
|---|---|---|
| 東京／自治体LP点群・2D樹冠 | A1 profileの樹冠・CHM等 | 現行狛江受入に使った具体tile・URL・license・Raw path・処理recipeは未確認。PDALがあることは取得／処理済み証拠ではない |
| GSI LiDAR・建物外周線 | A3構築profile | provider実装・具体入力の受入なし。工程A3 Adapterとは別。URL・版・license・path・recipe未確認 |
| GSI DEM等 | A2構築profile | 現行Tokyo DEMと置換可能な受入済みデータではない。具体release・URL・datum・処理recipe未確認 |
| EPW等気象・日射情報 | B1時刻／期間比較 | v0.1 §6の継承対象。狛江観測点・年・EPWファイル・URL・license未確認 |
| 同地点写真・視点情報 | B2検証 | v0.1 §7の写真比較。対象地点・撮影条件・使用許諾・ファイル未確認 |

地表土地被覆・LAD／透過パラメータ・鉛直変換grid等もB1/B2や将来処理で必要性を検討するが、本調査では具体datasetや値を追加決定しない。

## 7. 取得物以外の再現前提と証拠の限界

### 7.1 個人PCとruntime

[E-PC](../development/OUEM_Windows_Development_and_Remote_Setup_20261025.md)はGEEKOM A6／Windows 11 Pro／Ryzen 7 6800H／32 GB RAM／1 TB SSD、OUEM Python 3.11.9、QGIS 4.2.3、GDAL 3.13.3、GIS Python 3.12.15、PDAL 2.10.0を観測記録している。旧受入のGIS Python 3.12.14とは別の環境である。観測値を新たな最低version規則としない。

- 通常terminalでOUEM `.venv/Scripts/python.exe`を使い、GIS Pythonと混在させない。
- OSGeo4W Shellで`plateau_komae_local_acceptance.cmd gis`を実行し、ignoredな`scripts/work/.runtime/plateau_komae_gis.json`を使う。snapshotは端末固有で、会社PCから移植しない。
- VoxCity 1.7.0 commit `fa212656305328a9a657973bae26f352bfe813bc`を変更しない。integration / preflightはpackage provenance、direct_url／RECORD等の検査を実装する。
- pyprojectの他依存は下限指定が中心で、完全lockではない。PC間のbyte同一性・性能は未確認。新runの環境情報を保存する。
- E-PCは公開元から新規取得し、会社PCのデータ転送は予定しないとしている。環境受入時にはreal-data ouem stageを未実行。環境の過去テスト結果は新PCのPoC受入ではない。
- OUEM repository自身の[LICENSE](../../LICENSE)は未選定で許諾なしと記録。VoxCityや入力datasetのlicenseは別問題。入力の利用条件をOUEMの方針から推論しない。

### 7.2 統合runnerが必要とする既存成果

`src/ouem/komae_integration.py::input_paths`およびWindows launcherから確認したもの：

| 入力 | 準備・確認点 |
|---|---|
| Native Buildingと`.manifest.json` | 3,637棟、正しいlayer・CRS・Z・source id。receiptが存在する場合はそれもinventory対象 |
| Native Terrain JSONと参照RAW TIFF | 絶対path・hash・metadata一致。PC移動でJSONだけコピーしても再現しない |
| reference Standard Buildingと`.manifest.json` | full 111棟の受入条件を満たすbaseline。containedでも最初から92棟だけに置換しない |
| study-area YAML | `komae_09LD3451`、EPSG:6677、400×300 mの矩形。DEM tile IDと3次メッシュを同一視しない |
| GIS snapshot／pyproject／src／A3 runner | 独立runtime・コード・pinを記録。snapshot内の環境変数・秘密情報をGitへ入れない |
| optional CHMとprovenance | 実hashに一致し、根拠付きHAG宣言。既存handoff JSONだけでは入力一式にならない |

integration runnerはNative→Standard→Adapterを独立2反復するが、CityGML取得／Converter／Native Building ingestを実行しない。A3単体CLIにはStandard TerrainとBuildingの両方およびadjacent manifestが必要。統合runnerはNative TerrainからrepeatごとのTerrainを生成する。

### 7.3 run・hash・レビューの扱い

新runは`data/work/integration/<fresh-run-id>/`へ隔離し、既存runを再開・上書きしない。入力byte hash、Building geometry/attribute意味digest、Terrain値／mask hash、配列hash、run環境・コマンド・log、repeat比較をrunnerが記録する。byte一致、意味一致、同じpath family、同じ件数は互いに同義ではない。

- 2026-10-05 A3は111棟・1 mのACCEPTEDだが、元入力hashは記録していない。
- 2026-10-18 `komae-contained-002`は92棟のレビューPASS。reportの`acceptance=PENDING_LOCAL_REVIEW`は未変更で、当該修復出力のQGIS目視未実施。
- 建物高さの約37 m差は研究記録で未確定。Native以降のZ保持はConverter以前の正しさを保証しない。
- 既存runへの属性追加等によるhash不一致はstrict診断をblockする。exploratory modeの比較一致で正式provenanceへ昇格させない。

これらは既存正式記録の差・制約として報告し、今回修正しない。

## 8. 正式Source Catalog / Acquisition Recipe / Dataset Manifestの設計候補

以下は**未承認の提案**であり、新たなStandard契約やschema、配置、必須fieldを確定するものではない。現行manifestを置換せず、既存手順を参照して重複を避ける候補である。

| 成果候補 | 役割とfield候補 | 既存証拠との関係・未決点 |
|---|---|---|
| Source Catalog | source_id、provider、dataset/release、layer、coverage、source CRS／vertical意味、提供URLと種類（案内／直接DL／根拠）、license URL・本文版・確認日・確認者・未確認状態 | メッシュ所属やStandard適合性を保証しない。利用条件変更と旧版保持方法は未決 |
| Acquisition Recipe | recipe_id/version、catalog参照、手動／任意自動、tile選択・archive解凍・必要layer、期待Raw配置、tools/version、GUI LOD・CRS／vertical操作、期待検査、失敗時停止条件 | `scripts/work/README.md`を手順の所有元として参照する候補。Converter記録粒度・OS差分は要検討 |
| Dataset Manifest | dataset_id/version、取得日・取得元release、実file一覧・size・SHA、範囲・CRS・vertical status/evidence、Raw retained/external/removed、親dataset、recipe、tool環境、Native/Standard/QA artifact参照、制約 | 既存Native／Standard／Adapter manifestへの外側の索引候補。既存のschemaや受入fieldを書換えない。path可搬性・安定ID・署名等は未決 |
| Run Log（別管理） | run_id、dataset manifest参照、code commit、環境pin検査、command、開始／終了／exit、artifact hash、qualityとreproducibility、レビュー記録参照 | provenanceとrunを分離するv0.2 §6に対応。既存integration-reportを再利用する粒度は要検討 |

候補の関係は「Catalogで公開元を記述→Recipeで取得・前処理方法を記述→Dataset Manifestで実際に取得したbytesを同定→Run Logで処理を記録」。Catalogのlicense確認とDatasetのQA、文書登録とデータ受入を独立させる。未確認の値は空欄で隠さず未確認と根拠不足を記載する案である。

## 9. GEEKOM A6再実行の前提・不足・確認事項

| 順序 | 前提／不足・確認事項 | 次の判断に必要な証拠 |
|---|---|---|
| P0：取得前 | PLATEAU年度・archive・DL URL・license、Tokyo tile直リンク／選択・licenseを特定。CHMは後段別扱い | 各providerの元ページ・利用条件・取得時点・版。今のリポジトリだけでは完全な再取得recipeを確定できない |
| P0：元入力準備 | CityGMLと09LD3451 DEM、元archive・全tile・hash。現PCにあるかは未確認 | 新規取得file inventory、Raw保存、A2 source hashとの比較。会社PCからのデータ移送は前提にしない |
| P0：Converter | GUI版、maximum LOD、3D保持、CRS／vertical操作、id／feature countを記録 | 対応する元CityGML全ZとConverter Z、代表建物の比較。高さ原因未確定なら解析妥当性を保留 |
| P0：実行環境 | E-PCとruntime境界を再確認。snapshotをPC固有で用意 | `.venv`、GIS子runtime、pin provenance、依存整合、ローカルtool版本。今回検査していない |
| P0：baseline生成・検査 | manual/gis/ouem/standardとTerrain手順に従い、Native/Standardとmanifestを用意する計画 | 3,637→111、grid／Z／metadata／hash、QGIS位置・形状・地盤／屋根。既存受入の自動継承なし |
| P0：preflight | `preflight_komae.cmd`はfull111参照・固定run-dir例。既存run-dirなら別名をmodule引数で指定する計画 | PASSは前提確認のみ。contained用の92選択・CHM完全性まで合格したとはしない。コード`--contained-poc`はrun限定 |
| P0：個人PC新run | full111とcontained92の目的を区別。`run_komae_contained_e2e.cmd <fresh-run-id>`は92/19固定 | 新reportと2反復比較、geometry repair診断、QGISレビュー、既存baselineとの差と新規受入判断。所要時間／RAM未確認 |
| P1：canopy | 元Meta CHM、実hash付きHAG根拠、coverage・NoData、下端モデル妥当性、licenseが不足／未確認 | opt-in別run、Current/No-Canopy、2D/3Dレビュー。AUTOMATED_PASSだけで精度・formal acceptanceとしない |
| P1：B1/B2 | 気象／時間条件、透過、視点／ray、比較対象、評価方法が具体化されていない | v0.1継承詳細とv0.2に整合する別の実装・検証計画。shade/GVIの受入宣言を先行させない |

この文書は再実行準備の不足を列挙するもので、実データ実行手順の承認・新契約の確定・受入範囲の拡張ではない。今回変更するのは本書と実装インベントリの2文書のみである。
