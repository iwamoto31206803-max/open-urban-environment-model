# STEP 2-B Mixed-LoD Canopy Integration Feasibility

**合成統合 PASS / 実データCanopy統合 NOT_VERIFIED**。PR #154マージ後main `62ec99e` を基点にGEEKOM-A6のOUEM Windows venvで検証。 `terrain_integration_ready=false`。 [STEP 1監査](../../planning/OUEM_STEP1_Compatibility_Audit_v0.1.md) · [H0](../../planning/OUEM_H0_Height_Distribution_Design_Audit_v0.1.md) · [STEP 2-A](STEP2A_BUILDING_SHADOW_E2E.md)

## 実データの入力監査

ローカル `data/` の `height_envelope_manifest.json` と既存B1の実行手順を確認した。確認できた実データHeight Envelopeは `data/work/height-envelope/komae-exploratory-20261026-01/generated/` の1件。他の検索結果はテスト生成物であり、実証用の追加入力とは扱わなかった。他ドライブの網羅的探索は実施していない。

| 項目 | 既存Height Envelope | Candidate B |
|---|---|---|
| CRS | EPSG:6677、north-up | 保存中心はEPSG:6677、VoxCity uv軸 |
| 範囲 | [-23600,-40800,-23200,-40500] | Processing Domain [-22588,-39938,-22461,-39811] |
| 格子 | 1 m、400×300 | Terrain 0.5 m、254×254、Voxel 127×127×12 |
| Model中心をsampleした結果 | valid 0／outside 16,129／missing inside 0 | 全16,129列が既存Envelopeの外側 |
| 元DEM SHA | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` | `ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2` |

範囲は重ならず、元DEMの同一性も成立しないため、既存Envelopeを平行移動・補完せず、実データのTREE配列生成は実施しなかった。T5のD0=23.959999084 mや所有ID別平均地盤へ、旧Envelopeの絶対Zをそのまま接続できるという判定も行っていない。

既存Envelopeのmanifest SHAは `6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68`。manifest・全出力・元CHM・DEM・出典snapshot・限定レビュー記録をハッシュで再照合し、`height_envelope.validate_sources:109` で既存の来歴条件を確認した。各TIFFのCRS・Affine・shape・NoData・単位・鉛直タグも照合した。 [元Height Envelopeの実装](../../../src/ouem/height_envelope.py)

元CHMはMeta CHMv2のHAG（local groundからの高さm）。既存モデルは `top=DEM+CHM`、`bottom=DEM+(1−CR)×CHM`、CR=.60。上端・下端はT.P.絶対標高mという限定レビューに基づく推定で、観測された樹冠下端や樹木存在の証明ではない。既存レビューは旧DEMのSHAに結び付いている。Candidate Bの区部DEMのT.P.継承推定、realization・epoch・標高精度、CHMの時点・精度・位置ずれ、CRの誤差は引き続き留保する。

state=1は計算上有効で、top>bottomの時だけTREE候補。top=bottomの有効セルもあり、不存在の観測証拠とは扱わない。浮動ラスタのNoDataは−9999。stateのerror bitはmissing CHM/DEM=2/4、invalid CHM/DEM=8/16、outside CHM/DEM=32/64、model/Float32不正=128。state自体のNoData指定はなく、原マスク・範囲外・非有限値を別に判定する。

### 保存Raw CHMの次工程への利用候補

取得済みタイル `1330021123.tif`（EPSG:3857、SHA `6313f286dca3b9f760be95d998e9648d0dd77b0a9305081b67422150340af862`）について、実中心を正しく変換し元マスクを尊重してnearest sampleした。16,129中心すべてが範囲内かつ有効で、うち値0は13,819。これはHAG入力の読取監査であり、Candidate B用Envelopeの完成やCanopy不存在の確認ではない。新規ダウンロードは行っていない。

## 最小adapterと合成検証

`src/ouem/candidate_b_canopy.py::integrate` はSTEP 1 Probeと既存 `real_komae_solar.integrate_canopy:47` を利用する。Candidate Bの絶対地盤配列をB1の `effective_ground_H` へ対応させ、D0相対地盤、保存セグメント・高さ、地表面index+1を渡す。絶対T.P.宣言と元DEM SHAの一致を要求し、不明な鉛直基準・D0変更・不正区間を拒否する。この呼出境界は探索的なadapterで、正式Canopy/ Terrain schemaや来歴validatorを代替しない。

既存B1と同じ固定VoxCity 1.7.0、commit `fa212656305328a9a657973bae26f352bfe813bc` の公開 `Voxelizer.generate_combined` を合成モデルで実行した。元B1/B2実装は変更していない。公開APIが生成した非TREE占有を保存baseと比較して一致を要求するため、後続実データでは背景の再構成が少しでも異なると拒否する。保存T5を再生成したり置換する処理は今回実行していない。

| 合成条件 | 独立した期待値と実測 |
|---|---|
| 4×6×8、地盤25 m、表面k=0、建物1棟はk=1〜3、Canopy下端27 m・上端30 m | TREEはk=3〜5、建物と競合するk=3を除く。71 TREE、24占有列。候補建物列1、建物優先で除かれたTREE候補1ボクセル |
| TREE除去 | No-Canopyと全値一致。No-Canopyのbase prefixも元配列と全値一致 |
| 上下端34/37 mへ変更 | 必要なZ容量だけ8→13へ拡張。TREE k=10〜12。元占有とD0=25 mを維持 |
| missing inside・outside・invalid state・below-ground・zero-depth | 別のセルで各1列を確認。地盤下の区間は全体を除外し、地盤へ吸着させない |
| 不整合 | 鉛直基準、HAGを絶対Zとする誤宣言、元DEM SHA、D0、反転区間、有効指定のNaN、不正state、base改変を拒否 |
| 入力保護と再現性 | read-only入力で実行。入力・セグメント不変。同じ入力のCurrentとQAが一致 |

上下端のnominal edgeと入力Hとの差は通常ケースでそれぞれ+1 m。既存の「最初の空気index＋相対区間の丸め」規則に対応する。整数化・薄いcrownの拡張も既存B1の独立scalar QAと回帰fixtureで検査し、元Hの値は変更しない。この数値差を測量精度・鉛直datum補正と解釈しない。

Currentの合成int8 C順バイトSHAは `f150c46875fa23ea34a61a027968647835224a0a4935a8d18a390d6fb7cf0e65`。合成・関連pytestは57件通過、Solarを計算する1件は明示的に除外した。

既存helperの制約も維持した。TREEが1つも生成されない場合は成功を返さない。また、公開APIが必要なTREE終端まで割り当てられない丸め条件は、上端切捨てを修復せず拒否する。これらは実データを無条件に統合できるという保証にせず、次工程で診断対象にする。

## 再現手順

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_canopy `
  --source-run data/work/terrain-candidate-b/t5-23-02 `
  --envelope-manifest data/work/height-envelope/komae-exploratory-20261026-01/generated/height_envelope_manifest.json `
  --output-dir data/work/terrain-candidate-b/step2b-audit-repro

.venv/Scripts/python.exe -m pytest -q -s -ra tests/test_candidate_b_canopy.py tests/test_compatibility_probe.py tests/test_shared_vertical_domain.py --deselect=tests/test_shared_vertical_domain.py::test_expanded_solar_uses_same_observers_and_pair_grid
```

監査CLIは入力を読み取るだけで、Current配列やSolar/GVIを生成しない。新規監査runの `report.json` に監査完了と実統合NOT_VERIFIEDを別々に保存する。今回の `data/work/terrain-candidate-b/step2b-audit-03/report.json` のSHAは `d0b489272865a04bde2c411713f3ad23dd188e46ffd09111195a1fa30292f24e`。再実行 `step2b-audit-04` はバイト一致。合成実行ログは `data/work/terrain-candidate-b/step2b-related-final.log`。T5ボクセルとSTEP 2-Aのreport・GeoTIFFも記録済みSHAと一致した。

## STEP 2-Cへ必要な条件

1. 保存Raw CHMを再利用候補とし、Candidate B全処理域のcrop・マスク・0 mの意味を保持する。Meta HAGと候補B DEMの組合せ、時点差、CR=.60等の推定モデルを明示的にレビューする。
2. T5の拡張Terrain SHAに結び付く絶対top/bottom・stateを新規実験用Envelopeとして生成する。既存 `validate_sources` はAccepted Standard Terrainを要求するため、Experimental Terrainをそのschemaや受入記録に偽装しない。限定profileで既存計算・書込helperを利用する設計を別途承認する。
3. 全モデル中心の被覆・validity・来歴を検証し、欠測の扱いを決める。不明セルを樹木不存在へ置き換えない。D0・地盤条件付けとEnvelope DEMの対応を再確認する。
4. 保存T5の高さ・セグメントを固定SHAで読み、上記adapterでCurrent/No-Canopyを新規出力して全占有・区間・共通Z容量を再監査する。state・missing・outsideも同時に保存して、未知セルが指標計算で不存在として集計されることを防ぐ。今回の実統合はNOT_VERIFIED。
5. その成立後に観測点・Solar/GVI条件と評価域を決める。今回の検証にはSolar/GVI実行、正式Terrain統合、樹木の現地検証を含まない。

## 回帰結果

Solar/GVI計算を除く回帰は **1,106件通過、9件skip、3件deselect、286件警告、失敗0**（890.69秒）。ログは `data/work/terrain-candidate-b/full-step2b.log`。skipは専用GIS/QGIS Python 4件とWindows symlink権限5件。Markdownリンクと `git diff --check` も確認した。

今回の選択は `--ignore-glob=tests/*gvi*`、`--ignore-glob=tests/*shadow*` に加え、`test_b1_physical_sanity.py`、`test_canopy_observer_geometry.py`、`test_e2e_config.py`、`test_synthetic_building_solar.py` をignoreした。次のSolar実行3件もdeselectした。したがって、この件数を全テスト無条件のPASSとは扱わない。

- `tests/test_real_komae_solar.py::test_real_solar_common_observers_sign_and_crop_diagnostic`
- `tests/test_shared_vertical_domain.py::test_expanded_solar_uses_same_observers_and_pair_grid`
- `tests/test_gis_visualization.py::test_actual_synthetic_e2e_handoff`
