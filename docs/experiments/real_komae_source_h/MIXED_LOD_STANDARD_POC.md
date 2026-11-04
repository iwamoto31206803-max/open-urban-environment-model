# Mixed-LoD Standard Building PoC

状態は **EXPERIMENTAL**。基準mainはPR #138を取り込んだ `a67aeb8`。候補B（EPSG:6677、`[-22575, -39925, -22475, -39825]`）のMixed NativeからStandard Buildingを生成した。 [Mixed-LoD計画](../../planning/OUEM_Komae_Mixed_LOD_Implementation_Plan_v0.1.md) · [Raw selector](MIXED_LOD_SELECTOR_POC.md) · [Converter Bridge](MIXED_LOD_CONVERTER_BRIDGE_POC.md) · [Mixed Native](MIXED_LOD_NATIVE_POC.md)

## 入力と再現

通常のWindows OUEM venvを使用する。Native manifestに記録された成果物の保存場所を維持し、既存の親ディレクトリの下に新しい出力先を指定する。Native manifestのハッシュは保存済み実行記録から指定する。

| 入力 | SHA-256 |
|---|---|
| Mixed Native `run-02/manifest.json` | `b7e932b9b6da9da98a59ccb6e1acb5a60a1cb7d50ea5c3d5e86782eccbcfc46d` |
| Mixed Native `run-02/native.gpkg` | `1e2af898307e5f9bfbc4fbc86ab714dfad2557e2371ff98138171eb768ca7da7` |
| Raw selector manifest | `eea7a117658208018fb0e12d212f7e63a6fef69a0c86c1265fd6692fda4b0785` |
| Raw selector geometries.jsonl | `51386b7fb5286e18bf5d310e09ddd7c438c92188efcd713fac7222cf3b9485ef` |
| Converter Bridge receipt | `53e72d051136df1cc9d2c92701243a7f28b7a144123e52ba50ab81cff6a92900` |

Raw ZIP・memberと両Converter GPKGのハッシュはMixed Native報告書に記載。新manifestの `inputs` はこれらの上流成果物にも解決できる。

```powershell
New-Item -ItemType Directory -Force data/work/mixed-lod-standard | Out-Null
.venv/Scripts/python.exe -m ouem.standardize.building.mixed_lod `
  --native-manifest data/work/mixed-lod-native/run-02/manifest.json `
  --native-sha256 b7e932b9b6da9da98a59ccb6e1acb5a60a1cb7d50ea5c3d5e86782eccbcfc46d `
  --bounds -22575 -39925 -22475 -39825 `
  --output-dir data/work/mixed-lod-standard/run-repro-01
```

Mixed専用validatorがNative manifestの固定SHA、profile、完了状態、隣接GPKGを検証する。Raw selectorを元ZIPから再実行し、Bridgeの両passを照合し、Nativeの全ID・選択・属性・BLOB・幾何と全除外記録を再構築して照合する。再検証したNative実ファイルを投影入力に使う。過去のPASSフラグは判定に使わない。選択件数は実ファイルから算出する。

## Standard構造と属性

profileは `ouem-standard-building/plateau-mixed-lod-source-h/v0.1`。GPKGの `building` レイヤはEPSG:6677、MULTIPOLYGON、Z必須、Mなし。格納順はX（easting）、Y（northing）、H。GPKGのSRSは水平投影を記述し、鉛直EPSG:6695の重力関連高さ（m）はmanifestに記述する。 [探索的manifest schema](../../schemas/ouem_mixed_lod_standard_manifest_v0.1.schema.json)

| Standard属性 | 内容 |
|---|---|
| `source_id` / `ouem_id` | Nativeの `id` と決定論的 `ouem_id` をそのまま保持。各列一意 |
| `source_dataset` | `PLATEAU CityGML` |
| `source_lod` | Native `selected_lod` を整数1/2として必須化 |
| `selection_reason` / `source_member` / `source_release` / `converter_pass` | Nativeからそのまま転記 |
| `measured_height` | Nativeの解析列 `measuredHeight` を転記。NULLを保持 |
| `measured_height_raw` | Nativeの監査用原値を転記。幾何の絶対標高Hとは別 |

`Transformer.from_crs(6668, 6677, always_xy=True, allow_ballpark=False, only_best=True)` に経度・緯度のみ渡す。Hは変換せず、面・外周・内周・頂点順と多重度を保持する。再選択、clip、geometry repairは行わない。再オープン後、保存形状と閉じたAOI矩形の交差を再評価する。不一致時はIDを記録して停止し、選択を補正しない。

## 候補Bの実測

2026-11-04 19:03 JSTにWindows build 26300、Python 3.11.9、pyproj 3.7.2、PROJ 9.5.1で実行した。保存先はGit管理外の `data/work/mixed-lod-standard/run-02/`。座標操作はGRS80の第IX系横メルカトル投影で、pipelineと操作設定をmanifestに記録した。

| 選択LoD | 建物 | 面 | 外周ring | 内周ring | 頂点出現（閉鎖点を含む） | 不一致 |
|---|---:|---:|---:|---:|---:|---:|
| LoD1 | 31 | 303 | 303 | 0 | 1,749 | 0 |
| LoD2 | 32 | 1,357 | 1,357 | 0 | 6,003 | 0 |
| 合計 | 63 | 1,660 | 1,660 | 0 | 7,752 | 0 |

全63棟でID、ouem_id、LoD、出典属性、面・ring・頂点順、AOI交差が一致した。Hは全頂点でビット一致。再オープン監査の `Proj` によるXY最大軸差は0 m（許容差 `1e-7 m`）。これは浮動小数点照合の予算であり、測量精度の評価ではない。

追加の独立監査はStandardizerをimportせず、SQLiteとShapelyで両GPKGを再読込した。元ZIPのRaw面を直接読み、Raw→Nativeは面の順序差を許したXYZビット列の多重集合、Native→Standardは順序付き構造とHビット列を照合した。第IX系の明示パラメータからXYを再計算した最大軸差も0 m。候補Bの `-9999` 2件は解析列がNULLで原値が保存された。候補Bに内周ringはなく、内周保持は合成テストで確認した。GeoPandas 1.2.0でEPSG:6677の3D MultiPolygon 63件を読み込んだ。QGIS GUIは未確認。

| 出力 | SHA-256 |
|---|---|
| `standard.gpkg`（303,104 bytes） | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |
| `manifest.json` | `9789d443e0286ad0c5da57156d7ba10ed19adafba5e42cec068e9deeead0f789` |

独立監査コードとログは `data/work/mixed-lod-standard/audit.py` と `audit.log` に保存した。

## 公開と失敗

ステージしたGPKGの監査後、入力を再ハッシュする。新規run内にGPKGを公開し、入力とGPKGを再確認してから完了マーカー `manifest.json` を最後に公開する。通常の例外では当該runが公開した出力を取り消し、`failure.json` を残す。ハードリンク対応の同一ファイルシステムが必要。途中停止後は完了マーカーとSHAを確認し、新しいrunで再実行する。ハッシュによる変更検出はファイルロックを伴わない。

誤ったNative SHAで試した `run-invalid-sha/` は `Native.manifest` のエラーを記録し、GPKGと完了マーカーを公開しなかった。合成試験で、LoDや幾何を改変したNative、古いmanifest、CRS不整合、欠損LoD、投影後のAOI差、XY・H差、公開直前の入力変更、既存run再使用も拒否した。

## テスト

新規合成テスト13件、関連テスト271件が通過（関連の警告4件）。全体の初回は既存Height Envelopeテスト1件が作業ツリーの変更と同時にGit状態の差を検出して停止した。同テストの単独再実行は通過。作業ツリーを固定した全体再実行は1,175件通過、10件skip、336件警告（580.36秒）。skipの内訳は専用GIS/QGIS Python 5件、Windows symlink権限5件。ログは `data/work/mixed-lod-standard/related.log`、`full.log`、`full-02.log`。

成功・失敗manifestのschema、Markdownリンク、`git diff --check`、PR #134のNative・Standard・VoxCity report・Voxelの既存SHA-256を確認した。

## Independent Consumerへの引き継ぎ

独立ConsumerはこのMixed profileと完了manifestを明示して受け付け、保存済みPASSを前提にせず、Native・Bridge・Rawへのハッシュ参照、AOI選択、整数LoD、実GPKGの3D構造・属性・座標・Hを再検証する。旧LoD2-only Consumerのprofile、schemaとテキスト型LoD条件は従来どおり。候補BのTerrain、VoxCity、QGIS GUI、鉛直datum実現の精度と正式Acceptanceは未検証。
