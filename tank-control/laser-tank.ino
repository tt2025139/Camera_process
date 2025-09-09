#include "Motor.h"
#include "sonic.h"
#include "bluetooth.h"

// 超声波相关参数
unsigned long previousUltrasonicTime = 0;
const long ultrasonicInterval = 100; // 每100ms测一次距
long duration;
int distance_cm;
bool newDistanceAvailable = false; // 新数据标志
// 电机任务变量
unsigned long previousMotorTime = 0;
const long motorInterval = 20; // 每20ms更新一次电机控制（PID周期）
// PID参数
int targetSpeed = 0; // 目标速度 (0-255)
int currentSpeed = 0; // 当前速度
// 状态变量
bool obstacleDetected = false;

unsigned long laserTimer = millis();

constexpr size_t BT_TX = 7;
constexpr size_t BT_RX = 6;

SoftwareSerial bluetooth(BT_RX, BT_TX);
ReadState bluetoothReadState;
size_t i_read_buf;
uint8_t buffer[6];



// 创建NewPing对象
NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE);


 // --- 超声波测距函数 ---
void updateUltrasonic() {
  distance_cm = sonar.ping_cm();

   // 设置障碍物检测标志
  obstacleDetected = (distance_cm < 30); // 30厘米内检测到障碍物
  
  newDistanceAvailable = true;
}
 
// --- 电机控制函数 ---
void updateMotorControl() {
  // 基于超声波读数控制电机
  if (obstacleDetected) {
    Forward(300);
  }
  else {
   Stop();
  }
}


void setup() {
  Serial.begin(115200);
  
  Motor_Start();

  Serial.println("Zyduino CDS5500 Bus Servo Control Start!");
  ServoInit(SERVO_ID1, 0, 300);
  ServoInit(SERVO_ID2, 0, 1023);
  MotorInit(SERVO_ID3);
  MotorInit(SERVO_ID4);
  MotorInit(SERVO_ID5);
  MotorInit(SERVO_ID6);

  setup_bluetooth(bluetooth, bluetoothReadState, i_read_buf, buffer, laserTimer);
}


void loop() {
  loop_process_bluetooth(bluetooth, bluetoothReadState, i_read_buf, buffer, laserTimer);

  if (millis() < laserTimer) {
    digitalWrite(LASER_PIN, HIGH);
  } else if (millis() > laserTimer) {
    digitalWrite(LASER_PIN, LOW);
  }
}
