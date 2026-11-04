# Mixed-LOD Raw selector PoC

基準mainは `9d1f4e88cb9e427941755df7b63fa6c5ab65b60a`。市境をまたぐ候補Bをユーザー承認の下で使用した。今回の処理範囲はRaw選択とXYZ照合まで。Converter、Native、Standard、Consumer、VoxCity、正式Acceptanceは今回の検証対象外。 [設計計画](../../planning/OUEM_Komae_Mixed_LOD_Implementation_Plan_v0.1.md) · [4メッシュLoD2 PoC](FOUR_MESH_REPRESENTATIVE_HEIGHT_POC.md)

## 選択と証跡

`python -m ouem.mixed_lod_selector` は明示指定されたZIP内のCityGML 2.0を読み取り、全親Buildingを検査する。LoD1・LoD2のbranch存在を先に記録し、存在する両branchを検証する。LoD2が有効なら2、LoD2が欠損しLoD1が有効なら1を選ぶ。両方欠損なら理由付きで除外する。空・不正・未対応のLoD1/2、重複Building ID、検査対象branchの未対応xrefは処理を停止する。LoD3/4の存在は記録し、その形状は選択に使わない。自治体コードとcodeSpaceは監査欄に保持する。 [selector実装](../../../src/ouem/mixed_lod_selector.py)

LoD1は直接のinline Solid exteriorからCompositeSurfaceのPolygonを読む。Polygonの内周ringを保持し、Solidのinterior shellを拒否する。LoD2は複数のinline MultiSurfaceと任意の同一Building内参照Solidを扱う。branch一覧はRaw XML順とし、各面に元branchとbranch内の1起点ordinalを保持する。面はSolidがあれば参照順、なければRawのbranch・面順で保存する。Solidの参照は全Polygonとの一対一対応を要求し、欠落・重複・別Building参照を拒否する。重複XML IDも拒否する。VALIDは対応構造、有限3D座標、経緯度範囲、閉じたring、対応する参照の検証結果を示す。XSD全体、3Dの水密性、測量・鉛直datumの精度は未検証。

AOI判定はLoD選択後、全選択面を水平変換した一時コピーとEPSG:6677矩形のXY交差で行う。境界接触を含む。保存面は無切断で、Rawの緯度・経度・Hから経度・緯度・Hへの軸順整理だけを行う。EPSG:6697の明示宣言から水平6668、鉛直6695の絶対Hを記録する。

| 保存物 | 内容 |
|---|---|
| manifest.json | 全Buildingの選択表。各行のsource_memberからZIP、release、member SHA-256、共通CRS宣言へ辿る。presence、検証状態、選択理由、AOI交差、親ID基準のbranch locator、Polygon IDまたは1起点ordinalを保持 |
| geometries.jsonl | 選択LoDを持つ全Buildingの順序付き面・ring・XYZ。AOI外も保存する。source_idで選択表に結び、行ごとの面digestとファイルdigestを検証できる |
| failure.json | 停止理由と、branch検査まで到達した場合は失敗レコード。再実行には新しい出力ディレクトリを指定 |

成功manifestはRaw検査、geometry書込、ZIPの再ハッシュ後に公開する。ZIP SHA-256の前後照合は変更検出であり、ファイルロックによる不変スナップショットは未実装。release名は呼出側の宣言として保存する。branch locatorの接頭辞はmanifestの名前空間表を参照する。schema検証と、参照先・件数・座標の実データ照合は別に実施した。 [探索的JSON Schema](../../schemas/ouem_raw_mixed_lod_selector_manifest_v0.1.schema.json)

## 候補Bの再現

既存ZIPの `udx/bldg/53393466_bldg_6697_op.gml` を直接読み取る。ZIP SHA-256は `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555`、member SHA-256は `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9`。既存取得記録を出典とする。 [PLATEAU取得記録](../voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md)

通常のWindows OUEM venvから、存在する親ディレクトリの下に新しいrun名を指定する。

```powershell
New-Item -ItemType Directory -Path data/work/mixed-lod-selector -Force | Out-Null
.venv/Scripts/python.exe -m ouem.mixed_lod_selector `
  --zip data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip `
  --member udx/bldg/53393466_bldg_6697_op.gml `
  --release plateau-13219-komae-shi-2025 `
  --bounds -22575 -39925 -22475 -39825 `
  --output-dir data/work/mixed-lod-selector/run-repro-01
```

## 実測

初回レビュー前の実測は2026-11-04 16:16 JSTに完了した。保存先は `data/work/mixed-lod-selector/run-20261104-01/`。実行時間は67.01秒。Python 3.11.9、Shapely 2.2.0、PyProj 3.7.2。schemaの読取検証には環境に既存のjsonschema 4.26.0を使用した。

| 対象 | LoD1選択 | LoD2選択 | 合計 |
|---|---:|---:|---:|
| mesh66全体 | 487 | 3,291 | 3,778 |
| 候補B交差 | 31 | 32 | 63 |

全親Building IDは一意。両LoDなしは0棟。候補BのLoD1 31棟はRaw city属性13112、LoD2 32棟は13219。件数はRaw選択面の交差数であり、格子上のowner数は未計測。

独立した読取スクリプトはZIPを再度開き、RawのposListを直接数値化して、全3,778棟の選択LoD、面の多重集合、各ringの順序と全XYZを照合した。145,951面、閉鎖点を含む664,021頂点出現が一致した。全出力行のschemaと面digest、geometryファイル全体のdigestも検証した。候補Bの63組のsource_id/LoD、mesh66全棟のcity属性とLoD1-onlyフラグはPR #135の保存診断と一致した。

独立照合の初回は旧診断の `source_lod` 欄を `selected_lod` として参照し、ID比較で停止した。欄名を修正して照合を再実行した。実行コードと結果はローカルの `data/work/mixed-lod-selector/audit-final.py` と `audit-final.log` に保存した。

| 出力 | bytes | SHA-256 |
|---|---:|---|
| manifest.json | 29,286,802 | `e369025717f5d41172f461e8858d7b5b0e467501b5d89b7098312c0bf6dcaaab` |
| geometries.jsonl | 32,731,212 | `51386b7fb5286e18bf5d310e09ddd7c438c92188efcd713fac7222cf3b9485ef` |

初回 `run-20261030-01` と最終版のgeometryファイルは同一バイトだった。初回後に経緯度範囲検査と成功manifestの一時ファイル経由公開を追加した。既存Preflightの保護入力9件とPR #134 Standard/voxelの記録済みhashを照合した。

### PR #136 再レビュー時の再実行

単一branch制約を撤回した。対象GMLのLoD2 3,291棟は全棟が5～138の `lod2MultiSurface` branchを持つ。単一branch制約を試した `run-pr136-review-01` は `LOD2_INVALID` で停止した。

上記コマンドの出力先を `data/work/mixed-lod-selector/run-pr136-rereview-01` として2026-11-04 17:36 JSTに再実行した。処理時間は67.53秒。候補BはLoD1 31棟、LoD2 32棟、計63棟で、PR #135診断と全source_id/LoDが一致した。manifest SHA-256は `eea7a117658208018fb0e12d212f7e63a6fef69a0c86c1265fd6692fda4b0785`。geometryファイルは初回レビュー前の実測と同一バイトだった。

selectorをimportしない独立スクリプトで、全3,778棟のRaw branch順、Polygon IDとbranch内ordinal、LoD2 3,291棟のSolid参照の一対一対応と順序、145,951面の664,021頂点出現を照合した。各ringの順序とXYZが一致し、Raw Polygonの欠落や出力時の重複はなかった。スクリプトとログは `data/work/mixed-lod-selector/audit-pr136-rereview.py` と同名の `.log` に保存した。


## テスト

合成fixtureは手で定義した面、座標、期待LoDを用いた。両LoD、片方のみ、両方欠損、empty/不正、重複、内周ring、Solid interior shell、AOI順序と境界接触、LoD3/4、xref、XYZ、自治体属性、入力変更、出力再利用の拒否、schemaを検証する。旧LoD2 Readerとの回帰比較を含む。初回のdimension異常テストはfixture生成が2を3へ上書きしていたため失敗し、異常値を保持するようfixtureを修正した。 [合成テスト](../../../tests/test_mixed_lod_selector.py)

| 実行 | 結果 |
|---|---|
| 新規selectorテスト | 39 passed |
| selectorとSource-H・PR #134の関連テスト | 298 passed、4 warnings、69.82秒 |
| 全体 `.venv/Scripts/python.exe -m pytest -q -ra` | 1,135 passed、10 skipped、336 warnings、520.95秒 |

全体のskipはGIS/QGIS専用Python未指定5件とWindows symlink権限5件。関連テストの警告はRasterio/Affineのpending deprecationと既存stat/fstat ctime診断。全体ログは `data/work/mixed-lod-selector/full.log`、関連ログは同directoryの `related.log`。Markdownリンク、JSON Schema、Python AST、`git diff --check` を確認した。

再レビューでは、複数branchのRaw順・逆順のSolid参照・全Polygonの出典を検証した。Solid参照の欠落・重複およびbranchをまたぐPolygon ID重複は、LoD1があっても失敗し、成功成果物を公開しないことを確認した。関連テストは236件通過、警告4件（76.38秒）。ログは `data/work/mixed-lod-selector/related-pr136-rereview.log`。

全体pytestは1,140件通過、10件skip、警告336件（493.14秒）。skipの内訳は上記と同じ。ログは `data/work/mixed-lod-selector/full-pr136-rereview.log`。
