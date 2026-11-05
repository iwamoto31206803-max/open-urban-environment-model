# Candidate B T5-4 実験の総括

**EXPERIMENTAL / terrain_integration_ready=false**。PR #149マージ済みmain `efe8d88` を基点とする。

| 段階 | 実験で確認した内容 |
|---|---|
| T0 | CONDITIONAL PASS。建物のEPSG:6695のH、多摩のT.P.明示、区部点群からDEMへのT.P.継承推定。 [判断記録](../../planning/OUEM_Candidate_B_Terrain_Integration_Decision_Plan_v0.1.md) |
| T1 | 4枚を固定SHAで照合。重複差は最大約0.656 m。WARD_FIRSTの切替辺284本、最大段差0.172 m。 [実測](MIXED_LOD_TERRAIN_CANDIDATE_B_DIAGNOSTICS.md) |
| T2 | 区部有効値を優先し、欠損のみ多摩を採用。標高値を変更せず候補Bで試す方針。 [設計](../../planning/OUEM_Candidate_B_Terrain_Integration_Decision_Plan_v0.1.md) |
| T3 | Experimental Terrainの40,000セル全数で原Float32値とタイル出典を確認。 [実測](MIXED_LOD_TERRAIN_CANDIDATE_B_T3.md) |
| T4-A | 全63棟を地盤と照合。AOI内で指摘なし40棟、越境23棟。 [診断](MIXED_LOD_CANDIDATE_B_T4A.md) |
| T4-B1/B2 | 40棟すべてに所有セルとボクセル。競合1セルは所有IDとセグメントを分けて検証。鉛直基準の候補B限定PASS提案を記録。 [B1](MIXED_LOD_CANDIDATE_B_T4B1.md) · [B2](MIXED_LOD_CANDIDATE_B_T4B2.md) |
| T5-1 | 63棟を収める127 m四方を決定。原DEM4枚で全域被覆。 [領域](MIXED_LOD_CANDIDATE_B_T5_1.md) |
| T5-2/T5-3 | 両Gate PASS。拡張Terrain 254×254、既存T3と重なる40,000セルは値・出典が一致。127×127×12の配列で全63棟（LoD1 31、LoD2 32）の所有・占有を確認。 [実測](MIXED_LOD_CANDIDATE_B_T5_23.md) |

## 責任範囲

Accepted A2/A3の対象は各受入記録が定める。Candidate Bは隔離された実験で、上表のPASSは各診断に限定する。日陰精度と正式Terrain統合Acceptanceは未検証。鉛直基準の実現方法（realization）、epoch、標高精度の留保を維持する。 [既存受入記録](../../acceptance/)

- **Evaluation AOI** はEPSG:6677の `[-22575,-39925,-22475,-39825]`。100 m四方の評価範囲。
- **Processing Domain** は `[-22588,-39938,-22461,-39811]`。元AOIと交差する建物の完全形状を含む処理域。
- **Source Coverage** は4枚のDEMで有効標高を持つセル。処理域全体を覆うことを確認済み。
- **Target Buildings** は元AOIと交差した63棟。元AOI内のセル中心で所有が確認できたのは62棟。残る1棟も処理域内に72所有セルがある。
- **Context Buildings** は対象建物以外の遮蔽物候補。今回の拡張域にも追加していない。

日陰の必要処理域は太陽方向・高度と外部遮蔽物に依存し、T5の形状収容余裕では保証されない。1 m格子の水平・鉛直量子化、代表高さによるMixed-LoD形状の簡略化、地表面日陰精度、樹冠・植生の効果は後続検証事項。 [E0合成検証](MIXED_LOD_CANDIDATE_B_E0_SHADOW.md) · [E1最小設計](../../planning/OUEM_Candidate_B_E1_Minimal_Shadow_Design.md)
