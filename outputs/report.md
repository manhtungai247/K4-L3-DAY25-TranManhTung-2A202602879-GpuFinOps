# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Cheapest+cleanest region: europe-north1

_Figures are June-2026 as-of snapshots; re-baseline before acting._

## Inference unit economics

- Baseline: **$6.488/1M-token** ($1,466.10/month over 225,990,810 tokens).
- Optimized: **$1.126/1M-token** ($254.40/month over the same tokens; 82.6% lower).
- Cascade selects the small model for eligible traffic; cached input is billed at 10% and batch traffic at 50%.

## Measured extensions

| GPU | Current → recommended | MFU | MBU | $/GB-hour | Monthly saving/GPU |
|---|---|---:|---:|---:|---:|
| gpu-a10g-0 | A10G → L4 | 0.218 | 0.235 | $0.0417 → $0.0333 | $144.00 |
| gpu-a10g-1 | A10G → L4 | 0.268 | 0.302 | $0.0417 → $0.0333 | $144.00 |

Eligible inference right-sizing opportunities total **$288.00/GPU-month gross**. $144.00 overlaps the util-lie lever; incremental extension opportunity is **$144.00/GPU-month**. Candidates preserve observed peak memory and bandwidth with 10% headroom.

Reasoning traffic: **201/2,400 requests (8.4%)**, 1,241,156 tokens, $1.40/day and 29,787.7 Wh/day under the lab's 80× energy multiplier. Track this budget separately and route only tasks that need multi-step reasoning.

## GPU efficiency finding and actions

- **gpu-h100-4 (H100)**: utilization 98.2% with MFU 0.194; busy time does not mean useful FLOPs. Check memory stalls, kernel launch gaps, and input pipeline before resizing.
- **gpu-a10g-1 (A10G)**: utilization 96.9% with MFU 0.268; busy time does not mean useful FLOPs. Check memory stalls, kernel launch gaps, and input pipeline before resizing.
- The largest modeled lever is **Purchasing (spot/reserved)** ($10,040/month). Validate right-sizing against latency and quality SLOs; route eligible jobs to spot and stop idle instances.
