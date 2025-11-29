/*
 * Smart E-Parking System - Arduino Uno R3
 * Chỉ dùng 1 cảm biến SRF05 cho Slot 1
 * Điều khiển servo barrier, LCD, buzzer
 * Gửi dữ liệu JSON qua Serial cho Raspberry Pi
 * 
 * LƯU Ý VỀ BUZZER:
 * - Buzzer ACTIVE: có mạch dao động bên trong, kêu ngay khi nối HIGH
 *   → Dùng: digitalWrite(BUZZER_PIN, HIGH/LOW)
 * - Buzzer PASSIVE: cần tần số để kêu, linh hoạt hơn
 *   → Dùng: tone(BUZZER_PIN, frequency) / noTone(BUZZER_PIN)
 * 
 * Nếu buzzer kêu liên tục khi chưa có xe:
 * 1. Kiểm tra cảm biến đọc đúng chưa (xem Serial Monitor)
 * 2. Điều chỉnh SLOT_OCCUPIED_MAX nếu cần
 * 3. Kiểm tra wiring buzzer (có thể cần đảo cực)
 */

#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ============================================
// PIN CONFIGURATION (Arduino Uno)
// ============================================
// Cảm biến SRF05 (chỉ 1 cái cho Slot 1)
#define SLOT1_TRIG 9
#define SLOT1_ECHO 10

// Actuators
#define SERVO_PIN 5
#define BUZZER_PIN 3
#define LED_PIN 4

// LCD I2C (SDA=A4, SCL=A5 - mặc định của Arduino)
#define LCD_ADDRESS 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

// ============================================
// THRESHOLDS (cm)
// ============================================
#define SLOT_OCCUPIED_MAX 50   // < 50cm = có xe
#define SLOT_FREE_MIN 80       // > 80cm = trống
#define SENSOR_TIMEOUT 30000   // 30ms timeout (microseconds)

// ============================================
// SERVO CONFIG
// ============================================
#define SERVO_OPEN_ANGLE 90
#define SERVO_CLOSE_ANGLE 0
#define SERVO_OPEN_DELAY 300   // ms
#define SERVO_CLOSE_DELAY 400  // ms

// ============================================
// GLOBAL OBJECTS
// ============================================
Servo barrierServo;
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// State
int slot1Status = 0;  // 0=free, 1=occupied
int freeSlots = 1;    // Chỉ có 1 slot
bool barrierOpen = false;
unsigned long lastLCDUpdate = 0;
unsigned long lastSerialUpdate = 0;

// Operation Mode (từ Raspberry Pi)
bool autoControlEnabled = true;  // Mặc định AUTO mode
String serialBuffer = "";        // Buffer để nhận command từ Pi

// Filter để tránh đọc sai
int lastDistance = 999;
int stableCount = 0;
const int STABLE_THRESHOLD = 3;  // Cần đọc ổn định 3 lần mới thay đổi trạng thái
bool systemReady = false;  // Đảm bảo hệ thống đã khởi động xong
unsigned long startupTime = 0;

// ============================================
// SETUP
// ============================================
void setup() {
  Serial.begin(115200);
  
  // QUAN TRỌNG: Tắt buzzer và LED ngay từ đầu
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);  // Đảm bảo buzzer TẮT
  digitalWrite(LED_PIN, LOW);     // Đảm bảo LED TẮT
  
  // Cấu hình pin cảm biến Slot 1
  pinMode(SLOT1_TRIG, OUTPUT);
  pinMode(SLOT1_ECHO, INPUT);
  digitalWrite(SLOT1_TRIG, LOW);  // Đảm bảo TRIG ở LOW
  
  // Khởi tạo Servo
  barrierServo.attach(SERVO_PIN);
  barrierServo.write(SERVO_CLOSE_ANGLE);
  barrierOpen = false;
  
  // Đảm bảo state ban đầu là đúng (slot trống)
  slot1Status = 0;
  freeSlots = 1;
  stableCount = 0;
  
  // Khởi tạo LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Smart Parking");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  
  // Đợi cảm biến ổn định (quan trọng!)
  delay(500);
  
  // Test buzzer ngắn (1 tiếng beep)
  digitalWrite(BUZZER_PIN, HIGH);
  delay(50);  // Beep ngắn hơn
  digitalWrite(BUZZER_PIN, LOW);
  
  // Đợi thêm để cảm biến hoàn toàn ổn định
  delay(500);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Slot 1: FREE");
  lcd.setCursor(0, 1);
  lcd.print("Ready!");
  
  startupTime = millis();
  systemReady = true;  // Hệ thống đã sẵn sàng
  
  Serial.println("Arduino Smart Parking System Ready (1 Slot)");
  Serial.println("Buzzer should be OFF now. If it's still beeping, check wiring!");
  Serial.println("Waiting 2 seconds for sensor stabilization...");
}

// ============================================
// MAIN LOOP
// ============================================
void loop() {
  // Đọc command từ Serial (Pi gửi xuống)
  readSerialCommands();
  
  // CHỈ đọc cảm biến sau khi hệ thống đã khởi động xong (đợi 2 giây)
  if (systemReady && (millis() - startupTime) > 2000) {
    // Đọc cảm biến Slot 1
    readSlot1Sensor();
    
    // CHỈ điều khiển barrier khi ở AUTO mode
    // Trong MANUAL mode, Pi sẽ điều khiển barrier
    if (autoControlEnabled) {
      controlBarrier();
    }
  } else {
    // Trong thời gian khởi động, đảm bảo buzzer TẮT
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);
    // Giữ state ban đầu (trống)
    slot1Status = 0;
    freeSlots = 1;
  }
  
  // Cập nhật LCD (mỗi 1 giây)
  if (millis() - lastLCDUpdate >= 1000) {
    updateLCD();
    lastLCDUpdate = millis();
  }
  
  // Gửi JSON qua Serial (mỗi 500ms)
  if (millis() - lastSerialUpdate >= 500) {
    sendJSON();
    lastSerialUpdate = millis();
  }
  
  // Kiểm tra buzzer khi full (CHỈ khi thực sự đầy)
  // Đảm bảo buzzer TẮT nếu slot còn trống
  if (freeSlots == 0 && slot1Status == 1) {
    // CHỈ kêu khi slot thực sự đầy (đã xác nhận)
    // Buzzer: nếu dùng buzzer ACTIVE (có mạch dao động bên trong)
    // thì dùng digitalWrite. Nếu dùng PASSIVE thì dùng tone().
    
    // Cho buzzer ACTIVE (thường kêu ngay khi HIGH):
    digitalWrite(BUZZER_PIN, HIGH);
    
    // Cho buzzer PASSIVE (cần tần số):
    // tone(BUZZER_PIN, 1000);  // 1000Hz - Uncomment nếu dùng passive
    
    digitalWrite(LED_PIN, HIGH);
  } else {
    // Tắt buzzer NGAY LẬP TỨC nếu slot trống
    digitalWrite(BUZZER_PIN, LOW);
    // noTone(BUZZER_PIN);  // Uncomment nếu dùng buzzer passive
    
    digitalWrite(LED_PIN, LOW);
  }
  
  delay(50);  // Main loop delay
}

// ============================================
// ĐỌC CẢM BIẾN SLOT 1 (có filter để tránh đọc sai)
// ============================================
void readSlot1Sensor() {
  int dist = readUltrasonic(SLOT1_TRIG, SLOT1_ECHO);
  
  // Debug: in khoảng cách ra Serial (mỗi 500ms)
  static unsigned long lastDebug = 0;
  if (millis() - lastDebug >= 500) {
    Serial.print("Distance: ");
    Serial.print(dist);
    Serial.println(" cm");
    lastDebug = millis();
  }
  
  // Filter: chỉ thay đổi trạng thái khi đọc ổn định
  bool currentOccupied = (dist < SLOT_OCCUPIED_MAX);
  bool lastOccupied = (slot1Status == 1);
  
  if (currentOccupied == lastOccupied) {
    stableCount = 0;  // Đọc ổn định, reset counter
  } else {
    stableCount++;
    if (stableCount >= STABLE_THRESHOLD) {
      // Đã đọc ổn định, cập nhật trạng thái
      slot1Status = currentOccupied ? 1 : 0;
      stableCount = 0;
    }
  }
  
  // Tính số chỗ trống (chỉ có 1 slot)
  freeSlots = (slot1Status == 0) ? 1 : 0;
}

// ============================================
// ĐỌC KHOẢNG CÁCH TỪ SRF05
// ============================================
int readUltrasonic(int trigPin, int echoPin) {
  // Phát xung 10µs
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Đọc thời gian echo
  long duration = pulseIn(echoPin, HIGH, SENSOR_TIMEOUT);
  
  // Tính khoảng cách (cm)
  // Vận tốc âm thanh = 343 m/s = 0.0343 cm/µs
  // Khoảng cách = (duration / 2) * 0.0343
  int distance = (duration * 0.0343) / 2;
  
  // Nếu timeout hoặc quá xa, trả về giá trị lớn
  if (distance <= 0 || distance > 400) {
    return 999;
  }
  
  return distance;
}

// ============================================
// ĐIỀU KHIỂN BARRIER
// ============================================
void controlBarrier() {
  // Logic đơn giản: Mở barrier khi có chỗ trống, đóng khi đầy
  if (freeSlots > 0 && !barrierOpen) {
    // Có chỗ trống -> mở barrier
    barrierServo.write(SERVO_OPEN_ANGLE);
    barrierOpen = true;
    delay(SERVO_OPEN_DELAY);
  }
  else if (freeSlots == 0 && barrierOpen) {
    // Hết chỗ -> đóng barrier
    barrierServo.write(SERVO_CLOSE_ANGLE);
    barrierOpen = false;
    delay(SERVO_CLOSE_DELAY);
  }
}

// ============================================
// CẬP NHẬT LCD
// ============================================
void updateLCD() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Slot 1: ");
  lcd.print(slot1Status == 0 ? "FREE" : "OCCUPIED");
  
  lcd.setCursor(0, 1);
  if (freeSlots == 0) {
    lcd.print("FULL! Gate: CLOSED");
  } else {
    lcd.print("Gate: ");
    lcd.print(barrierOpen ? "OPEN" : "CLOSED");
    lcd.print(" ");
    lcd.print(autoControlEnabled ? "[A]" : "[M]");  // [A]uto hoặc [M]anual
  }
}

// ============================================
// ĐỌC COMMAND TỪ SERIAL (từ Raspberry Pi)
// ============================================
void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      // Xử lý command đã nhận đủ
      if (serialBuffer.length() > 0) {
        processCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
      // Giới hạn buffer để tránh overflow
      if (serialBuffer.length() > 50) {
        serialBuffer = "";
      }
    }
  }
}

// ============================================
// XỬ LÝ COMMAND TỪ PI
// ============================================
void processCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  
  // Command: MODE:AUTO hoặc MODE:MANUAL
  if (cmd.startsWith("MODE:")) {
    String mode = cmd.substring(5);
    mode.trim();
    
    if (mode == "AUTO") {
      autoControlEnabled = true;
      Serial.println("OK:MODE=AUTO");
    } else if (mode == "MANUAL") {
      autoControlEnabled = false;
      Serial.println("OK:MODE=MANUAL");
    } else {
      Serial.print("ERROR:Invalid mode:");
      Serial.println(mode);
    }
  }
  // Command: GATE:OPEN hoặc GATE:CLOSED (từ Pi trong MANUAL mode)
  else if (cmd.startsWith("GATE:")) {
    String state = cmd.substring(5);
    state.trim();
    
    if (state == "OPEN") {
      barrierServo.write(SERVO_OPEN_ANGLE);
      barrierOpen = true;
      Serial.println("OK:GATE=OPEN");
    } else if (state == "CLOSED") {
      barrierServo.write(SERVO_CLOSE_ANGLE);
      barrierOpen = false;
      Serial.println("OK:GATE=CLOSED");
    } else {
      Serial.print("ERROR:Invalid gate state:");
      Serial.println(state);
    }
  }
  // Command: PING (kiểm tra kết nối)
  else if (cmd == "PING") {
    Serial.println("OK:PONG");
  }
}

// ============================================
// GỬI JSON QUA SERIAL
// ============================================
void sendJSON() {
  // Gửi format tương thích với backend (1 slot trong array)
  Serial.print("{\"slots\":[");
  Serial.print(slot1Status);
  Serial.print(",0,0");  // Slot 2 và 3 luôn trống (không có cảm biến)
  Serial.print("],\"gate\":\"");
  Serial.print(barrierOpen ? "open" : "closed");
  Serial.print("\",\"free\":");
  Serial.print(freeSlots);
  Serial.print(",\"mode\":\"");
  Serial.print(autoControlEnabled ? "auto" : "manual");
  Serial.println("\"}");
}
