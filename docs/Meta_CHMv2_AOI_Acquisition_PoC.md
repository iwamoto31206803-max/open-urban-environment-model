# Meta/WRI CHMv2 AOI取得PoC

本実装は[Concept v0.2](OUEM_Concept_Architecture_v0.2.md)と[C-01設計案](planning/OUEM_Source_Catalog_and_Acquisition_Recipes_v0.1_Draft.md)のうち、索引によるタイル選択、元COGの保持、モザイク・AOI切出しに限定する。Native／Standard Canopy契約や樹冠存在判定、CR推定、絶対Z化、engine接続、B1/B2は含まない。既存Building／Terrain／Adapter契約・受入記録を変更しない。

## Windows実行方法

[個人PC環境記録](development/OUEM_Windows_Development_and_Remote_Setup_20261025.md)に従い、リポジトリルートの通常PowerShellからOUEM venvを使う。OSGeo4W Shellから起動しない。新規依存・AWS資格情報は不要で、既存のRasterio・Shapely・NumPyと標準ライブラリを使う。

```powershell
.venv\Scripts\python.exe -m ouem.acquire.meta_chmv2 `
  --study-area config/study_areas/komae_09LD3451.yaml `
  --raw-dir data/raw/canopy/meta_chmv2/komae-run-001 `
  --work-dir data/work/meta_chmv2/komae-run-001
```

RawとWorkは別の**未使用ディレクトリ**を指定する。既存の内容を上書き・再開しない。索引約59 MBと、選択した元COG全体（狛江で確認した1件は約69 MB）を匿名HTTPSで取得する。COGのAOI範囲だけをRawと称して保存する方式ではない。

出力：

- Raw：`tiles.geojson`と選択した`<quadkey>.tif`のみ。
- Work：`chmv2_aoi.tif`、`acquisition-record.json`。GeoTIFFは切出し成果で、COG出力であることは要求しない。
- 失敗時は非0終了、recordの`status=FAILED`。途中のRaw／`.part`と、検証に失敗した`.unverified.tif`は診断用に残り、成功出力として登録しない。元入力や既存証拠を削除して再利用せず、調査後の再試行は新しいディレクトリで行う。

`--max-tile-bytes`は1タイルの取得上限（既定1 GiB）、`--max-pixels`は切出し出力上限（既定16,000,000画素）。索引上限は128 MiB。巨大なAOIはこの最小PoCの対象外で、COG全体のダウンロード時間・ディスク容量と出力メモリを事前に確認する。

## 索引・画素の処理方針

1. 既存`load_study_area`で矩形YAMLを読む。WGS84へ辺をdensifyして変換した外接範囲と、実索引のPolygon/MultiPolygonが正面積で交差するタイルだけを選ぶ。`properties.tile`をzoom-10 quadkeyとして検証する。架空の計算quadkeyへfallbackしない。任意ポリゴンAOIやBuffer指定は今回対象外。
2. 索引にAOI外接範囲の被覆がない場合は停止。元タイルの実CRS、単バンド、north-up、COG layout、dtype、NoData、scale/offset、units、元格子の一致を検査する。不一致は黙って変換しない。
3. 出力は**EPSG:3857の元格子を保持**し、変換後AOI外接範囲を外側の画素境界へsnapして切り出す。出力端はAOIより最大約1画素外へ広がる。元画素のコピーだけを行い、再投影・再サンプル・値の正規化・閾値処理はしない。
4. NoDataタグがない場合も内部マスクを保持し、0を欠損と仮定しない。NoDataが数値・NaNの場合も値とmaskを保持する。重複タイルで値／maskが食い違う場合、または実ラスタがsnap後範囲を覆わない場合は停止し、優先順位・穴埋めを追加しない。
5. 同じWorkディレクトリの一時`.unverified.tif`へ書込み、writerを閉じてから再読込する。値・maskと、CRS・transform・寸法・band数・dtype・NoData・scale/offset・unitsを検証する。readerと元COGのhandleも閉じた後、同一filesystem内のハードリンクで最終名を原子的に作成する。既存最終名は置換せず、ハードリンク非対応filesystemは停止する（WindowsではNTFSで検証）。検証失敗時に最終GeoTIFFを公開しない。途中ファイルはFAILED recordの`unverified_artifacts`に列挙し、`output`には登録しない。検証成功後の一時名削除だけが失敗した場合は、成功した出力を維持し`temporary_cleanup_pending`を記録する。SHAは元配布物と確定した出力それぞれに付け、maskはTIFF内部へ保存する。

これは取得・画素保持の検査であり、推定樹高の精度、樹冠存在、鉛直基準、下端モデルの妥当性や正式受入のPASSではない。

## 来歴とオフライン再現

`acquisition-record.json`はPoC専用の実行記録であり、設計ドラフトの正式Catalog／Recipe／Dataset Manifest共通schemaを確定しない。取得物の台帳（index / tiles）と処理（aoi / parameters / output / status）を区別して記載する。複数タイルと出力間の対応を追えるようにする。

- index / tile：URL、取得開始／完了日時、HTTP ETag・Last-Modified、保持パス・サイズ・SHA-256。
- tile / output：CRS、サイズ、dtype、解像度、transform・bounds、NoData、scale/offset、units、mask flags、image structure、tags。
- run：study-areaファイルhash、元AOI・変換後bounds、選択quadkey、処理内容、環境、code revisionと実行モジュールhash、開始／終了時のGit HEAD・作業ツリー状態・HEAD内moduleのSHA-256とのbyte一致、状態・開始／終了・失敗理由。
- source：registry URL・配布prefix・releaseラベルを記録。モデル重みrevision、個別画像撮影日は未確認のnull。object Last-Modifiedを撮影日やモデル版と同一視しない。
- SHAはファイル同一性であり、ライセンスや樹高の意味を単独で証明しない。記録に秘密情報／AWS credentialは不要。

保存済み索引・元COGでネットワークなしの再実行ができる。元取得recordは別途保持する。

```powershell
.venv\Scripts\python.exe -m ouem.acquire.meta_chmv2 `
  --study-area config/study_areas/komae_09LD3451.yaml `
  --index data/raw/canopy/meta_chmv2/komae-run-001/tiles.geojson `
  --tiles-dir data/raw/canopy/meta_chmv2/komae-run-001 `
  --raw-dir data/raw/canopy/meta_chmv2/komae-offline-002 `
  --work-dir data/work/meta_chmv2/komae-offline-002
```

ローカル再入力は`method=local_copy`、`acquired_at=null`とし、保持時刻・コピー元を記録する。外部ダウンロード成功として扱わない。`--index`だけなら索引はローカル、COGはHTTPS取得となる。recordは既存`komae_canopy.validate_provenance`用JSONの代替ではなく、既存Canopyへの自動投入やprovenance自動作成は行わない。

## 配布仕様の実アクセス確認（2026-10-25）

[公式AWSレジストリ](https://registry.opendata.aws/dataforgood-fb-forestsv2/)に、prefix `s3://dataforgood-fb-data/forests/v2/global/dinov3_global_chm_v2_ml3/`、匿名アクセス、CC BY 4.0へのlicense参照と引用例が掲載されている。参照：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。個別画像撮影日・モデル重みrevision・推定精度の独立検証は未実施。

参考：[rslearn実装資料](https://allenai.github.io/rslearn/reference/data_sources/meta_canopy_height/)。ただし索引の属性名とNoDataは推測せず、下記の実アクセスで確認した。

| 確認対象 | 実アクセスで観測した内容 |
|---|---|
| 索引 | `https://dataforgood-fb-data.s3.amazonaws.com/forests/v2/global/dinov3_global_chm_v2_ml3/tiles.geojson`、HTTP 200、58,856,501 bytes、213,109 features、GeoJSON crs指定なし、属性`tile` |
| 索引SHA-256 | `3f3d102d4a4d2d221125744c9c081b2420ce1cf1322e08c568ebf48678e84c2e` |
| 狛江選択 | 既存YAMLから`1330021123`の1件 |
| COG URL | `https://dataforgood-fb-data.s3.amazonaws.com/forests/v2/global/dinov3_global_chm_v2_ml3/chm/1330021123.tif`。HEAD HTTP 200、68,699,950 bytes、Last-Modified 2026-01-14 |
| Rangeメタデータ | EPSG:3857、32,768×32,768、1 band、uint8、解像度約1.1943285669559 m、COG・DEFLATE、scale=1、offset=0、unitsなし |
| 欠損 | NoDataタグは未設定（None）、per_dataset内部マスク。欠損を0とみなす根拠にはならない |

この観測は当該タイル・当該取得時点に限定し、全タイルに同じNoData等を保証しない。Rawと生成物は`.gitignore`対象としてGitへ含めない。実取得・切出しの最終成否とhashは下記の実行結果およびローカルrecordを参照する。

## 狛江での実取得・再実行結果（2026-10-25）

**実取得とAOI切出しはCOMPLETED**。索引は最初のHTTP取得でRawへ保存し、取得CLIには`--index`で渡したため、取得recordの索引欄はlocal_copyであり取得日時はnull。COGは同CLIからHTTPSで実取得した。当時の未コミットコードはその保存済み索引・元COGを使い、別Raw／Workでネットワークなしに再実行した。元タイルと生成物はローカルにのみ保持し、Gitへ含めていない。

| 項目 | 実測結果 |
|---|---|
| COG取得完了 | 2026-10-25 11:48:51 UTC、1タイル、68,699,950 bytes |
| COG SHA-256 | `6313f286dca3b9f760be95d998e9648d0dd77b0a9305081b67422150340af862` |
| 出力 | EPSG:3857、414×313、uint8、元格子約1.1943285669559 m、18,861 bytes |
| 欠損 | NoDataタグNoneを保持、出力mask無効セル0。これを元tile全体の欠損0とは解釈しない |
| 出力SHA-256 | `c5f99a4e9b21e8f419825ef2cac25ec7b36bafbe8a79a89b062201343f0ef880` |
| 当時の未コミットコードによる再実行 | COMPLETED、上記出力SHA-256と一致。当時のmodule hashをreplay recordに保持。コミット済みコード実行の証拠とはしない |
| 実取得record | `data/work/meta_chmv2_komae_acquisition_20261025/acquisition-record.json`、SHA-256 `c4c4a842a2271c12a29f62672ee57632f2a7bcea10b79806cafdd761777c98a7` |
| 当時の未コミットコードreplay record | `data/work/meta_chmv2_komae_replay_20261025/acquisition-record.json`、SHA-256 `3666e113b2e15df6bad9d09aeb9dca7f516b4dc2cf9448479ad7094fe65d6f63` |

実取得のRawは`data/raw/canopy/meta_chmv2_komae_acquisition_20261025/`、replayのRawは`data/raw/canopy/meta_chmv2_komae_replay_20261025/`。これらのローカルrecordは新たな実行で上書きしない。code revisionは実行時のGit HEADを記録するため、コミット前実行では変更前HEADとなる。当時のreplayでは実行モジュールSHA-256も併用して実体を識別していたが、作業ツリー状態は記録していなかった。

ネットワークはCodexサンドボックス内でDNSエラーとなったため、個別承認を得たサンドボックス外のコマンドで公開S3を確認・取得した。単体テストは公開データ不要。サンドボックスの一時ファイルrenameがWinError 5になるため、通常環境でテストを確認した。これは入力データの欠損処理やテスト期待値を変更して回避したものではない。

未確認：個別画像撮影日・モデル重みrevision・推定樹高精度、複数の実COG間の格子整合（複数タイルのモザイクは合成COGで検証）、Canopy／B1/B2への適合性・受入。既存の狛江受入記録は変更していない。

## 初期実装時のテスト結果（79a2461作成前）

通常Windows環境のリポジトリ`.venv/Scripts/python.exe`で実施：

- 最終取得テスト：`-m pytest -q tests/test_meta_chmv2_acquisition.py` → **20 passed、21 warnings**。
- 最終全体：`-m pytest -q` → **420 passed、5 skipped、149 warnings**（134.17秒）。warningsはRasterioのAffine演算に関するPendingDeprecationWarning。
- 合成COGで複数tile接合、AOIの元格子snap、画素・mask／数値NoData・NaN保持、valid zero、hash再現性、格子不整合・重複矛盾・coverage不足・上限・取得失敗を検証。テスト実行時に公開ネットワークは不要。
- サンドボックス内実行はdownload完了時の一時ファイルrenameに対するWinError 5で1件失敗。実装の期待値を変更せず、個別承認による通常環境の再実行で上記結果を確認した。

## PR #63 独立監査Blocking対応：証拠の境界

B-01は一時TIFFの再読込検証後にのみ最終名を作る処理へ変更した。画素・mask・CRS破損の注入、最終名確定の失敗、別producerが最終名を作る競合を回帰テストで扱う。元の上書き拒否とRaw／Work分離を維持する。

B-02では次の証拠を区別する。

1. **元の実取得**：recordのGit HEADは`37ebfa9a497dc466d89bf6dd0273d0df56422abf`（当時のmain）。そのcommitには取得moduleがなく、未コミットの実装で実行した。元recordにmodule SHA-256／作業ツリー状態は存在せず、後から補って当時の実行コードが同定済みとは主張しない。元recordは上記SHA-256のまま保持する。
2. **当時の未コミットコードreplay**：HEADは同じ`37ebfa9...`、disk module SHA-256は`59d5191353158f9918e5a926f9b9bb123f9b04997253e329d12a0f198db40568`。これもコミット前実行で、clean状態の証拠はない。GitはLFを格納する一方、当時のWindows fileはCRLFだったため、このdisk hashを後のcommit blob hashと同一視しない。
3. **今回の修正をコミット後のreplay**：新しいRaw／Workを使う。開始／終了それぞれのHEAD、`git status --porcelain --untracked-files=all`、disk module hash、HEADのmodule blob hashを記録し、両時点が同じ・clean・moduleのbyte一致がすべて成立するときだけ`committed_code_identity_verified=true`とする。Git情報取得失敗や改行差も未一致として扱い、無条件にコミットと実行コードの同一性を主張しない。対象はこのmoduleのbyte一致とGit作業ツリーであり、依存全体・Pythonのロード済みmemoryの独立証明ではない。

今回の入力は元取得Rawからのローカルコピーで、ネットワーク再取得ではない。入力SHA-256を比較し、元の実取得recordと当時のreplay recordのSHA-256が変わっていないことも確認する。コミット済みコードの再実行結果は、実装commit後に別項として追記する。
