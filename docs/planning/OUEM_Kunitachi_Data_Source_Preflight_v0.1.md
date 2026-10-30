# 国立市 Data Source Preflight v0.1

調査日: **2026-10-30 JST**。基準main:
`2295ce7051748e83c31577bf8ee19f26fc14202f`（PR #131 merged）。
状態: **実データ取得・読取診断までの探索的事前確認**。
Native登録、Converter、Standard生成、Height Envelope生成、VoxCity、GIS子処理・GUIは未実施。
既存設定・コード・Standard契約・狛江成果物・Acceptance・Technical E2E・Backlogは変更しない。

## 1. 結論と固定Study Area

[kunitachi_2km.yaml](../../config/study_areas/kunitachi_2km.yaml)を変更せず使用。
EPSG:6677、`[-36000,-34700,-34000,-32700]`、2,000×2,000m、4,000,000m²。
XYはeasting/northing。4326外接範囲は
`[139.4354989742,35.6865753994,139.4576849947,35.7046733794]`。
これは行政界・データ被覆・解析用contextを含む範囲と同義ではない。

| ソース | 実確認 | 2km全体についての判定 |
|---|---|---|
| 国立市PLATEAU 2025 / 製品仕様5.0 | API候補9メッシュ、LOD2掲載2ファイルを取得。既存Raw readerで299+8棟のLOD2を確認し、307棟すべてAOIと交差 | **全域LOD2利用準備は未成立**。残る7候補はAPI上LOD2=0。隣接市・全建物のLOD2充足は未確認 |
| 東京都多摩0.50m ground DEM | 公式配信索引から特定した35実交差タイル。AOIの16,000,000セルを重複なく被覆、全セル有効 | **ラスタの被覆・構造は確認**。35タイルのままで既存単一TIFFの下流処理へ渡せるわけではない |
| Meta/WRI CHMv2 | 既存取得CLIが1タイルを取得・crop。AOI中心判定4,261,587セルが全数有効、0mも有効値 | **ラスタの被覆は確認**。HAGの出典宣言は確認したが、実樹冠存在・DEMとの地盤整合・Standard Canopy受入ではない |

**推奨は2km設定を維持し、建物の対象自治体・LoD方針を先に決めること。**
2kmの全域LOD2を前提としたSource-H本処理へはまだ進めない。
公式関連データの国立市行政界との面積交差は約66.31%、約33.69%が市外である。
国立市2025だけでは市外の建物まで調べたことにならない。

## 2. 取得元・版・利用条件

すべて匿名公開元を使用。取得時の本文・メタデータ・hash・URLはローカルに保持。
Webツールで一部API/ページを取得できず、通常terminalのDNSも失敗したため、
承認されたネットワーク実行で公式URLへアクセスした。TLS検証を無効化していない。

| ID | 一次出典 / 実際の確認内容 |
|---|---|
| P1 | [国立市2025 CKAN API](https://www.geospatial.jp/ckan/api/3/action/package_show?id=plateau-13215-kunitachi-shi-2025): 市コード13215、製品仕様5.0、CityGML v5リソース、license_id=`plateau` |
| P2 | [PLATEAU BuildingファイルAPI](https://api.plateauview.mlit.go.jp/datacatalog/citygml/13215?types=bldg): year=2025、spec=5.0、17ファイル、各mesh/LoD件数・直接URL・メタデータZIP |
| P3 | [PLATEAU利用条件](https://www.mlit.go.jp/plateau/site-policy/): 現行§3はPDL1.0準拠、出典・加工明示、CC BY 4.0互換の説明。個別権利表示・測量法等の留保を含む。契約の無条件な利用許可を新たに判断していない |
| P4 | [座標・高さの公式説明](https://www.mlit.go.jp/plateau/learning/tpc03-4/)、取得metadata XMLの`JGD2011, TP / (B, L), H`: 標高と地盤相対高さを区別する根拠 |
| T1 | [東京都公式catalogue API](https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_show?id=t000029d0000000020): CC-BY-4.0、JGD2011/平面直角IX系、標高=東京湾平均海面という提供元宣言。HTMLページは403、APIは200 |
| T2 | [多摩CKAN API](https://www.geospatial.jp/ckan/api/3/action/package_show?id=tokyopc-tama-2023): ground由来0.50m標高GeoTIFF、配信索引PBFと索引PDF ZIP。0.25m参考データやDSMとは別 |
| T3 | [東京都配信利用規約](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/doc/license.pdf): 免責・禁止行為等を確認。今回の対象限定取得を無制限の一括取得の許可と解釈しない |
| C1 | [Meta/WRI CHMv2 AWS registry](https://registry.opendata.aws/dataforgood-fb-forestsv2/): release prefix `forests/v2/global/dinov3_global_chm_v2_ml3/`、CC BY 4.0、機械学習推定データ、引用案内 |
| C2 | [提供者の探索notebook](https://github.com/facebookresearch/dinov3/blob/main/notebooks/chmv2_dataset_exploration.ipynb): 各バンドを地上から樹冠上端までの高さmと説明。notebookは本文を保存しただけで実行していない |

PLATEAUの「v5」は製品仕様版でありOGC CityGML 5という意味ではない。
実読取ファイルは既存readerが要求するCityGML 2 / 明示6697の構造を通過した。
東京都は2023配信prefixを使用したが、個別計測日・その後の標高改定適用は未確認。
CHMv2の画像日・モデル重みrevision・地上精度も未確認。
Last-Modifiedや年度ラベルを測量・撮影日と同一視しない。

## 3. PLATEAU実ファイル確認

### 選択と取得量

P2に掲載された第三次メッシュ矩形をXY変換してAOIとの候補交差を調べた。
メッシュは候補選択にのみ使用し、実建物の有無・survey coverageには置き換えない。

| 候補mesh | APIの建物数 | API LOD2 | 実ファイル確認 |
|---|---:|---:|---|
| 53394324 | 2,546 | 0 | 未取得 |
| 53394325 | 2,614 | 0 | 未取得 |
| 53394326 | 3,367 | 0 | 未取得 |
| 53394334 | 4,060 | 0 | 未取得 |
| 53394335 | 2,728 | 299 | 取得、Raw readerで299、うちAOI交差299 |
| 53394336 | 3,837 | 0 | 未取得 |
| 53394344 | 2,431 | 0 | 未取得 |
| 53394345 | 3,141 | 8 | 取得、Raw readerで8、うちAOI交差8 |
| 53394346 | 3,836 | 0 | 未取得 |

直接配信のベースURLは
`https://assets.cms.plateau.reearth.io/assets/0a/a234cd-ac3a-4b53-aedc-3beebe457341/13215_kunitachi-shi_pref_2025_citygml_1_op/udx/bldg/`。
取得ファイル名は`53394335_bldg_6697_op.gml`と`53394345_bldg_6697_op.gml`。
それぞれ**43,330,011 / 41,402,459 bytes**。
小さなmetadata ZIP **20,920 bytes**も取得し、source metadata XMLを確認した。

全ZIPの[P2掲載URL](https://assets.cms.plateau.reearth.io/assets/0a/a234cd-ac3a-4b53-aedc-3beebe457341/13215_kunitachi-shi_pref_2025_citygml_1_op.zip)は
HEAD **210,698,074 bytes**。候補9件のAPI fileSize合計378,160,849 bytesに対し、
LOD2掲載2件だけなら約85MBなので、全ZIPと残るLoD1ファイルは取得しなかった。
取得前の空き容量は約840GiBを確認した。容量不足ではなく必要性により選択取得とした。
CKAN掲載の別asset URLとP2のassetを同じbytesと仮定していない。
実GMLサイズはAPI fileSizeから+118 / -126 bytes異なる。API値は完全性hashではなく、
今回取得物自身のhashを使用した。全ZIP内メンバーとのbyte一致・CRCは未確認。

### Raw検証と互換性

既存[read_lod2](../../src/ouem/native/building/source_h_lod2.py)でファイルを読み、
6697、明示3D、有限座標、リング、対応LoD2表現・内部参照等の既存制約を検査した。
LoD2無しの除外数は2,429 / 3,133。この数は2ファイル全体の値でありAOI全体の欠損率ではない。
全2ファイル以外のCityGML構造、隣接市のファイル、全建物分母は実検証していない。

AOI判定は既存Source-Hの`map_xy` / `intersects`を使用し、
**6668→6677の水平2引数変換のみ**を行った。Hを変換・加減算・DEM吸着していない。
307棟の全頂点外接範囲は概ね
`[-35255.095,-33645.132,-34714.463,-33138.732]`で、約541×506mに集中する。
この矩形内のすべての建物がLOD2という意味ではない。

Raw profile検査の成功はConverter出力との対応確認ではない。
Source-H Nativeには実Converter GPKG・固定binary・plan・hash chainが別途必要。
既存`real_komae_source_h`は狛江2メンバー固定なので、国立GMLへそのまま置換できない。
旧Building経路も6697のRawを4979へラベル変更して取り込む経路ではない。
Native／Standard互換は**Raw段階で有望、全工程未検証**とする。

## 4. 東京都DEM実確認

公式PBFテンプレートは
`https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/Vectortile/tama/grd50/{z}/{x}/{y}.pbf`。
AOIに重なるz14の`14537/6450`, `14537/6451`, `14538/6450`, `14538/6451`を取得。
GDAL MVT reader（既存Pyogrio）でEPSG:3857の索引を読み、6677へ変換した。
属性`MESH_NO`と`URL`から実配信先を得ており、狛江`09LD3451`は使っていない。
PDF索引ZIP14,585,621 bytesも保持したが、タイル選択の根拠は空間参照付きPBFである。

MVTの量子化境界を考慮してAOI+2mに触れる候補56タイルを取得し、実TIFFの
正面積交差で35タイルに絞って集計した。残る21は境界接触/周辺で、集計から除外。
ZIP合計**48,307,908 bytes**。各ZIPの指定名TIFFだけを読み、CRC・サイズ上限を確認した。
ZIP/展開TIFFの各hashはdownload receiptsに保持。

AOI実交差の35タイル:

```text
09LD0190 09LD0191 09LD0192 09LD0193 09LD0194
09LD1100 09LD1101 09LD1102 09LD1103 09LD1104
09LD1110 09LD1111 09LD1112 09LD1113 09LD1114
09LD1120 09LD1121 09LD1122 09LD1123 09LD1124
09LD1130 09LD1131 09LD1132 09LD1133 09LD1134
09LD1140 09LD1141 09LD1142 09LD1143 09LD1144
09LD1150 09LD1151 09LD1152 09LD1153 09LD1154
```

配信先は各索引の`URL`、形式は
`https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/<tile>.zip`。
全35件で既存[inspect_dem](../../src/ouem/native/terrain/__init__.py)を実行。
EPSG:6677、800×600、0.5m、Float32、単バンドnorth-up、有限NoData
`1.701410009187828e38`、scale=1/offset=0を確認した。

AOIの**4,000×4,000=16,000,000セル**をnative grid上で集計し、被覆・有効とも100%。
NoData/未被覆0、重複被覆0。地盤の真値精度を確認した値ではない。
T1の高さは提供元宣言のT.P.で、水平EPSGから推測していない。
PLATEAUのTP宣言と名称が整合しても、測量epoch・基準改定・実現精度の一致は未検証。

個々のTIFFは現行Terrain Native/Standardの構造条件に適合する。
ただし既存取得CLIは狛江1タイルhash固定で使えず、今回は変更していない。
現行Standardizerはモザイクを作らず、Native登録やStandard化も実行していない。
2kmの単一地盤入力を作るには、値・格子・maskを保持する別の準備手順とprovenanceが必要。

## 5. Meta CHMv2実確認

既存[acquire.meta_chmv2](../../src/ouem/acquire/meta_chmv2.py)を変更せず実行:

```powershell
.venv/Scripts/python.exe -m ouem.acquire.meta_chmv2 `
  --study-area config/study_areas/kunitachi_2km.yaml `
  --raw-dir data/raw/canopy/meta_chmv2/kunitachi-20261030-01 `
  --work-dir data/work/kunitachi-source-preflight/20261030-01/chm `
  --max-tile-bytes 1073741824 --max-pixels 16000000
```

索引から選ばれた実タイルは**1330021122**。
元URLは`https://dataforgood-fb-data.s3.amazonaws.com/forests/v2/global/dinov3_global_chm_v2_ml3/chm/1330021122.tif`。
元COG **164,037,271 bytes**、索引58,856,501 bytes。17:35:11–17:45:28 JST、約617秒。
`COMPLETED`、`committed_code_identity_verified=true`、基準mainでの実行を記録。
転送待ちの診断でHEAD 200と先頭64KiBのRange 206も確認したが、全量の重複取得はしていない。

cropは**2,069列×2,078行、367,938 bytes、uint8、単バンド、EPSG:3857**。
元格子の約1.194328566956m/pixelを保持し、再投影・再サンプルしていない。
Web Mercator上の間隔は地上の等距離1m格子とは異なる。
scale=1/offset=0、unit tag=None、NoData tag=None、元maskを保持。
数値の意味はC2のHAG m宣言から判断し、タグ無しや0から推測していない。

AOIの辺を6677で25mごとに細分して3857へ変換し、cropの**セル中心がAOI内**かを判定。
外接crop全体をAOI統計の分母にしていない。

| AOI内native-centre集計 | 実測値 |
|---|---:|
| セル数 / 有効数 | 4,261,587 / 4,261,587 |
| mask欠損・非有限・負値 | 0 |
| 有効0m | 3,697,230（86.7571%） |
| 有効正値 | 564,357 |
| 最小 / 最大 | 0 / 24m |
| 平均 / 中央値 | 0.8537443915 / 0m |
| P05 / P95 | 0 / 7m |

有効0mは欠損ではなく、現地の樹冠不存在を独立に保証する値でもない。
画素の単純統計であり、投影歪み補正後の面積加重平均・測定された緑被率ではない。
CHM中心を6677に戻して0.5m DEMの所属セルを調べると、全4,261,587中心でDEMも有効。
高さ同士の加算・比較による鉛直基準の認定は行っていない。

現行Height Envelopeには、別途CHM意味のhash-bound evidence bridge・snapshot・
review、生成したStandard Terrainとmanifest、対象hashを明記した受入証拠が必要。
今回それらを架空作成しておらず、35 Raw DEMとcropだけでは生成条件は満たさない。
1mの2kmGridSpecは数値上4百万セルでPoC上限内だが、生成成功・全体性能は未検証。
**CHMv2 cropから直接Standard Canopyを生成できるとは扱わない。**

## 6. 重複・被覆図・AOI推奨

DEMはnative 0.5m格子で全面有効、CHMはnative中心判定で全面有効。
両方に共通して有効なCHM中心は4,261,587点。これが連続面・全将来格子での
同一被覆を数学的に保証するわけではない。307棟のLOD2位置はこのAOI内にある。
建物投影の面積を地域のデータ被覆率と見なさず、全建物LOD2率は未確認とする。

公式関連データ約18KBの行政界GeoJSONは**MultiLineString**であった。
既存shapeを6677へ変換し、snap/repairなしのpolygonizeで閉じた有効polygon 1件を得た。
AOI内面積2,652,433.59m²、市外1,347,566.41m²（33.6892%）。
国分寺市等の隣接市データは調べていないため、市外を「建物無し」と扱わない。

ローカル`coverage.geojson`はEPSG:6677、347 feature。
AOI、DEM tile矩形35件、307棟の**全頂点XY外接矩形**、LOD2全体外接矩形、
DEM/CHMのAOI支持範囲、行政界と市外部分を`kind`で区別できる。
建物外接矩形は正式footprint・建物網羅範囲ではない。
QGISへ通常のベクタとして読み込み、`kind`による分類表示が可能。
GeoJSONの再読取/CRS/feature数を確認したが、QGIS GUI表示は未検証。

選択肢は次のとおり。**設定は一切変更していない。**

1. 推奨: 2kmをデータ事前確認の基準として維持し、隣接市調査とLOD1/LOD2混在の
   許容をユーザーが判断する。LoD1 fallbackは現行Source-H profileの無断拡張になるため実装しない。
2. LOD2限定の小域試験なら候補矩形`[-35300,-33700,-34700,-33100]`（600m四方）を
   別途検討可能。ただし307棟の外接範囲を含むだけで、その内側のLOD2完全性は未確認。
   context/周辺遮蔽物の充足を保証しない。単純なAOI縮小だけで合格にはしない。

## 7. 来歴・保存先・未確認事項

以下はすべてGit除外領域。初回取得・失敗調査・再読取で既存狛江Runを使用/上書きしていない。

| ローカル保存先（repository相対） | 内容 |
|---|---|
| `data/work/kunitachi-source-preflight/20261030-01/` | API/出典snapshot、HEAD/取得receipts、索引PBF/PDF、各summary JSON、被覆GeoJSON |
| `data/raw/building/plateau_kunitachi/preflight-20261030-01/` | GML2件・metadata ZIP・download-receipts.json |
| `data/raw/terrain/tokyo_tama_dem_050m/kunitachi-preflight-20261030-01/` | 索引で選んだ56 ZIP/TIFFと各URL・hash・取得日時のdownload-receipts.json |
| `data/raw/canopy/meta_chmv2/kunitachi-20261030-01/` | 索引・元COG。今回国立用の新規取得 |
| work内`chm/` | 実cropとacquisition-record.json |

主要SHA-256:

| 対象 | SHA-256 |
|---|---|
| Study Area実作業コピー（開始/終了で不変） | `f10f7b8c7b875bcf583f145482fb27a4461593cac76860f1cac2905f630a806a` |
| PLATEAU API snapshot | `c1853b3abf29d66a28569418bac1f3bb1a624f4af8eefbbfd3605369d2836ab4` |
| 53394335 GML | `a8c291eb410b893861e978b20e2b85b64827a02c884e097801d6b4cda255e4b7` |
| 53394345 GML | `0fe3225e9bb275b84c2b8fae6713c4e19a5ef93b72770a2b73b5f541d20a04b6` |
| DEM56件receipts JSON | `047d6844f76d2b086f04379c81d5823e606ffefaf93b9d8e25b22a455819f381` |
| CHMv2元COG | `a82d9ad5b7fc7b6a96725c7e7e1f2497fb1e10999a31e8056aa68ba3e05f7d9d` |
| CHMv2 crop | `2355b33f4d14a728620ac7b9543c44cf85f0c7039c4efb6c426a61207d66982a` |
| CHMv2 acquisition record | `ddea23791505db046e42ef016d2759de308563e7ab7a15027b24f36f1dc9b4de` |
| coverage.geojson | `1349822fd64a5989821092c325545328bd744b65128c528fd2cfd6cc43db9a5e` |

DEM各タイルの個別hash/URLは上記receiptで追える。供給元を今回取得時点で固定する
記録であり、将来の同一URLが同一bytesとは保証しない。期限付きリダイレクトURLのqueryは
HEAD記録から除外し、公式の安定した入口URLを使用する。

検証環境: ordinary Windows OUEM venv Python3.11.9、NumPy2.4.6、Rasterio1.4.4、
GeoPandas1.2.0、Shapely2.2.0、PyProj3.7.2、Pyogrio0.13.0。
PDFの読取だけは既存bundled pypdfを使用し、OUEM/GIS環境へ導入していない。

失敗・訂正・限界:

- 通常環境のDNS失敗、Web/APIの一部403、PDF抽出exe不在、ZIP名表示のcp932エラーがあった。
  APIの別の公式入口、既存PDF読取環境、ASCII表示で確認し、資料取得と診断は完了した。
- 行政界を面だと思った初回診断は交差面積0を出したが、線だったため無効。
  `border-line-first-attempt.json`を保持し、閉じた線のpolygonizeによる値に訂正した。
- 初期の建物面投影は中庭・垂直面の退化を十分扱わないので面積やfootprintを採用しなかった。
  最終AOI判定は既存Source-H関数、表示は全頂点外接矩形を使用。Raw座標・H・リングは変更していない。
- 一時的な部分取得ファイルのサイズは通常sandboxと取得実環境で表示差があった。
  完了は実環境・moduleの最終record・最終bytes/hashで確認し、途中の表示を失敗扱いしていない。
- 新たな測量真値、全建物分母、他市LOD2、Converter/Native/Standard出力、QGIS GUI、
  2024以降の標高基準整合、科学的妥当性・Formal Acceptanceは未確認。

## 8. 関連テストと次工程

以下の既存テストをOUEM venvで実行:

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_study_area.py tests/test_standard_terrain.py tests/test_source_h_xlink.py tests/test_source_h_ingestion.py tests/test_meta_chmv2_acquisition.py tests/test_tokyo_tama_dem_acquisition.py tests/test_height_envelope.py
```

**169 passed、123 warnings、263.48秒、失敗/skip 0**。
警告はRasterio/AffineのPendingDeprecationWarning。テスト内合成fixtureの検証であり、
国立市のStandard/Envelopeを生成した結果ではない。
新規本番コード・補助モジュールを追加せず、本報告と再読取用レシピのみとしたため、
全体pytestは再実行しない。既存設定・コードの不変性、相対リンクと`git diff --check`を確認。

次工程は(1)対象自治体/LoD方針の判断、(2)Source-Hの対象メンバー設定の別PR、
(3)DEMの値・grid/mask・来歴を保つ準備設計、(4)実際のStandard Terrain証拠と
CHM/DEM compatibility reviewを揃えてからEnvelope移行を別途判断する順が妥当。
現行[一般化監査](OUEM_Data_Pipeline_Generalization_Audit_v0.1.md)と
[B1](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md) /
[B2](../status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md)の境界を維持する。

## 9. 被覆判定の再現レシピ

取得は上記CLIと各receiptの公式URL・実hashを参照し、再試行は新規directoryへ行う。
既存local bytesがある場合、次のPythonをrepository rootのOUEM venvで実行すると
主要被覆数・LOD2数をネットワークなしで再計算できる。再取得時は今回のhashと比較し、
異なる版を黙って同一結果にしない。sourceを変更しない読取診断である。

```python
from pathlib import Path
import hashlib
import json
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds
from pyproj import Transformer
from shapely import segmentize
from shapely.geometry import box, mapping
from shapely.ops import transform, polygonize, unary_union
import geopandas as gpd
from ouem.study_area import load_study_area
from ouem.native.terrain import inspect_dem
from ouem.native.building.source_h_lod2 import read_lod2
from ouem.standardize.building.source_h_geometry import map_xy, intersects

work = Path('data/work/kunitachi-source-preflight/20261030-01')
dem_root = Path('data/raw/terrain/tokyo_tama_dem_050m/kunitachi-preflight-20261030-01')
bldg_root = Path('data/raw/building/plateau_kunitachi/preflight-20261030-01')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
area = load_study_area('config/study_areas/kunitachi_2km.yaml')
assert area.epsg == 6677
x0, y0, x1, y1 = area.extent
aoi = box(*area.extent)
cover = np.zeros((round((y1-y0)/.5), round((x1-x0)/.5)), dtype='uint8')
valid = np.zeros_like(cover)
selected = []
for receipt in json.loads((dem_root/'download-receipts.json').read_text()):
    path = Path(receipt['path'])
    assert sha(path) == receipt['sha256']
    with rasterio.open(path) as src:
        overlap = box(*src.bounds).intersection(aoi)
        if overlap.area <= 0:
            continue
        metadata = inspect_dem(path)
        assert metadata['horizontal_crs'] == 'EPSG:6677'
        assert metadata['dtype'] == 'float32' and src.res == (.5, .5)
        assert src.scales == (1.0,) and src.offsets == (0.0,)
        win = from_bounds(*overlap.bounds, src.transform).round_offsets().round_lengths()
        data = src.read(1, window=win, masked=True)
        good = ~np.ma.getmaskarray(data) & np.isfinite(data.data)
        left, bottom, right, top = overlap.bounds
        row, col = round((y1-top)/.5), round((left-x0)/.5)
        slot = np.s_[row:row+data.shape[0], col:col+data.shape[1]]
        cover[slot] += 1
        valid[slot] += good
        selected.append(path.stem)
print('DEM', len(selected), int((cover > 0).sum()),
      int((valid > 0).sum()), 'duplicates', int((cover > 1).sum()))

acq = json.loads((work/'chm/acquisition-record.json').read_text())
crop = work/'chm/chmv2_aoi.tif'
assert acq['status'] == 'COMPLETED' and sha(crop) == acq['output']['sha256']
with rasterio.open(crop) as src:
    forward = Transformer.from_crs(6677, src.crs, always_xy=True)
    backward = Transformer.from_crs(src.crs, 6677, always_xy=True)
    polygon = transform(forward.transform, segmentize(aoi, 25))
    inside = geometry_mask([mapping(polygon)], src.shape, src.transform,
                           invert=True, all_touched=False)
    data = src.read(1, masked=True)
    good = inside & ~np.ma.getmaskarray(data) & np.isfinite(data.data) & (data.data >= 0)
    values = data.data[good]
    rows, cols = np.nonzero(inside)
    xs, ys = rasterio.transform.xy(src.transform, rows, cols)
    xs, ys = backward.transform(xs, ys)
    rr = np.floor((y1-np.asarray(ys))/.5).astype(int)
    cc = np.floor((np.asarray(xs)-x0)/.5).astype(int)
    supported = (rr >= 0) & (rr < valid.shape[0]) & (cc >= 0) & (cc < valid.shape[1])
    dem_good = np.zeros(len(rows), dtype=bool)
    dem_good[supported] = valid[rr[supported], cc[supported]] > 0
    print('CHM', int(inside.sum()), int(good.sum()), 'zero', int((values == 0).sum()),
          'min/max/mean/median', values.min(), values.max(), values.mean(), np.median(values))
    print('common DEM/CHM centres', int((dem_good & good[rows, cols]).sum()))

for receipt in json.loads((bldg_root/'download-receipts.json').read_text()):
    assert sha(receipt['path']) == receipt['sha256']
xy = Transformer.from_crs(6668, 6677, always_xy=True)
for path in sorted(bldg_root.glob('*.gml')):
    buildings, excluded = read_lod2([path])
    count = 0
    for faces in buildings.values():
        tree = ('GeometryCollection', tuple(('Polygon', face) for face in faces))
        count += bool(intersects(map_xy(tree, xy.transform), area.extent))
    print('LOD2', path.name, len(buildings), 'no-LOD2', len(excluded), 'AOI', count)
lines = unary_union(gpd.read_file(work/'municipality-border.geojson').to_crs(6677).geometry)
polygons = list(polygonize(lines))
assert len(polygons) == 1 and polygons[0].is_valid
print('AOI outside municipality m2', aoi.difference(polygons[0]).area)
```

今回このレシピをローカル再実行し、DEM 35 / 16,000,000有効、CHM 4,261,587有効、
共通中心4,261,587、LOD2 299+8、市外1,347,566.41m²を再確認した。
Shapely `ops.transform` のDeprecationWarningが出るが、依存・既存コードは変更していない。
