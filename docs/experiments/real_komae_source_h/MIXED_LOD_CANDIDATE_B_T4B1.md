# Candidate B VoxCity Grid Preflight — T4-B1

**COMPLETED / EXPERIMENTAL / NOT_FORMALLY_ACCEPTED**。`terrain_integration_ready=false`、鉛直 `CONDITIONAL`。PR #145を取り込んだmain `45f7d43` を基準とする。T4-B2の技術候補を判定するための格子診断。 [T4-A](MIXED_LOD_CANDIDATE_B_T4A.md) · [T3](MIXED_LOD_TERRAIN_CANDIDATE_B_T3.md) · [A3仕様](../../OUEM_VoxCity_Adapter_v0.1.md)

## 再現と入力

GEEKOM-A6のWindows OUEM venv、Python 3.11.9で実行した。インストール済みVoxCity 1.7.0とGit commit `fa212656305328a9a657973bae26f352bfe813bc` をメタデータで確認する。Mixed Standard、Consumer receipt、T3、T4-Aの固定SHAと出力のハッシュ連鎖を検証し、公開前に再ハッシュする。T4-Aのフラグ、フットプリント状態、AOI外面積と実GPKGのID・LoDを照合し、初期対象40棟（LoD1 19、LoD2 21）を選択した。AOI越境の23棟はID・LoD・理由を除外一覧に残した。元形状と絶対H、出典は保持する。

```powershell
.venv/Scripts/python.exe -m ouem.candidate_b_t4b1 `
  --building-run data/work/mixed-lod-standard/run-02 `
  --consumer-receipt data/work/mixed-lod-consumer/run-04/receipt.json `
  --terrain-run data/work/terrain-candidate-b/t3-02 `
  --t4a-report data/work/terrain-candidate-b/t4a-02/report.json `
  --output-dir data/work/terrain-candidate-b/t4b1-repro
```

新規runの完了マーカーは `report.json`。読取や検証に失敗した場合は `failure.json` にBLOCKEDの理由を保存する。既存出力先の再利用は拒否する。

## 実格子とDEM被覆

固定AOIはEPSG:6677、`[-22575,-39925,-22475,-39825]`。南西・北西・北東・南東の四隅を経度緯度に変換し、ピン済みVoxCityの格子計算へ渡す。実格子の原点は (139.584058973085°, 35.639877696301°)。配列は第0軸が南→北、第1軸が西→東。mesh指定は1 m、エンジン計算結果は100×100、調整間隔は約1.000094 mずつ。格子の寸法はエンジンから取得した。

ローカルT3 GeoTIFFから `dem_interpolation=False` で読んだ。この指定の実装はUTM上の最近傍であるため、呼び出し前に全中心がT3のAOIおよび有効なソースセル中心の凸包内にあることを確認する。T3全セルが有効かつエンジンの値置換対象外であることも検査した。生DEM 10,000値は独立したUTM EPSG:32654最近傍照合と全値一致。T3行列を保存し、再読込でも原値と一致した。AOI端から中心までの最短距離は0.499860 m、最近傍距離の最大は0.353515 m。地盤の外挿やNoData充填は適用していない。

## 建物格子と高さ

A3の派生フットプリント正規化と4326変換を再利用し、元3Dを変更しない。変換後の修復は0棟。 `ouem_id` の字句順に1～40の数値IDを付与し、精密モード `overlapping_footprint=True` で単棟・全棟を格子化した。全棟では仮高さ1 mから開始し、実所有セルの生DEM平均 `G_eff_abs` を使う `height = max(Z_abs) - G_eff_abs` へ更新して再格子化した。 `min_height=0`。T4-Aの0.5 m中心平均は別列に保持した。

全40棟が計2,998セルを所有し、棟別4～189セル。ゼロ所有、フィルタ除外、ID再割当、単棟候補外への所有は0件。2回目の全棟格子でID変更は0セル。 `G_eff_abs` は24.434731～25.258567 m、相対高さは2.020000～9.033854 m。 `G_eff_abs` とT4-A平均の差は−0.016000～+0.008192 m。

正面積のフットプリント同士の重複は0組。一方、単棟で両方が取得できるセルが1つあり、全棟でも2セグメントが記録された。配列 [48,83]、中心 (−22491.500463, −39876.500087) でID 28と35が競合し、所有者は35。保存する高さ格子はエンジンの出力で、競合セルの高さと所有IDの意味は分けて扱う。T4-B2では単一所有格子とセグメントを区別し、屋根Z再構成時にこの競合を検証する。

## 成果物と判定

Git管理外の `data/work/terrain-candidate-b/t4b1-04/` に保存した。再実行 `t4b1-05` はJSON・全6配列が同一バイト。

| ファイル | SHA-256 |
|---|---|
| `report.json` | `f8e0e72ac4aa2b39b090a4b1f0e54fe5b6b796b1a079661c044eb9d9dedc013f` |
| `grids/dem.npy` | `1c1df09b21ff1c1622e9f831c942c03c33123b1e7a8b52b6986d83ad42a61a62` |
| `grids/building_ids.npy` | `39befce3b0692a58a51f3ba9416f673f561d1243e267b476fc0172b29b61d481` |
| `grids/building_height.npy` | `59ba0e3c2727d8b87813d7b3117971c49310c190fc96539a7b204c2aed2b5852` |
| `grids/isolated_claim_count.npy` | `f776b29f87a15fe25984e0b1dfcc579accd64a5382af2eef89acd34d4c5ca3dd` |
| `grids/centres_xy.npy` | `5c922053b741fa430a041358af70b3b3258e445bb6c0610fbff92267b51b68f6` |
| `grids/t3_row_col.npy` | `887ef5d86671485afb68a0003b52377d7b8cc804cdc50253dc30e69ceca059f3` |

`t4b2_candidate=true` は同じ入力・AOI・40棟に限定した技術候補。T4-B2の実行は別レビューを要する。鉛直datum実現・epoch・測量整合は未確認で、AOI越境23棟、競合セル、ボクセル上の屋根・地盤再構成が残る。T3を正式Standard Terrainへ昇格せず、既存A3の正式入力ゲートは維持した。

関連pytestは27件通過、6件警告。追加6件でAOI外・有効中心凸包外・NoDataの拒否、最近傍値の照合、競合とゼロ所有の保持を検証した。A2再現Terrain、PR #134のNative・Standard・VoxCity報告・Voxelの記録済みハッシュと照合した。旧A3受入記録の歴史的な固定パスの2ファイルはローカルに無く、同記録に比較用ハッシュもないため直接照合は未実施。

全体pytestは1,241件通過、10件skip（専用GIS/QGIS Python 5件、Windows symlink権限5件）、345件警告（800.52秒）。ログは `data/work/terrain-candidate-b/full-t4b1.log`。A2の取得済み原TIFFも記録済みSHA-256と一致した。
