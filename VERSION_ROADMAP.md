# SMART E-PARKING - VERSION ROADMAP

## TỔNG QUAN

Dự án được chia thành 5 version chính, từ MVP (Minimum Viable Product) đến hệ thống production-ready với đầy đủ tính năng.

---

## 📦 VERSION 1.0 - MVP (Minimum Viable Product)
**Mục tiêu:** Hệ thống cơ bản hoạt động với hardware và web dashboard đơn giản

### Tính năng:
- ✅ Hardware Integration
  - Arduino Uno R3 + SRF05 sensor
  - Servo motor (barrier control)
  - LCD 1602 I2C (hiển thị trạng thái)
  - Buzzer (cảnh báo)
- ✅ Serial Communication
  - Giao tiếp Pi ↔ Arduino qua Serial
  - JSON data exchange
  - Simulation mode cho development
- ✅ Basic Web Dashboard
  - Hiển thị trạng thái slot (trống/đầy)
  - Hiển thị trạng thái barrier (mở/đóng)
  - Real-time updates (polling)
- ✅ State Management
  - Thread-safe state manager
  - Hardware synchronization

### Files cần thiết:
```
core/
  - state_manager.py
  - controller.py
utils/
  - serial_client.py
  - logger.py
hardware/ (optional, có thể bỏ qua nếu dùng Arduino)
web/
  - app.py
  - main_routes.py
  - templates/base.html
  - templates/index.html (simple dashboard)
  - static/dashboard.js (basic)
arduino/
  - smart_parking.ino
main.py
config.py
requirements.txt (minimal: Flask, pyserial)
```

### Deployment:
- Chạy trên Raspberry Pi 4
- Kết nối Arduino qua USB
- Web dashboard tại `http://<pi-ip>:5000`

### Test Cases:
- Sensor đọc được khoảng cách
- Barrier mở/đóng theo sensor
- Web hiển thị đúng trạng thái
- LCD hiển thị thông tin

---

## 📦 VERSION 2.0 - Authentication & User Management
**Mục tiêu:** Thêm hệ thống xác thực và quản lý người dùng

### Tính năng mới:
- ✅ User Authentication
  - Login/Register
  - Password hashing (Werkzeug)
  - Session management (Flask-Login)
- ✅ Role-based Access
  - Admin role
  - Client role
  - Protected routes
- ✅ User Management (Admin)
  - Danh sách users
  - Kích hoạt/vô hiệu hóa user
  - Xem thông tin user

### Files thêm vào:
```
auth/
  - __init__.py
  - forms.py
  - routes.py
database/
  - db.py
  - models.py (User model)
web/
  - templates/auth/login.html
  - templates/auth/register.html
  - templates/admin/users.html
```

### Dependencies thêm:
- Flask-Login
- Flask-WTF
- WTForms
- Werkzeug
- Flask-SQLAlchemy

### Database:
- SQLite database
- User table với roles

### Test Cases:
- Đăng ký user mới
- Đăng nhập với admin/client
- Phân quyền truy cập dashboard
- Admin quản lý users

---

## 📦 VERSION 3.0 - Parking Sessions & Operation Modes
**Mục tiêu:** Quản lý phiên đỗ xe và chế độ hoạt động

### Tính năng mới:
- ✅ Parking Session Management
  - Tự động tạo session khi xe vào
  - Tự động kết thúc session khi xe ra
  - Lưu lịch sử đỗ xe
  - Tracking thời gian đỗ
- ✅ Operation Modes
  - AUTO mode: Tự động theo sensor
  - MANUAL mode: Điều khiển thủ công qua web
  - Chuyển đổi mode real-time
  - Mode locking mechanism
- ✅ Manual Control (Admin)
  - Điều khiển barrier thủ công
  - Đánh dấu slot trống/đầy
  - Override sensor trong MANUAL mode
- ✅ Session History
  - Xem lịch sử đỗ xe (Admin)
  - Xem lịch sử của mình (Client)
  - Filter theo ngày, slot, user

### Files thêm/sửa:
```
core/
  - mode_manager.py (NEW)
  - parking_service.py (NEW)
database/
  - models.py (ParkingSession, SystemLog)
web/
  - templates/admin/dashboard.html (enhanced)
  - templates/client/dashboard.html (NEW)
  - static/dashboard.js (enhanced với mode switching)
```

### Database Schema:
- `parking_sessions` table
- `system_logs` table

### Test Cases:
- Session tự động tạo khi slot chuyển từ trống → đầy
- Session tự động kết thúc khi slot chuyển từ đầy → trống
- Chuyển đổi AUTO/MANUAL mode
- Manual control trong MANUAL mode
- Sensor không override manual trong MANUAL mode

---

## 📦 VERSION 4.0 - Pricing & Payment System
**Mục tiêu:** Hệ thống tính phí linh hoạt và thanh toán

### Tính năng mới:
- ✅ Flexible Pricing Rules
  - Time-based pricing (theo khung giờ)
  - Per-hour pricing (phí theo giờ)
  - Flat rate (đồng giá)
  - Overnight pricing (qua đêm)
  - Custom pricing (theo user)
  - Priority system (ưu tiên rule)
- ✅ Fee Calculation
  - Tự động tính phí khi kết thúc session
  - Áp dụng pricing rules phù hợp
  - Hiển thị chi tiết tính phí
- ✅ Payment Management
  - Payment status (pending/paid/free)
  - Payment methods (cash/card/online)
  - Payment time tracking
  - Mark as paid (Admin)
- ✅ Pricing Admin Panel
  - Tạo/sửa/xóa pricing rules
  - Preview pricing
  - Enable/disable rules

### Files thêm/sửa:
```
database/
  - models.py (PricingRule)
core/
  - parking_service.py (calculate_fee method)
web/
  - templates/admin/pricing.html (NEW)
  - templates/admin/dashboard.html (payment section)
  - main_routes.py (pricing endpoints)
```

### Database Schema:
- `pricing_rules` table

### Test Cases:
- Tạo pricing rule mới
- Tính phí theo time-based rule
- Tính phí qua đêm
- Custom pricing cho user cụ thể
- Payment workflow (pending → paid)

---

## 📦 VERSION 5.0 - Advanced Features & Production Ready
**Mục tiêu:** Tính năng nâng cao và sẵn sàng production

### Tính năng mới:
- ✅ Reports & Analytics
  - Revenue reports (theo ngày/tuần/tháng)
  - Occupancy statistics
  - User activity reports
  - Export to CSV/PDF
- ✅ Notifications
  - Email notifications (session start/end)
  - SMS notifications (optional)
  - In-app notifications
- ✅ API Documentation
  - RESTful API endpoints
  - API authentication (tokens)
  - Swagger/OpenAPI docs
- ✅ System Monitoring
  - Health check endpoints
  - Performance metrics
  - Error tracking
  - Log rotation
- ✅ Security Enhancements
  - CSRF protection
  - Rate limiting
  - Input validation
  - SQL injection prevention
- ✅ Deployment
  - Systemd service (auto-start)
  - Production WSGI server (Gunicorn)
  - Nginx reverse proxy
  - Database backup scripts
  - Environment configuration

### Files thêm:
```
web/
  - templates/admin/reports.html
  - templates/admin/analytics.html
utils/
  - email_service.py
  - backup_service.py
scripts/
  - deploy.sh
  - backup_db.sh
  - systemd/smart-parking.service
api/
  - __init__.py
  - routes.py
  - auth.py
docs/
  - API.md
  - DEPLOYMENT.md
```

### Dependencies thêm:
- Gunicorn (production server)
- Celery (background tasks, optional)
- ReportLab (PDF generation)
- Pandas (data analysis)

### Test Cases:
- Generate revenue report
- Export data to CSV
- Email notification khi session start
- API authentication
- System health check
- Auto-start on boot

---

## 📊 SO SÁNH CÁC VERSION

| Tính năng | V1.0 | V2.0 | V3.0 | V4.0 | V5.0 |
|-----------|------|------|------|------|------|
| Hardware Integration | ✅ | ✅ | ✅ | ✅ | ✅ |
| Basic Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| Authentication | ❌ | ✅ | ✅ | ✅ | ✅ |
| User Management | ❌ | ✅ | ✅ | ✅ | ✅ |
| Parking Sessions | ❌ | ❌ | ✅ | ✅ | ✅ |
| AUTO/MANUAL Modes | ❌ | ❌ | ✅ | ✅ | ✅ |
| Manual Control | ❌ | ❌ | ✅ | ✅ | ✅ |
| Pricing System | ❌ | ❌ | ❌ | ✅ | ✅ |
| Payment Tracking | ❌ | ❌ | ❌ | ✅ | ✅ |
| Reports & Analytics | ❌ | ❌ | ❌ | ❌ | ✅ |
| Notifications | ❌ | ❌ | ❌ | ❌ | ✅ |
| API Documentation | ❌ | ❌ | ❌ | ❌ | ✅ |
| Production Deployment | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 🚀 KẾ HOẠCH TRIỂN KHAI

### Phase 1: MVP (V1.0)
**Thời gian:** 1-2 tuần
- Setup hardware
- Basic web dashboard
- Serial communication
- Testing cơ bản

### Phase 2: Authentication (V2.0)
**Thời gian:** 1 tuần
- Database setup
- User authentication
- Role-based access
- User management

### Phase 3: Sessions & Modes (V3.0)
**Thời gian:** 1-2 tuần
- Session management
- AUTO/MANUAL modes
- Manual control
- History tracking

### Phase 4: Pricing (V4.0)
**Thời gian:** 1-2 tuần
- Pricing rules system
- Fee calculation
- Payment management
- Admin pricing panel

### Phase 5: Production (V5.0)
**Thời gian:** 2-3 tuần
- Reports & analytics
- Notifications
- API documentation
- Production deployment
- Security hardening

**Tổng thời gian ước tính:** 6-10 tuần

---

## 📝 GHI CHÚ

1. **Version hiện tại:** Dự án đã có đầy đủ tính năng từ V1.0 đến V4.0
2. **V5.0:** Cần phát triển thêm các tính năng nâng cao
3. **Backward Compatibility:** Mỗi version mới tương thích ngược với version trước
4. **Testing:** Mỗi version cần có test suite riêng
5. **Documentation:** Cập nhật README và docs cho mỗi version

---

## 🔄 MIGRATION GUIDE

### Từ V1.0 → V2.0:
- Cài thêm dependencies: `Flask-Login`, `Flask-WTF`, `Werkzeug`
- Chạy database migration để tạo User table
- Update routes để thêm authentication

### Từ V2.0 → V3.0:
- Thêm ParkingSession và SystemLog models
- Implement mode_manager và parking_service
- Update dashboard với mode controls

### Từ V3.0 → V4.0:
- Thêm PricingRule model
- Implement fee calculation logic
- Thêm pricing admin panel

### Từ V4.0 → V5.0:
- Setup production server (Gunicorn)
- Configure Nginx
- Implement reports và notifications
- API documentation

---

## 📌 TAGS & BRANCHES

Đề xuất Git workflow:
- `v1.0` - MVP release
- `v2.0` - Authentication release
- `v3.0` - Sessions & Modes release
- `v4.0` - Pricing & Payment release
- `v5.0` - Production release
- `main` - Latest stable version
- `develop` - Development branch

