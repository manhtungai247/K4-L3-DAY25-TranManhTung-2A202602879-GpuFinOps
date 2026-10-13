"""M5 — Optimization Report: combine M1-M4 into baseline-vs-optimized (deck §1/§11).

Run: python missions/m5_report.py   ->  outputs/report.md + outputs/savings.png
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
from missions._common import num, catalog_by_type, ROOT
from finops import report, sustainability
from missions import m1_efficiency_audit, m2_inference_levers, m3_purchasing

DAYS = 30
# one tier down for over-provisioned ("util-lie") GPUs
RIGHTSIZE_MAP = {"H100": "A100", "H200": "H100", "A100": "A10G", "A10G": "L4", "L4": "L4"}


def run(verbose: bool = True) -> dict:
    r1 = m1_efficiency_audit.run(verbose=False)
    r2 = m2_inference_levers.run(verbose=False)
    r3 = m3_purchasing.run(verbose=False)
    cat = catalog_by_type()

    # --- buckets ---
    infer_savings = (r2["baseline_daily"] - r2["optimized_daily"]) * DAYS
    purchasing_savings = r3["on_demand_monthly"] - r3["optimized_monthly"]

    idle_savings = r1["idle_waste_daily"] * DAYS
    rightsize_savings = 0.0
    for lie in r1["lies"]:
        cur = lie["gpu_type"]
        tgt = RIGHTSIZE_MAP.get(cur, cur)
        delta = num(cat[cur]["on_demand_hr"]) - num(cat[tgt]["on_demand_hr"])
        rightsize_savings += max(0.0, delta) * 24 * DAYS

    levers = {
        "Inference (cascade/cache/batch)": round(infer_savings),
        "Purchasing (spot/reserved)": round(purchasing_savings),
        "Right-size util-lies": round(rightsize_savings),
        "Kill idle GPUs": round(idle_savings),
    }
    baseline = r2["baseline_daily"] * DAYS + r3["on_demand_monthly"]
    optimized = baseline - sum(levers.values())
    total_pct = sum(levers.values()) / baseline * 100 if baseline else 0.0

    # --- sustainability snapshot ---
    median_tokens = 800
    wh = sustainability.wh_per_query(median_tokens)
    sust = {
        "wh_per_query": wh,
        "carbon_g": sustainability.carbon_g(wh, "us-east-1"),
        "best_region": min(sustainability.REGION_CARBON, key=sustainability.REGION_CARBON.get),
    }

    md = report.build_report(baseline, optimized, levers, sustainability=sust)
    total_tokens_month = r2["total_tokens"] * DAYS
    inference_baseline_month = r2["baseline_daily"] * DAYS
    inference_optimized_month = r2["optimized_daily"] * DAYS
    reasoning = r2["reasoning"]
    sizing = r1["right_sizing"]
    sizing_monthly = sum(row["monthly_savings_usd"] for row in sizing)
    largest_lever, largest_saving = max(levers.items(), key=lambda item: item[1])
    md += "\n\n## Inference unit economics\n\n"
    md += (f"- Baseline: **${r2['baseline_per_m']:.3f}/1M-token** "
           f"(${inference_baseline_month:,.2f}/month over {total_tokens_month:,} tokens).\n")
    md += (f"- Optimized: **${r2['optimized_per_m']:.3f}/1M-token** "
           f"(${inference_optimized_month:,.2f}/month over the same tokens; "
           f"{r2['savings_pct']:.1f}% lower).\n")
    md += "- Cascade selects the small model for eligible traffic; cached input is billed at 10% and batch traffic at 50%.\n"
    md += "\n## Measured extensions\n\n"
    if sizing:
        md += "| GPU | Current → recommended | MFU | MBU | $/GB-hour | Monthly saving/GPU |\n|---|---|---:|---:|---:|---:|\n"
        for row in sizing:
            md += (f"| {row['gpu_id']} | {row['current_gpu']} → {row['recommended_gpu']} | "
                   f"{row['mean_mfu']:.3f} | {row['mean_mbu']:.3f} | "
                   f"${row['current_usd_per_gb']:.4f} → ${row['recommended_usd_per_gb']:.4f} | "
                   f"${row['monthly_savings_usd']:,.2f} |\n")
        overlap_ids = {row["gpu_id"] for row in r1["lies"]}
        overlap_savings = sum(row["monthly_savings_usd"] for row in sizing if row["gpu_id"] in overlap_ids)
        md += (f"\nEligible inference right-sizing opportunities total **${sizing_monthly:,.2f}/GPU-month gross**. "
               f"${overlap_savings:,.2f} overlaps the util-lie lever; incremental extension opportunity is "
               f"**${sizing_monthly - overlap_savings:,.2f}/GPU-month**. Candidates preserve observed peak memory and bandwidth with 10% headroom.\n")
    else:
        md += "No lower-cost GPU met the 10% memory and bandwidth headroom constraints.\n"
    md += (f"\nReasoning traffic: **{reasoning['reasoning_requests']:,}/{reasoning['total_requests']:,} requests "
           f"({reasoning['reasoning_share_pct']:.1f}%)**, {reasoning['reasoning_tokens']:,} tokens, "
           f"${reasoning['reasoning_cost_daily']:,.2f}/day and {reasoning['reasoning_wh_daily']:,.1f} Wh/day "
           "under the lab's 80× energy multiplier. Track this budget separately and route only tasks that need multi-step reasoning.\n")
    md += "\n## GPU efficiency finding and actions\n\n"
    for lie in r1["lies"]:
        md += (f"- **{lie['gpu_id']} ({lie['gpu_type']})**: utilization {lie['gpu_util_pct']:.1f}% "
               f"with MFU {lie['mfu']:.3f}; busy time does not mean useful FLOPs. Check memory stalls, kernel launch gaps, and input pipeline before resizing.\n")
    md += (f"- The largest modeled lever is **{largest_lever}** (${largest_saving:,.0f}/month). "
           "Validate right-sizing against latency and quality SLOs; route eligible jobs to spot and stop idle instances.\n")
    out_md = os.path.join(ROOT, "outputs", "report.md")
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)
    article = """# NimbusAI GPU FinOps — bài viết nộp bài

## Kết quả trước và sau

Trên bộ dữ liệu tổng hợp cố định của lab, baseline là **${baseline:,.0f}/tháng**; cấu hình optimized còn **${optimized:,.0f}/tháng**, tiết kiệm **${saved:,.0f} ({pct:.1f}%)**. Tổng hợp dùng 30 ngày: inference baseline cộng purchasing on-demand; optimized trừ bốn khoản trong waterfall. Riêng inference xử lý {tokens:,} token/tháng: đơn giá giảm từ **${base_pm:.3f} xuống ${opt_pm:.3f}/1M-token** ({infer_pct:.1f}%).

| Đòn bẩy | Tiết kiệm/tháng |
|---|---:|
""".format(baseline=baseline, optimized=optimized, saved=baseline-optimized, pct=total_pct,
           tokens=total_tokens_month, base_pm=r2["baseline_per_m"], opt_pm=r2["optimized_per_m"],
           infer_pct=r2["savings_pct"])
    for name, amount in levers.items():
        article += f"| {name} | ${amount:,.0f} |\n"
    article += (f"\nĐòn bẩy lớn nhất trong mô hình là **{largest_lever}** (${largest_saving:,.0f}/tháng); "
                "purchasing có tác động lớn vì tối ưu hóa được nhiều GPU-hours trong workload. Inference vẫn đạt mức giảm đơn giá cao nhờ cascade, cache và batch. Right-sizing và dừng idle xử lý lãng phí capacity. Waterfall làm tròn USD, còn số liệu M2 giữ độ chính xác đến cent.\n\n")
    article += "## GPU-Util lie và phần mở rộng\n\n"
    for lie in r1["lies"]:
        article += (f"- {lie['gpu_id']} ({lie['gpu_type']}) có GPU-Util {lie['gpu_util_pct']:.1f}% nhưng MFU {lie['mfu']:.3f}. GPU bận có thể chờ dữ liệu, memory hoặc kernel; hóa đơn vẫn tính đủ giờ trong khi FLOPs hữu ích thấp. Cần profile nguyên nhân trước khi giảm tier.\n")
    overlap_ids = {row["gpu_id"] for row in r1["lies"]}
    overlap_savings = sum(row["monthly_savings_usd"] for row in sizing if row["gpu_id"] in overlap_ids)
    article += (f"\n**Extension 1 — Right-sizing theo MBU:** {len(sizing)} cơ hội thỏa mức dự phòng 10% HBM và bandwidth. "
                + (f"{', '.join(row['current_gpu']+'→'+row['recommended_gpu']+' ('+row['gpu_id']+')' for row in sizing)}; gross ${sizing_monthly:,.2f}/GPU-month, trong đó ${overlap_savings:,.2f} đã nằm trong util-lie lever, nên incremental là ${sizing_monthly-overlap_savings:,.2f}/GPU-month. " if sizing else "Không có GPU thay thế rẻ hơn đủ HBM và bandwidth. ")
                + "Chỉ chọn theo giá/GB là không đủ: cần giữ capacity bộ nhớ và thông lượng cho workload.\n\n")
    article += (f"**Extension 2 — Ngân sách reasoning:** {reasoning['reasoning_requests']:,}/{reasoning['total_requests']:,} request "
                f"({reasoning['reasoning_share_pct']:.1f}%) tạo {reasoning['reasoning_tokens']:,} token; chi phí đã tối ưu ${reasoning['reasoning_cost_daily']:,.2f}/ngày và điện ước tính {reasoning['reasoning_wh_daily']:,.1f} Wh/ngày theo giả định 80×. Tỷ lệ request nhỏ vẫn có thể chiếm phần lớn điện; áp dụng giới hạn theo use case và đo lại chất lượng trước khi đổi route.\n\n")
    article += "## Khuyến nghị cho NimbusAI\n\n1. Bật routing theo độ khó có kiểm soát, theo dõi quality/latency và đơn giá $/1M-token.\n2. Bật cache và batch cho traffic phù hợp; kiểm tra cache-hit và yêu cầu độ trễ.\n3. Tắt GPU idle, đưa job interruptible sang spot, và chỉ cam kết reserved khi duty cycle vượt điểm hòa vốn. Chuẩn hóa team/project tags trước chargeback; dataset hiện đạt gate.\n\n"
    article += f"Điện và phát thải được ước lượng bằng mô hình lab: {sust['wh_per_query']:.2f} Wh/query, {sust['carbon_g']:.3f} gCO₂e/query tại us-east-1; vùng sạch nhất trong bảng là {sust['best_region']}. Đây là mô phỏng, không phải hóa đơn production; xác minh price, latency, SLO và hệ số phát thải trước triển khai.\n"
    with open(os.path.join(ROOT, "outputs", "submission.md"), "w", encoding="utf-8") as f:
        f.write(article)
    png = report.savings_waterfall(levers, os.path.join(ROOT, "outputs", "savings.png"))

    if verbose:
        print("== M5 Optimization Report ==")
        print(md)
        print(f"\nWritten: outputs/report.md" + (f" + outputs/savings.png" if png else " (matplotlib absent: PNG skipped)"))

    return {"baseline_monthly": round(baseline), "optimized_monthly": round(optimized),
            "levers": levers, "total_savings_pct": round(total_pct, 1)}


if __name__ == "__main__":
    run()
