# VoxCity Canopy Shadow PoC — Phase 0–1

> 公開用整理: 2026-10-27。以下は2026-10-26の既存調査・提案の全文を保持した記録。調査結果と **CONDITIONAL** 判定は変更せず、今回新しいAPI実行・Adapter実装・voxel化・日射比較・pytestは行っていない。本文の「今回」「最新main」「commit／push／PR作成なし」は当時の調査実行を指し、本ドキュメントPRの提出操作とは区別する。
>
> ローカル証跡の基点（リポジトリ相対識別子）: `data/work/voxcity-canopy-shadow/komae-phase01-20261026-01/`。本文の `environment-and-api.json`、`input-evidence.json`、`source-index.json`、`source-snapshots/`、`inspect_inputs_and_api.py` は同run内の非公開ローカル証跡で、GitHubへ同梱しない。`.venv/Lib/site-packages/voxcity/` は調査したインストール環境内の相対位置。JSON内のローカル絶対パスは環境依存の監査情報であり、第三者の取得先ではない。本文のソース行は当時の保存ソースに対する位置。
>
> このPRは本ディレクトリのMarkdown 3件のみ。コード・テスト・入力データ・ローカルログ・未完成Adapterを含まず、Standard Canopy／既存VoxCity Adapter契約や正式受入記録を変更しない。実装・比較計算の開始を承認するものではなく、Draftとして独立レビューを待つ。
> 対応するローカル原本: `RESULTS.md`、SHA-256 `4620fbab0f69d78b5129f893161a7495c51f7011294b566b765130dfea2db4f4`。原本は不変。

[調査結果](RESULTS.md) · [API調査](API_REVIEW.md) · [最小Adapter案](MINIMAL_ADAPTER_PROPOSAL.md)


**判定: CONDITIONAL。Phase 0 API／入力／環境調査は完了。Phase 1の最小Adapter設計を提示し、実装前に停止。樹冠なし／ありの日陰・日射比較は未実行。**

理由: 指定pinの植生上下端・CPU日射APIは利用可能だが、Height Envelopeの絶対標高・north-up格子を、VoxCityが要求する地盤相対高・south-upへ変換する局所Adapterが未実装。既存komae_canopyの旧provenance／3m閾値を今回へ流用できない。さらにvoxelのround/+1地表層、真北方位、受光点と境界条件を固定・検証する必要がある。環境不足によるBLOCKEDではないが、実データ日射成功を主張する段階でもない。

## 確認済み環境

- 実行記録日時: 2026-10-26T23:47:38.824005+09:00。
- 最新main: `b626ee326c3a29836cb40d3b439d0d9db99fe0bb`。GitHubでPR #69 mergedを確認し、ローカル最新mainへ切替、PR head祖先確認。tracked working treeはclean。commit／push／PR作成なし。
- VoxCity1.7.0、pin `fa212656305328a9a657973bae26f352bfe813bc`。PEP610 VCS originとinstalled RECORDの全136 Python source照合にPASS。集約hash `33e2bfdbc8a677f53154e8cd16295603819c68cf9f24c7a4cdfeb196bcbcd0bd`。upstream Git treeとの独立照合ではない。
- Python3.11.9／Rasterio1.4.4／NumPy2.4.6／Numba0.68.0／Astral3.2／pytz2026.5／pandas2.3.3。通常WindowsのOUEM venvで実施、QGIS runtimeと混合していない。
- Voxelizer、update_voxcity、CPU get_direct_solar_irradiance_map／get_global_solar_irradiance_map／get_solar_positions_astralの実import・signature取得に成功。JIT kernelの実行、voxel化、太陽位置計算、日射計算は行っていない。import時のMatplotlib fontManager生成ログは日射実験成功ではない。

## 入力・来歴

元Height Envelope manifestはCOMPLETED、SHA `6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68`。下記実ファイルとmanifestを照合、EPSG:6677／1m／400×300、NoData=-9999（stateはタグなし）、全mask有効を確認。上流のCHM／acquisition record／bridge／Terrainとmanifest／受入記録など、元manifestの全input_filesの実hashも一致した。源の限定的適合性判断は実験用であり、科学的精度保証へ格上げしない。

| 識別子 | SHA-256 |
|---|---|
| `data/work/height-envelope/komae-exploratory-20261026-01/generated/canopy_bottom_z.tif` | `61e82f1d8e9c1c4afc653bf6d850cc35052535fd643462da0b89403efeda158e` |
| `data/work/height-envelope/komae-exploratory-20261026-01/generated/canopy_top_z.tif` | `65263bb32aa846688b3fecee3e7b0893c6a9d6f2e8fa9eebaf95c0bc576aed17` |
| `data/work/height-envelope/komae-exploratory-20261026-01/generated/height_envelope_state.tif` | `6a3debfbcd220d6bef9cdb736cc7d8abd545ee3156121746e019093edef71992` |
| `data/work/meta_chmv2_komae_committed_audit_20261025/acquisition-record.json` | `ab83b9b466b85a4dd2a4a73749b1c2fffb68104b88f9d630ea88f2da76c956e0` |
| `data/work/meta_chmv2_komae_committed_audit_20261025/chmv2_aoi.tif` | `c5f99a4e9b21e8f419825ef2cac25ec7b36bafbe8a79a89b062201343f0ef880` |
| `data/work/height-envelope/komae-exploratory-20261026-01/inputs/source-evidence.json` | `afdf8560ac1d7a94cf599ffaa7fe17bbba29df5fca7a61df994052cdc04bf6a9` |
| `data/work/height-envelope/komae-exploratory-20261026-01/inputs/hag-source-statement.txt` | `213860b4fe980cc1fed0857dfa36ccffa0f5c5d5fd5db65699f583fe9de8a32d` |
| `config/study_areas/komae_09LD3451.yaml` | `ccb6f29d713286bee12f6cd041b2085057b41b7d17f389c0422c8146dd984899` |
| `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif` | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| `docs/acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md` | `0ebf6efe75ebb72911a6e86c35c027a67d8e3d6cb4764df5958cadd78c760689` |
| `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif.manifest.json` | `5e96bf3e0ababad7e2f79a0d2090d0356fdc707dff6115575c8b0ba8b88f5dbb` |

元runと既存3D可視化run内の全ファイルを、今回の読取前後にハッシュ照合して不変を確認した（input-evidence.jsonのprotected_files）。Terrain、Height Envelope、Building、正式記録は変更していない。Building成果物は今回入力に使わず、A/Bとも建物なしを提案する。

## API調査の主結果

実ファイル・関数・行番号と根拠は [API_REVIEW.md](API_REVIEW.md)。取得済みソースのバイト同一snapshotはsource-snapshots/、関数のAST行範囲とSHAはsource-index.json。

1. `CanopyGrid.top/bottom`と`update_voxcity(..., canopy_top=..., canopy_bottom=...)`、`Voxelizer.generate_combined(..., tree_grid_ori=..., canopy_bottom_height_grid_ori=...)`で上下端を表現できる。ただし地盤相対高。絶対Zを渡さない。
2. `Voxelizer`はDEM最小値で正規化し、建物IDごと地盤を平均化。ID全0なら地盤平坦化なし。kernelは地表levelに+1し、上下端を個別roundしてTREE_CODE=-2を配置する。建物は後に-3で上書き。voxel化面位置は入力Zと厳密一致しないため、kernel通りの量子化誤差を別に監査する必要がある。
3. CPU日射は植生voxelを通る長さに対し `exp(-tree_k * tree_lad * length)` を累積し、直達APIがDNI×sin(太陽高度)を掛ける。既定tree_k=.6、tree_lad=1、透過率<.01は直達経路で0へ打切り。**植生減衰は実装上接続されているが、今回実データでの作用は計算していない。**
4. 瞬時直達APIの出力は2D float、W/m²、観測できない地点はNaN。binaryという内部関数名でも連続透過率を返す。日陰を独断の閾値で二値化しない。
5. 日時はAstral helperで太陽位置へ変換し、直達APIへ度単位の方位・高度を渡す。UTC差を使う積算APIもある。leaf-on/offの自動季節モデルは調査したCPU経路にはない。
6. north/east/up配列とnorth-up TIFFの反転、投影北と真北、方位docstringとsolar呼出の読み方に注意。独断で太陽azimuthへ180度を足さない。API説明と具体的な要確認点をAPI_REVIEWに記録した。

## 小領域・比較の未実装案

[MINIMAL_ADAPTER_PROPOSAL.md](MINIMAL_ADAPTER_PROPOSAL.md) に、実装前レビュー用の最小構成を記載した。

- 評価ROI EPSG:6677 bounds [-23320,-40760,-23256,-40696]、64×64、4096 valid。正厚さ3842、ゼロ厚さ254。inputの読取集計だけを実施し、変換成果物は未生成。
- 32m halo付き128×128を候補とする。source AOI内だが、太陽条件に対するhalo十分性は未検証。
- A=同一DEM＋共通仮置き地表ラベル、樹冠なし。B=同一条件＋Height EnvelopeからDEMを1回だけ引いた相対上下端。両ケース建物なし、同一1m格子・同一Z基準・同一太陽と光学設定。
- 候補太陽時刻2026-06-21 12:00 JST、DNI800 W/m²、k=.6／LAD=1。すべて実験仮定であり観測ではない。太陽位置の実数値も未計算。CR=.60は既存Height Envelopeの仮定を保持する。
- 元EPSG:6677格子を保持して全配列flipud、GridMetadataを正確に記録する低level経路を提案。投影北の中心方位は読取座標計算で-0.14979770792591632°。rotationのsignと各方向fixtureは次工程で検証する。

## 実行済み／未実行

実行済み: GitHub merge確認・main更新、pin/RECORD/source調査、API import、既存テストの内容調査、入力metadata/hash/不変性、ROIの読取集計と中心座標計算。作業スクリプトは `inspect_inputs_and_api.py`、記録はenvironment-and-api.jsonとinput-evidence.json。

未実行: Adapter変換、樹冠voxel生成、A/B日射、差分図・数値、JIT実行能力、pytest、実測精度検証。従って日陰・日射成功、樹冠有無による変化セル数、科学的効果量の結果は存在しない。既存テストはkernelの建物優先などを含むが、今回PASSしたと記載しない。

## 次の最小作業

独立したローカルAdapterとA/B runnerの実装へ進むか判断を受ける。実装時は(1)絶対Z−DEMと同一DEM照合、(2)方位・flip・grid metadata、(3)kernelのround/+1/薄冠拡張、(4)同一A/B地形・共通Z上限、(5)NaNと共通観測領域、(6)境界buffer、を先にfixtureで検証し、既存CPU直達APIで実小領域比較する。実装範囲は新しいローカルPoCのみとし、既存Standard・Building Adapter・komae_canopy.pyは不変。

制約: 樹冠存在範囲未判定、一定CRは仮定、CHM画像2019-05-25／DEM2022～2023の時期差、水平位置・樹高・光学パラメータの精度未検証、地盤面差、voxel量子化と有限domainを残す。Standard Canopy受入・本番VoxCity環境評価は宣言しない。
