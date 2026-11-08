# P1-1b — S/M/C LoD2形状検証

2026-11-08。基点main: `8cbaac6d474fa5770b31d8e2dba774f9b4e30ed5`（PR #171 merged）。
[P1-0](../P1-0_REPORT.md)と[P1-1a](../p1-1a/P1-1a_REPORT.md)の固定入力・エンジン・未解決事項を継承する。
今回の対象は三角形化と水密化まで。**voxel化、voxel marching、日陰・日射・GVI、地形統合は実行していない。**

## 結果と次工程への判断

S/M/Cすべてで、元LoD2の全polygon/ringと絶対Hを保持した三角形化が成立し、**mergeのみで水密solid**になった。
追加の補修を要する建物は今回の3棟には見つからなかった。

| 建物 | 入力・三角形化 | 水密化 | 追加補修 | 次の限定voxel実験 |
|---|---|---|---|---|
| S | PASS | PASS_MERGE_ONLY | 不要・未実施 | CONDITIONAL_REVIEW_REQUIRED |
| M | PASS | PASS_MERGE_ONLY | 不要・未実施 | CONDITIONAL_REVIEW_REQUIRED |
| C | PASS | PASS_MERGE_ONLY | 不要・未実施 | CONDITIONAL_REVIEW_REQUIRED |

形状に関する新たなBLOCKED建物はない。3棟とも次の限定実験の候補だが、voxel化の成立・形状近似は未検証であり、本PRのレビューと次工程の承認を待つ。
`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`、`terrain_integration_ready=false`。

## F/S/M/Cの比較

FはPR #171の保存診断を参照し、今回は再実行していない。頂点数の左側は面ごとの重複を含み、閉合頂点を除く。
各建物ともring数はpolygon数と同じで、穴は0だった。複雑な外形であるCを「穴のある建物」とは解釈しない。

| 建物 | Roof / Wall / Ground | polygon / ring | 穴 | 頂点（三角形化→merge） | 三角形（前後同数） | 元H範囲 m | 最大座標変化 m |
|---|---:|---:|---:|---:|---:|---|---:|
| F（保存結果） | 1 / 4 / 1 | 6 / 6 | 0 | 24→8 | 12 | 24.888792〜27.0858 | 1.723092282190919e-7 |
| S | 69 / 61 / 1 | 131 / 131 | 0 | 408→75 | 146 | 24.877753〜33.6846 | 1.7317506717517972e-7 |
| M | 30 / 57 / 1 | 88 / 88 | 0 | 284→56 | 108 | 24.607191〜32.38 | 1.7281126929447055e-7 |
| C | 12 / 25 / 1 | 38 / 38 | 0 | 128→28 | 52 | 24.821855〜32.0034 | 1.725638867355883e-7 |

全建物でmerge後の境界edge・非多様体edgeは0。S/M/Cでは`is_watertight=true`かつ`is_volume=true`となり、検証時の追加法線修正も不要だった。
これは元面・三角形の対応と限定的なsolid性の確認であり、現実の建物精度や任意の3D自己交差・意味的完全性まで認証するものではない。

## 固定入力とID

P1-0の[identity記録](../evidence/source_identity.json)と[SHA連鎖](../evidence/input_chain.json)を採用し、Run名から入力を選び直していない。
PR #171の[manifest](../p1-1a/manifest.json)が固定した以下3ファイルのSHAを実行前に要求し、各建物の処理後も同一であることを確認した。

| 入力 | SHA-256 |
|---|---|
| 元member `53393466_bldg_6697_op.gml` | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| Mixed-LoD Standard `standard.gpkg` | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |
| STEP 4-0対応監査 `report.json` | `71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e` |

| 建物 | source_id | ouem_id |
|---|---|---|
| S | `bldg_040379e5-dffb-40b6-a392-6396158211f5` | `oub-664a9132-cf36-52a5-96f5-577e78c91e59` |
| M | `bldg_2bd71700-a145-46ff-b14f-ad60394ff253` | `oub-cb250497-c12d-5fcc-9dca-e82c8b051398` |
| C | `bldg_2d5a9713-b02f-4903-9164-c5653e03494d` | `oub-10894413-4369-5131-ac0d-78ee9d234016` |

矩形ではなくXML Building IDで1棟ずつ選択し、対象IDの重複・欠落を拒否した。
全257 polygon IDが保存監査と一致。Standardのouem_id/LoD2、geometry BLOB SHA、保存済み一意face対応、各ringの頂点を照合した。
Nativeの再生成・再処理はなく、その対応はP1-0の固定監査を継承する。
全polygon ID、面種、ring頂点数・XYZ配列SHA、Standardとの対応、三角形数・被覆診断は建物別JSONに保持している。

- [S geometry diagnostics](S_geometry_diagnostics.json)
- [M geometry diagnostics](M_geometry_diagnostics.json)
- [C geometry diagnostics](C_geometry_diagnostics.json)
- [manifest・来歴・再現性](manifest.json)

## 三角形化の忠実性

`parse_polygon_to_triangles`を各LoD2面へ適用する前に、面種、有限XYZ、ringの閉合、外周1本と全内周を検証した。
返却頂点は元ring（閉合の重複を除く）を外周・内周順に連結したものと**完全一致**することを要求した。
さらに、建物全体の`extract_buildings_from_root(prefer_lod=2, max_lod=2)`の返却ID/LoDと、三角形座標multisetの完全一致を確認した。
他LoDへのfallback、別建物混入、頂点の新規作成・Hの変更はない。

水平変換はFと同じ既存関数を再利用した。EPSG:6697のlat/lon/Hから、XYのみEPSG:6668→6677へ変換し、HをPROJへ渡さず保持する。
StandardとのXY最大差は3棟とも0m、全H値は完全一致。ring開始点の循環移動・逆順は一意対応として記録する。
既存FのXY許容値1e-7mを継承し、今回の測定に合わせた変更はしていない。

独立した被覆検査では、metric XYZの外周法線の最大成分の軸を落として局所2Dへ投影し、Shapelyで元polygonと三角形unionを比較した。
元polygonの未被覆、外側へのはみ出し、三角形の重なりを別々に測定。穴があれば元polygonから除外した状態で比較し、exterior-only fallbackを拒否する。
数値面積予算は実データ実行前に定義した
`256 × eps(float64) × max(1, extent²) × (ring頂点数 + 三角形数)`。
これは局所座標での演算誤差検査であり、物理的形状誤差の許容値ではない。
全257面で未被覆・はみ出しは0、重なり最大はSで5.684341886080802e-14m²、Mで0、Cで8.881784197001252e-16m²で、各予算内だった。
非平面面の一意な曲面復元や現実の曲面精度を検証したものではなく、元頂点を使用する三角形化と投影支持の検査である。

## 水密化の処理と形状変化

auto cascadeを使わず、固定VoxCityGMLの`make_watertight_mesh(method="merge", precision=6)`を明示指定した。
実行時の関数hookで、各操作の入力/出力の頂点・三角形SHA、面積・体積・bounds・edge・solid性と配列変化を記録した。
3棟すべてのtraceは **`_merge_vertices` → `_validate_watertight`** の2段階のみ。

1. 読み込み・三角形化直後：面ごとの重複頂点を含み、index位相では非水密。
2. merge：metric座標を小数6桁へ丸め、重複頂点を結合しface indexを付け替える。全三角形の座標multisetを保持。
3. validation：既に水密・正のsolid。頂点配列もface配列も変更なし。`fix_normals`による変更は発生しなかった。

merge前後の比較では、6桁丸めで座標同定した三角形の追加・欠落は全棟0。
全固有H値も同一で、new_H/lost_Hは空。最大XY座標変化は比較表のとおり。
Fの`repair_correspondence`をそのまま再利用し、既定6桁丸めから導く **0.5e-6m/座標＋source 1 ULP**以内を要求した。
補修後の配列は元配列と異なるため、「原形状と同一の配列」とは扱わない。

trimesh repair、穴埋め、voxel marching、convex hullは一切実行していない。
mergeが成立しない場合だけ、明示的なtrimesh repairを診断用に記録する分岐を設けたが、結果を無条件に採用せず`BLOCKED_REPAIR_REVIEW`とする。
voxel marching/hullへ進む分岐はない。この診断分岐は今回の実データでは未使用であり、複雑補修の実データ妥当性をPASSとはしない。
既存import警告には「…voxel→hull」と表示されるが、P1-0で記録した警告文と実コードの差は残る。今回は明示methodと実traceで経路を限定した。

## 環境・不変性・再現性

独立P1環境のPython 3.11.9、VoxCityGML 0.3.0 / commit `19628c033b1cbbbdee80fe781f516672765d1eee`、
VoxCity 1.7.0 / commit `fa212656305328a9a657973bae26f352bfe813bc`を継続使用した。
VoxCityGMLはP1-0の29ソースSHA一致、VoxCityはPEP 610 commitと136ソースのRECORD一致を確認。
VoxCity側の確認はupstream Git treeとの独立全照合ではない。元VoxCityGMLソースのHEAD一致・cleanも確認した。
使用版はNumPy 2.4.6、trimesh 5.2.0、pyproj 3.7.2、Shapely 2.2.0、mapbox-earcut 2.1.0。
**新規install/upgradeはなく、MeshLibも不在**。ライセンスはP1-0/P1-1aのCONDITIONALと残余課題を継承し、再配布条件の解決とは扱わない。

Fのrunner・tests・旧成果物は変更していない。今回のrunnerからFの読み取りhelperだけを利用し、Fの実験処理・voxel APIは呼び出していない。
OUEMとP1両venvのパッケージ版/METADATA・pyvenv.cfgが実行前と各建物の処理後で一致した。環境全ファイルのbytewise監査ではない。
入力3ファイル・参照証拠・F runnerの前後SHA一致を確認し、共有入力/環境の変化は後続建物も含め停止する条件としている。
建物固有の形状不整合はその建物を停止し、他の独立建物については別判定を残す。
実行中はsocket接続/名前解決と保護対象への書込openを拒否し、記録された試行は0。
これはOS全体の通信/全syscall監査ではない。directory parserを使わず、入力横cache経路を避け、cache先は新規run内へ指定した。

最終実装で、新規run `p1-1b-final-d` / `p1-1b-final-e`へ独立プロセス実行。
両manifestと、建物別の元三角形・merge後の頂点/face NPYおよび診断JSONの**全15出力SHAが一致**した。
NPY再読込でshape・有限性・頂点/face数・配列SHAも確認した。
初期確認runおよびtrace追加前/最終停止制御追加前のrunは再現性の組から除外し、既存runを上書きしていない。
公開JSONはLFへ正規化し、元ローカル出力のSHAと公開ファイルのSHAをmanifestで分けている。
元XYZ、XML、NPY、環境、cacheはGitへ登録しない。

## テストと再実行

[限定runner](../../../../src/ouem/p1_lod2_smc.py)と[独立合成pytest](../../../../tests/test_p1_lod2_smc.py)を追加した。
F既存回帰を含む関連pytestは **18 passed**（新規10＋既存F 8）。失敗・skip・警告なし。
合成fixtureでは、穴を持つ面の支持とexterior-only拒否、欠落/重複/不正三角形、H変更、厳密ID・LoD、
repair traceの明示methodとhook復元、SHA改変拒否、途中失敗の完了誤認防止を検証した。
合成の穴検証を、実建物の穴保持検証として数えない。ローカル全体pytestは未実行。
Windows/Ubuntuの既存Actions・合格条件を維持し、PRでの全体回帰をmerge前ゲートとする。CI完了は本記録時点で未確認。

再実行は独立P1 Python、リポジトリroot、`PYTHONPATH=src`、`PROJ_NETWORK=OFF`、`PYTHONDONTWRITEBYTECODE=1`で行う。
`MPLCONFIGDIR`/`NUMBA_CACHE_DIR`は新規run配下へ指定する。

```text
-B -m ouem.p1_lod2_smc
  --member data/work/mixed-lod-converter-bridge/run-02/extracted/udx/bldg/53393466_bldg_6697_op.gml
  --standard data/work/mixed-lod-standard/run-02/standard.gpkg
  --audit-report data/work/step4-0-roof-audit/audit-final-e/report.json
  --output data/work/voxcitygml_p1/<new-run>
```

次のvoxel実験では今回の水密meshが候補となるが、P1-1aで確認した接触shell近似、軸・原点・絶対H維持、無DEM/無外部取得の制御は別途必要。
本PRだけでvoxel化や環境評価の成功、科学的妥当性、正式Acceptanceを宣言しない。

Documentation Impact: 新しい限定runner・独立tests・本記録と建物別診断/manifestのみ。
正式Concept/Standard/Adapter、ロードマップ、旧Acceptance、FやSTEP 2/3/4成果物を変更せず、Draft PR作成後は停止する。
