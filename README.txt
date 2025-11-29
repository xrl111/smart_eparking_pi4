SMART E-PARKING (Raspberry Pi 4 + Arduino)
=========================================

1. MÔ TẢ
- Raspberry Pi 4 nhận dữ liệu JSON từ Arduino qua Serial, cập nhật trạng thái slot, hiển thị dashboard web và quản lý hệ thống.
- Arduino điều khiển:
  * SRF05 sensor (1 cái cho Slot 1) - đọc trạng thái slot
  * Button DIP - điều khiển barrier (nhấn để mở/đóng)
  * Servo SG90 - barrier control
  * LCD 1602 I2C - hiển thị "Tong slot: X" và "Con trong: Y"
  * 3 LED (Xanh lá, Vàng, Đỏ) - status indicators
- Arduino gửi frame JSON dạng:
  {"slots":[1,0,0], "free_slots":2, "total_slots":3, "barrier":"closed", "button_pressed":false, "led_status":"green"}
- LƯU Ý: 
  * Slot 1: Đọc từ SRF05 sensor (tự động)
  * Slot 2, 3: Có thể set manual từ web dashboard (MANUAL mode)
  * Barrier được điều khiển bằng Button DIP hoặc từ web

2. CẤU TRÚC THƯ MỤC
- config.py: cấu hình pin, timing, logging.
- core/: state manager, controller.
- utils/: logging + serial client (hỗ trợ mô phỏng trên PC).
- hardware/: abstraction cho cảm biến, servo, buzzer, LCD (dùng nếu mở rộng điều khiển trực tiếp từ Pi).
- web/: Flask app, template, static assets.
- main.py: entrypoint khởi động controller + web server.
- tests/: pytest unit tests cơ bản.
- arduino/: code Arduino Uno (smart_parking.ino) để nạp vào board.
- WIRING_V2.txt: hướng dẫn chi tiết nối dây phần cứng (Button DIP, 3 LED, SRF05).
- DEPLOYMENT_GUIDE.md: hướng dẫn triển khai backend lên Raspberry Pi 4.
- SYNC_IMPROVEMENTS.md: hướng dẫn đồng bộ dữ liệu Arduino ↔ Web.
- CHANGELOG_V2.md: thay đổi trong version 2.0.

3. CÀI ĐẶT

3.1. Phần cứng Arduino:
- Nối dây theo hướng dẫn trong WIRING_V2.txt
  * Button DIP → Digital Pin 2
  * SRF05 (Slot 1) → Digital Pin 9, 10
  * Servo SG90 → Digital Pin 5
  * LCD I2C → A4 (SDA), A5 (SCL)
  * 3 LED → Digital Pin 4, 6, 7 (với resistor 220Ω)
- Mở file arduino/smart_parking.ino trong Arduino IDE
- Cài thư viện cần thiết (nếu chưa có):
  - Servo (thường có sẵn)
  - LiquidCrystal_I2C (cài qua Library Manager: Tools → Manage Libraries)
- Chọn board: Arduino Uno
- Chọn port: COMx (Windows) hoặc /dev/ttyACM0 (Linux)
- Upload code vào Arduino
- Mở Serial Monitor (115200 baud) để kiểm tra

3.2. Phần mềm Raspberry Pi 4:
───────────────────────────────────────────────────────────────────────────────

A. CHUẨN BỊ HỆ THỐNG:
- Cài đặt Raspberry Pi OS (Raspbian) trên Pi 4
- Cập nhật hệ thống:
  sudo apt update && sudo apt upgrade -y
- Cài đặt Python 3 và pip:
  sudo apt install python3 python3-pip python3-venv -y
- Cài đặt các thư viện hệ thống cần thiết:
  sudo apt install git build-essential -y

B. COPY CODE LÊN PI:
- Cách 1: Clone từ Git (nếu có repository):
  cd ~
  git clone <repository-url> smart_eparking_pi4
  cd smart_eparking_pi4

- Cách 2: Copy qua SCP từ máy tính:
  scp -r smart_eparking_pi4 pi@<pi-ip>:~/
  ssh pi@<pi-ip>
  cd ~/smart_eparking_pi4

- Cách 3: Copy qua USB hoặc thẻ nhớ

C. TẠO VIRTUAL ENVIRONMENT:
- Tạo venv:
  python3 -m venv .venv

- Kích hoạt venv:
  source .venv/bin/activate
  # (Bạn sẽ thấy (.venv) ở đầu dòng prompt)

D. CÀI ĐẶT DEPENDENCIES:
- Nâng cấp pip:
  pip install --upgrade pip

- Cài đặt dependencies:
  pip install -r requirements.txt

  LƯU Ý: RPi.GPIO sẽ được cài đặt tự động trên Raspberry Pi.
          Nếu gặp lỗi, cài thủ công:
          pip install RPi.GPIO

E. CẤU HÌNH MÔI TRƯỜNG (.env):
- Tạo file .env từ template:
  cp env.sample .env

- Chỉnh sửa file .env:
  nano .env

- Các biến môi trường cần thiết:
  * SERIAL_PORT=/dev/ttyACM0
    (Kiểm tra port: ls /dev/ttyACM* /dev/ttyUSB*)
  
  * SERIAL_SIMULATION=false
    (false = dùng Arduino thật, true = mô phỏng)
  
  * LOG_LEVEL=INFO
    (DEBUG, INFO, WARNING, ERROR)
  
  * FLASK_DEBUG=false
    (false = production, true = development)
  
  * FLASK_HOST=0.0.0.0
    (0.0.0.0 = listen trên tất cả interfaces)
  
  * FLASK_PORT=5000
    (Port cho web server)
  
  * DATABASE_URL=sqlite:///instance/parking.db
    (SQLite database path - sẽ tự động tạo)
  
  * SECRET_KEY=<tạo-key-ngẫu-nhiên>
    (Tạo key: python3 -c "import secrets; print(secrets.token_hex(32))")
    (Hoặc dùng: openssl rand -hex 32)

F. CẤU HÌNH QUYỀN TRUY CẬP SERIAL:
- Thêm user vào group dialout để truy cập serial:
  sudo usermod -a -G dialout $USER
  # Logout và login lại để áp dụng

- Kiểm tra quyền:
  groups | grep dialout
  # Nếu thấy "dialout" → OK

G. KHỞI TẠO DATABASE:
- Database sẽ tự động tạo khi chạy lần đầu
- Hoặc tạo thủ công:
  python3 -c "from database.db import db, create_app; app = create_app(); app.app_context().push(); db.create_all(); from database.db import init_db; init_db()"

4. CHẠY ỨNG DỤNG TRÊN RASPBERRY PI 4
───────────────────────────────────────────────────────────────────────────────

4.1. KIỂM TRA KẾT NỐI ARDUINO:
- Cắm Arduino vào Pi qua USB
- Kiểm tra cổng Serial:
  ls /dev/ttyACM* /dev/ttyUSB*
- Thường sẽ là /dev/ttyACM0 hoặc /dev/ttyUSB0
- Nếu không thấy, kiểm tra:
  * Arduino đã được cắm đúng chưa
  * Driver USB đã cài đặt chưa
  * Thử rút và cắm lại
- Cập nhật SERIAL_PORT trong file .env cho đúng

4.2. KHỞI CHẠY BACKEND:
- Đảm bảo đã kích hoạt virtual environment:
  source .venv/bin/activate
  # (Bạn sẽ thấy (.venv) ở đầu dòng prompt)

- Kiểm tra cấu hình .env:
  cat .env
  # Đảm bảo SERIAL_PORT đúng và SERIAL_SIMULATION=false

- Khởi chạy backend:
  python3 main.py

- Kiểm tra log để đảm bảo không có lỗi:
  # Log sẽ hiển thị:
  # - "SerialJSONClient bắt đầu ở chế độ serial (/dev/ttyACM0)"
  # - "Khởi động ParkingController với 3 slot"
  # - "Running on http://0.0.0.0:5000"

4.3. TRUY CẬP WEB DASHBOARD:
- Tìm IP của Raspberry Pi:
  hostname -I
  # Hoặc: ip addr show | grep "inet "

- Mở trình duyệt trên máy tính/điện thoại:
  http://<pi-ip>:5000
  # Ví dụ: http://192.168.1.100:5000

- Đăng nhập:
  * Admin: username="admin", password="admin123"
  * Hoặc đăng ký tài khoản mới

4.4. CHẠY Ở CHẾ ĐỘ BACKGROUND (OPTIONAL):
- Sử dụng nohup:
  nohup python3 main.py > parking.log 2>&1 &

- Hoặc sử dụng screen:
  screen -S parking
  python3 main.py
  # Nhấn Ctrl+A, D để detach
  # screen -r parking để attach lại

- Hoặc sử dụng systemd service (xem DEPLOYMENT_GUIDE.md)

4.5. DỪNG BACKEND:
- Nếu chạy foreground: Nhấn Ctrl+C
- Nếu chạy background:
  * Tìm process: ps aux | grep "python3 main.py"
  * Kill process: kill <PID>
  * Hoặc: pkill -f "python3 main.py"

4.6. TROUBLESHOOTING:
- Lỗi "Permission denied" khi truy cập serial:
  → Thêm user vào group dialout (xem mục 3.2.F)

- Lỗi "Port not found":
  → Kiểm tra Arduino đã cắm chưa
  → Kiểm tra SERIAL_PORT trong .env
  → Thử: ls -l /dev/ttyACM*

- Lỗi "Module not found":
  → Đảm bảo đã activate venv
  → Cài lại: pip install -r requirements.txt

- Web không truy cập được:
  → Kiểm tra firewall: sudo ufw allow 5000
  → Kiểm tra Pi đang chạy: ps aux | grep python3
  → Kiểm tra log để xem lỗi

- Arduino không kết nối:
  → Kiểm tra cáp USB
  → Thử rút và cắm lại
  → Kiểm tra Arduino có nguồn không (LED sáng)
  → Xem Serial Monitor trong Arduino IDE để debug

5. KIỂM THỬ
- pytest

6. ĐIỀU KHIỂN THỦ CÔNG (MANUAL CONTROL)
- Hệ thống hỗ trợ điều khiển thủ công qua Web Dashboard và API.
- Các tính năng:
  * Điều khiển barrier (mở/đóng) thủ công
  * Đặt trạng thái slot thủ công (Slot 2, 3)
  * Chuyển đổi chế độ AUTO/MANUAL
  * API endpoints: /api/gate, /api/slot/<id>, /api/mode
- Lưu ý: Manual control chỉ hoạt động trong MANUAL mode

7. VERSION MANAGEMENT
- Hệ thống được chia thành 5 version từ MVP đến Production Ready.
- Version hiện tại: 4.0 (Pricing & Payment System)
- Xem chi tiết:
  * VERSION_ROADMAP.md        : Roadmap chi tiết các version
  * VERSION_CURRENT.md         : Thông tin version hiện tại (4.0)
  * DEPLOYMENT_GUIDE.md        : Hướng dẫn triển khai từng version
- Sử dụng version manager:
  * python scripts/version_manager.py list        # Liệt kê versions
  * python scripts/version_manager.py info 2.0   # Xem thông tin version
  * python scripts/version_manager.py current     # Version hiện tại
  * python scripts/version_manager.py generate 1.0 # Tạo requirements.txt cho version

8. ĐỒNG BỘ DỮ LIỆU
- Hệ thống tự động đồng bộ dữ liệu giữa Arduino và Web Dashboard.
- Features:
  * Heartbeat system: Ping Arduino mỗi 2 giây
  * Auto-reconnect: Tự động kết nối lại khi mất kết nối
  * Full sync: Đồng bộ toàn bộ state khi kết nối lại
  * Connection status: Hiển thị trạng thái kết nối trên dashboard
- Xem chi tiết: SYNC_IMPROVEMENTS.md

9. GHI CHÚ
- LCD/Servo trong thư mục hardware là optional. Hệ thống điều khiển các phần này bằng Arduino.
- Logging ghi ra console và file parking.log (có thể chỉnh trong config.py).
- Manual control gửi commands xuống Arduino để điều khiển hardware.
- Buzzer đã được loại bỏ, thay bằng web notifications.
- Xem WIRING_V2.txt để biết cách nối dây với hệ thống mới (Button DIP, 3 LED).

