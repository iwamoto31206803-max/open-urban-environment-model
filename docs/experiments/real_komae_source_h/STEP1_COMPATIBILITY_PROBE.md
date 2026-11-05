# STEP 1 読取専用Compatibility Probe

2026-11-05、GEEKOM-A6の通常Windows OUEM venvで実施。main基点 `8093eba`。 [接続監査](../../planning/OUEM_STEP1_Compatibility_Audit_v0.1.md) · [H0設計と引継ぎ](../../planning/OUEM_H0_Height_Distribution_Design_Audit_v0.1.md)

## 実測

| 保存済み入力 | 配列shape | TREE数 | B2定義の有効観測点 | ROIセル | 数値handoff |
|---|---|---:|---:|---:|---|
| B1 A、phase3c | 128×128×27 | 95,735 | 12,638 | 4,096 | PASS |
| B1 B、phase3c | 128×128×26 | 87,384 | 13,923 | 4,096 | PASS |
| Candidate B、T5-3 | 127×127×12 | 0 | 10,782 | 10,000 | PASS |

ROI値は保存config・中心配列から取得した。このphase3cのB1評価域は64×64セルで、処理配列128×128と区別する。T5の63棟とD0・格子・クラス・ROIを再生成せず読み込んだ。Candidate B観測点は保存されていないため、既存B2の1.5 m要求・整数化定義で再構成して接続条件を調べた。新しい実データSolar/GVI計算、Candidate B E1日陰runner、高さ分布ボクセルは未実施。

判定は `NUMERICAL_HANDOFF_PASS` に限定する。B1の既存readerが保存receipt・config・出力SHA・上流入力と観測点を照合し、Candidate Bは固定T5 reportとその出力SHAを照合した。Raw→Mixed Standardの独立Consumerを今回新規実行した結果ではない。測量精度・科学検証・正式統合・新たなAcceptanceは未検証。 `terrain_integration_ready=false`。

## 実行

```powershell
.venv/Scripts/python.exe scripts/work/step1_compatibility_probe.py `
  --b1-run data/work/shared-vertical-domain/phase3c-20261029-01/outputs/komae-a-3c-20261029-01 `
  --candidate-run data/work/terrain-candidate-b/t5-23-02 `
  --candidate-report-sha256 1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f
```

B側は `komae-b-3c-20261029-01` に置き換える。stdoutを新しいGit管理外ファイルへ保存する。入力NPYはread-only mmap、probeは配列を変更しない。B1は既存Watchの全runと上流ファイル、Candidate Bは固定reportと全出力を実行後に再照合し、変更なしを確認した。ファイルが無い環境では読込失敗として報告し、合成テストだけを実施する。

| 今回の保存ログ | SHA-256 |
|---|---|
| data/work/terrain-candidate-b/step1-probe-a-final.json | `7aa348e75c450397205ae02b20fda9be5e7a92176b8a23cd999521141d5b9e7a` |
| data/work/terrain-candidate-b/step1-probe-b-final.json | `44aeee34d7c5f7542965e757560ed78f22576ccf76223e13ed1f09a79c2af3a6` |

ログには入力パス・サイズ・SHA、固定VoxCityバージョンとcommit、判定範囲を保存した。数値probeは既存のD0・観測点helperを共有するため、それら自体の独立検証を完全に置き換えない。

## 合成・回帰検証

`tests/test_compatibility_probe.py` は非正方形の手作成grid、地表index 0、観測点index 2、絶対H=27.5 mを期待値として定義する。正常入力、read-only配列、Canopy識別、LoDラベル非依存を確認する。軸・shape・D0・ROI・クラス・座標・観測点XY/H・index・所有ID・source_id・地盤・domain・dtypeの不整合を明示的に拒否する。

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_compatibility_probe.py tests/test_b2_gvi.py
```

関連pytestは34件通過、2件警告（Matplotlibの非対話描画と将来の非推奨API）。既存B2回帰には小さい合成モデルでの公開CPU API呼出しが含まれる。実データ評価の再実行は含まれない。全体pytestの実行ログはGit管理外の `data/work/terrain-candidate-b/full-step1.log`、最終件数はPR本文に記録する。

全体pytestは1,276件通過、10件skip、345件警告、1件失敗。失敗は既存の `test_zip_repack_is_recorded_not_mistaken_for_tiff_revision` で、開始時のGit識別情報が取得できた一方、終了時は取得失敗によりnullとなり、不変性ゲートが停止した。コードのSHAは前後で同一。Git subprocessの10秒制限と整合する一時的取得失敗として記録し、既存のゲートや取得コードは変更していない。該当ファイル `tests/test_tokyo_tama_dem_acquisition.py` を同じWindows venvで再実行し、44件すべて通過した（474.28秒）。再実行ログは `data/work/terrain-candidate-b/step1-dem-retry.log`。全体初回の失敗と限定再実行の成功を区別する。skipは専用GIS/QGIS Python 5件とWindows symlink権限5件。
