# P1-1a — F建物のLoD2最小3D検証

2026-11-07。基点main: `40832eb64b41d3e9f6dabcf63b2b68eaed81c1c0`（PR #170 merged）。
[P1-0](../P1-0_REPORT.md)の過去の判定・未解決事項を変更せず、今回明示的に許可された独立環境の導入とF限定実験を記録する。

## 結果

| 項目 | 判定 | 検証した範囲 |
|---|---|---|
| P1-1a_ENVIRONMENT | **PASS** | 独立venvで両エンジンimport、固定ソース照合、使用した低位API、pip checkが成立。全APIの互換性保証ではない。 |
| P1-1a_SOURCE_IDENTITY | **PASS** | XML IDでFだけを抽出。保存監査の6 polygon ID、Standardのsource_id/ouem_id/LoD2、全ringとの一意対応を確認。 |
| P1-1a_GEOMETRY | **PASS（結合変化を明記）** | 6四角形→12三角形。重複頂点結合により24→8頂点。全三角形の座標対応を保持し水密化。原形状と補修配列は別物。 |
| P1-1a_VERTICAL | **PASS（元H保持のみ）** | XYだけを投影し、元のH値をそのまま保持。DEM、鉛直変換、再アンカーなし。基準実現・時点・精度は未検証。 |
| P1-1a_VOXEL | **PASS（mesh-only）** | 無MeshLibの既存低位APIで1m、shape=(6,15,6)、建物156セル。地盤も環境評価も生成していない。 |
| P1-1b_READY | **CONDITIONAL（レビュー待ち）** | Fの限定接続は成立。次工程の条件・形状近似・ライセンス残余課題のレビューが必要。追加実験へ自動進行しない。 |

`scientific_validation=NOT_VERIFIED`、`formal_acceptance=NOT_VERIFIED`、`terrain_integration_ready=false`。

## 入力・対応関係

- source_id: `bldg_09532951-4dab-457d-b1c6-56d509900d1b`
- ouem_id: `oub-c56cb020-c11c-5f9c-a37f-73018266a333`
- 元member: `53393466_bldg_6697_op.gml`。矩形選択ではなく、XML Building IDの一致を要求。対象IDの重複も拒否。
- 元CityGML SHA: `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9`
- Mixed-LoD Standard SHA: `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60`
- STEP 4-0 report SHA: `71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e`

来歴の既存照合範囲は[P1-0入力連鎖](../evidence/input_chain.json)、Fの対応は[既存identity記録](../evidence/source_identity.json)を参照。
今回の実入力3ファイルを上記固定SHAと照合し、処理後も一致した。
Nativeを再生成せず、SHA固定のSTEP 4-0一意face対応を継承し、元XML→Standardの全ring対応を今回再検証した。

RoofSurface 1、WallSurface 4、GroundSurface 1。各面は閉じた外周ring 1、穴0、頂点4（閉合を含め5）。
全polygon ID、面種、Standard ringの循環開始点・逆順対応、三角形indexは[geometry_diagnostics.json](geometry_diagnostics.json)に保持。
元XYZはローカル成果物に残し、Git公開版ではringの頂点数・SHA・原polygon参照へ縮約した。公開JSONと元JSONのSHAは区別している。
穴のある実建物での保持は未検証であり、本Fプロファイルに予期しない穴が現れた場合は停止する。

## 環境・依存・ライセンス

独立P1 venvのみへ導入。Python 3.11.9、VoxCityGML 0.3.0、VoxCity 1.7.0。
固定commitはそれぞれ `19628c033b1cbbbdee80fe781f516672765d1eee` と `fa212656305328a9a657973bae26f352bfe813bc`。
元GMLソース作業ツリーはcleanのまま。固定commitのgit archiveコピーをビルドし、導入された29 PythonファイルをP1-0の固定ソースSHAと照合した。
VoxCityはPEP 610 commitと136ソースのRECORD整合を確認。これはupstream Git tree全体との独立照合ではない。
NumPy 2.4.6、Numba 0.68.1、trimesh 5.2.0、pyproj 3.7.2、mapbox-earcut 2.1.0。

元dependency-plan SHA `b620d3bf18b80b6b9220404f8f480cbecaaf704a9d9f8a1b09a079d3686e06bf`を採用。
211 runtime候補は両エンジンと209通常依存。上流が通常依存として宣言するnotebook/可視化パッケージも含むが、GPU/mesh/dev等のoptional extrasは追加していない。
壊れた依存環境での実行を避けるため、固定された通常依存の閉包を導入した。pip/setuptoolsを含む導入後総数は213。
209 artifactを元URL・SHAで固定して取得し、`--no-deps --require-hashes`で導入。エンジンは固定ソースから`--no-deps`で導入した。
3件のsdist（py-vox-io、reverse_geocoder、timezonefinder）は一時的なbuild isolationでmetadata/wheel生成を行った。ビルド用一時依存の全バージョン固定は未実施であり、環境を別マシンで再構築した際のwheel同一性までは主張しない。
`pip check`: **No broken requirements found**。MeshLibは導入・importしていない。

209 artifactのMETADATA/PKG-INFOと同梱LICENSE/NOTICEを一次確認し、全件にlicense表記・classifier・noticeのいずれかを確認。
[artifact一覧](dependency_artifacts.csv)は取得物SHAとSPDX/classifier/notice数を記録する。空欄は商用利用禁止の意味ではない。
VoxCityGML本体MITを継承。pycountry LGPL-2.1-only、fqdn MPL-2.0、timezonefinder-data ODbL-1.0等の条件は消えない。
reverse_geocoder 1.5.1のsdistは「lgpl」表記のみでLICENSE未同梱。
[上流LICENSE](https://github.com/thampiman/reverse-geocoder/blob/master/LICENSE)のLGPL-2.1を参照したが、このmasterの本文を当該配布版と一意に結び付けたとはしない。
変更・依存バイナリ再配布を伴わないローカル実験を止める明確な条件は見つからなかった、という限定判断である。
再配布・組込みデータ・第三者同梱物の最終的な法的確認は**CONDITIONAL**。Gitには依存バイナリ、環境、元データを含めない。

既存OUEMの215パッケージはP1-0時点の版一覧と一致。実形状処理前後でMETADATAとpyvenv.cfgのSHAも一致した。
これは環境全ファイルのbytewise監査ではない。既存OUEM環境に対するinstall/upgradeは行っていない。

## 座標・三角形化・補修

元EPSG:6697のlat/lon/Hから、水平EPSG:6668→6677を`always_xy=True`で変換。
PROJへHを渡さず、H配列をそのままコピーする。StandardとのXY最大差は0m、Hは完全一致。
XY照合許容値1e-7mは既存source-H契約から継承し、今回の結果へ合わせていない。
エンジンには経緯度/ECEFではなく、明示した投影metric XYZを低位APIへ渡した。高位pipelineは使用していない。

元H範囲は24.888792〜27.0858m。各四角形のring頂点を保った三角形化で、24頂点・12三角形となる。
面ごとに重複頂点を持つ読み込み直後のmeshは、index位相上は非水密。
実際の補修は`make_watertight_mesh`の**merge**で、8頂点・12三角形の水密solidとなった。
6桁丸め・重複頂点結合とwindingの変更を許して全三角形の座標multiset一致を検査した。面の追加・消失・再三角形化はない。
最大座標変化は **1.723092282190919e-7m**、全固有H値は完全一致。
許容境界は固定実装の6桁丸めから導いた0.5e-6m/座標＋source 1 ULPであり、実測結果から調整していない。
面積107.8527971277263→107.85279712009044m²、符号付き体積51.11014714164776→51.11014713677772m³。

trimesh repair、穴埋め、voxel marching、convex hullへの補修段階の移行は発生していない。
import時の既存警告は「merge→trimesh repair→voxel→hull」と表示するが、P1-0で確認した通りauto実装はhullを除外する。警告文と実行traceを混同しない。
本runnerはmerge以外へ移行すればvoxel実行前に停止する。補修後を原形状と同一とは扱わない。

## 最小voxel検証

使用API: `voxcitygml.voxelizer3d._voxelize_building_solid`。**固定commitのprivate低位API**であり、安定した公開契約とはしない。
VoxCity本体の建物height-grid Voxelizerは今回使用していない。
CPU 2 threads、voxel size=1m、class=-3、初期配列はAIRのみ。
X=[-22583,-22568]、Y=[-39851,-39845]、絶対Z=[23,29]m、shape=(row=6,col=15,z=6)。
中心位置はX=min_x+(col+0.5)、Y=max_y−(row+0.5)、H=min_z+(z+0.5)。rowは南向き、colは東向き、zは上向き。
鉛直原点23mは元Hから取った明示的な格子境界であり、地盤への再アンカーやHの減算ではない。

実traceは`repair:merge`→`occupancy:True`。voxel内で再度実行されるmerge結果も診断済み配列のSHAと一致した。
既定occupancy_threshold=0、subdivisions=3。既存APIのZ parity内部充填とtriangle-box接触shellの和集合で156セル。
この接触shellは境界セルも含むため、156m³というセル総体積を原solid体積51.11m³の保存・精度検証とは扱わない。
sealed-surface fallbackは実行時に禁止し、実際にも発生していない。
元配列の前後SHA、NPY保存後の再読込一致を確認した。

DEM、ゼロ地盤代替、水面補正、land-cover、canopy、外部データ取得、日陰・日射・GVIは実行していない。
実験開始後はsocket接続/名前解決と保護対象への書込openをaudit hookで拒否し、記録された試行は0。
入力横cacheを作るdirectory parserを使用せず、Numba/Matplotlib cacheは各新規run内へ指定した。
hookはOS全体の通信・全filesystem syscallを監査する仕組みではなく、入力不変性は別途SHAで検証した。
依存取得時の許可された通信と、geometry実行時の無通信制御は区別する。

## 再現・テスト・残余条件

Git管理外の新規run `p1-1a-final-b` / `p1-1a-final-c`で独立プロセス実行。
両manifestと、F-only XML・元三角形配列・補修配列・voxel配列・診断の全7出力SHAが一致。
初期run-aは修正前の実装SHAを持つ開発確認runで、最終再現性の組には採用していない。既存runは上書きしていない。
ローカル大容量成果物の識別・SHAと公開縮約JSONのSHAは[manifest](manifest.json)で区別する。

[runner](../../../../src/ouem/p1_lod2_f.py)と[独立合成テスト](../../../../tests/test_p1_lod2_f.py)を追加。
関連pytestは**8 passed**。ID混入/重複、LoD fallback、面/ring/穴不整合、XY/H保持、結合の面消失・H変更、途中失敗の完了誤認を検査。
既存OUEM venvで合成テストのみ実行し、実F処理は独立P1 venvで実行した。
ローカル全体pytestは未実行。既存Windows/Ubuntu GitHub Actionsを変更せず、merge前の全体回帰ゲートとする。CI結果はPRで別途確認する。

再実行は独立P1 Pythonで、リポジトリrootを作業位置、`PYTHONPATH=src`、`PROJ_NETWORK=OFF`、
`NUMBA_CACHE_DIR`/`MPLCONFIGDIR`を新規run配下に設定し、次の引数を指定する。

```text
-B -m ouem.p1_lod2_f
  --member data/work/mixed-lod-converter-bridge/run-02/extracted/udx/bldg/53393466_bldg_6697_op.gml
  --standard data/work/mixed-lod-standard/run-02/standard.gpkg
  --audit-report data/work/step4-0-roof-audit/audit-final-e/report.json
  --output data/work/voxcitygml_p1/<new-run>
```

新規環境再構築のruntime版・取得物SHAはartifact一覧と固定commitを参照。完全なビルド環境再現lockの提供ではない。
今回のFは穴なし・単純solidに限定され、他建物、薄部、穴、複雑屋根への一般化は未検証。
P1-1bではprivate API依存と接触shell近似の扱い、必要な形状許容条件、配布を伴う場合のライセンス条件を独立レビューする。
科学的なHAG、現実の形状精度、環境評価の正しさを本結果から認証しない。

Documentation Impact: 本実験記録・証拠と限定runner/testsのみ。
正式Concept、Building/Terrain Standard、Adapter、ロードマップ、旧AcceptanceとSTEP 2/3/4保存成果物は変更していない。
