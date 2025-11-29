# CẢI THIỆN ĐỒNG BỘ DỮ LIỆU ARDUINO ↔ WEB

## 🎯 TỔNG QUAN

Đã cải thiện hệ thống đồng bộ dữ liệu giữa Arduino và Web Dashboard để đảm bảo:

- ✅ Đồng bộ 2 chiều ổn định
- ✅ Xử lý mất kết nối
- ✅ Tự động đồng bộ lại khi kết nối lại
- ✅ Hiển thị trạng thái kết nối real-time
- ✅ Retry mechanism cho commands

---

## ✨ TÍNH NĂNG MỚI

### 1. Heartbeat System

- ✅ Ping Arduino định kỳ (mỗi 2 giây) để kiểm tra kết nối
- ✅ Tự động đồng bộ lại LCD mỗi 5 giây để đảm bảo không mất đồng bộ
- ✅ Track thời gian nhận dữ liệu cuối cùng

### 2. Full Sync khi Kết nối lại

- ✅ Khi Arduino kết nối lại, tự động đồng bộ toàn bộ state:
  - Mode (AUTO/MANUAL)
  - LCD display
  - Slots (nếu ở MANUAL mode)
  - Barrier status (nếu ở MANUAL mode)

### 3. Connection Status Tracking

- ✅ Track trạng thái kết nối Arduino (`is_connected`)
- ✅ Track thời gian nhận dữ liệu cuối cùng
- ✅ Hiển thị trên web dashboard

### 4. Retry Mechanism

- ✅ Commands gửi xuống Arduino có retry (mặc định 2 lần)
- ✅ Exponential backoff cho web polling khi có lỗi
- ✅ Tự động retry khi mất kết nối

### 5. Optimized LCD Updates

- ✅ Chỉ update LCD khi có thay đổi (tránh spam)
- ✅ Track nội dung LCD cuối cùng để so sánh

---

## 🔧 THAY ĐỔI KỸ THUẬT

### Backend (Python)

#### `core/controller.py`:

- ✅ Thêm `_full_sync_to_arduino()`: Đồng bộ toàn bộ state khi kết nối lại
- ✅ Thêm `_heartbeat_loop()`: Thread riêng để ping và đồng bộ định kỳ
- ✅ Cải thiện `_sync_hardware()`: Chỉ update LCD khi có thay đổi
- ✅ Track `_last_lcd_update` để tránh update không cần thiết

#### `utils/serial_client.py`:

- ✅ Thêm `_is_connected` flag để track kết nối
- ✅ Thêm `_last_received` để track thời gian nhận dữ liệu
- ✅ Cải thiện `send_command()`: Thêm retry mechanism (mặc định 2 lần)
- ✅ Thêm `flush()` để đảm bảo data được gửi ngay
- ✅ Thêm `is_connected()` method
- ✅ Thêm `get_last_received_time()` method

#### `web/main_routes.py`:

- ✅ Update `/api/status` để trả về thông tin kết nối Arduino:
  - `arduino_connected`: Boolean
  - `arduino_last_update`: ISO timestamp
  - `arduino_update_age`: Số giây từ lần cập nhật cuối

### Frontend (JavaScript)

#### `web/static/dashboard.js`:

- ✅ Sửa route từ `/status` → `/api/status`
- ✅ Thêm error counting và exponential backoff
- ✅ Hiển thị trạng thái kết nối Arduino
- ✅ Cảnh báo khi Arduino không cập nhật > 10 giây
- ✅ Reset error count khi kết nối lại thành công

#### `web/templates/admin/dashboard.html`:

- ✅ Thêm `arduino-status` element để hiển thị trạng thái Arduino

---

## 📊 DATA FLOW

### Arduino → Backend:

```
Arduino gửi JSON mỗi 500ms
    ↓
Serial Client nhận và parse JSON
    ↓
Update _last_received timestamp
    ↓
Emit payload đến listeners
    ↓
Controller._handle_payload()
    ↓
Update State Manager
    ↓
Sync hardware (LCD, etc.)
```

### Backend → Arduino:

```
Controller/Web gửi command
    ↓
Serial Client.send_command() với retry
    ↓
Gửi command xuống Arduino
    ↓
Flush để đảm bảo gửi ngay
    ↓
Retry nếu thất bại (tối đa 2 lần)
```

### Heartbeat Loop:

```
Mỗi 2 giây:
    ↓
Ping Arduino (PING command)
    ↓
Update _last_arduino_ping
    ↓
Mỗi 5 giây:
    ↓
Sync LCD để đảm bảo đồng bộ
```

### Full Sync (khi kết nối lại):

```
Arduino kết nối lại
    ↓
Controller._full_sync_to_arduino()
    ↓
Sync Mode
    ↓
Sync LCD
    ↓
Sync Slots (nếu MANUAL)
    ↓
Sync Barrier (nếu MANUAL)
```

---

## 🔍 MONITORING

### Web Dashboard hiển thị:

- **Arduino Status**:
  - 🟢 "Arduino: Kết nối (X giây trước)" - Khi connected
  - 🔴 "Arduino: Mất kết nối" - Khi disconnected
- **Warning**: Cảnh báo nếu không cập nhật > 10 giây

### Logs:

- `INFO`: Kết nối thành công, đồng bộ state
- `WARNING`: Mất kết nối, retry commands
- `ERROR`: Lỗi sau nhiều lần retry

---

## ⚙️ CONFIGURATION

### Có thể điều chỉnh:

```python
# core/controller.py
self._sync_interval = 2.0  # Heartbeat interval (seconds)

# utils/serial_client.py
retry = 2  # Số lần retry cho commands
reconnect_interval = 5.0  # Thời gian chờ trước khi reconnect
```

### Web Dashboard:

```javascript
const MAX_FETCH_ERRORS = 3; // Số lỗi tối đa trước khi backoff
// Exponential backoff: 5s, 10s, 20s, 30s (max)
```

---

## 🧪 TESTING

### Test Cases:

1. **Normal Operation**:

   - ✅ Arduino gửi data → Web hiển thị đúng
   - ✅ Web gửi command → Arduino nhận và thực thi
   - ✅ LCD update khi có thay đổi

2. **Connection Loss**:

   - ✅ Rút USB Arduino → Web hiển thị "Mất kết nối"
   - ✅ Cắm lại → Tự động đồng bộ lại toàn bộ state
   - ✅ Commands được retry khi mất kết nối

3. **Sync Recovery**:

   - ✅ Kết nối lại → Full sync mode, LCD, slots, barrier
   - ✅ LCD được update với giá trị đúng

4. **Error Handling**:
   - ✅ Web polling lỗi → Exponential backoff
   - ✅ Command lỗi → Retry 2 lần
   - ✅ Connection timeout → Reconnect sau 5 giây

---

## 📝 LƯU Ý

1. **LCD Update**: Chỉ update khi có thay đổi để tránh spam Serial
2. **Heartbeat**: Chạy trong thread riêng, không block main thread
3. **Retry**: Commands quan trọng (MODE, BARRIER) được retry tự động
4. **Connection Status**: Hiển thị real-time trên dashboard
5. **Backoff**: Web polling tự động giảm tần suất khi có lỗi

---

## 🚀 NEXT STEPS

- [ ] Thêm WebSocket để real-time updates (optional)
- [ ] Thêm metrics/statistics cho connection quality
- [ ] Thêm auto-recovery cho các lỗi cụ thể
- [ ] Thêm notification khi mất kết nối lâu

---

## ✅ KẾT LUẬN

Hệ thống đồng bộ đã được cải thiện đáng kể:

- ✅ Đồng bộ 2 chiều ổn định
- ✅ Xử lý mất kết nối tốt hơn
- ✅ Tự động recovery
- ✅ Monitoring và logging đầy đủ
- ✅ User experience tốt hơn với status indicators
