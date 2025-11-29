# CHANGELOG - VERSION 2.0

## 🎯 TỔNG QUAN

Version 2.0 là bản redesign hoàn toàn hệ thống Smart E-Parking với các thay đổi lớn về hardware và software.

---

## ✨ TÍNH NĂNG MỚI

### 1. Button Control Barrier

- ✅ Thay thế SRF05 ở cổng bằng Button DIP 6x6x10MM
- ✅ Nhấn 1 lần: Mở barrier (auto-close sau 5-10 giây)
- ✅ Nhấn lần 2: Giữ mở barrier
- ✅ Nhấn lần 3: Đóng barrier
- ✅ Debounce để tránh nhấn nhiều lần

### 2. Multi-Slot Support

- ✅ Slot 1: SRF05 sensor (đọc tự động)
- ✅ Slot 2, 3: Manual control từ web (có thể set từ admin dashboard)
- ✅ Hỗ trợ mở rộng khi có thêm sensor

### 3. LCD Display Format Mới

- ✅ Dòng 1: "Tong slot: 3"
- ✅ Dòng 2: "Con trong: 2" (hoặc "Con trong: 0" khi full)
- ✅ Cập nhật real-time từ backend

### 4. LED Status System (3 LED)

- ✅ LED Xanh lá: Hệ thống OK, có slot trống
- ✅ LED Vàng: Barrier đang mở (nhấp nháy) hoặc cảnh báo (còn 1 slot)
- ✅ LED Đỏ: Bãi đầy hoặc lỗi hệ thống (nhấp nháy)

### 5. Web Notifications

- ✅ Thay thế buzzer feedback bằng web notifications (toast)
- ✅ Thông báo khi slot thay đổi
- ✅ Thông báo khi barrier mở/đóng
- ✅ Thông báo khi bãi đầy

### 6. Manual Control từ Web

- ✅ Admin có thể set Slot 2, 3 từ web dashboard
- ✅ Admin có thể điều khiển barrier từ xa
- ✅ Chỉ hoạt động trong MANUAL mode

---

## 🔧 THAY ĐỔI KỸ THUẬT

### Arduino Code

- ✅ Rewrite hoàn toàn `arduino/smart_parking.ino`
- ✅ Button interrupt handling với debounce
- ✅ Multi-slot state management
- ✅ LED status control (3 LED)
- ✅ LCD update với format mới
- ✅ Serial commands: `SLOT:X:Y`, `LCD:UPDATE:...`, `BARRIER:OPEN/CLOSE`

### Backend Python

- ✅ Update `core/state_manager.py`: Thêm `total_slots`, `button_pressed`, `led_status`
- ✅ Update `core/controller.py`: Manual slot control, LCD update, barrier control
- ✅ Update `web/main_routes.py`: API `/api/gate`, `/api/slot/<id>`

### Web Dashboard

- ✅ Update `web/templates/admin/dashboard.html`: Loại bỏ buzzer test button
- ✅ Update `web/static/dashboard.js`: Manual slot control, web notifications
- ✅ Hiển thị slot status với manual control cho Slot 2,3

---

## 📝 FILES MỚI

- `WIRING_V2.txt` - Hướng dẫn nối dây mới
- `LED_FUNCTIONALITY.md` - Chức năng LED chi tiết
- `NEW_SYSTEM_DESIGN.md` - Thiết kế hệ thống mới
- `scripts/clean_project.py` - Script clean dự án
- `CHANGELOG_V2.md` - File này

---

## 🗑️ FILES ĐÃ XÓA

- `LED_3COLOR_DESIGN.md` - Trùng với `LED_FUNCTIONALITY.md`
- `parking.log` - Log file cũ (sẽ tự tạo lại khi chạy)

---

## 📦 DEPENDENCIES

Không thay đổi dependencies. Vẫn sử dụng:

- Flask, Flask-SQLAlchemy, Flask-Login
- pyserial
- python-dotenv
- Werkzeug, WTForms

---

## 🔄 MIGRATION GUIDE

### Từ V1.0 → V2.0:

1. **Hardware Changes:**

   - Thêm Button DIP (nối vào Digital Pin 2)
   - Thêm 3 LED (Xanh lá, Vàng, Đỏ)
   - Di chuyển SRF05 từ cổng sang Slot 1
   - Xem `WIRING_V2.txt` để biết chi tiết

2. **Software Changes:**

   - Nạp code Arduino mới: `arduino/smart_parking.ino`
   - Không cần thay đổi Python dependencies
   - Database schema không thay đổi

3. **Configuration:**
   - `.env` không thay đổi
   - Có thể cấu hình `BARRIER_AUTO_CLOSE_DELAY` trong Arduino code

---

## ⚠️ BREAKING CHANGES

1. **Arduino Code:**

   - Format JSON thay đổi: thêm `free_slots`, `total_slots`, `button_pressed`, `led_status`
   - Commands mới: `SLOT:X:Y`, `LCD:UPDATE:...`, `BARRIER:OPEN/CLOSE`

2. **API Changes:**

   - `/api/gate` thay đổi từ GET query → POST JSON
   - `/api/slot/<id>` mới (thay vì `/api/slot?index=...`)

3. **Hardware:**
   - Buzzer đã được loại bỏ
   - SRF05 không còn ở cổng (chỉ ở Slot 1)

---

## 🐛 BUG FIXES

- ✅ Fix manual slot control không hoạt động trong MANUAL mode
- ✅ Fix LCD update không đồng bộ
- ✅ Fix barrier control từ web

---

## 📚 DOCUMENTATION

- ✅ `WIRING_V2.txt` - Hướng dẫn nối dây chi tiết
- ✅ `LED_FUNCTIONALITY.md` - Chức năng LED
- ✅ `NEW_SYSTEM_DESIGN.md` - Thiết kế hệ thống
- ✅ `README.txt` - Đã cập nhật

---

## 🚀 NEXT STEPS

- [ ] Test toàn bộ hệ thống với hardware mới
- [ ] Thêm statistics & reports cho multi-slot
- [ ] Tối ưu performance
- [ ] Production deployment guide

---

## 📅 RELEASE DATE

**Version 2.0** - 2025-01-XX

---

## 👥 CONTRIBUTORS

- System redesign và implementation
