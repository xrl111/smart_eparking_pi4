# VERSION HIỆN TẠI - SMART E-PARKING

## 🎯 VERSION: 4.0 (Pricing & Payment System)

**Trạng thái:** ✅ Đã triển khai đầy đủ

---

## ✅ TÍNH NĂNG ĐÃ CÓ

### V1.0 - MVP ✅
- [x] Hardware Integration (Arduino + SRF05 + Servo + LCD + Buzzer)
- [x] Serial Communication (Pi ↔ Arduino)
- [x] Basic Web Dashboard
- [x] State Management
- [x] Real-time Status Updates

### V2.0 - Authentication ✅
- [x] User Authentication (Login/Register)
- [x] Role-based Access (Admin/Client)
- [x] User Management (Admin panel)
- [x] Password Security (Werkzeug hashing)
- [x] Session Management (Flask-Login)

### V3.0 - Sessions & Modes ✅
- [x] Parking Session Management
  - [x] Auto-create session khi xe vào
  - [x] Auto-end session khi xe ra
  - [x] Session history tracking
  - [x] Duration calculation
- [x] Operation Modes
  - [x] AUTO mode (sensor-driven)
  - [x] MANUAL mode (web control)
  - [x] Mode switching real-time
  - [x] Mode locking
- [x] Manual Control
  - [x] Manual gate control
  - [x] Manual slot marking
  - [x] Sensor override trong MANUAL mode
- [x] Session History
  - [x] Admin: Xem tất cả sessions
  - [x] Client: Xem sessions của mình
  - [x] Filter và search

### V4.0 - Pricing & Payment ✅
- [x] Flexible Pricing Rules
  - [x] Time-based pricing (theo khung giờ)
  - [x] Per-hour pricing
  - [x] Flat rate
  - [x] Overnight pricing
  - [x] Custom pricing (theo user)
  - [x] Priority system
- [x] Fee Calculation
  - [x] Auto-calculate khi session end
  - [x] Apply pricing rules
  - [x] Fee display
- [x] Payment Management
  - [x] Payment status (pending/paid/free)
  - [x] Payment methods
  - [x] Payment time tracking
  - [x] Mark as paid (Admin)
- [x] Pricing Admin Panel
  - [x] Create/Edit/Delete rules
  - [x] Enable/Disable rules
  - [x] Preview pricing

---

## 📦 DEPENDENCIES

```txt
Flask>=3.0.0
pyserial>=3.5
RPLCD>=1.3.1
smbus2>=0.4.3
RPi.GPIO>=0.7.1  # Chỉ trên Raspberry Pi
pytest>=7.0.0
python-dotenv>=1.0.1
Flask-SQLAlchemy>=3.1.1
Flask-Login>=0.6.3
Flask-WTF>=1.2.1
WTForms>=3.1.1
Werkzeug>=3.0.1
```

---

## 🗂️ CẤU TRÚC DỰ ÁN

```
smart_eparking_pi4/
├── arduino/
│   └── smart_parking.ino          # Arduino code
├── auth/                          # Authentication
│   ├── __init__.py
│   ├── forms.py
│   └── routes.py
├── core/                          # Core logic
│   ├── controller.py              # Main controller
│   ├── mode_manager.py            # Operation modes
│   ├── parking_service.py         # Session & pricing
│   └── state_manager.py           # State management
├── database/                      # Database
│   ├── db.py                      # DB initialization
│   └── models.py                  # User, Session, PricingRule, Log
├── hardware/                      # Hardware abstraction
│   ├── actuators/
│   ├── display/
│   └── sensors/
├── utils/                         # Utilities
│   ├── logger.py
│   └── serial_client.py
├── web/                           # Web application
│   ├── app.py                     # Flask app factory
│   ├── main_routes.py             # Main routes
│   ├── static/
│   │   ├── dashboard.js
│   │   └── style.css
│   └── templates/
│       ├── admin/
│       │   ├── dashboard.html
│       │   ├── users.html
│       │   ├── logs.html
│       │   └── pricing.html
│       ├── auth/
│       │   ├── login.html
│       │   └── register.html
│       ├── client/
│       │   └── dashboard.html
│       └── base.html
├── main.py                        # Entry point
├── config.py                      # Configuration
├── requirements.txt
├── env.sample
└── README.txt
```

---

## 🗄️ DATABASE SCHEMA

### Tables:
1. **users**
   - id, username, email, password_hash
   - role (admin/client)
   - full_name, phone, is_active
   - created_at, last_login

2. **parking_sessions**
   - id, user_id, slot_id, vehicle_plate
   - entry_time, exit_time, duration_minutes
   - status (active/completed/cancelled)
   - fee_amount, payment_status, payment_time, payment_method
   - notes

3. **pricing_rules**
   - id, name, rule_type, is_active, priority
   - start_hour, end_hour, days_of_week
   - first_hour_fee, subsequent_hour_fee
   - flat_rate_fee, overnight_fee
   - user_id (custom pricing)
   - description, created_at, updated_at

4. **system_logs**
   - id, event_type, message
   - user_id, meta_data (JSON)
   - created_at

---

## 🔑 DEFAULT CREDENTIALS

- **Admin:**
  - Username: `admin`
  - Password: `admin123`

- **Client:**
  - Đăng ký tài khoản mới qua `/register`

---

## 🚀 CÁCH CHẠY

### Development (Windows):
```powershell
# Tạo và activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Cài dependencies (bỏ RPi.GPIO trên Windows)
pip install Flask pyserial RPLCD smbus2 pytest python-dotenv Flask-SQLAlchemy Flask-Login Flask-WTF WTForms Werkzeug

# Chạy
python main.py
```

### Production (Raspberry Pi):
```bash
# Tạo và activate venv
python3 -m venv .venv
source .venv/bin/activate

# Cài dependencies
pip install -r requirements.txt

# Cấu hình .env
cp env.sample .env
# Chỉnh SERIAL_PORT=/dev/ttyACM0
# Chỉnh SERIAL_SIMULATION=false

# Chạy
python3 main.py
```

---

## 📋 API ENDPOINTS

### Public:
- `GET /` - Redirect to dashboard/login
- `GET /login` - Login page
- `POST /login` - Login
- `GET /register` - Register page
- `POST /register` - Register
- `POST /logout` - Logout

### Protected (Login required):
- `GET /dashboard` - Dashboard (admin/client)
- `GET /api/status` - Get parking status
- `GET /api/my-sessions` - Get my sessions (client)
- `GET /api/history` - Get session history

### Admin Only:
- `GET /api/mode` - Get operation mode
- `POST /api/mode` - Change operation mode
- `POST /api/gate` - Control gate (MANUAL mode)
- `POST /api/slot/<id>` - Control slot (MANUAL mode)
- `GET /admin/users` - User management
- `GET /admin/logs` - System logs
- `GET /admin/pricing` - Pricing rules
- `POST /api/pricing` - Create pricing rule
- `PUT /api/pricing/<id>` - Update pricing rule
- `DELETE /api/pricing/<id>` - Delete pricing rule
- `GET /api/session/<id>/fee` - Calculate fee
- `POST /api/session/<id>/pay` - Mark as paid

---

## 🧪 TESTING

Chạy tests:
```bash
pytest
```

Xem test guide: `TEST_GUIDE.txt`

---

## 📝 NEXT STEPS (V5.0)

Các tính năng cần phát triển cho V5.0:
- [ ] Reports & Analytics
- [ ] Email/SMS Notifications
- [ ] RESTful API với authentication tokens
- [ ] API Documentation (Swagger)
- [ ] System Monitoring & Health Checks
- [ ] Production Deployment (Gunicorn + Nginx)
- [ ] Database Backup Scripts
- [ ] Security Enhancements (CSRF, Rate Limiting)
- [ ] Export to CSV/PDF

---

## 📚 TÀI LIỆU

- `README.txt` - Hướng dẫn tổng quan
- `VERSION_ROADMAP.md` - Roadmap các version
- `TEST_GUIDE.txt` - Hướng dẫn test
- `QUICK_START.txt` - Quick start guide
- `SETUP_VENV.txt` - Setup virtual environment

