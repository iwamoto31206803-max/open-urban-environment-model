# Mixed-LoD Independent Consumer PoC

状態は **EXPERIMENTAL**。基準mainはPR #139を取り込んだ `f73858d`。候補B（EPSG:6677、`[-22575, -39925, -22475, -39825]`）について、Raw CityGMLからMixed Standardまでを読取専用で検証する。 [Mixed-LoD計画](../../planning/OUEM_Komae_Mixed_LOD_Implementation_Plan_v0.1.md) · [Raw selector](MIXED_LOD_SELECTOR_POC.md) · [Converter Bridge](MIXED_LOD_CONVERTER_BRIDGE_POC.md) · [Mixed Native](MIXED_LOD_NATIVE_POC.md) · [Mixed Standard](MIXED_LOD_STANDARD_POC.md)

## 入力と再現

通常のWindows OUEM venvを使用する。既存manifestに記録された絶対パスを維持する。artifact rootは、既存run、実装ファイル、固定Converterの保存場所を含むディレクトリとする。この環境では `C:/dev`。出力先は既存の親ディレクトリの下に新しく作る。

```powershell
New-Item -ItemType Directory -Force data/work/mixed-lod-consumer | Out-Null
.venv/Scripts/python.exe -m ouem.consumers.mixed_lod `
  --standard-manifest data/work/mixed-lod-standard/run-02/manifest.json `
  --standard-sha256 9789d443e0286ad0c5da57156d7ba10ed19adafba5e42cec068e9deeead0f789 `
  --artifact-root C:/dev `
  --bounds -22575 -39925 -22475 -39825 `
  --output-dir data/work/mixed-lod-consumer/run-repro-01
```

| 入力 | SHA-256 |
|---|---|
| Mixed Standard GPKG | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |
| Mixed Native manifest | `b7e932b9b6da9da98a59ccb6e1acb5a60a1cb7d50ea5c3d5e86782eccbcfc46d` |
| Mixed Native GPKG | `1e2af898307e5f9bfbc4fbc86ab714dfad2557e2371ff98138171eb768ca7da7` |
| Bridge receipt | `53e72d051136df1cc9d2c92701243a7f28b7a144123e52ba50ab81cff6a92900` |
| Raw selector manifest | `eea7a117658208018fb0e12d212f7e63a6fef69a0c86c1265fd6692fda4b0785` |
| Raw selector geometries.jsonl | `51386b7fb5286e18bf5d310e09ddd7c438c92188efcd713fac7222cf3b9485ef` |

Komae 2025のZIP・`udx/bldg/53393466_bldg_6697_op.gml`・両GPKG・固定nusamai 0.1.19のハッシュはBridge・Native報告書とreceiptに記録する。Consumerは元ZIPとmemberを別々にハッシュし、release・抽出member・実行引数・ログ・実装SHAをグラフ全体で照合する。固定Converterを再実行しない。

## 独立性と検証方法

- [Raw reader](../../../src/ouem/consumers/_mixed_lod_raw.py) は生成側をimportせず、ZIPの元XMLから親Building、LoD1 Solid、複数LoD2 MultiSurface、同一Building内のSolid参照を読む。各branchの出典とPolygon順、内周、3D座標を検証し、存在する両LoDを検査してからLoD2を優先する。LoD2不正時は停止する。両LoDが欠損するBuildingもこのConsumerでは拒否する。selectorは当該ケースの除外を記録できるため、ここは意図的に厳しい受渡条件である。候補Bの元memberには該当棟なし。
- [Consumer](../../../src/ouem/consumers/mixed_lod.py) は固定SHAから入力を辿り、既存Consumerの `Watch`、厳格JSON読取、read-only SQLiteを再利用する。Native/ConverterとStandardの低水準ISO WKBデコーダを再利用するため、共有デコーダが共通障害点になり得る。採用Native（選択Converter BLOBと同一）とStandardをGEOSでも解読し、順序付きXYZのビット列を照合する。手作成WKBで両読取経路を検証した。生成側の選択・writer・投影・監査関数は呼ばない。
- Rawの両LoDを両Converter出力の全featureと照合する。面の順番、内周ringの順番、ringの開始点と向きを除き、面・ring・頂点の多重度とXYZビット列を比較する。選択行のConverter→NativeはBLOBのバイト一致を要求する。Native→Standardでは各面・ring・頂点を順序付きで対応させ、全Hをビット比較する。
- XY参照は、EPSG:6677の投影定義をローカルPROJデータベースで確認して設定した独立の `Proj(tmerc)`。GRS80、緯度36°、経度139°50′、縮尺0.9999、原点オフセット0 m。第IX系原点を制御点とし、候補Bの全頂点を軸別最大差 `1e-7 m` 以下で照合する。Hを渡さない。許容差は数値照合用であり、測量精度を示さない。
- 選択したRaw LoDの各投影面を閉じたAOI矩形と比較し、境界接触を含める。Raw選択とNative・StandardのID集合を照合し、Standardの保存形状から交差を再検査する。clipや件数調整は行わない。共有するGEOSのXY交差述語は数学的・測量的な独立検証の範囲外。
- UUIDv5を独立に再計算する。採用棟はRawの `measuredHeight`（単一の `uom=m`、または欠損）をConverter原値と照合し、NativeとStandardの原値、解析用NULL、LoD、選択理由、member、release、passを比較する。保存済みの `h_exact`、XY誤差、PASSは合否の根拠に使わない。

## 候補Bの実測

2026-11-04 19:45 JSTに、Windows build 26300、Python 3.11.9、pyproj 3.7.2、PROJ 9.5.1で完了した。保存先はGit管理外の `data/work/mixed-lod-consumer/run-04/receipt.json`、SHA-256は `1f9de8a7bdd7c92fd455f7c3897f45d8280dff05da90634f2aa677a86298e415`。元memberの親Building 3,778棟を検査し、3,715棟のAOI非交差を確認した。両Converterの3,778件（LoD1）と3,291件（LoD2）をRawと照合した。

| 選択LoD | 建物 | 面 | 外周ring | 内周ring | 頂点出現（閉鎖点含む） |
|---|---:|---:|---:|---:|---:|
| LoD1 | 31 | 303 | 303 | 0 | 1,749 |
| LoD2 | 32 | 1,357 | 1,357 | 0 | 6,003 |
| 合計 | 63 | 1,660 | 1,660 | 0 | 7,752 |

Consumer実測のID・LoD・XYZ/H・属性・AOI不一致は各0件。独立XY最大軸差は **0 m**、全Hビット一致。Standardizerの自己監査値は参照せず、結果が同じであることを事後に確認した。候補BのRaw `-9999 m` 2件はConverter・Native・Standardで原値が一致し、解析列はNULL。候補Bに内周はなく、保持は合成で確認した。

完了時は `execution_status=COMPLETED`、`consumer_validation=PASS`、`formal_acceptance=NOT_VERIFIED`。出力先を新規作成し、全入力のSHA・ファイル識別を再確認してからreceiptを公開する。失敗は最初の原因を `failure.json` に保存し、成功receiptを公開しない。誤ったStandard SHAでの実行でもこの動作を確認した。強制終了や並行変更に対しロックや原子的な入力スナップショットは提供しない。 [Consumer receipt schema](../../schemas/ouem_mixed_lod_consumer_receipt_v0.1.schema.json)

## テスト

新規合成テスト25件、関連テスト296件通過（警告4件）。手作成CityGML・WKB、Rawの不正LoDや参照、境界接触、重複・欠損ID、LODとpass、XY/H、原値とNULL、出典グラフの改変、公開前の差替えと中断を検証した。全体pytestは1,200件通過、10件skip、336件警告（632.67秒）。skipは専用GIS/QGIS Python 5件とWindows symlink権限5件。ログは `data/work/mixed-lod-consumer/related-final.log` と `full.log`。成功・失敗receiptのschema、Markdownリンク、`git diff --check`、PR #134保護成果物4点のSHA-256も確認した。

## Terrain / VoxCityへの引き継ぎ

このreceiptは、候補BのMixed Standardの技術的な整合を示す。下流の利用時には入力SHAを再確認する。Terrainの取得・被覆、座標・鉛直基準の整合、代表高さ、格子上の採用数、QGIS GUI、鉛直datumの実現精度と正式Acceptanceは未検証。既存LoD2-only Consumer、Standardizer、PR #134の経路は従来どおり。
