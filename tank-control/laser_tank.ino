#include "Motor.h"
#include "sonic.h"
#include "bluetooth.h"

byte count = 0;             // 计数循环，小车左转要持续的循环次数

uint8_t mov = 0;
uint8_t rotate_state = 0;

// 超声波相关参数
unsigned long previousUltrasonicTime = 0;
const long ultrasonicInterval = 10; // 每10ms测一次距
long duration;
int distance_cm;
bool newDistanceAvailable = false; // 新数据标志
// 电机任务变量
unsigned long previousMotorTime = 0;
const long motorInterval = 30; // 每30ms更新一次电机控制（PID周期）

unsigned long previousLaserTime = 0;
const long laserInterval = 10;  // 每隔10ms更新云台及激光状态

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
uint8_t buffer[8];



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
  if (obstacleDetected){
  count = 13;    
}
  if (count != 0 ) {
    
    AntiClockWise(600);
    count--;
  }
  else {
    Forward_1(500);
  }
}


void updateLaserControl() {
   loop_process_bluetooth(bluetooth, bluetoothReadState, i_read_buf, buffer, laserTimer);
   if (millis() < laserTimer) {
    digitalWrite(LASER_PIN, HIGH);
  } else if (millis() > laserTimer) {
    digitalWrite(LASER_PIN, LOW);
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
//  Forward_1(500);
  
  
  loop_process_bluetooth(bluetooth, bluetoothReadState, i_read_buf, buffer, laserTimer);
   if (millis() < laserTimer) {
    digitalWrite(LASER_PIN, HIGH);
  } else if (millis() > laserTimer) {
    digitalWrite(LASER_PIN, LOW);
  }
  mov =  moveornot();
  rotate_state = getRotateState();

  if (mov == 1){
    updateUltrasonic();
    updateMotorControl();
  }
  else if (rotate_state == 1 && mov == 0){
    ClockWise(300); 
  }
  else if (rotate_state == 2 && mov == 0) {
    AntiClockWise(300);   
  }
  else if (rotate_state == 3 && mov == 0) {
    Backward(300);   
  }
  // 下述为遥控情形
  else if (mov == 2) {
    Forward_1(400);   
  }
  else if (mov == 3) {
    Backward(400);   
  }
  else if (mov == 4) {
    AntiClockWise(400);   
  }
  else if (mov == 5) {
    ClockWise(400);  
  }
  else {
  Stop();    
  }




  
/*
  if (mov == 1){
  // updateUltrasonic();
  // updateMotorControl();
  Forward_1(300);
  }
  else{
    Stop();
  }
  */
  
  /*
  if (mov == 1){
  // 任务1: 定时执行超声波测距（非阻塞）
  unsigned long currentMillis = millis();
  if (currentMillis - previousUltrasonicTime >= ultrasonicInterval) {
    previousUltrasonicTime = currentMillis;
    updateUltrasonic();
  }
  
  // 任务2: 定时更新电机控制（非阻塞）
  if (currentMillis - previousMotorTime >= motorInterval) {
    previousMotorTime = currentMillis;
    updateMotorControl();
  }
} 

 else {
    Stop();
}
*/
}
