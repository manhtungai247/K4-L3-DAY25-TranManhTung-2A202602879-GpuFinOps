"""Measured student extensions for right-sizing and reasoning governance."""
from __future__ import annotations

from collections import defaultdict

from finops.pricing import request_cost
from finops.sustainability import wh_per_query
from missions._common import num

MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}


def right_sizing(telemetry: list[dict], catalog: dict) -> list[dict]:
    """Suggest cheaper GPUs only when observed memory and bandwidth fit with 10% headroom.

    Memory-dominant means measured MBU exceeds MFU. Candidates must preserve
    HBM capacity and peak bandwidth; this avoids picking a cheap but undersized GPU.
    Savings are per GPU-month at 24x30 on-demand hours.
    """
    grouped = defaultdict(list)
    for row in telemetry:
        grouped[row["gpu_id"]].append(row)

    suggestions = []
    for gpu_id, rows in grouped.items():
        if rows[0].get("workload") != "infer":
            continue
        source_type = rows[0]["gpu_type"]
        source = catalog[source_type]
        max_mem = max(num(row.get("mem_used_gb")) for row in rows)
        max_bw = max(num(row.get("achieved_bw_tbs")) for row in rows)
        mean_mfu = sum(num(row.get("achieved_tflops")) / max(num(source["peak_tflops_fp16"]), 1e-9) for row in rows) / len(rows)
        mean_mbu = sum(num(row.get("achieved_bw_tbs")) / max(num(source["peak_bw_tbs"]), 1e-9) for row in rows) / len(rows)
        if mean_mbu <= mean_mfu:
            continue

        candidates = []
        for gpu_type, target in catalog.items():
            if gpu_type == source_type:
                continue
            if num(target["hbm_gb"]) < max_mem * 1.10:
                continue
            if num(target["peak_bw_tbs"]) < max_bw * 1.10:
                continue
            if num(target["on_demand_hr"]) < num(source["on_demand_hr"]):
                candidates.append((num(target["on_demand_hr"]), gpu_type, target))
        if not candidates:
            continue
        _, target_type, target = min(candidates)
        delta = num(source["on_demand_hr"]) - num(target["on_demand_hr"])
        suggestions.append({
            "gpu_id": gpu_id,
            "current_gpu": source_type,
            "recommended_gpu": target_type,
            "mean_mfu": mean_mfu,
            "mean_mbu": mean_mbu,
            "current_usd_per_gb": num(source["on_demand_hr"]) / num(source["hbm_gb"]),
            "recommended_usd_per_gb": num(target["on_demand_hr"]) / num(target["hbm_gb"]),
            "monthly_savings_usd": round(delta * 24 * 30, 2),
        })
    return suggestions


def reasoning_budget(rows: list[dict]) -> dict:
    """Measure reasoning traffic cost and energy under the lab's stated model."""
    reasoning = [row for row in rows if int(num(row.get("is_reasoning"))) == 1]
    token_count = sum(int(num(row.get("input_tokens"))) + int(num(row.get("output_tokens"))) for row in reasoning)
    cost = 0.0
    energy = 0.0
    for row in reasoning:
        tier = row.get("route_tier", "large")
        in_price, out_price = MODEL_PRICES[tier]
        cost += request_cost(
            int(num(row.get("input_tokens"))), int(num(row.get("output_tokens"))),
            in_price, out_price,
            cached_in=int(num(row.get("cached_input_tokens"))),
            batch=bool(int(num(row.get("is_batch")))),
        )
        energy += wh_per_query(
            int(num(row.get("input_tokens"))) + int(num(row.get("output_tokens"))),
            is_reasoning=True,
        )
    return {
        "reasoning_requests": len(reasoning),
        "total_requests": len(rows),
        "reasoning_share_pct": 100 * len(reasoning) / len(rows) if rows else 0.0,
        "reasoning_tokens": token_count,
        "reasoning_cost_daily": round(cost, 2),
        "reasoning_wh_daily": round(energy, 2),
    }
