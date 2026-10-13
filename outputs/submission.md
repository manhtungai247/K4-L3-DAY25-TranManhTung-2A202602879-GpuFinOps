# NimbusAI: kết quả tối ưu chi phí GPU

## Chi phí trước và sau tối ưu

Trong bộ dữ liệu của bài lab, NimbusAI đang tốn khoảng **$27,133 mỗi tháng**. Sau khi áp dụng các phương án tối ưu, chi phí ước tính còn **$14,626**, tức giảm **$12,507 (46.1%)**. Đây là mô hình tính theo 30 ngày, cộng chi phí inference với chi phí GPU on-demand rồi trừ các khoản tiết kiệm trong bảng dưới; con số này giúp so sánh các phương án chứ không phải hóa đơn production.

| Đòn bẩy | Tiết kiệm ước tính mỗi tháng |
|---|---:|
| Inference: cascade, cache và batch | $1,212 |
| Chọn hình thức thuê GPU: spot và reserved | $10,040 |
| Right-sizing các GPU bị util-lie | $655 |
| Tắt GPU chạy idle | $600 |

Khoản tiết kiệm lớn nhất đến từ cách mua GPU: **$10,040/tháng** trong mô hình này. Tuy vậy, với mỗi triệu token, chi phí inference cũng giảm đáng kể: từ **$6.488** xuống **$1.126**, tương đương **82.6%**. Cascade chuyển request phù hợp sang model nhỏ; cache giảm giá phần input đã lưu và batch giảm giá request có thể xử lý theo lô. Ba cách này giúp phục vụ cùng lượng token với chi phí thấp hơn.

## GPU-Util cao chưa chắc làm được nhiều việc

Hai GPU bị đánh dấu là `gpu-h100-4` và `gpu-a10g-1`. H100 báo GPU-Util **98.2%** nhưng MFU chỉ **0.194**; A10G báo **96.9%** nhưng MFU là **0.268**. GPU-Util cho biết thiết bị bận bao nhiêu thời gian, còn MFU phản ánh mức sử dụng năng lực tính toán. Vì vậy, một GPU bận gần như liên tục vẫn có thể tạo ra ít FLOPs hữu ích hơn kỳ vọng, trong khi chi phí thuê vẫn tính đủ giờ. Chờ dữ liệu, nghẽn bộ nhớ hoặc overhead khi khởi chạy kernel đều có thể là nguyên nhân; cần profile workload để xác định trước khi đổi GPU.

## Hai phần mở rộng

**Right-sizing theo MBU.** Mình so sánh GPU inference với lựa chọn rẻ hơn, đồng thời yêu cầu GPU thay thế đủ HBM và bandwidth cho mức sử dụng quan sát được, cộng thêm 10% dự phòng. Có hai cơ hội đổi **A10G sang L4**, tiết kiệm gộp **$288/GPU-tháng**. Trong đó, $144 đã được tính ở khoản right-sizing GPU bị util-lie, nên phần tiết kiệm tăng thêm là **$144/GPU-tháng**. Bài học ở đây là không nên chọn GPU chỉ vì giá mỗi giờ thấp hơn: nếu thiếu bộ nhớ hoặc băng thông, workload có thể không chạy được hoặc hiệu năng giảm.

**Ngân sách reasoning.** Chỉ **201 trên 2,400 request (8.4%)** được gắn cờ reasoning, với tổng cộng **1,241,156 token**. Theo giả định của lab, nhóm request này tốn khoảng **$1.40/ngày** và dùng **29,787.7 Wh/ngày**. Mức điện cao là ước tính từ hệ số reasoning 80×, không phải số đo thực tế. Kết quả gợi ý nên theo dõi riêng loại request này và chỉ bật reasoning khi tác vụ cần suy luận nhiều bước; sau đó cần kiểm tra lại chất lượng để tránh tiết kiệm chi phí nhưng làm câu trả lời kém đi.

## Nếu phụ trách FinOps ở NimbusAI

1. Rà soát lịch chạy và duty cycle để chuyển job phù hợp sang spot, đồng thời chỉ mua reserved khi mức sử dụng đủ cao để vượt điểm hòa vốn.
2. Triển khai cascade, cache và batch theo từng nhóm request; theo dõi đồng thời `$/1M-token`, latency và chất lượng để chắc chắn mức giảm giá không làm hỏng trải nghiệm.
3. Tắt GPU idle, kiểm tra các trường hợp util-lie bằng profiler, rồi right-size sau khi xác nhận yêu cầu bộ nhớ và bandwidth. Tag coverage hiện đạt **92%**, cao hơn ngưỡng 80% của lab, nên có thể chuẩn bị showback/chargeback sau khi rà soát các tag còn thiếu.

Về năng lượng, mô hình lab ước tính một query dùng **0.24 Wh** và phát thải **0.091 gCO₂e** tại `us-east-1`. Trong các vùng có dữ liệu, `europe-north1` có cường độ carbon thấp nhất. Trước khi áp dụng các con số này vào quyết định production, NimbusAI cần cập nhật giá, kiểm tra độ trễ và SLO theo vùng, và thay các hệ số mô phỏng bằng dữ liệu đo thực tế.