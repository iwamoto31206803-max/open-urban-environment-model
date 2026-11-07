# OUEM PoC-P1 / P1-0 事前調査

本書の「行っていない」は監査時点の実行範囲を示す。後日の本PRでは報告の公開整形とGit提出のみを行い、以下の判定は変更していない。

2026-11-07の監査記録。調査のみ。実装・インストール・VoxCityGML import/実行・3D解析・pytest・Git変更・GitHub操作は行っていない。
監査対象OUEM commit: `b261f1d749b6fcda42f795e7052b73f26557ee2a`（STEP 4-C作業ブランチ、追跡差分なし）。mainの更新取得はしていない。

| 判定項目 | 結果 | 根拠・境界 |
|---|---|---|
| P1-0_INPUT_CHAIN | **PASS** | 4-C文書のmanifest SHAから実際のinputsを逆追跡し、4-0→4-A→4-B1→4-B2→4-Cの429ファイルを照合。不一致0。Run名だけで採用していない。 |
| P1-0_SOURCE_IDENTITY | **PASS（保存監査との同一性）** | 4棟の元XML建物・全監査polygon ID、Native/StandardのID・LoD・ouem_idが一致。3D形状の変換対応はSHA同一の既存一意対応VERIFIED記録を継承。今回、水密性や三角形化は解析していない。 |
| P1-0_ENVIRONMENT | **CONDITIONAL** | ソースcommit一致。既存VoxCity 1.7.0の15 import箇所が静的に解決し、assemble引数も対応。136 PythonソースのRECORD一致。独立venvはPython 3.11.9だがpip/setuptoolsのみで、実行依存は未導入。ABI・実行互換は未検証。 |
| P1-0_LICENSE | **CONDITIONAL（一次監査）** | 211候補、license/classifier両欠落67を再現。うち47は既存同一版METADATAの追加SPDX表記を確認。VoxCityGML本体LICENSE/pyprojectはMIT。全wheelの同梱第三者条件・データ利用条件の最終確認は未完。UNKNOWNは商用利用禁止を意味しない。 |
| P1-1a_READY | **BLOCKED（準備・レビュー待ち）** | データ不足ではない。独立venvへの未導入と、F限定・無外部取得・原H保持・MeshLibなし補修の許容条件が未確定。今回は承認や導入・実験へ進まず停止する。 |

## 重要な発見

1. **MeshLibなしでも補修は自動実行され得る。** MeshLibはoptional extrasでdry-run 211件にも両venvにも存在しない。無MeshLibの建物経路は `make_watertight_mesh`→occupancy、失敗時sealed surface。auto補修はmerge→trimesh repair→voxel marching。冒頭説明にはhullとあるが、実コードのautoはconvex hullを除外し、hullは明示指定のみ。形状・穴・薄部・空洞が元のままとは保証されない。
2. **DEM選択により原Hが変わる。** `dem_source='Flat'` またはnamed sourceは `anchor_meshes_to_dem` で建物等のZを一律移動する。CityGML地盤なしでは `dz=DEM−min(mesh Z)`。絶対Hを保存するOUEMの経路に無断適用しない。`dem_source=None/'CityGML Terrain'` はこの再アンカーを呼ばないが、DEM欠如時のゼロ地盤やGeoTIFF読込失敗の扱いを別途厳格に検出する必要がある。
3. **標準設定のrun()はオフライン最小実験ではない。** source未指定は自動選択、地表・樹冠は取得処理へ進む。parse cacheは既定で入力データ横に作成され、water flattenも既定True。Fだけの棟ID whitelistはconfigにない。rectangle選択だけでは近傍棟を排除できない。
4. **LoD/面情報のfallbackに注意。** `building_lod=2` は優先指定で、見つからなければ他LoDへfallbackする。穴付きearcut失敗では外周のみ三角形化へfallbackする。Mesh3Dにはgml:idをfeature_idとして残すが、ouem_idや各triangleの元polygon ID/面意味対応は自動保持されない。
5. **軸と鉛直原点は既存モデルと同一ではない。** 入力meshはlat/lon/Z、内部はnorth-up、組立後のVoxCityはsouth-up。land-coverは内部でも別の向き。EPSG:6677 XYZをlat/lonとみなして渡さない。地理矩形格子・回転・中心座標と `extras['voxel_min_z']` を記録し、旧north-up格子やB2 D0をそのまま流用しない。2.5D regenerate_voxelsは詳細mesh占有を作り直すため使わない。

## F最小実験へ向けた次の最小作業（実施していない）

- 本報告をレビューし、独立venvだけを対象とした依存導入範囲と固定commitを確定する。既存OUEM .venvには導入しない。MeshLib extrasは選ばない。`mapbox-earcut`は必須で、既存OUEMにも未導入。
- Fの固定source_idを1棟だけ取り出す限定経路を決め、元XML/Standard/面IDを外部対応表として保持する。返却棟数1・feature_id・実際のLoD2・面欠落なしを停止条件にする。
- 高位pipelineか低位mesh/voxel APIかを選ぶ。外部取得・既存データ横cache・水面によるDEM変更を無効/遮断し、原Hを再アンカーしない。保存DEMを使う場合、GeoTIFF→TIN→補間は4-B2 nearest採取と異なるため独立Derivedとして記録する。
- 無MeshLib fallbackの採用段階・変形・欠落を検出する比較条件を決める。無承認の補修、外周のみfallback、欠測のゼロ地盤化、意図しないLoD/ID、外部アクセス、未説明のZ移動、軸不一致では停止する。許容値を本調査で創作しない。
- ライセンスの残余メタデータと配布物noticeをレビューする。pycountryのLGPL-2.1-only、tqdm/ certifi/ fqdnのMPL等は利用・改変・再配布形態に応じて確認し、商用禁止とは分類しない。原PLATEAU ZIPの利用条件と取得記録の表記差も解消/明示する。

## 入力・仕様上の境界

F: `bldg_09532951-4dab-457d-b1c6-56d509900d1b` / `oub-c56cb020-c11c-5f9c-a37f-73018266a333`。
F/S/M/CのRoof/Wall/Ground面数は **1/4/1、69/61/1、30/57/1、12/25/1**。
Native/Standard母集団はともに63棟（LoD1 31、LoD2 32）。詳細ID・polygon対応は[ID対応証拠](evidence/source_identity.json)を参照。

原CityGML ZIP SHA: `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555`。
member: `udx/bldg/53393466_bldg_6697_op.gml`、SHA `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9`。
Standard SHA: `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60`。

Concept v0.2は詳細3DをPrimary、エンジン固有水密処理をAdapter責務とする。現行A3契約は代表高さ/2Dフットプリント経路であり、今回それを変更していない。原H、鉛直宣言、IDと旧Accepted成果物を保護する。
鉛直CONDITIONAL、scientific_validation/formal_acceptance NOT_VERIFIED、terrain_integration_ready=falseを継承する。

アーキテクチャレビュー草案・PoC-P1仕様草案は、repo/docs・VoxCityGML/docs・指定preflightの限定探索でNOT_FOUND。他の私有領域まで探索したとの主張はしない。内容を推測せず、上記正式資料を優先した。

## 公開版の証拠・参照

本PRは完了済み監査の公開整形であり、新規調査・再判定ではない。元ローカル報告は変更していない。絶対パス、環境の全量スナップショット、長いライセンス本文、元XYZは省略し、確認結果・SHA・ID・未確認事項を残した。データlocatorは識別情報であり、GitHubにデータ本体を置くリンクではない。

- [入力連鎖・429件のSHA](evidence/input_chain.json) / [4棟のID対応](evidence/source_identity.json)
- [静的API・ソース証拠](evidence/static_compatibility.json)
- [211候補のライセンス一次監査CSV](evidence/dependency_licenses.csv) / [環境・ライセンス集計・原報告SHA](evidence/audit_summary.json)
- [詳細監査ログ](audit_log.md)
- 既存実験記録：[4-0](../height_distribution/STEP4_0_REAL_LOD2_ACCEPTANCE_AUDIT.md)、[4-A](../height_distribution/STEP4A_REAL_LOD2_ROOF_DISTRIBUTION.md)、[4-B1](../height_distribution/STEP4B_REAL_LOD2_VOXELIZATION.md)、[4-B2](../height_distribution/STEP4B2_REAL_LOD2_TERRAIN_VOXELIZATION.md)、[4-C](../height_distribution/STEP4C_REAL_LOD2_SHADOW_COMPARISON.md)
- 正式参照：[Concept v0.2](../../OUEM_Concept_Architecture_v0.2.md)、[Development Principles](../../OUEM_Development_Principles_v0.1.md)、[Building](../../OUEM_Standard_Building_v0.1.md)、[Terrain](../../OUEM_Standard_Terrain_v0.1.md)、[Adapter](../../OUEM_VoxCity_Adapter_v0.1.md)

レビュー待ちで停止する。追加実装・導入・P1-1a実験は行わない。
