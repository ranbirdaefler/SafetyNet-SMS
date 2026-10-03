# Errata (labels only; no number changes, tables not regenerated)

Found when reading `results/TABLES.md` after the single tabulation. The tables are left exactly as generated.

1. In the exploratory "deployed v1" and "v2 FP32" tables, the italic header line reads "Ours = FP32 ONNX on the Pi 5 (8 GB)". That header belongs to the pre-registered row. For these tables "ours" is the row named in the table title (deployed v1: vocab trim + 8-bit weights; v2: FP32 of the second training run).
2. In the MASSIVE table, the row "v1 (not shipped) v2_fp32" is the v2 FP32 model (second training run, not shipped), not a v1 model. The relabel step marked every encoder row from the first MASSIVE run as v1. Rows: E2 43/1000; v1 FP32 9/1000; v1 deployed 8/1000; v2 FP32 49/1000; deployed board model v2 59/1000.
