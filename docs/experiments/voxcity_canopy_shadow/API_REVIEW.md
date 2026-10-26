# VoxCity 1.7.0 Canopy / Solar API — Phase 0調査

> 公開用整理: 2026-10-27。以下は2026-10-26の既存調査・提案の全文を保持した記録。調査結果と **CONDITIONAL** 判定は変更せず、今回新しいAPI実行・Adapter実装・voxel化・日射比較・pytestは行っていない。本文の「今回」「最新main」「commit／push／PR作成なし」は当時の調査実行を指し、本ドキュメントPRの提出操作とは区別する。
>
> ローカル証跡の基点（リポジトリ相対識別子）: `data/work/voxcity-canopy-shadow/komae-phase01-20261026-01/`。本文の `environment-and-api.json`、`input-evidence.json`、`source-index.json`、`source-snapshots/`、`inspect_inputs_and_api.py` は同run内の非公開ローカル証跡で、GitHubへ同梱しない。`.venv/Lib/site-packages/voxcity/` は調査したインストール環境内の相対位置。JSON内のローカル絶対パスは環境依存の監査情報であり、第三者の取得先ではない。本文のソース行は当時の保存ソースに対する位置。
>
> このPRは本ディレクトリのMarkdown 3件のみ。コード・テスト・入力データ・ローカルログ・未完成Adapterを含まず、Standard Canopy／既存VoxCity Adapter契約や正式受入記録を変更しない。実装・比較計算の開始を承認するものではなく、Draftとして独立レビューを待つ。
> 対応するローカル原本: `API_REVIEW.md`、SHA-256 `5648ee3d42faf753af591bebe5d170e42aa39eb1511cf222a50568fbe58c1692`。原本は不変。

[調査結果](RESULTS.md) · [API調査](API_REVIEW.md) · [最小Adapter案](MINIMAL_ADAPTER_PROPOSAL.md)


2026-10-26 JST。**CONDITIONAL**。植生・直達日射APIは存在しimport成功。ただしOUEM Height Envelopeの絶対Zラスタをそのまま渡す入力契約ではない。最小Adapterの設計までとし、実装・voxel化・日射比較は実施していない。

## 基準と実装証拠

- 最新main `b626ee326c3a29836cb40d3b439d0d9db99fe0bb`。PR #69 merged、merge commit一致、PR head `db794b33cad5d980345bfc246507bb1a15c4cddf` の祖先確認済み。
- インストールvoxcity=1.7.0、PEP610 direct_url commit=`fa212656305328a9a657973bae26f352bfe813bc`。pyproject.tomlも同pin。
- 既存 `ouem.komae_integration.voxcity_provenance()` によりimport shadowなし、非editable VCS origin、全136 Python sourceのinstalled RECORD SHA-256照合に成功。内容集約SHA `33e2bfdbc8a677f53154e8cd16295603819c68cf9f24c7a4cdfeb196bcbcd0bd`。
- RECORD一致はupstream Git treeとの独立照合ではない。この限界を保持する。取得済みのインストールソースを直接調査し、12ファイルを `source-snapshots/` にバイト同一保存。SHAとASTの行番号は `source-index.json`。同JSONのGitHub locatorはpinに基づく参照候補であり、今回HTTP取得した根拠ではない。
- 以下のパスは `.venv/Lib/site-packages/voxcity/` 相対。記載行は今回保存したソースの1始まり行。環境固有の絶対パスはJSONの監査識別情報にのみ残す。

## APIと確認根拠

| 調査事項 | 実関数・クラス／ファイル:行 | 確認した実装・意味 |
|---|---|---|
| 植生入力 | `CanopyGrid`、`models.py:43` | topの2D ndarray、GridMetadata、任意bottom ndarray。型そのものには鉛直意味のvalidationなし |
| 上下端 | `update_voxcity`、`generator/update.py:31`、L288–304/L356–364 | `canopy_top` / `canopy_bottom`を受取り、そのままVoxelizerのtree_grid / canopy_bottom_height_gridへ渡す |
| 実voxel化 | `Voxelizer.generate_combined`、`generator/voxelizer.py:158`、`_voxelize_kernel`:39 | canopy top/bottomは**地盤からの相対高m**。kernelでground_levelへ加算。絶対標高を渡すとTerrain二重加算になる |
| 地盤 | 同generate_combined L188–189、`process_grid_optimized`、`geoprocessor/raster/core.py:48` | DEMから最小値を減算、建物ID≠0の領域をIDごとの平均で平坦化し再正規化。ID全0なら平坦化なし。最小値はAdapter側で保持する必要あり |
| voxel方向 | `utils/orientation.py`冒頭、`ensure_orientation`:140、`simulator/common/coordinates.py` | shape=(north,east,up)、行0=南、列0=西、k増加=上。sceneではx=east,y=north。north-up TIFFは縦反転。一般の「rasterio-layout」用transpose関数と混同しない |
| 入力格子のmetadata | `GridMetadata`、`models.py:10` | crs/bounds/meshsizeのdataclass。低level Voxelizer自体はCRSを読まない。高levelのrectangle経路との整合は呼出側の責任 |
| 高level格子 | `compute_cell_center_coords`、`geoprocessor/raster/core.py:189` | rectangle=[SW,NW,NE,SE]のlon/latからGeod距離とuvベクトルでcell centres生成。EPSG:6677の400×300格子と自動的に同一とはしない |
| 建物重複 | `_voxelize_kernel`、`generator/voxelizer.py:39` | ground→TREE_CODE=-2→BUILDING_CODE=-3の順に代入し、同voxelは建物で上書き。実樹冠の物理collision解決ではない |
| 直達日射 | `get_direct_solar_irradiance_map`、`simulator/solar/radiation.py:18` | VoxCity、azimuth度、elevation度、DNI(W/m²)を受取。返値2D float map=transmittance×DNI×sin(elevation)。無効観測地点NaN |
| 観測点・遮蔽 | `compute_direct_solar_irradiance_map_binary`、`simulator/solar/kernels.py:11` | 名称binaryだが返値は連続透過率。地表walkable transitionを探索。view_point_height既定1.5mを `int(height/meshsize)` に切捨て。水等7/8/9、ground等負クラス、屋上設定でNaN条件が変わる |
| 植生の実効減衰 | `trace_ray_generic`、`simulator/common/raytracing.py:11`、`calculate_transmittance`:6 | TREE_CODE=-2セルを通る実長(m)ごとにexp(-tree_k×tree_lad×length)を累積。他固体は不透過。直達経路は透過率<0.01でhit扱い→最終0。voxel生成だけでなく**計算経路に植生減衰が実装されている**。今回の実データでの作用は未実行 |
| 光学パラメータ | `radiation.py:18` L38–39、上記raytracing | `tree_k=0.6`、`tree_lad=1.0`が既定。一定値で全TREEセルへ作用。HAGやCRからLADが推定されるAPIではない。物理単位・観測根拠の保証はコードにない |
| 葉の有無 | 上記CPU direct API・raytracing | 調査対象の経路にはleaf-on/off引数・自動季節変化なし。日時でLADは自動変更されない。tree_lad=0なら減衰式上1だが、別ケースの検証なしに全処理同一とは主張しない |
| 方位 | `direction_to_axis_vector`、`utils/orientation.py:72` | azimuthは北から時計回り。azimuth−rotation_angleを使い、(cos el cos az,cos el sin az,sin el)がnorth/east/upのray方向。solar APIはextras.rotation_angle既定0を読む |
| 日時→太陽 | `get_solar_positions_astral`、`simulator/solar/temporal.py:30` | times、lon、latを受けAstral Observer/elevation/azimuthを呼ぶ。timezone-aware timesを呼出側で指定する。直達API自体には日時・timezone引数なし |
| 時系列／積算 | `get_cumulative_global_solar_irradiance`、`temporal.py:213` | dfのDNI/DHIとlon/lat、tz=UTC差(時間)。内部FixedOffset(tz×60分)→UTC→Astral。start/endはMM-DD HH:MM:SS。Wh/m²相当の積算。最小PoCには不要 |
| 散乱／合計 | `get_diffuse_solar_irradiance_map`、`radiation.py:97`、`get_global_solar_irradiance_map`:152 | SVF×DHI、直達＋散乱。直達と別の天空サンプリング条件が必要。今回の最小案は直達のみ、全天日射成功とは呼ばない |

### 座標・鉛直の注意（変更せず報告）

kernelの定義は、s=meshsize、D=同一格子DEM、D0=その最小値、建物なしの場合:

```text
g = int(float32(D-D0)/s + 0.5) + 1
b = int(float32(relative_bottom)/s + 0.5)
t = int(float32(relative_top)/s + 0.5)
TREE occupancy = [g+b, g+t)  # 整数k、半開区間
```

roundされたt=b>0ならbを1下げて少なくとも1層にする処理がある。占有面の候補絶対Zは `D0+k*s`、中心は `D0+(k+0.5)*s` と区別して照合する必要がある。地表の`+1`と地盤・樹冠高の個別roundで、単純な入力絶対Zと面位置が一致しない。これを隠すoffset補正は加えず、面／中心・丸め誤差・薄い冠の拡張を報告する。既存Building Adapterもvoxel化のroundを別途監査している。

`direction_to_axis_vector`のdocstringには太陽方位も+180変換するように読める記述がある一方、CPU solarはAstralの太陽方位をそのままこの関数へ渡す。rayはobserver→sunを必要とし、式もtoward方向。docstringを根拠に独断で+180を追加しない。次工程で北／東／南／西のrayと期待する影の反対方向を小fixtureで確かめ、既存ソースは変更しない。

CPU rayは有限domainを出ると未考慮の外部遮蔽物を追加しない。小領域端の影は過小になる可能性があり、bufferと評価内域を分ける。夜間は直達API入口でelevation>0をgateする設計が必要（sin(elevation)を直接掛けるため）。

## 既存OUEMコード／テストとの境界

- `src/ouem/komae_canopy.py:convert_chm`は旧HAG provenance schemaと既定3m閾値、bottom=0.4×CHMを使用。このHeight Envelope入力へ自動接続しない。
- 同`scenario_arrays`は相対top/bottomを受けupdate_voxcityを呼ぶが、絶対Height Envelopeのvalidity/provenance/格子変換入口ではない。既存コードを変更しない。
- `tests/test_komae_canopy.py:test_real_pinned_engine_overlap_and_component_preservation`は実pin engineの合成2×2で建物優先・配列保護・反復一致を確認する既存テスト。solar差分のテストではない。
- `tests/test_voxcity_adapter.py`、`test_voxcity_post_crs_repair.py`はBuilding Adapter関連。`tests/test_height_envelope.py`はHeight Envelopeの合成検証。今回再実行していない。
- 実行したのは入力読取、source/RECORD照合、API importとsignature取得。JIT kernel実行・voxel生成・solar計算・pytestは行っていない。CPU経路を調査し、GPU backendは実行・採用していない。
