SMART E-PARKING (Raspberry Pi 4 + Arduino)
=========================================

1. MÔ TẢ
- Raspberry Pi nhận dữ liệu JSON từ Arduino qua Serial, cập nhật trạng thái slot, hiển thị dashboard web và (tuỳ chọn) LCD.
- Arduino đo cảm biến SRF05 (1 cái cho Slot 1), điều khiển barrier, buzzer, LCD cục bộ và gửi frame dạng:
  {"slots":[0,0,0], "gate":"closed", "free":1}  (khi Slot 1 trống)
  {"slots":[1,0,0], "gate":"closed", "free":0}  (khi Slot 1 đầy)
- LƯU Ý: Code hiện tại chỉ dùng 1 cảm biến SRF05 cho Slot 1. Slot 2 và 3 luôn hiển thị trống (0) trong JSON.

2. CẤU TRÚC THƯ MỤC
- config.py: cấu hình pin, timing, logging.
- core/: state manager, controller.
- utils/: logging + serial client (hỗ trợ mô phỏng trên PC).
- hardware/: abstraction cho cảm biến, servo, buzzer, LCD (dùng nếu mở rộng điều khiển trực tiếp từ Pi).
- web/: Flask app, template, static assets.
- main.py: entrypoint khởi động controller + web server.
- tests/: pytest unit tests cơ bản.
- arduino/: code Arduino Uno (smart_parking.ino) để nạp vào board.
- WIRING.txt: hướng dẫn chi tiết nối dây phần cứng.
- DEPLOY_PI.txt: hướng dẫn triển khai backend lên Raspberry Pi 4.
- MANUAL_CONTROL.txt: hướng dẫn điều khiển thủ công qua web và API.
- MISSING_FEATURES.txt: phân tích các phần còn thiếu cho hệ thống thực tế.

3. CÀI ĐẶT

3.1. Phần cứng Arduino:
- Nối dây theo hướng dẫn trong WIRING.txt
- Mở file arduino/smart_parking.ino trong Arduino IDE
- Cài thư viện cần thiết (nếu chưa có):
  - Servo (thường có sẵn)
  - LiquidCrystal_I2C (cài qua Library Manager)
- Chọn board: Arduino Uno
- Chọn port: COMx (Windows) hoặc /dev/ttyACM0 (Linux)
- Upload code vào Arduino

3.2. Phần mềm Raspberry Pi:
- Xem hướng dẫn chi tiết trong DEPLOY_PI.txt để copy code lên Pi
- Sau khi copy code lên Pi:
  - python3 -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
  - cp env.sample .env rồi chỉnh các giá trị:
    * SERIAL_PORT: cổng Arduino (ví dụ /dev/ttyACM0)
    * SERIAL_SIMULATION: false (để dùng Arduino thật)
    * LOG_LEVEL: DEBUG/INFO...
    * FLASK_DEBUG: false (hoặc true nếu muốn debug)

4. CHẠY ỨNG DỤNG

4.1. Kiểm tra kết nối Arduino với Pi:
- Cắm Arduino vào Pi qua USB
- Kiểm tra cổng Serial: `ls /dev/ttyACM* /dev/ttyUSB*`
- Thường sẽ là /dev/ttyACM0 hoặc /dev/ttyUSB0
- Cập nhật SERIAL_PORT trong file .env cho đúng

4.2. Khởi chạy backend:
- Điều chỉnh file .env theo nhu cầu (hoặc export biến thủ công nếu muốn).
- Kích hoạt môi trường ảo:
  - Windows: `.venv\Scripts\activate`
  - Linux/macOS: `source .venv/bin/activate`
- Khởi chạy backend:
  - Windows: `python main.py`
  - Linux/macOS: `python3 main.py`
- Mở trình duyệt tới `http://<pi-ip>:5000` để xem dashboard.
- (Tuỳ chọn) khi phát triển muốn enable log chi tiết:
  - `set LOG_LEVEL=DEBUG` (PowerShell) hoặc `export LOG_LEVEL=DEBUG` (bash) trước khi chạy.

5. KIỂM THỬ
- pytest

6. ĐIỀU KHIỂN THỦ CÔNG (MANUAL CONTROL)
- Hệ thống hỗ trợ điều khiển thủ công qua Web Dashboard và API.
- Xem chi tiết trong MANUAL_CONTROL.txt
- Các tính năng:
  * Điều khiển gate (mở/đóng) thủ công
  * Đặt trạng thái slot thủ công
  * Kích hoạt buzzer test
  * API endpoints: /api/gate, /api/slot, /api/buzzer

7. VERSION MANAGEMENT
- Hệ thống được chia thành 5 version từ MVP đến Production Ready.
- Version hiện tại: 4.0 (Pricing & Payment System)
- Xem chi tiết:
  * VERSION_SUMMARY.txt      : Tóm tắt nhanh các version
  * VERSION_ROADMAP.md        : Roadmap chi tiết
  * VERSION_CURRENT.md        : Thông tin version hiện tại
  * DEPLOYMENT_GUIDE.md       : Hướng dẫn triển khai từng version
- Sử dụng version manager:
  * python scripts/version_manager.py list        # Liệt kê versions
  * python scripts/version_manager.py info 2.0   # Xem thông tin version
  * python scripts/version_manager.py current     # Version hiện tại

8. GHI CHÚ
- LCD/Servo/Buzzer trong thư mục hardware là optional. Hệ thống mẫu hiện điều khiển các phần này bằng Arduino như mô tả trong báo cáo.
- Logging ghi ra console và file parking.log (có thể chỉnh trong config.py).
- Manual control chỉ ảnh hưởng state trên Pi, không điều khiển trực tiếp Arduino.

