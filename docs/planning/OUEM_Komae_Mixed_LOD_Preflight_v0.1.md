# 狛江市 PLATEAU Building LoD1・LoD2混在 Preflight v0.1

調査日: **2026-10-30 JST**。基準main:
`c72460326b7b42d37ef4ea9aef6afcf227251e2e`（PR #132 merged）。
状態: **Raw・保存済み成果物の読取診断と実装準備の提案**。
既存Reader/Native/Standard/Adapterは拡張・置換していない。
Converter、Native登録、Standard生成、VoxCity、GIS子処理、正式Acceptanceは実行していない。
今回の候補選択・XY投影は作業用の診断であり、新しいStandard成果物ではない。

## 1. 結論

候補ルール「同一Building IDでLoD2があれば優先、なければLoD1」は、
今回のRaw形状・IDから**選択可能性を確認できた**。ただし、固定400m×300m AOI内の
**373棟は全棟が両LoDを持つため、候補選択はLoD2=373、LoD1=0**となった。
**このAOIで実際にLoD1が混在するケース、Mixed-LODのNative/Standard/engine動作は未検証**。
4ファイル全体にはLoD1-onlyが515棟あるが、いずれも今回AOIのfallbackには入らない。

また、入力範囲の差を確認した。400m×300m AOIは4メッシュにまたがり、既存Source-Hの
173棟は東側2ファイルの結果だった。今回の373棟には西側2ファイルの200棟が追加される。
過去の173棟の結果を373棟へ書き換えず、それぞれの入力・範囲を区別する。
旧111棟の受入記録は維持し、現存しない旧GPKGとの全ID/形状一致は主張しない。

代表高さの式自体は絶対Zの両LoDに適用し得るが、LoD1の上面は供給元の代表高さモデル、
LoD2の最大Zは詳細形状の最高点であり、同じ意味の屋根高ではない。
373棟の`maxZ(LoD2)-maxZ(LoD1)`は**−9.993542〜+5.106095m、中央値+1.099641m**。
LoD2の方が常に高いとは限らず、科学的な精度優劣・高さ補正量には解釈しない。

## 2. AOI・入力・所在

[既存設定](../../config/study_areas/komae_09LD3451.yaml):
EPSG:6677、`[-23600,-40800,-23200,-40500]`、400×300m。
XYはeasting/northing。6668へ水平変換した外接範囲は
`[139.5727577949,35.6319667616,139.5771829171,35.6346803430]`。
AOI・context・既存Runは変更していない。

| 種別 | ローカル所在 / 確認 |
|---|---|
| Raw ZIP | `data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip`、1,192,172,043 bytes、既存acquisition-manifest.jsonあり |
| 既存GML | `data/work/real-komae-source-h/run-20261028-04/extracted/udx/bldg/`の53393456 / 53393466。各238,819,640 / 199,626,757 bytes |
| 追加選択抽出 | 同じ既存ZIPの53393455 / 53393465、各83,731,855 / 210,083,285 bytesを今回work内`extracted/udx/bldg/`へ新規抽出。新規ダウンロードなし |
| Converter / Native | 既存run-20261028-04の`converter.gpkg`、`native/native.gpkg`、各66,576,384 bytes。LoD2固定実験の保存済み出力として所在/hashを確認。再実行なし |
| Source-H Standard | 同runの`standard/standard.gpkg`、1,093,632 bytes。SQLite/既存readerで読取り、173 source IDを確認 |
| 地盤 | `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif`、既存manifest。今回effective groundの計算には使用していない |
| 旧受入済みBuilding | 記録上の`data/native/building/komae.gpkg` / `data/standard/building/komae.gpkg`は現存せず。旧Converter出力の既定pathにも実体なし。テスト用GPKGを代用しない |

run-20261028-01/-03にも途中のGML・Converter/Native/Standardが残るが、
今回の比較基準は完了記録のある**-04**に限定した。別Runを混ぜて成功入力にしない。

### 出典と同一性

既存取得記録の公式元:
[PLATEAU Komae 2025 ZIP](https://assets.cms.plateau.reearth.io/assets/6c/9c8c10-16b2-4a21-b971-c9330d4c20f4/13219_komae-shi_pref_2025_citygml_1_op.zip)、
[CKAN](https://www.geospatial.jp/ckan/dataset/plateau-13219-komae-shi-2025)。
製品仕様5.0の2025年度配信物であり、OGC CityGML 5という意味ではない。
[取得記録](../experiments/voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md)には
2026-10-27取得、PLATEAU site policy/PDL1.0・出典表示・対象コンテンツのCC BY 4.0利用等の
確認が記録されている。今回は既存bytesの読取りで、現時点の配布・規約を再照会していない。

4 GMLはZIPメンバー`udx/bldg/<mesh>_bldg_6697_op.gml`。
既存56/66はZIPからのstream hash/EOF CRCと抽出済みGML hashの一致を再確認。
追加55/65も指定メンバーだけを上限256MiB内で新規抽出し、CRC/hash/抽出日時を記録した。
約294MBの追加展開であり、約1.19GB ZIPの再取得はしていない。元Rawは変更していない。

## 3. LoD件数・表現・候補選択

メッシュ矩形は候補入力の選択にだけ使い、実建物のAOI判定は全形状との交差で行った。
LoD2は既存[read_lod2](../../src/ouem/native/building/source_h_lod2.py)の厳密検査を再利用。
LoD1はwork内の限定診断で実XMLのinline Solidを読み、継承srsDimension、明示6697、
有限3D posList、閉じた外周/内周と構造を検査した。Readerの対応LoDは変更していない。

| mesh | Raw Building ID数 | LoD1あり | LoD2あり / 両方 | LoD1-only | AOI LoD1 | AOI LoD2 | 候補採用2 / 1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 53393455 | 1,411 | 1,411 | 1,411 | 0 | 89 | 89 | 89 / 0 |
| 53393465 | 3,637 | 3,637 | 3,609 | 28 | 111 | 111 | 111 / 0 |
| 53393456 | 4,021 | 4,021 | 4,021 | 0 | 53 | 53 | 53 / 0 |
| 53393466 | 3,778 | 3,778 | 3,291 | 487 | 120 | 120 | 120 / 0 |
| **合計** | **12,847** | **12,847** | **12,332** | **515** | **373** | **373** | **373 / 0** |

形状数ではなく親`bldg:Building/@gml:id`のユニーク件数。
両LoD無し0、4メンバーを通じた重複Building ID 0。
4メンバー全域の候補ルール集計なら12,332 LoD2 + 515 LoD1になるが、
その範囲でのMixed-LOD Standard/代表高さ/engine実行を行ったという意味ではない。

### 実際の形状表現

- LoD1: 全12,847 Buildingで`lod1Solid / gml:Solid / exterior / CompositeSurface /
  surfaceMember / Polygon`。polygonはinline、各ringはLinearRing/posList。
  今回AOIの373棟では各棟のZ値は2水準だった。完全なXSD/水密性/全3Dトポロジ検証ではない。
- LoD2: `boundedBy`等の`lod2MultiSurface`内のinline Polygonと、同一Building内の
  LoD2 Solid/CompositeSurfaceからの内部surfaceMember参照。既存readerがリング・
  face対応と参照の範囲/重複を検査した。Solidと参照先を別の建物として二重計上しない。
- LoD1 SolidをLoD2 MultiSurfaceと呼び替えたり、LoD1-onlyを現行LoD2 readerに
  通ったことにしていない。診断は面の集合をメモリ上で比較するだけで、Canonical出力を作らない。

### 選択順序とID

候補は**BuildingごとにLoDを決めてから、その選択形状がAOIと交差するか判定**した。
LoD2の形状がAOI外だからという理由でLoD1へfallbackしない。
今回はLoD1/LoD2のAOI ID集合が同一で、境界由来の集合差は0だった。

利用可能性は今回の構造検査を満たす幾何の存在であり、科学的品質保証ではない。
将来、LoD2が存在するが壊れている場合のLoD1 fallbackは別の方針決定が必要。
黙って「欠損」と同一扱いにせず、停止/隔離/レビューを明示すべきである。

同一親IDから1行だけ採用し、`source_id`と既存UUIDv5規則による`ouem_id`はLoD変更で
勝手に変えない。出典はZIP hash→member hash→親ID→選択LoD→原geometry branchの
連鎖で記録する候補。レコードをLoD別に2件登録する方式や最大LoDを単純連結する方式は採らない。
異年度/別dataset間の同一ID・同一実建物判定は今回検証していない。

## 4. 旧111棟・Source-H 173棟との関係

| 集合 | 根拠と関係 |
|---|---|
| 受入済み111 | [Building pilot](../../experiments/a1_e2e_pilot/README.md)、[A3](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)。既存Native入力3,637→Standard111の記録。現物がないため全ID・Z・形状の再比較不可 |
| 今回mesh65の111 | 2025 ZIPのmesh65もRaw3,637、AOI111で件数・mesh名が旧記録と対応。**同じ件数だけでは同一版・全ID・byte同一性を証明しない** |
| 既存Source-H 173 | 現物Standardを読取り、東側mesh56=53 + mesh66=120の今回Raw LoD2 AOI IDと一致。373の部分集合であることを実確認 |
| 今回4メッシュ373 | 上記173 + 西側mesh55=89 + mesh65=111。追加200を既存Standardや受入記録へ追加していない |

[contained受入記録](../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md)にある
canonical ID `oub-21a29be1-9794-593f-b22c-e3639a7d9d45`は、今回mesh65の
`bldg_992b6520-eba5-4a57-aae5-69d032dc7b8d`から既存規則で再現できた。
これは**1件のID対応**の補助証拠であり、111棟全体や形状・高さの一致を認定するものではない。
旧A3記録は凍結入力のhash自体を主張していない。

既存Source-H Standardの`source_lod`列は173件すべてNULLだった一方、manifestの
`selected_lod_by_id`は173件すべて2だった。NULLをLoD1/2の判断材料にせず、
将来のMixed-LODでは選択LoDの所在・検査方法を明示する必要がある。
既存NULLや過去manifestは修正しない。

今回の4メッシュ範囲確認は、[Source-H完了記録](../experiments/real_komae_source_h/RESULTS.md)や
B1/B2の凍結入力・ROI/contextの成果を遡って再実行・否定・再受入するものではない。
400m×300m全体を新しい入力で扱う場合に、既存2メンバー固定では不足することを示す。

## 5. CRS・高さ・代表高さへの影響

4ファイルの明示srsNameは6697、軸はRawの緯度・経度・H。
ZIP内`metadata/udx_13219_pref_2025_op.xml`は`JGD2011, TP / (B, L), H`を宣言し、
LoD1はLOD0形状へ航空写真測量由来の一律代表高さ（中央値）を付した立体、
LoD2は航空写真測量/航空レーザ成果から図化した立体と説明する。
診断は6668→6677の**XYだけ**を変換し、Hは元値のまま保持した。

したがって同一データ内では両LoDを**提供元宣言の絶対標高H**として解釈できる。
LoD1のZを相対建物高やゼロ基準の押出量とは扱わない。
一方、宣言は独立した測量精度・epoch・標高改定整合の確認ではない。
[Terrain受入](../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)と
[Tama出典訂正](../acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)の
source-declared T.P.との実現上の一致も新たに検証していない。

### 最大Zの実測比較（AOI内の同一373 ID）

`ΔZ = maxZ(LoD2) − maxZ(LoD1)`。
全373棟を対応付け、正303棟、負70棟、ゼロ0棟（診断比較の1e-9m以内）。
この閾値は計算比較用で、科学的/Acceptance許容差ではない。

| 統計 | ΔZ (m) |
|---|---:|
| 最小 | −9.993542 |
| P05 | −0.7684874 |
| 中央値 | +1.099641 |
| 平均 | +0.8680094611 |
| P95 | +2.5669744 |
| 最大 | +5.106095 |

最小差のIDはmesh65の`bldg_873c4f56-8867-4098-9430-9a9700efb4f6`:
LoD1 top=38.278240、LoD2 top=28.284698m。
最大差のIDはmesh66の`bldg_045cafc9-2fe4-4684-8dfb-6cfbed11fdeb`:
LoD1 top=42.414104、LoD2 top=47.520199m。
両者のどちらが現地屋根高に正しいか、差が形状モデル・時点・原典品質のどれに由来するかは未確認。
差を定数補正・誤差許容値・LoD2優位性の根拠にはしない。

### footprintと重複の実測比較

現在の純粋な[build_normalized_footprint](../../src/ouem/adapters/voxcity/__init__.py)を
各LoDのメモリ上の3D面集合に適用。正面積XY面のrepair/normalize/unionは既存Adapterの
派生表現ルールであり、Raw/Standardを修復・上書きしたことではない。

| paired footprint統計 | 実測 |
|---|---:|
| 対称差面積の中央値 / P95 | 3.56816646e-7 / 3.96556455e-6 m² |
| 対称差面積の最大 | 0.0200622101 m² |
| IoU最小 / 中央値 | 0.9997779570 / 0.9999999967 |
| 採用373棟の異なるID間・正面積overlap | 0組（>1e-9m²） |
| 異なるIDで同一footprint | 0組 |

この集団で平面支持は近いが、厳密にすべて同一ではない。小さい差でも格子境界で所有セルが
変わり得る。ベクトルoverlap 0もVoxCityの同一セル内に複数建物が交差しない証明ではない。
将来の他地域・複合建物・BuildingPart・同じ形状の異IDに一般化しない。

### 現行height式を使う条件

[現行Adapter契約](../OUEM_VoxCity_Adapter_v0.1.md)と`derive_attributes`は
`height = maxZ − G_eff_abs`、`min_height=0`。
`G_eff_abs`は**実VoxCity DEM格子のbuilding_id所有セルの平均**であり、
source DEMの任意点・footprint内単純平均・geometry底面ではない。

両LoDが同じ絶対H意味を持ち、有効footprint・実所有セル・整合する地盤があるなら、
式の型/次元は両LoDで成立する候補。ただしLoD1は代表的な平坦上面、LoD2は詳細最高点を
footprint全体へ展開する2.5D代表値になる。後者も高さ分布や屋根形状をengineへ保持しない。

同じGを固定すれば`Δheight = ΔZ`だが、一般には
`Δheight = ΔZ − (G_eff,2 − G_eff,1)`。
今回はengineを動かさないため、**各棟の新しいG_eff・正のheight・数値ID所有・格子/voxel成功は未確認**。
保存済みDEMの標高やsource rasterの平均をG_effの代用品として計算していない。

## 6. 現行パイプライン・VoxCityとの互換性

| 境界 | 現状 / 必要な検討 |
|---|---|
| Raw LoD1 | inline Solidの検査は今回の限定診断で可能。既存`read_lod2`はLoD2だけを選択し、LoD1-onlyを除外する。LoD1対応Readerになったわけではない |
| Source-H foundation / Native | [provenance.py](../../src/ouem/native/building/provenance.py)はrequested_lod=2、Converter use_lod=lod2等を厳密に要求。[Native](../../src/ouem/native/building/source_h.py)はRaw LoD2との対応を再検証。設定だけでMixedを通せない |
| Converter | 固定build/`--epsg 6697 -t use_lod=lod2`が既存経路。[合成実行記録](../experiments/plateau_converter/CLI_SYNTHETIC_EXECUTION_20261027.md)にLoD1 controlの成功はあるが、今回の実Mixed選択・出力・exact-H保存は未実行。単なるhighest指定は将来LoD3を選ぶ可能性もあり候補ルールと同義ではない |
| Source-H Standard | [Standardizer](../../src/ouem/standardize/building/source_h.py)とgeometry helperはLoD2 Raw照合、既知LoD属性2またはNULL、選択manifestのLoD2を前提。full3D/H保存の責任は維持し、LoD1 Solid由来面集合の対応・メタデータを別profileで検証する必要 |
| Consumer | [独立Validator](../../src/ouem/consumers/source_h_standard.py)もselected_lod_by_id=2とLoD2対応を検査。producerだけ緩めれば完了ではなく、独立した選択/形状/ID/Hの検証が必要 |
| accepted Adapter v0.1.1 | v0.1 Standard manifest whitelist、6677/T.P.等のgateがある。Source-H候補v0.2も既存accepted CLIのそのままの入力ではない。今回whitelistや受入範囲を変更しない |
| engine interface | installed VoxCity1.7.0とPEP610 pin `fa212656305328a9a657973bae26f352bfe813bc`を確認。静的ソースではfootprint / id / height / min_heightを消費しLoD列を要求しない。したがって数値/形状interface上は候補だがMixedの実動作成功ではない |

engineの読取箇所はinstalled packageの
`geoprocessor/raster/buildings.py:create_building_height_grid_from_gdf_polygon`、
`buildings_precise.py:_collect_building_polygons`と高さ順/ID処理、
`core.py:process_grid[_optimized]`のID別DEM平均と最小値シフト。
ソースを読んだだけで、これらのengine関数は呼んでいない。
LoD混在で数値IDが再採番される場合も、過去のID gridやmapを新規Runのものへ書き換えない。

## 7. 最小変更案と未解決事項

以下は次PR候補であり**未実装・未承認の契約拡張**。既存Source-Hを置換しない。

1. **選択仕様と別の明示profileを先にレビュー**: 対象release/member集合、親ID単位の
   LoD2→LoD1、壊れたLoD2の停止/隔離、BuildingPart/未対応表現の扱いを明記。
   欠損と品質不良、候補選択とAOI抽出を分離する。
2. **限定LoD1 Solid検証とRaw対応を追加**: 現物で見たinline構造・継承dimension・
   CRS/有限H/リングを検査し、選んだLoDの全faces/rings/XYZとConverter出力を照合。
   LoD1をLoD2と詐称せず、旧read_lod2と旧profileの挙動を維持する。
3. **producer/consumerのLoD来歴**: feature source_lodとper-ID selectionの規則、
   source member/hash/branch、選択除外・fallback理由、ID一意性とexact H保持を検査。
   既存UUIDv5 ID・全3DStandard保持を前提に、output profile/manifestの互換性を明示する。
4. **合成検証を最初の実装sliceにする**: both/LoD1-only/LoD2-only/neither、重複ID、
   invalid LoD2、内周、境界でLoD間AOI判定が異なる例を用意し、選択前後のID集合を独立照合。
   current LoD2出力を変えない回帰を実施。現AOIはfallback0なので、これだけでMixedの
   実データ検証を代用しない。実fallbackを確認する次地域/別範囲は別途承認する。
5. **代表高さAdapterは上流安定後の別PR**: 明示profileのConsumerから、現行2.5D純粋helperを
   再利用できるか検討し、VoxCity実行・G_eff/ownership/小建物/重複/境界を新規Runで確認。
   v0.1.1 whitelistを清掃名目で拡張しない。高さ分布モデルはさらに別課題とし、Standardの
   元3Dを潰さず保持する。

優先は**範囲4メッシュの明示と選択profile/合成fixture設計**。
新しい373棟をそのまま既存A3の111や既存Source-Hの173へ置換する作業ではない。
地盤/鉛直datum/時点、LoD1上面とLoD2最高点の科学的意味、実測精度、
AOI外の515 fallback建物や他地域での適用、壊れたLoD2からのfallback方針は未解決。

## 8. 来歴・再現・検証

作業領域は`data/work/komae-mixed-lod-preflight/20261030-01/`（Git除外）。
`input-inventory.json`は開始時hash、`additional-member-receipts.json`は新規選択抽出の来歴、
`zip-member-check.json`は既存GMLとの照合。
`summary.json`、`selected-buildings.json`、`paired-comparison.json`、`overlap-pairs.json`に
集計・ID・LoD・全件の数値を保持。大容量/実データ・JSON・ローカル診断スクリプトはコミットしない。

| 入力 | SHA-256 |
|---|---|
| 既存ZIP | `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555` |
| 53393455 GML | `07245d14727d83c769a7809e3b135bf651ace6c3a18293b35c6a7ffe33b45b1f` |
| 53393465 GML | `32f8912b2c3f8b09a2c76211b8ea22c9402f5b1357d36843dcfd5c93616ff613` |
| 53393456 GML | `eaff3868a122e28e8c23810a45165675591ddfa72e1077a1948aa04bd0d89c30` |
| 53393466 GML | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| 比較用Source-H Standard GPKG | `a23829bbcb689a3e830535b7654f0c5b892554b0ad26e0222eaf146e5b9aca3c` |
| 既存Terrain TIFF | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| 元metadata XML | `2c796611353a8168dc11030d0b904ef9205b048fdf2d34212f8c9c953f07ff0b` |
| 最終診断スクリプト | `53c61b57a49ba64127b3dff634ed9c42e8f8f0da0aaf18520fd3a45a0fe3a9c3` |
| 最終summary JSON | `2686702de422263f9a51fd55e171cd492f33adcab22763a9be459e0865ae7df7` |

選択抽出日時は2026-10-30 **19:55:16 JST**（UTC10:55:16）で、元データの取得日とは別。
元ZIPは前掲の2026-10-27取得記録。ネットワーク取得・新しい配布版への置換はない。
開始/終了で既存ZIP/GML/Converter/Native/Standard/Terrain/設定/既存reportのhash不変を確認。

環境はordinary Windows OUEM venv Python3.11.9、NumPy2.4.6、Shapely2.2.0、PyProj3.7.2。
GIS Pythonとの統合、依存更新、engine import/実行は行っていない。
呼んだAdapter helperはOUEM側の純粋geometry関数である。

検証:

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_study_area.py tests/test_source_h_xlink.py tests/test_source_h_ingestion.py tests/test_source_h_standard.py tests/test_source_h_consumer.py tests/test_standard_building.py tests/test_voxcity_adapter.py
.venv/Scripts/python.exe -m pytest -q -ra tests/test_building_provenance.py
```

結果はそれぞれ**205 passed / 1 warning / 63.60秒**、**73 passed / 0.75秒**。
失敗/skipなし。warningは既存stat/fstat ctime診断。
合成fixture・純粋helperの既存テストで、VoxCityや実Converterを呼ぶテストは含めない。
新規本番コードなしの報告書PRなので全体pytestは実行していない。
文書リンク、差分1新規文書、`git diff --check`を確認する。

初回の2ファイルだけの診断では173棟だったが、AOI全体の候補メッシュ確認後に4ファイルで
再集計した。初回値をAOI全体の数として流用していない。旧111ファイル不在や
fallback未発生を不足/限界として残し、失敗・未検証をPASSへ読み替えない。

### 再現方法

基準commitのOUEM venv、同じ4メンバー/shaと設定を使用する。
ローカルには下記コードを`diagnose_mixed_lod.py`として作業領域へ保存し実行した。
以下の付録は実行コードと同じ内容で、後からReaderの正式機能へ昇格させるものではない。
実入力は読み取り専用、JSON出力先は**新しい作業directory**に限定して再試行する。
保存済み完了Run内や今回の証拠を上書きしない。

既存runの56/66メンバーを参照し、55/65は同じZIPから新作業領域の`extracted/udx/bldg/`へ選択抽出する。下記スクリプトもその新作業領域へ保存し、リポジトリrootから`.venv/Scripts/python.exe <新作業領域>/diagnose_mixed_lod.py`で実行する。既存run・今回の保存済み診断directoryは出力先にしない。

### 付録: 実行した読取診断コード

```python
"""Local read-only diagnostic, NOT a new Source-H ingestion/profile implementation."""
from pathlib import Path
from collections import Counter
import json
import math
import hashlib
import xml.etree.ElementTree as ET
import numpy as np
from pyproj import Transformer
from shapely.geometry import box
from ouem.study_area import load_study_area
from ouem.native.building.source_h_lod2 import read_lod2, _ring
from ouem.standardize.building.source_h_geometry import map_xy, as_shape, points
from ouem.adapters.voxcity import build_normalized_footprint
from ouem.consumers._source_h_geometry import read_standard

WORK = Path(__file__).resolve().parent
BASE = Path('data/work/real-komae-source-h/run-20261028-04')
G = '{http://www.opengis.net/gml}'
B = '{http://www.opengis.net/citygml/building/2.0}'
X = '{http://www.w3.org/1999/xlink}href'
SRS = 'http://www.opengis.net/def/crs/EPSG/0/6697'
area = load_study_area('config/study_areas/komae_09LD3451.yaml')
xy = Transformer.from_crs(6668, area.epsg, always_xy=True)
bounds = Transformer.from_crs(area.epsg, 6668, always_xy=True).transform_bounds(*area.extent, densify_pts=21)
aoi = box(*area.extent)


def stats(values):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return None
    return dict(zip(('min', 'p05', 'median', 'p95', 'max', 'mean'),
                    map(float, [*np.percentile(a, [0, 5, 50, 95, 100]), a.mean()])))


def projection(faces):
    raw_points = [p for face in faces for ring in face for p in ring]
    xs, ys = [p[0] for p in raw_points], [p[1] for p in raw_points]
    if not box(min(xs), min(ys), max(xs), max(ys)).intersects(box(*bounds)):
        return None
    tree = ('GeometryCollection', tuple(('Polygon', face) for face in faces))
    tree = map_xy(tree, xy.transform)
    geometry = as_shape(tree)
    if not geometry.intersects(aoi):
        return None
    footprint, diag = build_normalized_footprint(geometry, 'read-only-preflight')
    zs = [p[2] for p in points(tree)]
    return dict(top=max(zs), bottom=min(zs), levels=len(set(zs)), footprint=footprint,
                footprint_area=footprint.area, vertices=len(zs), surface_parts=len(faces),
                footprint_diagnostics=diag)


def lod1_records(path):
    """Inspect this corpus' inline LoD1 Solid; fail rather than invent a conversion."""
    result = {}
    inherited_dim = []
    forms = Counter()
    for event, node in ET.iterparse(path, events=('start', 'end')):
        if event == 'start':
            inherited_dim.append(node.get('srsDimension', inherited_dim[-1] if inherited_dim else None))
            assert inherited_dim[-1] in (None, '3')
            if 'srsName' in node.attrib:
                assert node.get('srsName') == SRS
            if node.tag == G+'posList' and inherited_dim[-1] == '3':
                node.set('srsDimension', '3')  # in-memory validation only
            continue
        inherited_dim.pop()
        if node.tag == B+'Building':
            identifier = node.get(G+'id')
            assert identifier and identifier not in result
            branches = node.findall(B+'lod1Solid')
            assert len(branches) <= 1
            faces = []
            if branches:
                branch = branches[0]
                assert len(branch) == 1 and branch[0].tag == G+'Solid'
                solid = branch[0]
                assert len(solid) == 1 and solid[0].tag == G+'exterior'
                assert len(solid[0]) == 1 and solid[0][0].tag == G+'CompositeSurface'
                members = list(solid[0][0])
                assert members
                for member in members:
                    assert member.tag == G+'surfaceMember' and X not in member.attrib
                    assert len(member) == 1 and member[0].tag == G+'Polygon'
                    polygon = member[0]
                    assert polygon[0].tag == G+'exterior'
                    assert all(r.tag == G+'interior' for r in list(polygon)[1:])
                    faces.append(tuple(_ring(r) for r in polygon))
                forms['inline Solid/exterior/CompositeSurface/Polygon'] += 1
            result[identifier] = tuple(faces)
            node.clear()
        elif node.tag.endswith('}cityObjectMember'):
            node.clear()
    return result, dict(forms)


file_rows = []
selected = {}
pair_rows = []
seen = set()
lod1_aoi_ids, lod2_aoi_ids = set(), set()
paths = sorted((BASE/'extracted/udx/bldg').glob('*.gml')) + sorted((WORK/'extracted/udx/bldg').glob('*.gml'))
for path in sorted(paths):
    # Existing strict reader audits Raw XML/IDs/LoD2 profile; no Converter/Native call.
    lod2, excluded = read_lod2([path])
    lod1, forms = lod1_records(path)
    assert not (seen & lod1.keys()), 'duplicate Building ID across files'
    seen.update(lod1)
    assert set(lod2) | set(excluded) == set(lod1)
    row = dict(file=path.name, buildings=len(lod1), lod1=sum(bool(x) for x in lod1.values()),
               lod2=len(lod2), both=sum(bool(lod1[k]) for k in lod2), forms=forms,
               lod1_aoi=0, lod2_aoi=0, selected_lod1=0, selected_lod2=0, neither=0)
    for identifier, faces1 in lod1.items():
        p1 = projection(faces1) if faces1 else None
        p2 = projection(lod2[identifier]) if identifier in lod2 else None
        if p1:
            lod1_aoi_ids.add(identifier)
            row['lod1_aoi'] += 1
        if p2:
            lod2_aoi_ids.add(identifier)
            row['lod2_aoi'] += 1
        if p1 and p2:
            pair_rows.append(dict(source_id=identifier, file=path.name,
                top_lod1=p1['top'], top_lod2=p2['top'], delta_top_2_minus_1=p2['top']-p1['top'],
                bottom_lod1=p1['bottom'], bottom_lod2=p2['bottom'],
                area_lod1=p1['footprint_area'], area_lod2=p2['footprint_area'],
                footprint_symdiff_m2=p1['footprint'].symmetric_difference(p2['footprint']).area,
                footprint_iou=p1['footprint'].intersection(p2['footprint']).area/p1['footprint'].union(p2['footprint']).area,
                levels_lod1=p1['levels'], levels_lod2=p2['levels']))
        # Choose LoD globally BEFORE AOI: no fallback merely because LoD2 misses AOI.
        chosen, lod = (p2, 2) if identifier in lod2 else (p1, 1)
        if chosen:
            assert identifier not in selected
            selected[identifier] = dict(chosen, source_id=identifier, source_lod=lod, file=path.name)
            row['selected_lod'+str(lod)] += 1
        if not faces1 and identifier not in lod2:
            row['neither'] += 1
    file_rows.append(row)

standard = read_standard(BASE/'standard/standard.gpkg', 'building')
overlaps, identical = [], []
items = list(selected.items())
for i, (aid, a) in enumerate(items):
    for bid, b in items[i+1:]:
        overlap = a['footprint'].intersection(b['footprint']).area
        if overlap > 1e-9:
            overlaps.append(dict(id1=aid, id2=bid, area=overlap, lods=[a['source_lod'], b['source_lod']]))
        if a['footprint'].equals(b['footprint']):
            identical.append([aid, bid])
serializable = [{k:v for k,v in item.items() if k != 'footprint'} for item in selected.values()]
summary = dict(files=file_rows, unique_raw_building_ids=len(seen), duplicate_building_ids=0,
    lod1_aoi=len(lod1_aoi_ids), lod2_aoi=len(lod2_aoi_ids), mixed_aoi=len(selected),
    mixed_lod_counts=dict(Counter(str(v['source_lod']) for v in selected.values())),
    lod1_aoi_not_lod2_aoi=sorted(lod1_aoi_ids-lod2_aoi_ids),
    lod2_aoi_not_lod1_aoi=sorted(lod2_aoi_ids-lod1_aoi_ids),
    source_h_standard_ids=len(standard), raw_lod2_ids_equal_standard=set(standard)==lod2_aoi_ids,
    source_h_standard_is_subset=set(standard)<=lod2_aoi_ids,
    extra_lod2_vs_standard=sorted(lod2_aoi_ids-set(standard)),
    pair_count=len(pair_rows), delta_top_2_minus_1=stats([x['delta_top_2_minus_1'] for x in pair_rows]),
    delta_positive=sum(x['delta_top_2_minus_1']>1e-9 for x in pair_rows),
    delta_negative=sum(x['delta_top_2_minus_1'] < -1e-9 for x in pair_rows),
    delta_zero=sum(abs(x['delta_top_2_minus_1'])<=1e-9 for x in pair_rows),
    footprint_symdiff_m2=stats([x['footprint_symdiff_m2'] for x in pair_rows]),
    footprint_iou=stats([x['footprint_iou'] for x in pair_rows]),
    levels_lod1=dict(Counter(x['levels_lod1'] for x in pair_rows)),
    overlap_pairs=len(overlaps), identical_footprint_pairs=identical,
    overlap_max_m2=max((x['area'] for x in overlaps), default=0),
    selected_top=stats([v['top'] for v in selected.values()]))
for name, value in [('summary',summary),('selected-buildings',serializable),('paired-comparison',pair_rows),('overlap-pairs',overlaps)]:
    (WORK/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(summary,indent=2))
```
