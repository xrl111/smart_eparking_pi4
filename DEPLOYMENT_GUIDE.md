# HƯỚNG DẪN TRIỂN KHAI THEO VERSION

## 📋 TỔNG QUAN

Tài liệu này hướng dẫn cách triển khai từng version của hệ thống Smart E-Parking, từ MVP đến Production.

---

## 🚀 VERSION 1.0 - MVP DEPLOYMENT

### Yêu cầu:
- Raspberry Pi 4
- Arduino Uno R3
- SRF05 sensor
- Servo motor
- LCD 1602 I2C
- Buzzer

### Bước 1: Setup Hardware
1. Nối dây theo `WIRING.txt`
2. Nạp code Arduino: `arduino/smart_parking.ino`
3. Kiểm tra Serial port: `ls /dev/ttyACM*`

### Bước 2: Setup Software
```bash
# Clone/copy code lên Pi
cd ~/smart_eparking_pi4

# Tạo venv
python3 -m venv .venv
source .venv/bin/activate

# Cài dependencies tối thiểu
pip install Flask pyserial python-dotenv

# Cấu hình .env
cp env.sample .env
nano .env
```

### Bước 3: Cấu hình .env (V1.0)
```env
SERIAL_PORT=/dev/ttyACM0
SERIAL_SIMULATION=false
LOG_LEVEL=INFO
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### Bước 4: Chạy
```bash
python3 main.py
```

### Bước 5: Test
- Truy cập `http://<pi-ip>:5000`
- Kiểm tra dashboard hiển thị trạng thái
- Test sensor → barrier → web update

---

## 🔐 VERSION 2.0 - AUTHENTICATION DEPLOYMENT

### Thêm vào V1.0:

### Bước 1: Cài thêm dependencies
```bash
pip install Flask-SQLAlchemy Flask-Login Flask-WTF WTForms Werkzeug
```

### Bước 2: Cấu hình database
```env
# Thêm vào .env
DATABASE_URL=sqlite:///instance/parking.db
SECRET_KEY=your-secret-key-here
```

### Bước 3: Khởi tạo database
```bash
python3 -c "from database.db import db, create_app; app = create_app(); app.app_context().push(); db.create_all(); from database.db import init_db; init_db()"
```

### Bước 4: Test
- Truy cập `/register` để tạo user mới
- Đăng nhập với admin/admin123
- Kiểm tra phân quyền admin/client

---

## 🎛️ VERSION 3.0 - SESSIONS & MODES DEPLOYMENT

### Thêm vào V2.0:

### Bước 1: Update database schema
```bash
# Database sẽ tự động tạo tables mới khi chạy
# Nếu cần migrate, xóa database cũ:
rm instance/parking.db

# Chạy lại để tạo schema mới:
python3 main.py
```

### Bước 2: Update Arduino code
- Đảm bảo Arduino code hỗ trợ MODE commands:
  - `MODE:AUTO`
  - `MODE:MANUAL`
  - `GATE:OPEN`
  - `GATE:CLOSED`

### Bước 3: Test
- Chuyển đổi AUTO/MANUAL mode
- Test manual control (gate, slot)
- Kiểm tra session tự động tạo/kết thúc

---

## 💰 VERSION 4.0 - PRICING & PAYMENT DEPLOYMENT

### Thêm vào V3.0:

### Bước 1: Database đã có sẵn PricingRule table
- Không cần migration thêm

### Bước 2: Tạo pricing rules mẫu
1. Đăng nhập admin
2. Vào `/admin/pricing`
3. Tạo rules:
   - Giờ cao điểm: 7h-9h, 17h-19h
   - Giờ thường: 9h-17h
   - Qua đêm: 22h-6h
   - Đồng giá: 10,000 VNĐ

### Bước 3: Test
- Tạo session test
- Kết thúc session → kiểm tra fee calculation
- Mark as paid

---

## 🏭 VERSION 5.0 - PRODUCTION DEPLOYMENT

### Bước 1: Cài production server
```bash
pip install gunicorn
```

### Bước 2: Tạo systemd service
```bash
sudo nano /etc/systemd/system/smart-parking.service
```

Nội dung:
```ini
[Unit]
Description=Smart E-Parking System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/smart_eparking_pi4
Environment="PATH=/home/pi/smart_eparking_pi4/.venv/bin"
ExecStart=/home/pi/smart_eparking_pi4/.venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Bước 3: Enable và start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable smart-parking
sudo systemctl start smart-parking
sudo systemctl status smart-parking
```

### Bước 4: Setup Nginx (Optional)
```bash
sudo apt install nginx
sudo nano /etc/nginx/sites-available/smart-parking
```

Nội dung:
```nginx
server {
    listen 80;
    server_name your-pi-ip;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/smart-parking /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Bước 5: Setup Database Backup
```bash
# Tạo backup script
nano ~/backup_parking.sh
```

Nội dung:
```bash
#!/bin/bash
BACKUP_DIR="/home/pi/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp /home/pi/smart_eparking_pi4/instance/parking.db $BACKUP_DIR/parking_$DATE.db
# Giữ lại 7 ngày
find $BACKUP_DIR -name "parking_*.db" -mtime +7 -delete
```

```bash
chmod +x ~/backup_parking.sh

# Thêm vào crontab (chạy mỗi ngày lúc 2h sáng)
crontab -e
# Thêm dòng:
0 2 * * * /home/pi/backup_parking.sh
```

---

## 🔄 ROLLBACK PROCEDURE

### Nếu cần rollback về version trước:

1. **Backup database:**
```bash
cp instance/parking.db instance/parking_backup_$(date +%Y%m%d).db
```

2. **Checkout version cũ:**
```bash
git checkout v3.0  # hoặc version cần rollback
```

3. **Reinstall dependencies:**
```bash
pip install -r requirements.txt
```

4. **Restart service:**
```bash
sudo systemctl restart smart-parking
```

---

## 📊 MONITORING

### Logs:
```bash
# Application logs
tail -f parking.log

# System logs
sudo journalctl -u smart-parking -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
```

### Health Check:
```bash
curl http://localhost:5000/api/health
```

### Database Status:
```bash
sqlite3 instance/parking.db "SELECT COUNT(*) FROM users;"
sqlite3 instance/parking.db "SELECT COUNT(*) FROM parking_sessions;"
```

---

## 🐛 TROUBLESHOOTING

### Service không start:
```bash
sudo systemctl status smart-parking
sudo journalctl -u smart-parking -n 50
```

### Serial port không tìm thấy:
```bash
ls -l /dev/ttyACM*
sudo usermod -a -G dialout pi
# Logout và login lại
```

### Database locked:
```bash
# Kiểm tra process đang dùng database
lsof instance/parking.db
# Kill process nếu cần
```

### Port 5000 đã được dùng:
```bash
sudo lsof -i :5000
# Hoặc đổi port trong .env
```

---

## ✅ CHECKLIST TRIỂN KHAI

### V1.0:
- [ ] Hardware đã nối đúng
- [ ] Arduino code đã nạp
- [ ] Serial port đúng
- [ ] Web dashboard hiển thị
- [ ] Sensor hoạt động

### V2.0:
- [ ] Database đã tạo
- [ ] Admin user đã có
- [ ] Login/Register hoạt động
- [ ] Phân quyền đúng

### V3.0:
- [ ] Session tự động tạo/kết thúc
- [ ] AUTO/MANUAL mode hoạt động
- [ ] Manual control hoạt động
- [ ] History hiển thị

### V4.0:
- [ ] Pricing rules tạo được
- [ ] Fee calculation đúng
- [ ] Payment tracking hoạt động

### V5.0:
- [ ] Gunicorn chạy ổn định
- [ ] Systemd service auto-start
- [ ] Nginx reverse proxy (nếu dùng)
- [ ] Backup script hoạt động
- [ ] Monitoring setup

---

## 📞 SUPPORT

Nếu gặp vấn đề:
1. Kiểm tra logs
2. Xem `TEST_GUIDE.txt`
3. Kiểm tra `README.txt`
4. Review error messages

