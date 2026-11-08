# P1-1c — F/S/M/C voxel化と形状近似診断

2026-11-08。基点main `f6b5d78fb921bff9a8115595c88f1bc30f1f1860`（PR #172 merged）。
[P1-0](../P1-0_REPORT.md)、[FのP1-1a](../p1-1a/P1-1a_REPORT.md)、[S/M/CのP1-1b](../p1-1b/P1-1b_REPORT.md)の固定入力と未解決事項を継承する。

## 結果と判定

**4棟すべてでmesh-only voxel化が成立し、Fの1m配列は保存P1-1aと完全一致した。**
一方、voxel集合は元solidより大きく、特に薄いFで過大側の近似と格子依存性が大きかった。
0.5mでは全棟の体積比が1に近づいたが、精度の十分性を認証する結果ではない。

| 建物 | Technical execution | 形状近似の評価 | 環境解析への移行 |
|---|---|---|---|
| F | PASS_MESH_ONLY | 診断実施。1m体積比3.0522、0.5mでも1.8196。サンプリング偏りも大きい | CONDITIONAL_REVIEW_REQUIRED |
| S | PASS_MESH_ONLY | 診断実施。1m体積比1.4384、0.5mは1.1975 | CONDITIONAL_REVIEW_REQUIRED |
| M | PASS_MESH_ONLY | 診断実施。1m体積比1.5229、0.5mは1.2122。境界上サンプルあり | CONDITIONAL_REVIEW_REQUIRED |
| C | PASS_MESH_ONLY | 診断実施。1m体積比1.5546、0.5mは1.2565 | CONDITIONAL_REVIEW_REQUIRED |

形状近似には合格閾値を設けていない。技術的PASSと、幾何近似の診断・科学的精度・環境解析の適格性を分ける。
`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`、`terrain_integration_ready=false`。
日陰・日射・GVI・地形統合は実行していない。

## 固定入力と再照合

元member、Standard、STEP 4-0対応reportはP1-1a manifestの固定SHAを要求した。

| 入力 | SHA-256 |
|---|---|
| `53393466_bldg_6697_op.gml` | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| `standard.gpkg` | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |
| STEP 4-0 `report.json` | `71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e` |

保存meshは、公開P1-1a/P1-1b manifestが固定した**ローカルmanifest SHAと各成果物SHA**から同定した。Run名だけで採用していない。
FはP1-1aの元三角形/補修配列/旧voxel、S/M/CはP1-1bの元三角形/merge配列を読み取り専用で使用した。
元CityGMLから各Building IDを厳密に再抽出し、Standardのouem_id・LoD2・BLOB SHA、全polygon ID、各ring XYZを再照合。
XYだけをEPSG:6677へ投影しHを保持して再三角形化し、保存元三角形配列との完全一致を要求した。
建物全体のextractorもID/LoDと三角形座標multisetを確認し、別建物・他LoDへのfallbackを認めていない。
再構築・照合だけを新規実行し、過去の保存ファイルは変更・上書きしていない。

| 建物 | source_id | ouem_id | Roof/Wall/Ground | 三角形数 |
|---|---|---|---:|---:|
| F | `bldg_09532951-4dab-457d-b1c6-56d509900d1b` | `oub-c56cb020-c11c-5f9c-a37f-73018266a333` | 1/4/1 | 12 |
| S | `bldg_040379e5-dffb-40b6-a392-6396158211f5` | `oub-664a9132-cf36-52a5-96f5-577e78c91e59` | 69/61/1 | 146 |
| M | `bldg_2bd71700-a145-46ff-b14f-ad60394ff253` | `oub-cb250497-c12d-5fcc-9dca-e82c8b051398` | 30/57/1 | 108 |
| C | `bldg_2d5a9713-b02f-4903-9164-c5653e03494d` | `oub-10894413-4369-5131-ac0d-78ee9d234016` | 12/25/1 | 52 |

全263面の対応を確認。全棟穴0であり、穴のある実建物への適用は未検証。
比較referenceは、原LoD2の全三角形を保持する**保存merge-only水密solid**。6桁丸めによる微小XY変化を含み、Raw配列と同一ではない。
P1-1a/P1-1bの丸め境界（0.5e-6m/座標＋source 1 ULP）をそのまま使用し、今回の結果に合わせて変更していない。H値は完全一致。

## voxel化経路と格子

固定VoxCityGML commit `19628c033b1cbbbdee80fe781f516672765d1eee`のprivate低位API
`voxcitygml.voxelizer3d._voxelize_building_solid`を使用した。
`make_watertight_mesh`を実行時にmergeへ限定し、返却頂点/face配列が保存mergeと完全一致することを要求。
内部処理の三角形座標も、順序・向きを除いて**丸めなしの完全一致**を要求した。
実traceは全12条件で `repair:merge` → `occupancy:True`。
sealed-surface fallbackは禁止し、想定外補修・面欠落・H変更を検出すればその建物を停止する。
MeshLib、trimesh repair、voxel marching、convex hullは使用していない。
警告文にある「…voxel→hull」はP1-0からの既知の説明不整合で、今回の実traceを表すものではない。

内部観測に使ったprivate APIも固定commit依存である：
`_voxelize_by_occupancy`、`_z_scanline_fill`、`_surface_voxelize_numba`。
エンジン本体は変更せず、実行時hookは終了/例外時に復元する。

- **scanline fill**：XYセル中心に既定jitter（X=0.00137h、Y=0.00098h）を加えた+Z rayの交差をparityで組み、lower/upper Zをfloorして両端を含む層を充填する。これは「セル全体がsolid内部」という分類ではない。
- **contact shell**：triangle-box接触判定。半幅は`h/2 + h*1e-6`で、面がセル壁に接すれば両側のセルが入ることがある。
- **出力**：fillとshellの和集合。両マスクを別々に保存し、和集合が最終占有と完全一致することを確認した。
- `occupancy_threshold=0`、`occupancy_subdivisions=3`は既定条件。threshold=0なのでshellの占有率filterは非作動。後述の独立サンプリング密度とは別設定。

座標はmetric EPSG:6677 XY＋元の絶対H。row南向き、col東向き、z上向き。
中心は `X=min_x+(col+0.5)h`、`Y=max_y−(row+0.5)h`、`H=min_z+(z+0.5)h`。
基準格子の各軸下限は`floor(元頂点min)−1`、上限は`ceil(元頂点max)+1`。
min_zは絶対Hの格子境界であり、地盤高でも建物Hの減算anchorでもない。

| 条件 | 解像度 | 格子範囲・位相 |
|---|---|---|
| 1m | 1m | 上記基準格子。Fの範囲・shape・配列はP1-1aと一致 |
| 0.5m | 0.5m | 基準と同じ物理範囲・原点。各軸セル数を2倍 |
| 1m_shift_xyz | 1m | 基準の上下限をXYZそれぞれ+0.5m。meshの座標/Hは移動しない |

位相条件では外枠も移るが、各条件内で元solidとvoxelを**同じ絶対座標・評価枠**で診断し、solid全体の被覆を要求した。
各条件で同位相の格子を全方向1セル拡張して再実行し、元領域の配列完全一致と、追加領域の占有0を確認した。
比較差が領域切断によるものではないことを検査している。異なる格子の配列indexを直接対応付けてはいない。
XYZ同時移動の1条件だけなので、どの軸の位相がどれだけ寄与したかは分離できない。

## 体積・境界・空間一致の比較

referenceの数値体積は三角形solidの符号付き体積：F **51.110147**、S **1590.649217**、M **578.489287**、C **398.823460 m³**。
これは現実の建物の真値ではない。
下表のvoxel体積は非重複セル集合の`N×h³`であり、**正確な建物体積として扱わない**。

| 建物 | 条件 | 占有セル数 | voxel集合体積 m³ | voxel/reference体積比 | 参考推定IoU（q=2） |
|---|---|---:|---:|---:|---:|
| F | 1m | 156 | 156.000 | 3.0522 | 0.2917 |
| F | 0.5m | 744 | 93.000 | 1.8196 | 0.5013 |
| F | 1m_shift_xyz | 117 | 117.000 | 2.2892 | 0.3889 |
| S | 1m | 2288 | 2288.000 | 1.4384 | 0.6805 |
| S | 0.5m | 15239 | 1904.875 | 1.1975 | 0.8204 |
| S | 1m_shift_xyz | 2120 | 2120.000 | 1.3328 | 0.7344 |
| M | 1m | 881 | 881.000 | 1.5229 | 0.6669〜0.6677 |
| M | 0.5m | 5610 | 701.250 | 1.2122 | 0.8423 |
| M | 1m_shift_xyz | 814 | 814.000 | 1.4071 | 0.7217〜0.7227 |
| C | 1m | 620 | 620.000 | 1.5546 | 0.6224 |
| C | 0.5m | 4009 | 501.125 | 1.2565 | 0.8056 |
| C | 1m_shift_xyz | 598 | 598.000 | 1.4994 | 0.6453 |

0.5m化で全棟の過大側体積比が減少したが、1への収束率や必要解像度はこの2解像度だけでは決められない。
1mの半セル位相移動だけで、体積はF−25.0%、S約−7.34%、M約−7.60%、C約−3.55%変化した。
薄いFでは1mに対する形状寸法が小さく、境界層の相対的影響が大きい。一般的な精度保証には外挿しない。

| 建物（1m） | shape(row,col,z) | scanline fill | contact shell | 両者の重なり | shellのみ |
|---|---|---:|---:|---:|---:|
| F | (6,15,6) | 96 | 138 | 78 | 60 |
| S | (15,26,12) | 1874 | 1071 | 657 | 414 |
| M | (14,16,11) | 669 | 520 | 308 | 212 |
| C | (12,12,11) | 499 | 365 | 244 | 121 |

shellはAPIが面との接触を検出したセルであり、「セル全体が誤占有」や「正確な境界体積」と同義ではない。
独立サンプルの内部/外部が混在するセル数、内部サンプルがない占有セル数も診断JSONに記録したが、これもサンプル由来の境界proxyである。

## 独立した参考推定と限界

エンジンのZ ray/SATを流用せず、各点から全三角形への**向き付き立体角和**で内外を分類する診断oracleを実装した。
各セル内q×q×qの等間隔中点を処理域全体に配置し、solid内部/外部とvoxel占有を比較する。
全条件q=2、1mだけq=3も実行。ROI切出しや占有セルだけのサンプリングではなく、空セルも含めて欠落を診断した。
実際の境界上点や、数値的に0/1のwindingへ確定できない点は曖昧として残し、内部や外部へ暗黙に置換しない。
平面距離予算は座標ULPとfloat64 eps・mesh寸法、barycentric予算は三角形conditioning、winding整数判定予算は`1024×eps×三角形数`から事前定義した。
実測に合わせた幾何誤差の合否閾値ではない。

交差量TP、voxel過剰量FP、solid取りこぼしFNをサンプル体積重みで推定し、`IoU=TP/(voxel集合体積+FN)`とした。
表やJSONの区間は**曖昧サンプルをどちらに割り当てるかだけの幅**であり、求積誤差の保証区間・統計的信頼区間ではない。
Mの1m/q=2と位相移動/q=2では境界上6点が残り、それぞれ0.75m³分の幅になる。

全条件で内部なのにvoxel非占有となる**サンプル**は0だった。しかしsolid全体の厳密包含は証明していない。
1m/q=2での過剰体積参考推定はF110.5、S731.125、M292.75〜293.5、C234.125m³。
これらは真の差体積ではなく、中点求積に依存する。
特に薄いFは、推定solid体積45.5m³（q=2）、46.6667m³（q=3）がreference51.1101m³を下回り、q=2では約11%の差が残った。
0.5m/q=2でもFの推定solid体積は46.625m³で、十分な求積収束を確認したとはいえない。
これは実際のH区間と規則的中点列の位置関係に敏感なaliasingの診断であり、参考IoUを厳密値として提示しない。
各条件に推定solid体積−reference体積を併記し、この偏りを隠していない。

1mでq=2→3とした参考IoUは、F 0.2917→0.2991、S 0.6805→0.6832、M 0.6669〜0.6677→0.6488、C 0.6224→0.6596。
サンプル密度を増やせば単調に改善するとは限らない。真のsolid/voxel交差を厳密に積分する実装は今回行っていない。

## 負荷・再現性・保護条件

最初の1m試行で、case時間は約0.38〜6.45秒（最初のNumba compileを含むFが最大）だった。
その後の追加を0.5mと1m半セル位相の2条件だけに限定した。最大配列はS/0.5mの(30,52,24)、37,440セル。
最大単一サンプリングは299,520点で、solid-angle計算は512点ずつに分割した。メモリピークは実測していない。
Numbaは2 threads。最大200,000セルの固定資源guardを持ち、精度条件の緩和に使っていない。

最終2runのcase時間合計は約19.92/19.88秒、case CPU時間合計は約20.94/20.84秒、最大単一caseは約6.19秒。
これらはvoxel化・padding QA・保存・サンプリングの時間で、Python起動/import・入力照合・XML読込を含むE2E総時間ではない。
初回Numba compileの影響があるため、最初のkernel時間とwarm後のkernel時間を混同しない。
[実測時間](timing_diagnostics.json)に2回分を記録した。

独立P1環境のPython 3.11.9、VoxCityGML 0.3.0、VoxCity 1.7.0（固定commit `fa212656305328a9a657973bae26f352bfe813bc`）を継続利用。
VoxCityGMLはP1-0の29ソースSHA、VoxCityはPEP 610と136ソースRECORDを照合。後者はupstream Git treeとの独立全照合ではない。
新規依存導入・upgradeなし。ライセンスはP1-0/P1-1aのCONDITIONALと残余課題を継承する。

元Hを保持し、DEM・ゼロ地盤代替・land-cover/canopy取得・水面補正・高位pipelineは使用していない。
実行中はsocket接続/名前解決と保護対象への書込openを拒否し、記録された試行0。
これはOS全体の通信/全syscall監査ではない。入力・旧runのSHA、OUEM/P1のパッケージMETADATA/pyvenv.cfg不変も建物ごとに確認した。
環境全ファイルのbytewise監査ではない。Numba/Matplotlib cacheは新規run配下へ指定し、旧入力横cacheを作るparserを呼ばない。

最終証拠は新規run `p1-1c-final-d` / `p1-1c-final-e`。
両manifestと、12条件のvoxel/fill/shell NPY＋4建物診断JSONの**全40出力SHAが一致**した。
NPY保存後の再読込一致、公開時のshape・占有数・配列SHA・fill/shell和集合も確認した。
時間値は非決定的なのでこの40出力には含めず、別ファイルとして各runの元時間記録SHAも公開manifestに記録する。
初期1m試行は4棟の処理自体が成立したが、manifest参照先の相対/絶対パス整形不備でglobal BLOCKEDとなった。
通常の保存処理の不備を修正し、完成証拠に使用していない。その他の開発確認runも最終再現性の組に含めず、旧runは上書きしていない。

## 成果物・テスト・次工程

- [F voxel diagnostics](F_voxel_diagnostics.json)
- [S voxel diagnostics](S_voxel_diagnostics.json)
- [M voxel diagnostics](M_voxel_diagnostics.json)
- [C voxel diagnostics](C_voxel_diagnostics.json)
- [manifest・入力/コード/出力SHA・再現性](manifest.json)
- [限定runner/独立診断oracle](../../../../src/ouem/p1_mesh_voxel.py)
- [独立合成テスト](../../../../tests/test_p1_mesh_voxel.py)

関連pytestは**27 passed（新規9＋既存P1 18）**。失敗・skip・警告なし。
解析解のあるcube、平行移動、傾斜tetrahedron、空洞、境界点、体積/過剰/欠落、軸/位相、
fill/shell観測とhook復元、1e-8mの意図しないH変更拒否、途中失敗の完了誤認防止を確認した。
OUEM venvでは合成テストのみ、実建物処理は独立P1 venvのみ。ローカル全体pytestは未実行。
既存Windows/Ubuntu Actions・合格条件を維持し、merge前の全体回帰ゲートとする。CI完了は本報告時点で未確認。

再実行は独立P1 Python、リポジトリroot、`PYTHONPATH=src`、`PROJ_NETWORK=OFF`、`PYTHONDONTWRITEBYTECODE=1`。
cache先は新規run配下に指定する。

```text
-B -m ouem.p1_mesh_voxel
  --member data/work/mixed-lod-converter-bridge/run-02/extracted/udx/bldg/53393466_bldg_6697_op.gml
  --standard data/work/mixed-lod-standard/run-02/standard.gpkg
  --audit-report data/work/step4-0-roof-audit/audit-final-e/report.json
  --archive-a data/work/voxcitygml_p1/p1-1a-final-b
  --archive-b data/work/voxcitygml_p1/p1-1b-final-d
  --output data/work/voxcitygml_p1/<new-run>
```

まず`--comparisons`なしで1mだけを計測し、負荷確認後に`--comparisons`を指定すると今回の3条件になる。
元CityGML・GPKG・XYZ・NPY・環境・cacheはGit管理外。公開JSONはLF正規化し、元出力SHAと公開ファイルSHAを分ける。

次の環境解析では、近似が大きいセルや格子位相の影響を前提に、採用解像度・占有規則とその限界をレビューする必要がある。
観測点、太陽方向、遮蔽物としての扱い、padding/context、無DEMの鉛直条件は未検証であり、voxel技術PASSから自動的に解析へ進めない。
Documentation Impact: 新規の限定runner・独立tests・本実験記録/診断のみ。正式設計、Standard、ロードマップ、旧Acceptance、旧runner/成果物は変更していない。
Draft PR提出後は停止し、追加実験・マージ・次工程には進まない。
