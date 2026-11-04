# Mixed-LoD Converter Bridge PoC

状態は **EXPERIMENTAL**。基準mainはPR #136を取り込んだ `c94fc0b`。対象は mesh 53393466 の Raw 選択、二系統の変換、IDと3D幾何の照合まで。 [Mixed-LoD設計](../../planning/OUEM_Komae_Mixed_LOD_Implementation_Plan_v0.1.md) · [Raw selector実測](MIXED_LOD_SELECTOR_POC.md) · [既存4メッシュPoC](FOUR_MESH_REPRESENTATIVE_HEIGHT_POC.md)

## 入力と再現手順

通常のWindows OUEM venvを使用する。固定CLIはnusamai 0.1.19、commit `ce7766df9788ce391b149c55df16d33082d0bc72`、binary SHA-256 `0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b`。既存の取得済みZIPと成功したRaw selector runを使用する。 [Converterの固定・合成実行記録](../plateau_converter/CLI_SYNTHETIC_EXECUTION_20261027.md)

| 入力 | SHA-256 |
|---|---|
| PLATEAU 13219 Komae 2025 ZIP | `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555` |
| `udx/bldg/53393466_bldg_6697_op.gml` | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| `run-pr136-rereview-01/manifest.json` | `eea7a117658208018fb0e12d212f7e63a6fef69a0c86c1265fd6692fda4b0785` |
| 同runの `geometries.jsonl` | `51386b7fb5286e18bf5d310e09ddd7c438c92188efcd713fac7222cf3b9485ef` |

```powershell
New-Item -ItemType Directory -Force data/work/mixed-lod-converter-bridge | Out-Null
.venv/Scripts/python.exe -m ouem.mixed_lod_converter_bridge `
  --selector-manifest data/work/mixed-lod-selector/run-pr136-rereview-01/manifest.json `
  --zip data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip `
  --converter C:/dev/plateau-gis-converter/target/x86_64-pc-windows-msvc/release-lto/nusamai.exe `
  --member udx/bldg/53393466_bldg_6697_op.gml `
  --release plateau-13219-komae-shi-2025 `
  --bounds -22575 -39925 -22475 -39825 `
  --output-dir data/work/mixed-lod-converter-bridge/run-repro-01
```

BridgeはZIP、member、release、AOI、実装SHA、全レコードとJSONLの順序付きXYZを、Raw selectorの再実行と照合する。新しいrunに対象GMLとZIP内のcodelistを抽出し、同じGMLに `--sink gpkg --epsg 6697 -t use_lod=lod1 -t split_components=false` と `use_lod=lod2` を別々に適用する。GPKGは読取専用で開き、複合CRS宣言、Z必須・Mなし、BLOBのSRIDと有限・閉鎖XYZを検査する。Rawは緯度・経度・H、格納順は経度・緯度・H。測量精度や鉛直datumの実現精度は未検証。

各passは対応するRaw branchが存在する全IDを対象とする。両LoDの建物については、選択JSONLにないLoD1の `posList` も検証済みRawから直接読む。面・ring・全XYZを厳密比較し、一致しない場合は面順、内周順、ringの開始点と向きだけを正規化して比較する。多重度と外周／内周の所属を保持する。許容誤差、分割統合、座標補正は適用しない。 `ORDER_ONLY` はこの限定正規化で一致した結果を表す。保存順そのものの一致は `EXACT` で区別する。

`bridge.json` に各passの引数、終了コード、ログ、GPKGハッシュ、全IDの照合結果と選択結果を保存する。 `COMPLETED` は照合処理が最後まで進んだ状態。入力や結果が条件を満たさない場合は `BLOCKED` と非ゼロ終了になる。 [探索的manifest schema](../../schemas/ouem_mixed_lod_converter_bridge_v0.1.schema.json)

## 実測結果

2026-11-04 18:05 JST、Windows build 26300、OUEM venvのPython 3.11.9で実行。保存先は `data/work/mixed-lod-converter-bridge/run-02/`。両passとも終了コード0。stdoutは空で、stderrにはGPKG sinkの非対応Point属性に関する警告が6件ずつあった。属性の完全保持は今回の判定に含めていない。実行開始から照合終了までLoD1は3.37秒、LoD2は6.61秒。これらの時間に事前のRaw再検証と抽出は含まない。

| 対象 | Raw期待 | GPKG実測 | EXACT | ORDER_ONLY | 欠落・余分・幾何不一致 |
|---|---:|---:|---:|---:|---:|
| LoD1 pass | 3,778 | 3,778 | 3,778 | 0 | 0 |
| LoD2 pass | 3,291 | 3,291 | 0 | 3,291 | 0 |

Rawの487棟はLoD1のみ、3,291棟は両LoDを持つ。両LoDの棟は各passに1回ずつ存在し、選択表はLoD2側だけを採用する。両passとも重複IDなし。LoD1の内周ringは4本すべて保存された。LoD2のRawと出力には内周ringがなかった。追加の面多重集合照合で、LoD2全3,291棟の差が面の並び順だけであることを確認した。各面内のring順・向き・開始点・XYZは同じで、Solid参照展開による面の欠落や重複はなかった。

候補Bは **LoD1 31棟、LoD2 32棟、計63棟**。31棟は `EXACT`、32棟は `ORDER_ONLY` で、63棟すべてに選択したpassのfeatureとBLOB SHA-256を割り当てた。Bridgeの受渡判定は `ELIGIBLE`。件数はRaw AOI交差数であり、格子上の採用数は今回計測していない。

| 出力 | SHA-256 |
|---|---|
| `bridge.json` | `53e72d051136df1cc9d2c92701243a7f28b7a144123e52ba50ab81cff6a92900` |
| `lod1.gpkg` | `bdb207ea324e8f1b9a7b45a5de748c9b62273c0f300adfbac349d15a697e38d6` |
| `lod2.gpkg` | `561b910286d5ac340298cd9029c8519459165a29ba69483b85bce7613b4fe048` |

初回 `run-01` は両LoD建物のLoD1比較に既存ring helperを直接使い、Rawの上位要素から継承する `srsDimension` が `posList` 自体にないため変換前に停止した。再実行版では、次元と形状をRaw selectorで検証したうえで、比較用の非選択LoD1座標をRaw `posList` から直接読んだ。初回の失敗receiptは別runに保存した。

## Mixed Native writerの入口

新しいwriterは、両GPKG、selector成果物、Bridge receiptのハッシュを再確認し、選択行の `selected_lod` でpassを決める。各passの `bldg:Building.id` をキーに一意に引き、格納CRS・geometry column・型を再検証して、記録済みSHA-256と一致するBLOBをコピーする。Converter由来のFIDは再採番可能なローカル行識別子として扱い、source_idとouem_idを維持する。両passの単純連結では両LoD建物が重複する。

属性は列名・型・NULLの差を調査して明示マッピングを定める。少なくとも `source_id`、`selected_lod`、`selection_reason`、元member、変換pass、BLOBハッシュを追跡可能にする。 `measuredHeight` と幾何由来のHは別に扱う。writerの受入条件案は、対象IDの過不足ゼロ、選択BLOBのバイト一致、全face/ring/XYZの再検証、CRS/H宣言の保持、独立した探索的provenance、既存の完了runを上書きしない公開手順。 `BLOCKED` のreceiptをwriter入力として受け付けない。今回、writerや既存Native契約への変更は行っていない。

両passは同じ41列定義で、geometry列はいずれもEPSG:6697の `MULTIPOLYGON`、Z必須、Mなしだった。 `measuredHeight` は両LoDの3,291棟で値が一致した。 `-9999` がLoD1に435件、LoD2に434件あるため、次PRでは欠損表現の属性契約を明示する。面順はRawと異なり得るため、選択BLOBのコピーではConverter格納順を維持し、Rawとの独立検証で面多重集合を比較する。

## テスト

Python合成テストでは固定CLIを実行せず、手作成のCityGMLとSQLite/ISO WKB fixtureで両LoDの選択、内周ring、複数branch、面順差、面の欠落・重複、H差、ID差、重複feature、古い・改変されたselector記録、出力改変、run再使用を検証した。関連テストは247件通過、警告4件（76.38秒）。固定CLIを必要とする実行は上記の手動PoCに分離している。

全体pytestは1,151件通過、10件skip、336件警告（491.52秒）。skipは専用GIS/QGIS Pythonが必要な5件とWindows symlink権限が必要な5件。成功・失敗receiptのschema、Markdownリンク、`git diff --check`、PR #134のNative・Standard・VoxCity report・Voxelの既存SHA-256を照合した。pytestログは `data/work/mixed-lod-converter-bridge/related.log` と `full.log`。
