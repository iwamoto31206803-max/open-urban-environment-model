# P1-2a — 日陰比較実験の条件確認・仕様草案

Status: **DRAFT / レビュー前。正式設計・Standard・Acceptanceの変更ではない。**
2026-11-08、main `59f331ef3717c042784c1f2ccbc8b4c10991e2fa`（PR #173 merged）。
今回行ったのは保存JSON/NPY/SHAの読取・整合確認と静的なソース調査のみ。
**新しいvoxel化・形状処理・日陰/日射/GVI計算、依存導入、実装・テストコード追加は行っていない。**

## 1. 調査判定と比較の問い

| 項目 | 判定 | 意味 |
|---|---|---|
| 入力・保存baseline | PASS（読取照合） | STEP 4-C manifestと125成果物、P1保存連鎖、選択した上流・実装を照合。不一致0 |
| 太陽・既存観測点 | PASS（保存値・静的定義） | 保存ベクトルが180°/45°と記録されたgrid bearingの式に一致。A/BのXYZ・mask・地盤が一致 |
| 保存Cの直接流用 | **BLOCKED** | 範囲・鉛直位相が異なり、bare mesh配列には自動観測点を作る地表面クラスがない |
| 同じray核での比較 | CONDITIONAL | 同一ソースを確認。明示起点adapterとA/B再現controlは未実装・未実行 |
| P1-2b_READY | **CONDITIONAL_REVIEW_REQUIRED** | 下記1m限定案、mask規則、controlと停止条件のレビュー承認後に進む。現時点の実行はNOT_EXECUTED |

比較するのは以下の3モデルである。

- **A**：建物内で一定の代表上端H＝保存cell_max Hの最大値を使用した2.5D。
- **B**：保存cell_max Hをセル別に使用した2.5D。
- **C**：固定PLATEAU LoD2の全三角形と元Hを保持したmerge-only solidを、VoxCityGMLでvoxel化した実験的3D表現。

Cはground truthではない。A/B/Cの差は、屋根/底面/張り出し等の形状表現と、水平支持・地盤押出し・鉛直量子化・contact shellの違いを含む。
3モデルの比較だけで、屋根幾何だけの因果効果へ完全に分離することはできない。
日陰精度の合格閾値、Cに近い方を正しいとする規則、最良IoUを得る解像度の選択は設けない。

## 2. 入力とmanifest/SHA対応

基準文書は[STEP 4-C](../../height_distribution/STEP4C_REAL_LOD2_SHADOW_COMPARISON.md)、
[P1-0](../P1-0_REPORT.md)、[P1-1a](../p1-1a/P1-1a_REPORT.md)、
[P1-1b](../p1-1b/P1-1b_REPORT.md)、[P1-1c](../p1-1c/P1-1c_REPORT.md)。
Run名はlocatorであり、選択の根拠は次の固定SHAとmanifest内の各output SHAである。

| 参照 | locator / SHA-256 |
|---|---|
| A/B保存manifest | `data/work/step4c-roof-shadow/final-c/manifest.json` / `82488e2807a0cbc95cb528d25a38bc77a2e4a1c3181122a091f75c2ec7eb7c8e` |
| A/B保存report | 同runの`report.json` / `c84599fdca7b20828702b314d1e1a863695567b30e3d670fcd23fddca4a4227e` |
| STEP 4-A manifest | `f73e65073ed823b9155cc75a93a4cfdbc314fb9a0f1859f4d635ec5e71a952bd` |
| STEP 4-B2 manifest | `9f564e7d2e06c74301fdcf3670d6f60e2a531e628cfb36de882d8dec6f286817` |
| STEP 4-0 manifest | `14498ba34826c2b68c2a22c29da6fcbeb8bc696e20b68f799d8a8cca0a41a852` |
| P1-1a保存manifest | `data/work/voxcitygml_p1/p1-1a-final-b/manifest.json` / `d140473154cc234a05fa42a55241fa59dee32e4c3e577da098a5ca5f5bf7052a` |
| P1-1b保存manifest | `data/work/voxcitygml_p1/p1-1b-final-d/manifest.json` / `97e790a12dc18c30c695f70b7d2bb9388d1a528cef67f5de0d960a0ee62edd1a` |
| P1-1c保存manifest | `data/work/voxcitygml_p1/p1-1c-final-d/manifest.json` / `b513b2527e82f0dbe9b35f5285f12b59e1f4b7a38de2e244c51da4c09c9a9fa2` |
| 共通DEM | `data/work/terrain-candidate-b/t5-23-02/t5-2/terrain.tif` / `ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2` |
| 元CityGML member | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| Standard GPKG | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |

SHA完全値・ファイル別対応は[input_alignment_evidence.json](input_alignment_evidence.json)に収録。
今回照合したユニーク**262ファイル**は選択した監査範囲で、P1-0の過去428件の全再監査という意味ではない。
STEP 4-Cはmanifestを除く125 outputs（manifestと合わせ126ファイル）。P1-1a/1b/1cは保存manifestに固定された7/15/40 outputsを照合した。
上流はSTEP 4-C report内の参照から4-A、4-B2、4-0、T5、Raw selector/Native/Standardのmanifestと主要入力を選択照合した。
公開JSONのLF正規化されたSHAと、ローカル生出力のSHAを区別している。確認対象の内容SHAは読取後も不変だった。

P1-2bで必要なファイルは、各建物のA/B `shared_voxels.npy`・`shadow.npy`・`ids.npy`・`dem.npy`・`metadata.json`・`qa.json`、
共通`observer_index.npy`・`observer_valid.npy`・`observer_xyz.npy`、保存reportのdirection/grid/vertical、P1の元三角形/merge配列と対応診断である。
各ファイルのSHAは上記manifest連鎖から要求し、ファイル名やshapeだけで代替データを採用しない。

## 3. すでに一致している条件

4棟のsource_id/ouem_idはP1とSTEP 4-Cで一致した。F/S/M/Cは従来どおり独立した単棟実験とし、周辺の実建物は省略する。
4つのcontextは重なるため、面積を市全域のunionとして合算しない。

| 建物 | STEP 4-C context bounds [xmin,ymin,xmax,ymax] | shape (R,C,Nz) | D0 m | 有効点 / 建物除外列 | A/B保存日陰セル |
|---|---|---|---:|---:|---:|
| F | [-22588,-39859,-22560,-39837] | (22,28,4) | 24.485000610351562 | 577 / 39 | 26 / 26 |
| S | [-22583,-39850,-22529,-39811] | (39,54,11) | 24.55299949645996 | 1845 / 261 | 192 / 118 |
| M | [-22548,-39937,-22506,-39897] | (40,42,10) | 24.336999893188477 | 1558 / 122 | 98 / 53 |
| C | [-22588,-39845,-22553,-39811] | (34,35,9) | 24.51799964904785 | 1108 / 82 | 60 / 44 |

全てEPSG:6677、1m、north-up、回転なし。Affineは`[1,0,xmin,0,-1,ymax]`、世界XY中心は`[xmin+c+0.5,ymax-r-0.5]`。
「回転なし」はラスタのAffineについてであり、grid northとtrue northが同一という意味ではない。
A/BのDEM、owner、GROUND/SURFACE配列、valid mask、保存observer XYZを実配列で確認した。
無効点のindex=-1、XYZ=NaN、日陰分類255も確認し、有効点数と保存日陰数がreportと一致した。
これは保存値の確認であり、新しい日陰を計算した結果ではない。

### 太陽方向

真北起点時計回りの**観測点→太陽**の方位角180°、高度45°。
光の進行方向や日陰の延長方向はその水平成分と逆であり、API説明のfrom/toward一般論からさらに180°を足してはならない。
STEP 4-Cはgrid northのtrue bearingを`beta`として、kernel軸(north,east,up)へ
`d=[cos(45°)cos(180°−beta), cos(45°)sin(180°−beta), sin(45°)]`を渡す。

| 建物 | beta（度、表示丸め） | 保存d_north | 保存d_east | 保存d_up |
|---|---:|---:|---:|---:|
| F | -0.145247401 | -0.707104509093 | -0.001792545861 | 0.707106781187 |
| S | -0.145132436 | -0.707104512688 | -0.001791127043 | 0.707106781187 |
| M | -0.144941694 | -0.707104518647 | -0.001788773036 | 0.707106781187 |
| C | -0.145225853 | -0.707104509767 | -0.001792279926 | 0.707106781187 |

保存ベクトルと静的実装の式が既存数値許容1e-12内で一致。実行時には表示丸め値でなく固定reportの完全値を使用する案とする。
既存と同様、単棟contextごとに中心bearing一つを全点へ使い、per-cellの収差補正を追加しない。
投影XYHへ並べ替えると`[d_east,d_north,d_up]`。日陰は投影北向き・わずかに東向きへ伸びる。
高さ差1mあたりの水平延長は`[-d_east/d_up, -d_north/d_up]`で、東約0.00253m、北約1m。
voxelと起点のaxis 0を一度だけ反転しkernelのnorth-increasingへ合わせ、結果は一度だけnorth-upへ戻す。
方位角を暗黙補正したり、配列とdirectionを二重反転したりしない。

### 観測点

requested heightは**0m**。実装上は地表面indexの直上セル中心であり、物理的DEM+0mではない。
binary kernelは整数`(i,j,k)`をray核へ渡し、ray核が`+0.5`を加えてセル中心を起点にする。
保存値は全有効点で`k=surface_index+1`、`H=D0+k+0.5`と一致した。

| 建物 | k範囲 | observer絶対H m | 実効地盤からの数値上の高さ m |
|---|---|---|---|
| F | 1〜2 | 25.985000610〜26.985000610 | 約1.001〜2.000 |
| S | 1〜2 | 26.052999496〜27.052999496 | 約1.003〜2.000 |
| M | 1〜2 | 25.836999893〜26.836999893 | 約1.001〜2.000 |
| C | 1〜2 | 26.017999649〜27.017999649 | 約1.001〜2.000 |

これは既存実験の数値observerであり、検証済みの測量上の観測高ではない。1.5m observerや屋根面観測点へ変更しない。

## 4. 調整可能だが新規検証が必要な条件

### Cの共通格子化（P1-2bの提案）

保存P1-1c Cの1m gridは小範囲、`min_z=23m`。A/Bは上表の非整数D0で、整数層のpad/切出しだけでは鉛直位相が一致しない。
旧C配列内に入る保存有効点はF/S/M/Cで51/129/102/62点、それ以外の526/1716/1456/1046点は旧配列の範囲外だった。
範囲内の旧C占有を引く読取probeでは起点占有0だったが、**保存XYZを旧Cの整数セル中心へ表せる有効点は全棟0**。
このprobeは日陰ではなく、将来のD0-gridでの観測点占有を保証するものでもない。

草案の既定案は、**P1-1cの元meshを保存A/B contextの1m XY格子とD0鉛直原点へ新しくvoxel化する**こと。
これは新しい明示的Derived profileであり、旧P1-1c NPYを移動・再ラベルする処理ではない。今回は生成していない。
源meshの絶対H・頂点は変更せず、DEMへ吸着・再アンカーしない。D0はobserverとセルを記述する座標原点として使い、Hから地盤相対高さを作らない。
草案のZminはD0、共通Nzは`max(Nz_AB, ceil(max(mesh_Hmax, observer_Hmax)−D0)+2)`と固定する。
現在の保存値から導く候補NzはF/S/M/C=5/12/11/10（未生成）。mesh下端がZmin未満なら切り捨てず停止する。
追加AIR以外の既存A/B層は完全保持し、旧保存ファイルを変更しない。
CにDEM/GROUND/SURFACEを重ねない。保存DEMは観測点の来歴と既存A/B条件として参照するため、「DEMと無関係な解析」とも主張しない。
枠外遮蔽・容量・境界を再検証し、既存A/Bの二セル境界無日陰QAをCへ無条件に流用しない。
Cでも幾何上の影到達枠の包含、外周二セル無日陰、さらに上部三層AIRを加えた判定不変を検証する案とする。
既存contextでは収まらない場合、既存A/Bの保存結果を越える領域へ拡張して直接比較せず、後続比較を停止する。

### 同じ判定核と固定起点

既存call chainは`synthetic_height_solar.evaluate`→`candidate_b_shadow.calculate`→
`compute_direct_solar_irradiance_map_binary`→`trace_ray_generic`。
設定は`hit_values=(0,-1,1)`、`inclusion_mode=False`、`include_building_roofs=False`、meshsize=1m。建物-3のみ遮蔽し、GROUND/SURFACEは透過する。
CPU/Numba 2 threadsを既定とし、GPUは使わない。独立P1環境を継続使用し、既存OUEM環境・依存を変更しない。新規run内へcacheを固定する案とする。
C bare配列はAIR/BUILDINGのみなので、そのままmap APIを呼んでもwalkable surfaceがなく有効観測点を自動構築できない。
偽のゼロ地盤や地表面を挿入してこれを解決しない。

提案は、保存valid点の**同じ整数起点**を明示的に既存`trace_ray_generic`へ渡す最小adapterである。
共通1m格子ではengine起点`(R−1−r,c,k_saved)`。ray内部の`+0.5`を含め、保存XYZへ厳密に戻ることを先に検証する。
同じd、hit_values、inclusion、tree_k=.6/tree_lad=1（TREEなしで非作動）を使う。新しいray追跡アルゴリズムは作らない。
これは上位map APIそのものではなく**同一DDA核への明示点入口**なので、P1-2bでA/Bを全保存valid点から同じ入口で評価し、保存A/B分類との完全一致を要求する。
このcontrolはCの日陰前に行い、失敗したらCへ進まない。maskを狭めてA/B不一致を隠してはならない。

OUEM/P1でorientation、binary kernel、raytracing、radiationの4ソースSHAが一致し、同じ固定VoxCity commitを確認した。
OUEM側のadapter/shared/shadow/observerの4入口ソースも、保存STEP 4-Cが記録したSHAと一致した。
ただしNumbaは保存STEP 4-C/現OUEM **0.68.0**、P1 **0.68.1**。ソース一致だけでJIT境界処理の数値再現性をPASSとはしない。
新規導入・downgradeは提案せず、上記controlで不成立なら停止して原因をレビューする。

VoxCityGMLの高位pipelineはDEM/land-cover/canopy・水面補正・座標frame生成等を含み得るので使わない。
`get_direct_solar_irradiance_map`はW/m²出力で、既定1.5m、透過class集合等も異なる。STEP 4-C二値日陰の代替として採用しない。
建物face日射APIも観測点/法線/SVFが異なるため対象外とする。
VoxCityGMLは固定meshの生成、VoxCityは固定ray核に限定する案で、private APIのcommit依存をmanifestへ明示する。

### 共通mask（結果を見る前に固定する提案）

保存A/Bのmaskを`M_AB`、共通D0-gridで保存XYZがCのAIRにある点を`M_C_air`とする。
**一次比較のmaskは `M=M_AB ∩ M_C_air`** と事前定義し、Cの日陰計算前にgeometryだけから確定・SHA保存する案とする。
A/B/C全ペアを同じMへ制限し、Cに入る点を勝手に移動したりshadowへ置き換えたりしない。
除外理由（元A/B建物除外、C起点占有、範囲/容量エラー）と元点数・除外数・位置を必ず保存する。
範囲/容量外は除外でごまかさずBLOCKED。有効点0もBLOCKED。

保存A/B全域のbaseline統計はそのまま残し、MでのA/B再集計を**別の共通支持統計**と呼ぶ。
元の全域A/B面積と制限後C面積を直接比較しない。C起点占有を除くことで境界shellの悪影響を過少表示し得るため、除外自体を主要診断として報告する。
この実験は元A/B建物列を評価しないので、3Dのピロティ・屋根下空間での新規観測点を評価できる設計でもない。
将来複数C解像度を比較するなら、それらのgeometryから先に共通AIR maskの交差を固定し、条件別maskで有利な結果を選ばない。

## 5. いま一致を保証できない条件・近似

P1-1cの体積比は1mでF/S/M/C=3.0522/1.4384/1.5229/1.5546、0.5mで1.8196/1.1975/1.2122/1.2565。
contact shell、floor両端を含むscanline fill、格子位相に依存し、サンプルIoUにも求積誤差が残る。Cを真値としない。
A/Bにも別の量子化があり、保存されたBのvoxel上端−元上端HはF=1.3992m、S約0.0478〜1.0456m、M約0.1469〜1.1354m、C約0.0853〜1.0673m。
FでA=Bは既存の対照条件だが、Cまで同じ日陰になることを合格条件にしない。
差があれば高さ丸め・水平支持・底面・shellを診断し、ゼロ差でも正しく実行できれば成立した比較とする。

**P1-2bの既定は1m一次比較のみ**とする草案。理由は保存A/Bとobserver格子の共通化であり、日陰結果や見かけの精度から選んだものではない。
0.5mと位相感度は必要性・負荷をレビューして別途事前条件を承認するまで実行しない。
同じ外枠を単純に0.5mへ細分すると、保存1mセル中心はfineセル境界になり、同じ整数起点へ表せない。
ray核は`origin+0.5`と`int(origin)`を併用するため、fractional originを渡して一般的な任意XYZを再現できるとは保証できない。丸め・微小位置補正は禁止する。

将来の候補として、fineの`xmin=xmin_AB−0.25`、`ymax=ymax_AB+0.25`、`zmin=D0−0.25`、h=.5なら保存中心を`(2r+1,2c+1,2k+1)`で共有できる。
これは**observer中心整列用の別位相profile**で、旧P1-1cの0.5mと同一条件ではなく、解像度だけの純粋な感度とも呼べない。
旧1m半セル移動も同様に保存observerの中心一致を壊す。そのまま旧NPYを日陰比較に使わない。
これらは数式上の候補整理のみで、実装・生成・実行互換を検証したものではない。

ABCだけでは形状差とvoxel方式差を完全には分離できない。C同一meshの格子感度は近似要因の一部を診断できるが、B対Cを純粋なLoD形状効果へ変換するものではない。
同じvoxel化方式で2.5D押出しsolidも評価する追加controlは、厳密分離が必要になった場合の別検討とし、初回の暗黙の第四モデルにしない。

鉛直はCityGMLのEPSG:6697（水平6668/鉛直6695）由来H、StandardのXY6677/H保持、DEMのT.P.継承working assumptionを区別する。
realization/epoch/測量精度・検証済みHAGは未確定。保存DEM由来observerとの条件付き数値的重ね合わせを維持し、正式Terrain統合に昇格させない。
[Concept §3/4.2](../../../OUEM_Concept_Architecture_v0.2.md)、[Building](../../../OUEM_Standard_Building_v0.1.md)、
[Terrain](../../../OUEM_Standard_Terrain_v0.1.md)、[正式Adapter](../../../OUEM_VoxCity_Adapter_v0.1.md)の契約とAcceptanceを緩和しない。

## 6. 比較指標・実装候補・停止条件

### 指標案

同一M上でA対B、A対C、B対Cを対称に評価する。
日陰セル数・面積（Mの各1m²観測セルに帰属する離散面積）、日陰割合、IoU、共通日向/日陰、第一モデルのみ日陰/第二モデルのみ日陰、両方向の変化数と差分mapを保存する。
符号は**第二モデル−第一モデル**。net面積差が0でも分類位置が変わるので変化の内訳を必ず残す。
Cのみの日陰も診断対象であり、それだけを失敗とはしない。STEP 4-CのB日陰⊆A日陰という特有の検査をCへ適用しない。
空unionのIoUは既存方式に合わせ1とするが、`empty_union=true`で非情報的な値と明示する。
有効点0・NaNのゼロ埋め・mask差を無視した比較は認めない。厳密な連続日陰面積や現地精度とは呼ばない。
元M_AB統計と共通M統計は別出力とし、F/S/M/Cの面積を地理的unionとして合算しない。

### P1-2bの実装候補（未実装）

既存[P1 mesh-only runner](../../../../src/ouem/p1_mesh_voxel.py)の入力pin/merge/axis制御と、
[STEP 4-C](../../../../src/ouem/real_roof_shadow.py)の保存grid/direction/maskを読み、
[binary入口](../../../../src/ouem/candidate_b_shadow.py)と同じ`trace_ray_generic`への明示点adapterを最小限に追加する案。
F/S/M/Cを独立に、全contextの遮蔽物でrayを処理した後にMを評価する。ROIだけの先行切出し、周辺建物追加、地形遮蔽追加は行わない。
将来出力はC-derived grid/mesh/voxel identity、保存点index/XYZ、maskと除外理由、A/Bcontrol、C分類、ペア別統計/差分図、manifest/SHA/QAを新規runへ保存する。
旧A/B/C成果物は変更せず、新規runを独立2回実行する案とする。

### 実行前に承認する条件と停止

1. 本草案の1m主条件、D0は座標原点のみとするC-derived profile、共通mask規則、同一ray核の明示点入口をレビューする。
2. 固定入力/ID/LoD/全三角形/H/基準宣言が一致しない、未説明の形状補修・軸変更がある場合は停止。
3. 1mで保存XYZが整数起点中心と一致しない、容量/領域外がある、共通有効点がない場合は停止。点の丸め・移動はしない。
4. A/B再現controlが全保存valid点で一致しない場合、C日陰を実行しない。Numba差等を記録し、依存や判定を無断変更しない。
5. Cの遮蔽がcontext境界で切れる、AIR容量で結果が変わる、占有規則/原Hが変わる場合は停止。
6. 未確認鉛直事項をCONDITIONALのまま記録する。明確な宣言矛盾が新たに見つかれば停止し、補正値を推定しない。
7. 外部取得、DEM再アンカー、ゼロ地盤代替、旧入力/環境/Acceptanceの変更は禁止。例外を隠すための欠測補完はしない。
8. 解像度/位相/評価mask/閾値を日陰結果に合わせて選び直さない。現在の草案にない感度条件は追加承認まで実行しない。

現在はこれらの実装・数値control・C再格子化・日陰計算はすべて**NOT_EXECUTED**。
P1-2bはレビュー承認後の条件付き着手候補であり、今すぐ計算可能な保存C入力が完成したという判定ではない。

## 7. 今回の検証とDocumentation Impact

JSON/NPY保存値・SHA・静的コードの照合、文書リンク・公開内容のscope確認だけを実施した。
sourceは読んだだけで、VoxCity/VoxCityGMLをimportして解析APIを呼び出していない。検査用の一時的読取処理を実装成果物として追加していない。
実装変更がないためpytestやシミュレーションは未実行。既存Windows/Ubuntu CI・合格条件は変更しない。
新規文書と必要な縮約証拠JSONだけを提出し、元データ、NPY、環境、実行cache、ローカル絶対パスは公開しない。
科学的/正式受入と、P1-0/P1-1aのライセンス残余課題の状態は変更しない。新規ライセンス監査を実施したという意味ではない。
scientific_validation=NOT_VERIFIED、formal_acceptance=NOT_VERIFIED、terrain_integration_ready=falseを維持する。
Draft PR作成後は停止し、マージ・P1-2b実装・日陰実験はレビュー承認を待つ。
