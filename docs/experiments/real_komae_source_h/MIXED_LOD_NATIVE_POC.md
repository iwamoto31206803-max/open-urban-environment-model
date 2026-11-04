# Mixed-LoD Native Building PoC

状態は **EXPERIMENTAL**。基準mainはPR #137を取り込んだ `a3eb93a`。Raw selectorの候補B（EPSG:6677、`[-22575, -39925, -22475, -39825]`）で、LoD2優先・LoD1 fallbackの選択を単一Native GPKGに格納する。 [Mixed-LoD実装計画](../../planning/OUEM_Komae_Mixed_LOD_Implementation_Plan_v0.1.md) · [Raw selector](MIXED_LOD_SELECTOR_POC.md) · [Converter Bridge](MIXED_LOD_CONVERTER_BRIDGE_POC.md)

## 入力と再現

次の入力を読み取り専用で使う。SHA-256は保存済みの実測記録に基づく。

| 成果物 | SHA-256 |
|---|---|
| Komae 2025 ZIP | `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555` |
| ZIP内 `udx/bldg/53393466_bldg_6697_op.gml` | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| Raw selector manifest | `eea7a117658208018fb0e12d212f7e63a6fef69a0c86c1265fd6692fda4b0785` |
| Raw selector geometries.jsonl | `51386b7fb5286e18bf5d310e09ddd7c438c92188efcd713fac7222cf3b9485ef` |
| Bridge receipt | `53e72d051136df1cc9d2c92701243a7f28b7a144123e52ba50ab81cff6a92900` |
| LoD1 GPKG | `bdb207ea324e8f1b9a7b45a5de748c9b62273c0f300adfbac349d15a697e38d6` |
| LoD2 GPKG | `561b910286d5ac340298cd9029c8519459165a29ba69483b85bce7613b4fe048` |

通常のWindows OUEM venvで実行する。入力はreceiptが記録した保存場所に置く。新規runは既存の親ディレクトリの下に作る。 `--bridge-sha256` は信頼できる実行記録の値を使用する。

```powershell
New-Item -ItemType Directory -Force data/work/mixed-lod-native | Out-Null
.venv/Scripts/python.exe -m ouem.native.building.mixed_lod `
  --bridge-receipt data/work/mixed-lod-converter-bridge/run-02/bridge.json `
  --bridge-sha256 53e72d051136df1cc9d2c92701243a7f28b7a144123e52ba50ab81cff6a92900 `
  --selector-manifest data/work/mixed-lod-selector/run-pr136-rereview-01/manifest.json `
  --zip data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip `
  --member udx/bldg/53393466_bldg_6697_op.gml `
  --release plateau-13219-komae-shi-2025 `
  --bounds -22575 -39925 -22475 -39825 `
  --output-dir data/work/mixed-lod-native/run-repro-01
```

Bridgeの `ELIGIBLE` と固定nusamaiの実行情報を確認し、Converter本体・抽出member・ログ・両GPKGをSHAで照合する。Raw選択を元ZIPから再実行してmanifestとJSONLを再検証し、全IDと両passの面・ring・XYZを再照合する。LoD2の面順差は記録し、コピーはConverter BLOBのバイト列を保つ。比較後に候補Bと交差する選択IDだけをコピーし、境界接触を含め、clipは適用しない。

新規run内の一時領域に作成し、再オープンして属性、BLOB、幾何を照合する。入力を再ハッシュしてからハードリンクで公開し、GPKGの公開後に入力を再確認して `manifest.json` を最後に公開する。例外時はこのrunが公開したファイルを取り消し、`failure.json` を残す。プロセス中断後の確認には完了マーカーとNative SHAを使用し、再実行は別のrunに行う。ハッシュ照合は通常の変更検出で、並行書き込みをロックする仕組みではない。

## Native schemaと属性

profileは `ouem-native-building/plateau-mixed-lod-source-h/v0.1`。レイヤは `bldg:Building`、`geometry` はEPSG:6697のMULTIPOLYGON、Z必須、Mなし。座標格納順は経度・緯度・H。鉛直EPSG:6695の重力関連高さ（m）を出典宣言として記録し、Hは変換しない。 [探索的manifest schema](../../schemas/ouem_mixed_lod_native_manifest_v0.1.schema.json)

| Converter／Rawの情報 | Mixed Nativeでの扱い |
|---|---|
| Converter `id` | `id` と `source_feature_id` に保持。Raw `source_id` と一致を確認し、manifestにも記録 |
| Converter `geometry` | 選択passのBLOBをそのまま保存し、`geometry_blob_sha256` を記録 |
| Converter `fid` | Nativeの行IDを新規発行。恒久IDはRaw selectorの決定論的 `ouem_id` |
| Converter `measuredHeight` | 原値を `measured_height_raw` に保持。解析用 `measuredHeight` ではこのデータの `-9999` と元のNULLをNULLとする。他の有限値はそのまま。幾何のHとは別 |
| Converterの残り37列 | 今回は転記せず、元GPKGを参照。名称・用途、日付、階数、境界・部品、住所、URO等の複合属性と親子列を含む |
| Raw selector | `selected_lod`、`selection_reason`、`source_member`、`source_release`、`ouem_id`、対応する `converter_pass` を保持。manifestにbranch・Polygon・Raw幾何SHAと全IDの採否を記録 |

LoD1 GPKGの `-9999` 435件を元CityGMLとIDで照合し、全件が `bldg:measuredHeight` の `-9999 m` に由来することを確認した。高さとして利用できない原値としてこのprofileで扱う。提供者が定める一般的な欠損コード表は未確認。

## 実データ検証

Windows build 26300、OUEM venvのPython 3.11.9で、2026-11-04 18:24 JSTに `data/work/mixed-lod-native/run-02/` を公開した。初回 `run-01` はsandboxがハードリンク公開を拒否し、`failure.json` を残して停止した。通常のWindows環境で新しいrunに再実行した。

| 選択LoD | Native件数 | 面 | 頂点出現（閉鎖点を含む） | ID・BLOB・XYZ/H不一致 |
|---|---:|---:|---:|---:|
| LoD1 | 31 | 303 | 1,749 | 0 |
| LoD2 | 32 | 1,357 | 6,003 | 0 |
| 合計 | 63 | 1,660 | 7,752 | 0 |

全3,778 IDの判断記録のうち、3,715棟はAOI非交差で除外した。独立スクリプトはwriterやBridgeモジュールをimportせず、SQLiteでNativeと両Converterを読み直し、GeoPackage BLOBをShapelyで解読した。全63棟のID・UUID・選択LoD・pass・選択理由を照合し、BLOBのバイト列とBridgeのID別SHAを確認した。ZIPから直接読んだRawの面多重集合と全ring・XYZも一致した。候補Bに内周ringはなく、内周保持は合成テストで確認した。候補Bの `measuredHeight=-9999` はLoD2の2件で、原値を保存して解析列をNULLとした。

| 出力 | SHA-256 |
|---|---|
| `native.gpkg`（307,200 bytes） | `1e2af898307e5f9bfbc4fbc86ab714dfad2557e2371ff98138171eb768ca7da7` |
| `manifest.json` | `b7e932b9b6da9da98a59ccb6e1acb5a60a1cb7d50ea5c3d5e86782eccbcfc46d` |

独立監査のコードとログはGit管理外の `data/work/mixed-lod-native/audit.py` と `audit.log`。成功manifestと初回失敗記録はJSON Schemaに適合した。

## テストと既存経路

新規合成テスト11件、関連テスト258件が通過（警告4件）。全体pytestの初回はWindowsの標準出力エラーで中断した。専用の一時ディレクトリとログに切り替えた再実行は1,162件通過、10件skip、336件警告（552.30秒）。skipは専用GIS/QGIS Python 5件とWindows symlink権限5件。ログは `data/work/mixed-lod-native/related.log`、`full.log`、`full-02.log`。

旧LoD2-only Standardizerが新manifestを拒否することを確認した。PR #134のNative、Standard、VoxCity report、Voxelの4ファイルは記録済みSHA-256と一致した。Markdownリンクと `git diff --check` を確認した。

## Mixed Standardへの申し送り

新しいStandard工程はこのprofileと完了manifestを明示的に受け取り、両passとRawの証跡、採用集合、Native BLOBとHを再検証する。水平座標のみ投影し、Nativeで確定したLOD・ID・非clip形状を保持する。属性マッピングでは解析用NULLと監査用原値を区別する。既存LoD2-only validatorとStandardizerは単一Converter graphおよび既存の隣接receiptを要求するため、本manifestは別入口で扱う。属性の完全移送、鉛直datum実現の精度、下流処理は別途検証が必要。
