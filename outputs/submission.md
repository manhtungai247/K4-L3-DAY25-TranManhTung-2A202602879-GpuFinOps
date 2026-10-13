# NimbusAI GPU FinOps — bài viết nộp bài

## Kết quả trước và sau

Trên bộ dữ liệu tổng hợp cố định của lab, baseline là **$27,133/tháng**; cấu hình optimized còn **$14,626/tháng**, tiết kiệm **$12,507 (46.1%)**. Tổng hợp dùng 30 ngày: inference baseline cộng purchasing on-demand; optimized trừ bốn khoản trong waterfall. Riêng inference xử lý 225,990,810 token/tháng: đơn giá giảm từ **$6.488 xuống $1.126/1M-token** (82.6%).

| Đòn bẩy | Tiết kiệm/tháng |
|---|---:|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

Đòn bẩy lớn nhất trong mô hình là **Purchasing (spot/reserved)** ($10,040/tháng); purchasing có tác động lớn vì tối ưu hóa được nhiều GPU-hours trong workload. Inference vẫn đạt mức giảm đơn giá cao nhờ cascade, cache và batch. Right-sizing và dừng idle xử lý lãng phí capacity. Waterfall làm tròn USD, còn số liệu M2 giữ độ chính xác đến cent.

## GPU-Util lie và phần mở rộng

- gpu-h100-4 (H100) có GPU-Util 98.2% nhưng MFU 0.194. GPU bận có thể chờ dữ liệu, memory hoặc kernel; hóa đơn vẫn tính đủ giờ trong khi FLOPs hữu ích thấp. Cần profile nguyên nhân trước khi giảm tier.
- gpu-a10g-1 (A10G) có GPU-Util 96.9% nhưng MFU 0.268. GPU bận có thể chờ dữ liệu, memory hoặc kernel; hóa đơn vẫn tính đủ giờ trong khi FLOPs hữu ích thấp. Cần profile nguyên nhân trước khi giảm tier.

**Extension 1 — Right-sizing theo MBU:** 2 cơ hội thỏa mức dự phòng 10% HBM và bandwidth. A10G→L4 (gpu-a10g-0), A10G→L4 (gpu-a10g-1); gross $288.00/GPU-month, trong đó $144.00 đã nằm trong util-lie lever, nên incremental là $144.00/GPU-month. Chỉ chọn theo giá/GB là không đủ: cần giữ capacity bộ nhớ và thông lượng cho workload.

**Extension 2 — Ngân sách reasoning:** 201/2,400 request (8.4%) tạo 1,241,156 token; chi phí đã tối ưu $1.40/ngày và điện ước tính 29,787.7 Wh/ngày theo giả định 80×. Tỷ lệ request nhỏ vẫn có thể chiếm phần lớn điện; áp dụng giới hạn theo use case và đo lại chất lượng trước khi đổi route.

## Khuyến nghị cho NimbusAI

1. Bật routing theo độ khó có kiểm soát, theo dõi quality/latency và đơn giá $/1M-token.
2. Bật cache và batch cho traffic phù hợp; kiểm tra cache-hit và yêu cầu độ trễ.
3. Tắt GPU idle, đưa job interruptible sang spot, và chỉ cam kết reserved khi duty cycle vượt điểm hòa vốn. Chuẩn hóa team/project tags trước chargeback; dataset hiện đạt gate.

Điện và phát thải được ước lượng bằng mô hình lab: 0.24 Wh/query, 0.091 gCO₂e/query tại us-east-1; vùng sạch nhất trong bảng là europe-north1. Đây là mô phỏng, không phải hóa đơn production; xác minh price, latency, SLO và hệ số phát thải trước triển khai.
