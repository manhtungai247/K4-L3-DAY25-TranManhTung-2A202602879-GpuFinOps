"""Small runnable checks for the two student extensions (not part of pytest suite)."""
from missions.extensions import right_sizing, reasoning_budget


def test_right_sizing_respects_memory_and_bandwidth():
    catalog = {
        "A10G": {"hbm_gb": 24, "peak_bw_tbs": 0.6, "peak_tflops_fp16": 125, "on_demand_hr": 1.0},
        "L4": {"hbm_gb": 24, "peak_bw_tbs": 0.3, "peak_tflops_fp16": 121, "on_demand_hr": 0.8},
    }
    telemetry = [{"gpu_id": "a10", "gpu_type": "A10G", "workload": "infer", "mem_used_gb": 20, "achieved_bw_tbs": 0.15, "achieved_tflops": 20}]
    result = right_sizing(telemetry, catalog)
    assert result[0]["recommended_gpu"] == "L4"
    assert result[0]["monthly_savings_usd"] == 144


def test_reasoning_budget_separates_reasoning_traffic():
    rows = [
        {"input_tokens": 1000, "output_tokens": 500, "route_tier": "small", "is_reasoning": 1},
        {"input_tokens": 1000, "output_tokens": 500, "route_tier": "small", "is_reasoning": 0},
    ]
    result = reasoning_budget(rows)
    assert result["reasoning_requests"] == 1
    assert result["reasoning_tokens"] == 1500
    assert result["reasoning_wh_daily"] == 36.0


if __name__ == "__main__":
    test_right_sizing_respects_memory_and_bandwidth()
    test_reasoning_budget_separates_reasoning_traffic()
    print("2 extension checks passed")
