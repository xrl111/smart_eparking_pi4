/*
 * Smart E-Parking System - Arduino Uno R3
 * Version 2.0 - Redesigned System
 * 
 * Hardware:
 * - 1 SRF05 sensor cho Slot 1
 * - Button DIP 6x6x10MM cho barrier control
 * - Servo SG90 cho barrier
 * - LCD 1602 I2C
 * - 3 LED: Xanh lá, Vàng, Đỏ
 * 
 * Features:
 * - Button control barrier (nhấn 1 lần mở, nhấn lần 2 giữ mở)
 * - Auto-close barrier sau 5-10 giây
 * - 3 LED status indicators
 * - LCD hiển thị "Tong slot: X" và "Con trong: Y"
 * - Slot 1: SRF05 sensor, Slot 2,3: Manual từ web
 */

#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ============================================
// PIN CONFIGURATION
// ============================================
// Button DIP
#define BUTTON_PIN 2

// SRF05 Sensor (Slot 1)
#define SLOT1_TRIG 9
#define SLOT1_ECHO 10

// Servo Barrier
#define SERVO_PIN 5

// LED Status (3 LED: Xanh lá, Vàng, Đỏ)
#define LED_GREEN_PIN 4
#define LED_YELLOW_PIN 6
#define LED_RED_PIN 7

// LCD I2C
#define LCD_ADDRESS 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

// ============================================
// CONFIGURATION
// ============================================
#define TOTAL_SLOTS 3
#define SLOT_OCCUPIED_MAX 50   // < 50cm = có xe
#define SLOT_FREE_MIN 80       // > 80cm = trống
#define SENSOR_TIMEOUT 30000   // 30ms timeout

// Servo
#define SERVO_OPEN_ANGLE 90
#define SERVO_CLOSE_ANGLE 0

// Barrier delay (có thể cấu hình từ web)
#define BARRIER_AUTO_CLOSE_DELAY 7000  // 7 giây (mặc định)

// Button debounce
#define BUTTON_DEBOUNCE_DELAY 50  // 50ms

// ============================================
// GLOBAL OBJECTS
// ============================================
Servo barrierServo;
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);

// ============================================
// STATE VARIABLES
// ============================================
// Slot status (0=trống, 1=đầy)
int slots[TOTAL_SLOTS] = {0, 0, 0};  // Slot 1 từ sensor, Slot 2,3 manual
int freeSlots = TOTAL_SLOTS;
int totalSlots = TOTAL_SLOTS;

// Barrier
bool barrierOpen = false;
unsigned long barrierOpenTime = 0;
bool buttonHoldMode = false;  // Giữ mở khi nhấn nút lần 2

// Button
bool buttonState = false;
bool lastButtonState = false;
unsigned long lastButtonDebounce = 0;
int buttonPressCount = 0;  // Đếm số lần nhấn

// Operation Mode
bool autoControlEnabled = true;  // AUTO mode mặc định
String serialBuffer = "";

// Sensor filter
int lastDistance = 999;
int stableCount = 0;
const int STABLE_THRESHOLD = 3;

// Timing
unsigned long lastLCDUpdate = 0;
unsigned long lastSerialUpdate = 0;
unsigned long lastSensorRead = 0;
bool systemReady = false;
unsigned long startupTime = 0;

// System error
bool systemError = false;

// ============================================
// SETUP
// ============================================
void setup() {
  Serial.begin(115200);
  
  // Pin modes
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // Button với pull-up internal
  
  pinMode(SLOT1_TRIG, OUTPUT);
  pinMode(SLOT1_ECHO, INPUT);
  digitalWrite(SLOT1_TRIG, LOW);
  
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_YELLOW_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  
  // Tắt tất cả LED ban đầu
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_YELLOW_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  
  // Servo
  barrierServo.attach(SERVO_PIN);
  barrierServo.write(SERVO_CLOSE_ANGLE);
  barrierOpen = false;
  
  // LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Smart Parking");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");
  
  // Đợi hệ thống ổn định
  delay(1000);
  
  // Khởi tạo state
  slots[0] = 0;  // Slot 1 trống
  slots[1] = 0;  // Slot 2 trống
  slots[2] = 0;  // Slot 3 trống
  freeSlots = TOTAL_SLOTS;
  
  // LCD ready
  lcd.clear();
  updateLCD();
  
  startupTime = millis();
  systemReady = true;
  
  Serial.println("Arduino Smart Parking System Ready v2.0");
  Serial.println("Features: Button control, 3 LED status, Multi-slot support");
}

// ============================================
// MAIN LOOP
// ============================================
void loop() {
  // Đọc command từ Serial
  readSerialCommands();
  
  // Đọc button
  readButton();
  
  // Xử lý button press
  handleButtonPress();
  
  // Đọc sensor Slot 1 (sau khi hệ thống ổn định)
  if (systemReady && (millis() - startupTime) > 2000) {
    if (millis() - lastSensorRead >= 200) {  // Đọc mỗi 200ms
      readSlot1Sensor();
      lastSensorRead = millis();
    }
  }
  
  // Cập nhật số slot trống
  updateFreeSlots();
  
  // Xử lý barrier auto-close
  handleBarrierAutoClose();
  
  // Cập nhật LED status
  updateStatusLEDs();
  
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
  
  delay(10);  // Main loop delay
}

// ============================================
// ĐỌC BUTTON VỚI DEBOUNCE
// ============================================
void readButton() {
  int reading = digitalRead(BUTTON_PIN);
  
  // Debounce
  if (reading != lastButtonState) {
    lastButtonDebounce = millis();
  }
  
  if ((millis() - lastButtonDebounce) > BUTTON_DEBOUNCE_DELAY) {
    if (reading != buttonState) {
      buttonState = reading;
      
      // Button được nhấn (LOW vì dùng pull-up)
      if (buttonState == LOW) {
        buttonPressCount++;
      }
    }
  }
  
  lastButtonState = reading;
}

// ============================================
// XỬ LÝ BUTTON PRESS
// ============================================
void handleButtonPress() {
  if (buttonPressCount > 0) {
    // Nhấn nút lần đầu
    if (buttonPressCount == 1) {
      if (freeSlots > 0) {
        // Có slot trống -> Mở barrier
        openBarrier();
        buttonHoldMode = false;
        barrierOpenTime = millis();
        Serial.println("INFO:Button pressed - Opening barrier");
      } else {
        // Bãi đầy
        Serial.println("WARN:Button pressed but parking is FULL");
        // LED đỏ đã được set trong updateStatusLEDs()
      }
    }
    // Nhấn nút lần 2 (giữ mở)
    else if (buttonPressCount == 2 && barrierOpen) {
      buttonHoldMode = true;
      barrierOpenTime = 0;  // Hủy timer
      Serial.println("INFO:Button pressed again - Holding barrier open");
    }
    // Nhấn nút lần 3 (đóng)
    else if (buttonPressCount >= 3) {
      closeBarrier();
      buttonHoldMode = false;
      buttonPressCount = 0;  // Reset
      Serial.println("INFO:Button pressed 3 times - Closing barrier");
    }
    
    // Reset counter sau khi xử lý
    buttonPressCount = 0;
  }
}

// ============================================
// MỞ BARRIER
// ============================================
void openBarrier() {
  if (!barrierOpen) {
    barrierServo.write(SERVO_OPEN_ANGLE);
    barrierOpen = true;
    barrierOpenTime = millis();
    Serial.println("INFO:Barrier opened");
  }
}

// ============================================
// ĐÓNG BARRIER
// ============================================
void closeBarrier() {
  if (barrierOpen) {
    barrierServo.write(SERVO_CLOSE_ANGLE);
    barrierOpen = false;
    buttonHoldMode = false;
    barrierOpenTime = 0;
    Serial.println("INFO:Barrier closed");
  }
}

// ============================================
// XỬ LÝ AUTO-CLOSE BARRIER
// ============================================
void handleBarrierAutoClose() {
  if (barrierOpen && !buttonHoldMode) {
    if (barrierOpenTime > 0 && (millis() - barrierOpenTime) >= BARRIER_AUTO_CLOSE_DELAY) {
      closeBarrier();
      Serial.println("INFO:Barrier auto-closed after delay");
    }
  }
}

// ============================================
// ĐỌC SENSOR SLOT 1
// ============================================
void readSlot1Sensor() {
  int dist = readUltrasonic(SLOT1_TRIG, SLOT1_ECHO);
  
  // Filter để tránh đọc sai
  bool currentOccupied = (dist < SLOT_OCCUPIED_MAX && dist > 0);
  bool lastOccupied = (slots[0] == 1);
  
  if (currentOccupied == lastOccupied) {
    stableCount = 0;
  } else {
    stableCount++;
    if (stableCount >= STABLE_THRESHOLD) {
      slots[0] = currentOccupied ? 1 : 0;
      stableCount = 0;
      
      Serial.print("INFO:Slot 1 status changed: ");
      Serial.println(slots[0] == 1 ? "OCCUPIED" : "FREE");
    }
  }
}

// ============================================
// ĐỌC KHOẢNG CÁCH TỪ SRF05
// ============================================
int readUltrasonic(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, SENSOR_TIMEOUT);
  int distance = (duration * 0.0343) / 2;
  
  if (distance <= 0 || distance > 400) {
    return 999;
  }
  
  return distance;
}

// ============================================
// CẬP NHẬT SỐ SLOT TRỐNG
// ============================================
void updateFreeSlots() {
  int occupied = 0;
  for (int i = 0; i < TOTAL_SLOTS; i++) {
    if (slots[i] == 1) {
      occupied++;
    }
  }
  freeSlots = TOTAL_SLOTS - occupied;
}

// ============================================
// CẬP NHẬT LED STATUS
// ============================================
void updateStatusLEDs() {
  // Tắt tất cả trước
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_YELLOW_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  
  if (systemError) {
    // Lỗi: Đỏ nhấp nháy
    digitalWrite(LED_RED_PIN, (millis() % 500) < 250 ? HIGH : LOW);
  } else if (freeSlots == 0) {
    // Bãi đầy: Đỏ sáng
    digitalWrite(LED_RED_PIN, HIGH);
  } else if (barrierOpen) {
    // Barrier mở: Vàng nhấp nháy
    digitalWrite(LED_YELLOW_PIN, (millis() % 500) < 250 ? HIGH : LOW);
  } else if (freeSlots == 1) {
    // Cảnh báo: Vàng sáng (còn 1 slot)
    digitalWrite(LED_YELLOW_PIN, HIGH);
  } else {
    // Bình thường: Xanh lá sáng
    digitalWrite(LED_GREEN_PIN, HIGH);
  }
}

// ============================================
// CẬP NHẬT LCD
// ============================================
void updateLCD() {
  lcd.clear();
  
  // Dòng 1: "Tong slot: 3"
  lcd.setCursor(0, 0);
  lcd.print("Tong slot: ");
  lcd.print(totalSlots);
  
  // Dòng 2: "Con trong: X"
  lcd.setCursor(0, 1);
  lcd.print("Con trong: ");
  lcd.print(freeSlots);
}

// ============================================
// ĐỌC COMMAND TỪ SERIAL
// ============================================
void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        processCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
      if (serialBuffer.length() > 100) {
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
  
  // MODE:AUTO hoặc MODE:MANUAL
  if (cmd.startsWith("MODE:")) {
    String mode = cmd.substring(5);
    mode.trim();
    
    if (mode == "AUTO") {
      autoControlEnabled = true;
      Serial.println("OK:MODE=AUTO");
    } else if (mode == "MANUAL") {
      autoControlEnabled = false;
      Serial.println("OK:MODE=MANUAL");
    }
  }
  // BARRIER:OPEN hoặc BARRIER:CLOSE
  else if (cmd.startsWith("BARRIER:")) {
    String state = cmd.substring(8);
    state.trim();
    
    if (state == "OPEN") {
      openBarrier();
      Serial.println("OK:BARRIER=OPEN");
    } else if (state == "CLOSE") {
      closeBarrier();
      Serial.println("OK:BARRIER=CLOSE");
    }
  }
  // SLOT:X:Y (Set slot X = Y, X=1,2,3, Y=0,1)
  else if (cmd.startsWith("SLOT:")) {
    int colonPos = cmd.indexOf(':', 5);
    if (colonPos > 0) {
      int slotId = cmd.substring(5, colonPos).toInt() - 1;  // Slot 1,2,3 -> index 0,1,2
      int status = cmd.substring(colonPos + 1).toInt();
      
      if (slotId >= 0 && slotId < TOTAL_SLOTS && (status == 0 || status == 1)) {
        slots[slotId] = status;
        Serial.print("OK:SLOT");
        Serial.print(slotId + 1);
        Serial.print("=");
        Serial.println(status);
      }
    }
  }
  // LCD:UPDATE:line1|line2
  else if (cmd.startsWith("LCD:UPDATE:")) {
    String content = cmd.substring(11);
    int pipePos = content.indexOf('|');
    
    if (pipePos > 0) {
      String line1 = content.substring(0, pipePos);
      String line2 = content.substring(pipePos + 1);
      
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(line1);
      lcd.setCursor(0, 1);
      lcd.print(line2);
      
      Serial.println("OK:LCD=UPDATED");
    }
  }
  // PING
  else if (cmd == "PING") {
    Serial.println("OK:PONG");
  }
}

// ============================================
// GỬI JSON QUA SERIAL
// ============================================
void sendJSON() {
  Serial.print("{\"slots\":[");
  for (int i = 0; i < TOTAL_SLOTS; i++) {
    Serial.print(slots[i]);
    if (i < TOTAL_SLOTS - 1) Serial.print(",");
  }
  Serial.print("],\"free_slots\":");
  Serial.print(freeSlots);
  Serial.print(",\"total_slots\":");
  Serial.print(totalSlots);
  Serial.print(",\"barrier\":\"");
  Serial.print(barrierOpen ? "open" : "closed");
  Serial.print("\",\"button_pressed\":");
  Serial.print(buttonState == LOW ? "true" : "false");
  Serial.print(",\"led_status\":\"");
  
  // LED status
  if (systemError) {
    Serial.print("error");
  } else if (freeSlots == 0) {
    Serial.print("red");
  } else if (barrierOpen) {
    Serial.print("yellow_blink");
  } else if (freeSlots == 1) {
    Serial.print("yellow");
  } else {
    Serial.print("green");
  }
  
  Serial.print("\",\"mode\":\"");
  Serial.print(autoControlEnabled ? "auto" : "manual");
  Serial.println("\"}");
}
