# Mixed-LoD Candidate B Terrain Preflight

**EXPERIMENTAL / NOT_FORMALLY_ACCEPTED — CONDITIONAL**。候補B（EPSG:6677、`[-22575,-39925,-22475,-39825]`、100 m四方）を対象とした。実データは両ソースから取得できた。多摩・区部のいずれも単独で全面を覆わず、区部のCRSと鉛直基準には後述の制約がある。Accepted Terrain 09LD3451の範囲は候補Bと交差しない。 [実行依頼](../../planning/OUEM_Candidate_B_Terrain_Preflight_Execution_Request_20261104.md) · [国立の取得手順](../../planning/OUEM_Kunitachi_Data_Source_Preflight_v0.1.md)

## 取得と出典

2026-11-04 21:16 JSTにGEEKOM-A6の通常OUEM venvで完了した。Python 3.11.9、Rasterio 1.4.4（GDAL 3.10.3）、Pyogrio 0.13.0、PyProj 3.7.2。各カタログの配信説明はグラウンド由来0.50 m標高GeoTIFF。提供は東京都デジタルサービス局。配信カタログのライセンス欄は多摩がCC-BY、区部がcc-by。多摩の東京都公式カタログではCC BY 4.0。両配信リソースの利用規約リンクも確認した。 [多摩配信API](https://www.geospatial.jp/ckan/api/3/action/package_show?id=tokyopc-tama-2023) · [区部配信API](https://www.geospatial.jp/ckan/api/3/action/package_show?id=tokyopc-23ku-2024) · [配信規約](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/doc/license.pdf)

AOIの2 m外周を含む検索範囲をEPSG:3857へ変換すると、z14のXYZは `14544/6453` の1枚だった。配信APIに載る実PBFをGDAL MVTでEPSG:3857として読み、6677へ投影した。両索引の `MESH_NO`／`URL` が `09LD3423` と `09LD3433` を示した。2 mは量子化を考慮した索引検索用で、被覆の集計範囲は元のAOI。 [多摩PBF](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/Vectortile/tama/grd50/14/14544/6453.pbf) · [区部PBF](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2024/dig/Vectortile/23ku/grd50/14/14544/6453.pbf)

| PBF | bytes | SHA-256 |
|---|---:|---|
| 多摩2023 | 5,603 | `e29db8c2dbcbca35af0cd1cae4be2991a8b7eee3c8b280ac9fb84dcefdd0da8e` |
| 区部2024 | 2,022 | `97354adeb86c26f4e7c8dc74e45fa6dd299f1349d3de63badce7de1e80530ad6` |

| 取得ZIP | ZIP bytes | ZIP SHA-256 | 原GeoTIFF SHA-256 |
|---|---:|---|---|
| [2023 09LD3423](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/09LD3423.zip) | 685,802 | `ed1699b039f654a965f3502247c1079adeba87e34187e514f8281112223a6c2d` | `8b92f4ce3cb72f6084858df629b0cc676cd7cd45e6973942f0a9cf0c793b34ca` |
| [2023 09LD3433](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/09LD3433.zip) | 707,852 | `0e9a4258d38015ec80205fa09b41a43b0174e8ac8abec0a532a242e78778f4d2` | `491defd8c37fb52241d73ae4bd2142c605056133b51a320a750aeddfb9018d92` |
| [2024 09LD3423](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2024/dig/grd50/09LD3423.zip) | 94,246 | `7262d5665839ccbe94e69bde5581311f70e71449fe6972b0f302140ce182ffe6` | `62b98534376827a0906b6703522764356e20eb5c2d8ef53ac36b1ea3e3e6b8b8` |
| [2024 09LD3433](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2024/dig/grd50/09LD3433.zip) | 60,479 | `d0b0a66ec25cee71432d73a69b9b11cc116b2e07ad1231ec655f7a3713d5e29d` | `66190876d0baab6aa25fb518a6e4827d45b78286a2e3fa385e0fe9b61f7eb18c` |

索引と4件のZIPはHTTP 200。取得時刻、URL、応答、バイト数、ハッシュはローカルの `data/work/terrain-candidate-b/run-03/report.json` に記録した。ZIPごとにmesh名のTIFFを1件だけ開き、サイズ上限とCRCを確認した。

## GeoTIFFと鉛直基準

全4件がnorth-up、0.5 m、単バンドFloat32、scale 1／offset 0。Rasterio/GDALが返すアフィンの格子原点は、診断で使う200×200のAOI格子に整列した。

| ソース・mesh | 行×列 | 左上（m） | AOI内有効セル | 有効標高範囲（m、原値） |
|---|---:|---|---:|---:|
| 多摩 3423 | 600×800 | (-22800, -39600) | 19,579 | 24.316–25.499 |
| 多摩 3433 | 600×793 | (-22800, -39900) | 8,654 | 24.141–25.352 |
| 区部 3423 | 584×304 | (-22552, -39608) | 13,682 | 24.230–24.930 |
| 区部 3433 | 600×209 | (-22504.5, -39900) | 2,421 | 24.230–24.660 |

- 多摩はEPSG:6677として識別でき、`AREA_OR_POINT=Area`、NoDataは `1.701410009187828e38`。既存 `inspect_dem()` のラスタ構造検査を通過した。東京都公式カタログは標高を東京湾平均海面（T.P.）と宣言している。 [東京都多摩カタログAPI](https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_show?id=t000029d0000000020)
- 区部は `AREA_OR_POINT=Point`、NoDataは `-32767`、バンド単位はmetre。WKT末尾にEPSG:6677のauthorityがあるが、基礎地理CRSはunknown、datumはunnamedで、Rasterioの `to_epsg()` はNone。配信カタログのJGD2011／第9系宣言と、埋め込みGRS80・投影パラメータ・easting/northingの一致を条件として、GDALが返すセル中心位置で比較した。原ファイルのCRSは変更していない。既存 `inspect_dem()` は区部2件を拒否した。
- 区部の東京都カタログAPI候補はHTTP 404。東京都デジタルサービス局名義の公開カタログミラーとG空間配信APIから、区部の鉛直datumの明示は確認できなかった。Mixed BuildingはEPSG:6697、鉛直EPSG:6695の重力関連Hを宣言する。多摩のT.P.宣言と比較できるが、測量epochやdatum実現精度の互換性は未検証。区部を同一鉛直基準として扱う根拠は得られていない。 [区部公開カタログAPI](https://odm.bodik.jp/api/3/action/package_show?id=t000029d00000000241) · [Mixed StandardのH宣言](MIXED_LOD_STANDARD_POC.md)

## 有効セル、重複、境界

マスク済みまたは非有限の値を除外し、AOIの40,000セル中心を数えた。区部を含む結果には上記の水平位置の条件が付く。値の選択、平均による結合、補間、再投影、再サンプリングはしていない。

| 診断範囲 | TIFF格子内 | 有効 | 有効率 | 格子内NoDataのみ | 有効未被覆 | 有効重複 |
|---|---:|---:|---:|---:|---:|---:|
| 多摩 | 40,000 | 28,233 | 70.5825% | 11,767 | 11,767 | 0 |
| 区部 | 26,050 | 16,103 | 40.2575% | 9,947 | 23,897 | 0 |
| 条件付き和集合 | 40,000 | 40,000 | 100% | 0 | 0 | 4,336 |

多摩だけの有効セルは23,897、区部だけは11,767。全セルを満たす最小集合は今回取得した4タイルすべて。両meshは `Y=-39900 m` を境とし、区部の格子左端は北側 `X=-22552 m`、南側 `X=-22504.5 m`。格子境界と実際の有効マスクには差がある。

| 同一セル中心の標高差（区部−多摩、m） | セル数 | 最小 | 最大 | 平均 | 中央値 |
|---|---:|---:|---:|---:|---:|
| 09LD3423 | 3,261 | -0.656 | +0.183 | -0.0472 | -0.0020 |
| 09LD3433 | 1,075 | -0.227 | +0.129 | -0.0167 | +0.0010 |

各セルを供給するタイルが1枚だけの中心同士を4近傍で比べると、北→南のmesh境界は多摩141辺（-0.102～+0.037 m）、区部37辺（-0.050～+0.090 m）。この定義でソースをまたぐ排他的な隣接辺は0だった。重複部の差には取得時期、計測、マスク・格子表現などの影響があり、鉛直datum差や将来のモザイクの段差を特定するものではない。

## 再現と次工程

| Preflight状態 | 意味 |
|---|---|
| `PASS` | 両ソースの取得・検査・集計が完了し、有効セルの和集合がAOIを覆う。全対象TIFFの水平CRSを識別でき、両ソースの鉛直基準に提供元宣言がある |
| `CONDITIONAL` | 両ソースの検査・集計は完了したが、有効未被覆または水平・鉛直メタデータの条件が残る |
| `BLOCKED` | 必要な取得・検査・集計が完了しなかった。原因をソース別の `error` または `aggregation_error` に記録する |

完了記録は一時ファイルから公開した `report.json`。記録の欠落や `BLOCKED` の場合、残存ZIP・TIFF・ソース別結果は診断用の証拠として扱う。集計が失敗した場合は結合結果を公開しない。

`terrain_integration_ready` はPreflight状態とは独立し、このPreflightでは `PASS` でも `false`。水平・鉛直基準の適合性、採用ソースと接合方針を別工程で確認する必要がある。今回の実データは `CONDITIONAL` かつ `terrain_integration_ready=false`。既存runの取得バイトをSHAで確認して別の `run-04-review-replay` で再集計し、件数・標高差・タイル情報が `run-03` と一致することを確認した。

```powershell
New-Item -ItemType Directory -Force data/work/terrain-candidate-b | Out-Null
.venv/Scripts/python.exe -m ouem.terrain_candidate_b_preflight --output-dir data/work/terrain-candidate-b/run-repro-01
.venv/Scripts/python.exe -m pytest -q -ra tests/test_terrain_candidate_b_preflight.py tests/test_terrain_local_acceptance.py tests/test_standard_terrain.py
```

ブラウズ経路ではカタログHTMLが403だったが、Windowsの配信APIは200。最初の厳格実行 `run-02` は区部の未識別CRSで停止した。確定版は明示的な条件を満たす区部WKTについて比較診断を行い、`CONDITIONAL` を記録した。取得・検査に失敗した場合は `BLOCKED` とエラーを出す。Rawと実測成果物はGit管理外。既存の単一TIFF向けTerrain Native/Standardの構造検査はAOI被覆を保証せず、モザイクも生成しない。

区部の水平・鉛直メタデータを提供元に確認し、重複部の採用・境界処理をレビューしてからAOI用地盤入力を検討する。Terrain Native／Standard生成、モザイク、VoxCity、QGIS表示、Acceptanceは未実施。

関連pytestは26件通過（新規6件、警告11件）。全体pytestは `.venv/Scripts/python.exe -m pytest -q -ra --basetemp data/work/terrain-candidate-b/pytest-full` で1,206件通過、10件skip、339件警告（679.04秒）。skipは専用GIS/QGIS Python 5件とWindows symlink権限5件。ログは `data/work/terrain-candidate-b/full.log`。

ローカルの `audit.py`／`audit.log` では、AOI全セル中心を各TIFFの逆アフィンで行・列へ変換して有効マスクを再集計した。取得ファイルのSHA、最小4タイル集合、既存A2と同一SHAの再現Terrain、Mixed Standard GPKGの記録済みSHAも照合した。実測 `report.json` のSHA-256は `720c1d4b18a047b97bdc0d643bb2f7ad665ff23793f37ad89f01b0ae86ea5392`。

レビュー対応後は、集計例外・非有限集計値・統合可否の分離を合成テストで確認した。関連pytestは30件通過、警告11件。全体pytestは1,210件通過、10件skip、339件警告（719.37秒）。skipの内訳は上記と同じ。ログは `data/work/terrain-candidate-b/full-review.log`。
