"""
Configuration file for Smart E-Parking System
Raspberry Pi 4
"""

# GPIO Pin Configuration (BCM numbering)
class GPIOPins:
    # Ultrasonic Sensors (HC-SR04)
    SLOT1_TRIG = 8   # Pin 29
    SLOT1_ECHO = 7   # Pin 31
    SLOT2_TRIG = 4   # Pin 7
    SLOT2_ECHO = 17  # Pin 11
    SLOT3_TRIG = 27  # Pin 13
    SLOT3_ECHO = 22  # Pin 15
    GATE_TRIG = 5    # Pin 26
    GATE_ECHO = 6    # Pin 27
    
    # Actuators
    SERVO_PIN = 18   # Pin 12 (PWM)
    BUZZER_PIN = 23  # Pin 16
    LED_PIN = 24     # Pin 18
    
    # I2C (LCD)
    I2C_SDA = 2      # Pin 3
    I2C_SCL = 3      # Pin 5
    LCD_I2C_ADDRESS = 0x27  # Default I2C address (check with i2cdetect)


# Sensor Thresholds (in centimeters)
class SensorThresholds:
    SLOT_OCCUPIED_MAX = 50   # < 50cm = occupied
    SLOT_FREE_MIN = 80       # > 80cm = free
    GATE_DETECTION_MAX = 30  # < 30cm = car present at gate
    SENSOR_TIMEOUT = 0.03    # 30ms timeout for sensor reading


# Servo Configuration
class ServoConfig:
    OPEN_ANGLE = 90      # Barrier open angle (degrees)
    CLOSE_ANGLE = 0      # Barrier close angle (degrees)
    OPEN_DELAY = 0.3     # Delay after opening (seconds)
    CLOSE_DELAY = 0.4    # Delay after closing (seconds)
    PWM_FREQUENCY = 50   # 50Hz for standard servos


# System Timing (in seconds)
class Timing:
    SENSOR_READ_INTERVAL = 0.1   # Read sensors every 100ms
    WEB_UPDATE_INTERVAL = 0.5    # Update web dashboard every 500ms
    LCD_UPDATE_INTERVAL = 1.0    # Update LCD every 1 second
    MAIN_LOOP_SLEEP = 0.05       # Main loop sleep (50ms)


# Buzzer Configuration
class BuzzerConfig:
    BEEP_DURATION = 0.2          # Beep duration (seconds)
    ERROR_BEEP_DURATION = 0.5    # Error beep duration
    BEEP_FREQUENCY = 1000        # Beep frequency (Hz)


# Web Server Configuration
class WebConfig:
    HOST = "0.0.0.0"             # Listen on all interfaces
    PORT = 5000                  # Flask default port
    DEBUG = False                # Debug mode (set True for development)


# Parking Configuration
class ParkingConfig:
    TOTAL_SLOTS = 3              # Total parking slots
    SLOT_NAMES = ["Slot 1", "Slot 2", "Slot 3"]


# Operation Mode Configuration
class OperationMode:
    AUTO = "auto"                # Arduino tự động điều khiển dựa trên cảm biến
    MANUAL = "manual"            # Web/Admin điều khiển thủ công
    DEFAULT_MODE = AUTO          # Chế độ mặc định khi khởi động


# LCD Display Configuration
class LCDConfig:
    ROWS = 2
    COLS = 16
    I2C_ADDRESS = 0x27           # Check with: sudo i2cdetect -y 1


# Logging Configuration
class LogConfig:
    LOG_LEVEL = "INFO"           # DEBUG, INFO, WARNING, ERROR
    LOG_FILE = "parking.log"     # Log file path
    ENABLE_FILE_LOGGING = True
    ENABLE_CONSOLE_LOGGING = True


