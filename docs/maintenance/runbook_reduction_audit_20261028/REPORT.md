# OUEM Runbook・歴史的スクリプトの削減設計

調査日: 2026-10-28。対象main: `1f0b9f0a48d86cf4097a846f987cbab14d958235`（PR #101 merge）。GitHub mainを照合してfetchし、対象commitのblobを調査した。作業ブランチは切り替えていない。PR #100は依存せず、そこで共有したローカル監査のARCHIVE候補5件を再評価した。

## 結論

**中間案を段階実施することを推奨する。** Runbookは1,080行・25区間、対象はscripts/workの23スクリプト（CMD15/Python8）とARCHIVE候補のsrc2本、合計25本・1,884行。文書分割でファイルを増やさず、既存READMEを圧縮し、重複launcherと単発ID診断を退役させる。削減見込みは最終的に管理対象6ファイル、Runbook約730行＋スクリプト466行。試験・リンク移行の追加を控除した純減は約1,156〜1,196行。

「正式記録に名前があるから永久保存」とはしない。一方、参照が少ないという理由だけでは削らない。退役時に何の再実行が現行checkoutでできなくなるかを区別し、immutable commitへの取得経路、旧入力/環境の要件、影響する試験を提示する。歴史参照だけで現行実行が可能になるわけではない。

PR #101のREADME/Current Stateは現行実都市source-H経路を既に案内している。RunbookへPR97–99のコマンドやRESULTSを複製せず、短いリンクだけ置く。accepted v0.1の操作と旧contained/Meta-CHM経路は、今のsource-H実験と別の機能として残す。

本提案は調査のみ。追跡ファイル編集・削除・移動、tag作成、commit/push/PR、モデル処理、pytestは実施していない。Formal Acceptance、source-H eligibility、Standard、Gateの状態も変更していない。

## 1. 調査範囲と計数方法

- Runbook全1–1080行を読んだ。親見出しは次の子見出しの前で区切る**排他的区間**にし、親子の行数二重計上を防いだ。空行・コードフェンスも1行。
- scripts/workの全CMD/Pythonの起動先、引数検査、Python imports/関数、参照を確認。PR100のARCHIVE 5件はID診断3本＋gdal_citygml_feasibility＋plateau_converter_probe。
- Git管理テキスト全体を対象にslash/backslashを正規化し、path・basename・module・import参照を抽出。AST、runpy/importlib、child script定数、試験でのread_text/copy2、正式記録・文書からの引用を合わせて判定した。CSVにはfile:lineを保存。
- file:lineは本baselineに対する位置。履歴文書が引用する旧時点の状態と、いま使われるコード依存を分けた。文字参照は利用証明ではなく、未検出は外部利用不存在の証明でもない。
- GitHub本文やユーザーの別手順まで全検索したものではない。通常inline相対リンクの個別anchorと、Runbook全体へのリンクも区別した。
- 本数/LOCは対象mainのGit blobに基づく。ignored Raw/成果物/venv、Git履歴のpackサイズは対象外。tagを作っても既存履歴のbyteやcloneサイズが直ちに減るわけではなく、主な効果は現行treeと管理面積の縮小。

## 2. Runbook全区間の削減予算

下表は原区間から取り除ける行数。C=保守的、M=中間、A=積極的。細かな残す内容・重複先・incoming anchor・commit permalinkは `runbook-sections.csv`。まだ編集していないため、すべて設計上の予算であり実測の編集結果ではない。

| 元行範囲 | セクション | 主用途 | 元行数 | C削減 | M削減 | A削減 |
| 1–6 | Windows local acceptance helpers | 入口 | 6 | 2 | 2 | 2 |
| 7–18 | Runtime boundary | 共通運用 | 12 | 4 | 6 | 6 |
| 19–37 | Diagnose unusually tall Komae Adapter buildings | 歴史診断 | 19 | 7 | 13 | 15 |
| 38–95 | Trace a building's vertical coordinates from CityGML | 歴史診断 | 58 | 26 | 46 | 52 |
| 96–97 | Komae PLATEAU acceptance workflow | accepted v0.1 | 2 | 0 | 0 | 0 |
| 98–117 | 1. Manual preprocessing | accepted v0.1 | 20 | 8 | 10 | 12 |
| 118–128 | 2. Capture the GIS child runtime | accepted v0.1/共通 | 11 | 3 | 5 | 6 |
| 129–170 | 3. Run OUEM ingest | accepted v0.1 | 42 | 16 | 24 | 30 |
| 171–182 | Manual QGIS acceptance | accepted v0.1 | 12 | 4 | 6 | 8 |
| 183–213 | Native to Standard Building acceptance | accepted v0.1 | 31 | 15 | 19 | 23 |
| 214–292 | Komae Terrain local acceptance | 現行Terrain/accepted | 79 | 31 | 39 | 47 |
| 293–294 | Isolated Komae A1/A2/A3 integration demonstration | legacy contained | 2 | 0 | 0 | 0 |
| 295–349 | Meta CHM canopy scenario PoC (opt-in) | legacy canopy | 55 | 23 | 41 | 49 |
| 350–407 | QGIS review of a saved canopy run | legacy canopy/QGIS | 58 | 26 | 44 | 52 |
| 408–473 | Read-only Adapter content failure diagnosis | 歴史診断 | 66 | 30 | 56 | 62 |
| 474–542 | Read-only geometry provenance diagnosis | 歴史診断 | 69 | 33 | 59 | 65 |
| 543–620 | Read-only Adapter intermediate geometry diagnosis | 歴史診断 | 78 | 38 | 68 | 74 |
| 621–719 | Memory-only CRS repair candidate evaluation | 歴史修復評価 | 99 | 49 | 87 | 95 |
| 720–756 | Export Candidate A for QGIS inspection | 歴史QGIS診断 | 37 | 15 | 29 | 33 |
| 757–843 | Opt-in 92-building contained E2E PoC | legacy contained | 87 | 39 | 59 | 71 |
| 844–902 | Read-only preflight (before authorizing a real-data run) | legacy preflight | 59 | 27 | 37 | 43 |
| 903–958 | Windows preparation and execution (explicitly authorized real-data runs only) | legacy contained/共通 | 56 | 24 | 36 | 42 |
| 959–981 | Preconditions and intentionally conservative checks | legacy engine契約 | 23 | 5 | 9 | 13 |
| 982–1056 | Evidence and report v0.1 | legacy evidence schema | 75 | 35 | 55 | 65 |
| 1057–1080 | Equality versus quality | legacy品質契約 | 24 | 6 | 10 | 12 |

区間ごとの削減合計はC466/M760/A877行。これに、共通安全条件、現行経路リンク、歴史参照・退役対応表の**追加予算**C24/M30/A36行を差し引く。したがってRunbookの最終見込みは638/350/239行、純削減442/730/841行。追加予算は全区間表と別計上し、実施時に全行数で再測定する。

### 重複として削れるもの

- 7–18、118–128、903–958のruntime説明は `docs/architecture.md` と前方のGIS捕捉手順へ寄せる。OUEM/GISを混ぜない操作順、trusted snapshotが秘密を含み得る点は残す。
- 129–213の過去count・Z/CRS詳細は既存Building契約とA1実行記録が所有。Runbookにはmanual/gis/ouem/standardの実行例と入力上書き/optional layerの意味を残す。
- 408–756は5つの旧診断/評価/exportで計349行。read-only、sidecar/hash拒否、stdout保存、INCONCLUSIVE、実行と受入の違いが反復される。1つの共通注意とCLI/固有出力/exit条件の短い表にできる。
- 757–843の2つのcontained launcher例は同一integration `run --contained-poc`。安全側e2e名へ統合可能。ただし旧name互換は失い、入力制約は追加される。
- 982–1080のschema全列・retry実装・個別試験の説明は保守時の二重管理になる。status、失敗の保存、qualityとrepeat equalityの違いを残し、コード/testsと固定履歴へ詳細を委ねる。

### 重複と断定してはいけないもの

- 621–719の候補A–D、現runtimeでのfidelity/INCONCLUSIVE条件はRunbookが最も詳しい説明になっている。PR101のREADMEと重複するから削れる、とはいえない。履歴への明示リンクで利用場所を変更する設計。
- 295–407は旧Meta CHMの3m閾値、ground-relative top/bottom、旧QGIS span export。現Envelopeのstate/positive crown depthやPR99可視化とは異なる。現行READMEを同等手順の代替としない。
- 38–95のstrict/exploratoryの違い、relocationのbyte照合は固有診断。source-Hで数値整合したことは旧Z異常の解決ではない。
- 214–292のTerrain helperは現E2E入力準備にも関係する。helperが未実装のacquisition cross-stage QA、`PROCESSING_COMPLETED_PENDING_REVIEW`の限界は消さない。

### 外部/内部参照の維持

既存の個別anchor `#komae-terrain-local-acceptance` は次から使われるため残す:

- `docs/Terrain_Acquisition_PoC_v0.1.md:177`
- `docs/acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md:90`
- `docs/acceptance/OUEM_A2_Terrain_Reproducibility_Verification_20261026.md:133`

Runbook全体にはAGENTS、README、Building Current State、governance、Windows setup、acquisition planning、A2記録、Phase5 readiness/source selection、旧canopy experiment index等から参照がある。これらの参照はファイル分割しない案で維持できる。25区間のうち他の個別anchor参照は対象Gitテキスト検索では検出されなかったが、未把握の外部bookmarkはあり得る。歴史CLIの短い見出しを残すか、既存見出しslugをexplicit anchorとして残す方法を選ぶ。

PR101で更新したREADME/Current Stateとの重複は「到達点」「既存契約」「runtime分離」「未受入」「出典/格子/観測点の注意」の要約レベル。PR101から移動してきた詳細手順はないため、同じコマンドをRunbookに新設して埋め戻さない。新しいcurrent章は3組の実験READMEへの数行の案内で十分。

## 3. 各スクリプトの分類

全25件の入口、依存、参照元file:line、代替手段、失う機能、案別の削除対象を `script-candidates.csv` に記載した。

分類は **KEEP 8 / MERGE 9 / REMOVE 5 / NEEDS REVIEW 3**。REMOVEは削除提案であって、現時点で削除実施が承認された意味ではない。MERGEは新dispatch frameworkを作る意味ではなく、既にあるPython CLIまたは安全側launcherへ導線を集めて旧wrapperをなくす意味。

| 分類 | 対象 | 理由/失うもの |
|---|---|---|
| KEEP | capture_gis_runtime.py、gis_runtime_check.py、ouem_runtime_check.py | 既存runtime捕捉/実機import/venv検証の操作。新GIS環境を作らず維持 |
| KEEP | plateau_komae_local_acceptance.cmd、terrain_komae_local_acceptance.cmd | accepted v0.1と現Terrain準備の入口。後者は薄くてもpath解決/exitと試験があり、一律に「薄いから削除」としない |
| KEEP | run_komae_contained_e2e.cmd | contained_poc.cmdの安全側統合先。portable run-ID、予約語、既存run拒否、report表示のWindows試験あり |
| KEEP | voxcity_komae_a3_acceptance.py | integrationのchild path定数、runpyを含む多数の回帰、旧canopy exporterのevidence再構築から利用。新source-H runnerは別契約で代替不可 |
| KEEP | src/ouem/gdal_citygml_feasibility.py | pure helper signature/source_referenceをsource-H Converter smokeがimport。GIS probe本体は歴史的でも検証oracleが現存 |
| MERGE | diagnose_komae_adapter_content.cmd、diagnose_komae_adapter_geometry_steps.cmd、diagnose_komae_geometry_provenance.cmd | それぞれ既存Python moduleに集約。診断module/品質predicateは削らない。失うのは旧CMD入口/cwd/arity/exit契約 |
| MERGE | evaluate_komae_adapter_crs_repairs.cmd、export_komae_adapter_repair_qgis.cmd | 既存moduleが代替。候補評価・exportそのものは維持。launcher試験の移設が必要 |
| MERGE | diagnose_komae_building_heights.cmd、diagnose_komae_vertical_exploratory.cmd、export_komae_canopy_qgis.cmd | 既存moduleへ。CMDのportable ID/特殊文字処理を提供しなくなるため、Python引数検査とWindows安全性を先に確認 |
| MERGE | run_komae_contained_poc.cmd | 同じ入力/expected92を持つe2e側へ。旧nameとUsage文面を失う。簡易検査を安全側へ維持/強化し、完全互換と呼ばない |
| REMOVE | diagnose_komae_dem_coverage.cmd | 9行の起動補助。repo rootから同名Pythonを明示実行できる。本体151行と独立oracleは残す |
| REMOVE | preflight_komae.cmd | 固定した旧run-dir/入力の21行補助。Runbookの明示integration preflight CLIに置換。自動cwdとまとめ打ちを失う |
| REMOVE | diagnose_voxcity_building_ids.py、diagnose_voxcity_id11.py、diagnose_voxcity_id37_overlap.py | 旧fast raster/ID11欠落/ID37重複の単発調査。現行経路の直接依存/CI直実行は未検出。正式A3からの参照は履歴取得で扱えるが、同じ診断を現checkoutでは再実行不可になる |
| NEEDS REVIEW | diagnose_komae_dem_coverage.py | test_komae_containedがimportlibで独立分類を比較。preflightは全同等でなく、削除すると独立oracleも失う。全3案で保持 |
| NEEDS REVIEW | run_komae_meta_chm_e2e.cmd | 固有CHM path/provenance/ID検査がある。現PR99ではない旧canopy再実行を1行で行う入口。積極案のみ削除対象 |
| NEEDS REVIEW | src/ouem/plateau_converter_probe.py | fixture構造とpreflight matrix/log recorderの手動入口・専用testsあり。srcの現行runnerから直接importは未検出だが、外部手動再利用は不明。積極案のみ専用testと合わせて退役 |

### ARCHIVE 5件の再評価

ID診断3本はA3正式記録152–154行から名指しされる。その記録自身が「production contractではないdiagnostic tooling」と説明しており、現行treeの永久保存要件とは読み取れない。削除後は旧診断が使う数値ID割当、threshold0.5、bootstrap height=1、overlapping_footprint=Falseの再現を**現行treeでは失う**。A3の一般回帰やPR98のprecise owner QAは同等の説明ツールではない。

gdal_citygml_feasibilityはARCHIVE候補からKEEPへ変更。`tests/integration/run_source_h_converter_smoke.py:19` が現存の明示smokeでimportすることが具体的根拠。plateau_converter_probeはNEEDS REVIEWを維持。独立したfixture/失敗記録の検証価値を失ってもよいか、用途を終了したとレビューする必要がある。

## 4. 3案の定量比較

対象mainは234管理ファイル。下記は新たなtracked文書やwrapperを作らない前提でのファイル純減。リンク更新・試験移行は既存ファイルを編集し、ファイル数に加算しない。ローカルデータ/成果物を減らす数ではない。

| 案 | Runbook最終行数（推定） | Runbook純減 | 削除コード等 | 管理ファイル純減 | 合算の行数純減（推定） |
|---|---:|---:|---:|---:|---:|
| 1 保守的 | 638 | 442 | 0 | 0（234のまま） | 約442 |
| 2 中間的 | 350 | 730 | 466行/6ファイル | 6（228へ） | 約1,156〜1,196 |
| 3 積極的 | 239 | 841 | 825行/16スクリプト＋90行/1専用test | 17（217へ） | 約1,636〜1,716 |

中間のgross削減は730+466=1,196行。既存test launcher節の移設や参照修正による純増0〜40行を控除。積極は841+825+90=1,756行から、parser/Windows安全性試験・履歴移行説明等の純増40〜120行を控除した。これらは行単位の編集前予算であり、試験を削って見かけの削減量を稼ぐ目標ではない。保守的以外は実装レビュー後に再見積もりが必要。

### 案1: 保守的

Runbook1ファイルのみを圧縮。全25区間の責務/入口は短い形で残し、重複するruntime・書込み禁止・受付状態を共通化。原スクリプトと試験を全保持。長い候補/報告仕様は既存ownerまたは対象commitへリンク。現在の操作機能は失わず、詳細の閲覧に履歴参照が必要になる。ファイル数の削減はできないため最終到達案としては弱い。

検証: 全relative target/heading anchor、サンプルCLI/parserの照合、読解レビュー、実編集後の行数/文字数、変更範囲。文書だけならpytest/実データ再処理を新たな成功証拠として要求しない。

### 案2: 中間的（推奨）

削除セットを固定:

1. scripts/work/diagnose_voxcity_building_ids.py（120行）
2. scripts/work/diagnose_voxcity_id11.py（163行）
3. scripts/work/diagnose_voxcity_id37_overlap.py（129行）
4. scripts/work/diagnose_komae_dem_coverage.cmd（9行）
5. scripts/work/preflight_komae.cmd（21行）
6. scripts/work/run_komae_contained_poc.cmd（24行）

失うもの: 旧ID固有診断のcurrent checkoutでの実行、3つの旧CMD名/shortcut。DEM診断本体、preflight、containedのモデル処理・accepted lane・PR94–99経路は保持する。旧poc入口の削除はbreaking CLI removalとして明記し、e2eに同じ引数を指定する移行先を示す。旧ID調査は固定commitを取得して実行できるようにする。

検証: test_komae_containedの旧launcher参照を安全側e2eへ移す（module-levelのcontained選択/coverage/XYZ検証は削らない）、test_komae_repair_acceptanceのWindows ID/exit/report試験を実行、A3/adapter/contained/preflight/source-Hとreal_komae回帰、全pytest。2つの薄いCMDは直接試験参照未検出でも、対応Python CLIの引数・cwd・exitを照合する。static import以外にsource path定数・manifest code fingerprintも保護し、古い実行記録を書き換えない。

### 案3: 積極的

15 CMD中、plateau_komae_local_acceptance.cmd、terrain_komae_local_acceptance.cmd、run_komae_contained_e2e.cmdの3本だけを残す。残り12 CMD（計249行）を除去し、各既存Python module/scriptへ案内する。ID診断3本（412行）、plateau_converter_probe.py（164行）、その専用tests/test_plateau_converter_probe.py（90行）も退役。合計17ファイル/915行のコード・試験削減。

失うもの: 12の旧CMD名、cwd検出、arity/portable ID/CHM pathのbatch検査、一括操作、ID固有調査、fixture recorder/preflight matrixの現行試験。probe専用testの8関数（parameterize展開で9ケース）は現行CIから消える。fixture自身、GDAL helperとtests、source-H Converter smoke、PR94–99回帰は残すため、Converter検証全般が不要になるという提案ではない。

条件: 各CMDの安全性がPython parser/直接呼び出しでどう置き換わるか先に設計し、既存test内のlauncher部分を移設してから削る。`cmd /c`のmetacharacter検査をテストごと捨てて「CI成功」とするのは不可。retired probeの専用tests以外は現行機能の回帰を維持。新しい共通dispatcherや大量のarchive文書は作らない。

この案は手動互換性と独立検証を相対的に多く失い、追跡行数純減も予算を超え得る。まず中間案で運用価値を確認するのがよい。

## 5. Git履歴/タグへの退避設計

既に存在するimmutable基準はmain `1f0b9f0a48d86cf4097a846f987cbab14d958235`。そのtreeにRunbook全文・全対象script/testがある。CSVのhistory_fallbackは全件このcommitへのURLで、branch名mainや未作成tagに依存しない。

退役を実施する別PRでは、削除前treeに到達する注釈付きtag（例 `archive/komae-runbook-20261028`、**現在は未作成**）を作成/remote保持するか、commit permalinkのみを使うかをレビューする。tagはdiscoverabilityを補い、commit SHAを置き換えるものではない。タグの公開・削除権限と長期保持を決め、private repoなら将来のアクセス権も要る。

既存Runbookに短い退役対応表（旧path、取得commit、代替CLI、失う診断）を置く。別archive treeや新しい文書群は作らない。復元は現行checkoutに旧コードを混ぜず、取得commitの別checkout/worktreeで行い、その時点の環境と元入力を用意する。現行engine/python依存で同じ結果が得られると保証しない。Raw/manifest/固定binary・過去ライブラリはGitだけでは復元されない。

正式A3やfrozen JSONの過去path/コマンドはその時点の事実として保持する。削除に伴い旧inventory等のMarkdownリンクが切れる場合は、状態/結果本文を変えず対象commitのblobリンクへ直すか、runbookの履歴対応表から旧pathの取得先を明示する。前者が実装可能なら優先。既存JSON中のhistorical commandを現CLIに書き換えてはいけない。

外部README/bookmarkから旧CMD/pathを呼ぶ利用は不明。互換stubを残せばファイル純減にならないので、remove案では互換を失うことを明示する。個別外部利用が判明したらそのファイルをKEEPへ戻し、ファイル/LOC予算を再計算する。

## 6. テスト・CIへの具体的影響

CIは `.github/workflows/pytest.yml` のUbuntu/Windows、Python3.12、`python -m pytest -q -ra`。`testpaths=[tests]` で通常のtest_*を収集。スクリプトのinbound importだけでは次を見落とす:

- `src/ouem/komae_integration.py:30` のA3_SCRIPT。A3 Pythonをchild実行するのでKEEP。
- `tests/test_voxcity_adapter.py`、`tests/test_komae_canopy.py` のrunpy、canopy exporterのsaved command照合。
- `tests/test_komae_contained.py:176` のDEM診断Pythonのimportlib、242行以降の旧poc CMD read_text/subprocess。
- wrapperをread_text/copy2してfake repo + venvへコピーしWindows実行するtests: adapter_diagnostics、geometry_steps、geometry_provenance、crs_repair_evaluation、repair_qgis_export、height_diagnostics、vertical_exploratory、canopy_qgis_export、canopy、repair_acceptance。
- plateau helperとTerrain launcherはtest_plateau_building、test_standard_terrain、test_terrain_local_acceptanceに依存。
- `tests/integration/run_source_h_converter_smoke.py:19` のGDAL helper import。run_*smokeは通常pytestでは走らず、全pytest PASSだけで保護を確認したことにしない。

現E2E保護セット: Native source-HのLoD2 xlink/全頂点H、Standard/Consumer、合成2.5D/voxel/solar、real_komae_source_h/voxel/solar、Height Envelope/Canopy presence/observer、accepted Building/Terrain/Adapter/runtime試験。engine固定版・水平/鉛直意味・raw/effective地盤とD0・actual centres/ID/観測点不変を変えない。

削除対象CMDの試験はmodule/CLI直接試験に移す。テストファイル数を減らすことを主目的にせず、将来どの入口を保証するかを明示。Windowsのquote・特殊文字・追加引数・予約語・既存run・exit code・別cwdを検査する。安全性検証がPython側になければ、その入口はNEEDS REVIEWのまま残す。unit移設と全pytestの結果/skip/warningをそのPRで報告する。

今回はコード変更なしの静的調査なのでpytest・実データsmokeは未実施。現在の897等の旧実行数を本調査の新結果として使わない。スクリプト削除だけならモデル再計算を常に要求しないが、現在の資料/receiptに記録されたコードhashを現mainのhashへ書き換えない。入力・依存・実行byteの違いをレビューし、実再現が必要なら明示的に新しいignored runで検証する。

## 7. 最初に実施する小規模PR

推奨: **「Runbook旧診断説明の圧縮＋DEM診断CMDの退役」**。中間案を次の小さな範囲から始める。

1. `scripts/work/README.md` の408–756（5診断/評価/export、349行）を約80行に圧縮。共有注意を一度、各moduleのCLI/固有検証/exit/出力/未受入範囲と元commitへのリンクを残す。他の主要セクションの順序や契約を変えない。
2. `scripts/work/diagnose_komae_dem_coverage.cmd`（9行）を削除し、repo rootからPython本体を明示実行する代替を同じREADMEへ数行で案内。本体と独立分類のtestsは保持。
3. `docs/experiments/voxcity_canopy_shadow/REPOSITORY_INVENTORY_20261027.md:201` の旧CMDへのMarkdownリンクのみを当該baselineのimmutable blob URLへ変更。歴史的分類・件数・結論を再記述しない。この参照移行を含めてレビューする。

変更対象3ファイル（README編集、CMD削除、inventoryリンク1箇所）。新規ファイル0、管理対象純減1。Runbook約269行削減から代替例3〜8行を控除し、CMD9行と合わせて**約270〜275行の純減**。削減量は実施後に測定する。Formal Acceptance/Gate/RESULTSとPR101文書は編集しない。

受入: 旧anchorまたは互換explicit anchor保持、全リンク/commit path存在、5つのCLIのhelp/parser/exit条件の整合、DEM Pythonのrepo-root呼出し文面・依存確認、test_komae_containedの独立分類比較を実行。スクリプト削除を含むので全pytestをWindows OUEM venvで実行し、CIを確認する。実データを未実行なのにdiagnostic成功とは書かない。

次PRで旧poc→e2eとpreflight補助を退役し、最後にID固定3診断を履歴へ退役する。削除範囲を小さくして、失われる入口と代替を1つずつ評価する。最初から全12 CMDとprobe/testsを除く積極案は勧めない。

## 8. 保存成果物と検証状態

- REPORT.md: 設計・比較・リスク・最初のPR範囲。
- runbook-sections.csv: 全25排他的区間、元行範囲・主用途・参照・重複/固有の判断・C/M/A予算・履歴URL。
- script-candidates.csv: 全25本、行数・分類・入口・imports/child・code/test/formal/doc参照元・代替・失う機能・案別対象・履歴URL。

成果物は `data/work/repository-cleanup-audit/runbook-reduction-20261028-01/` に保存。集計はGit blob、提案は静的調査と人間による内容評価であり、削除後の動作を実行検証したものではない。追跡ファイルが変更されていないことと、CSVの全区間網羅・本数・案別加算を最後に検証する。

最終静的検証: PASS。25区間で1–1080行を重複・欠落なく網羅、25スクリプト/1,884行、分類8/9/5/3、中間6本466行、積極16本825行の加算一致。履歴URLの全script pathは対象commitに存在。指定ディレクトリの成果物は3ファイルのみ、Git ignore適用、git statusはclean、HEADと対象mainの内容差分なし。テスト・モデル実行はなし。
