#include "Motor.h"
#include <SoftwareSerial.h>

// 将下方舵机角度为0时从对面看，上方舵机旋转方向为逆时针。

constexpr unsigned long SERVO_BAUD = 115200U; // CDS5500 Default

// 定义软串口引脚 (RX, TX)
// 将Arduino的PIN10连接至舵机的数据线(接收数据)
// 将Arduino的PIN11连接至舵机的数据线(发送数据)
SoftwareSerial ServoSerial1(8, 9); // RX, TX
SoftwareSerial ServoSerial2(10, 11); // RX, TX
SoftwareSerial ServoSerial3(12, 13); // RX, TX
SoftwareSerial ServoSerial[] = {ServoSerial1, ServoSerial2, ServoSerial3};
 
// 设置软串口的波特率
void Motor_Start() {
  for (int i = 0; i < 3; ++i) {
    ServoSerial[i].begin(SERVO_BAUD);
  }
}


byte Id2Order(byte id) {
    byte order = 0;
    if (id >= 3) {
    if (id >= 5) order = 2;
    else order = 1;
    }
    return order;
}


// 舵机角度转位置的映射,角度最大为300度
word angle2pos(word angle) {
  word pos = static_cast<double>(angle) / 300.0 * 1023.0;
  return pos; 
}


// 计算校验和
byte checkSum(byte buf[], byte length) {
  byte i;
  word temp = 0;
  for (i = 2; i < length - 1; i++) {
    temp += buf[i];
  }
  temp = ~temp; // 按位取反
  return byte(temp);
}


// 向舵机发送指令包
void sendCommand(byte id, byte instruction, byte parameter[], byte paramLength, byte order) {
  // 构建数据包
  byte packet[6 + paramLength];
  packet[0] = 0xFF; // 帧头
  packet[1] = 0xFF; // 帧头
  packet[2] = id;   // 舵机ID
  packet[3] = paramLength + 2; // 参数长度 + 指令和校验和所占的2字节
  packet[4] = instruction; // 指令

  // 填入参数
  for (byte i = 0; i < paramLength; i++) {
    packet[5 + i] = parameter[i];
  }

  // 计算并填入校验和
  packet[5 + paramLength] = checkSum(packet, sizeof(packet));

  // 通过软串口发送数据包
  ServoSerial[order].listen(); // 确保软串口正在监听
  for (byte i = 0; i < sizeof(packet); i++) {
    ServoSerial[order].write(packet[i]);
  }
  delay(1); // 短暂延迟，保证数据发送完成
}


// 将任一舵机作为电机使用前需先设置成电机模式
void MotorInit(byte id) {
    ServoInit(id, 0, 0);
}



// 设置舵机最大转角,要求顺时针角度限制 <= 目标角度值 <= 逆时针角度限制
void ServoInit(byte id, word clockwise, word anticlockwise) {
   byte clockwise_L = clockwise & 0xFF;        
   byte clockwise_H = (clockwise >> 8) & 0xFF; 
   byte anticlockwise_L = anticlockwise & 0xFF;        
   byte anticlockwise_H = (anticlockwise >> 8) & 0xFF; 
  
   byte parameters1[] = {ANGLE_CLOCKWISE_L, clockwise_L, clockwise_H, anticlockwise_L, anticlockwise_H};
   byte order = Id2Order(id);
   sendCommand(id, INST_WRITE, parameters1, sizeof(parameters1),order);
   
   
}


// 设置舵机目标位置，立刻执行;舵机能执行的灵敏度大约为10
void setServoPos(byte id, word pos, word speed) {
  byte pos_L = pos & 0xFF;        // 获取位置的低字节
  byte pos_H = (pos >> 8) & 0xFF; // 获取位置的高字节

  byte speed_L = speed & 0xFF;        
  byte speed_H = (speed >> 8) & 0xFF; 
  
  byte parameters[] = { GOAL_POSITION_L, pos_L, pos_H, speed_L, speed_H};
  byte order = Id2Order(id);
  sendCommand(id, INST_WRITE, parameters, sizeof(parameters),order);
}


// 设置舵机目标角度，立刻执行
void setServoAngle(byte id, word angle, word speed) {
  word pos = angle2pos(angle);
  setServoPos(id, pos, speed); 
}

// 目标速度设置，异步写指令
void setMotorSpeed(byte id, word speed) {
  byte speed_L = speed & 0xFF;        // 获取位置的低字节
  byte speed_H = ((speed) >> 8) & 0xFF; // 获取位置的高字节
  
  byte parameters[] = { GOAL_SPEED_L,speed_L, speed_H};
  byte order = Id2Order(id);
  sendCommand(id, REG_WRITE, parameters, sizeof(parameters),order);
 }



// 执行异步写指令
void setAction(byte order) {
  byte actionParam[] = {};
  sendCommand(0xFE, ACTION, actionParam, 0, order); // 0xFE 是广播ID
 
 }



 // 该函数控制小车向前，电机转速最好不超过1000.
void Forward(word speed) {                     // 后续可引入PID？
  setMotorSpeed(SERVO_ID3, speed+1024+Compesate);
  setMotorSpeed(SERVO_ID4, speed);
  setMotorSpeed(SERVO_ID5, speed);
  setMotorSpeed(SERVO_ID6, speed+1024+Compesate);
  setAction(1);
  setAction(2);
}

void Forward1(word speed) {
  setMotorSpeed(SERVO_ID3, speed+1024+Compesate);
  setMotorSpeed(SERVO_ID4, speed);
  
  setAction(1);
  setAction(2);
}

/*
void Stop(){
  setMotorSpeed(SERVO_ID1,0);
  setMotorSpeed(SERVO_ID2,0);
  setAction();
}
*/

/*
void TurnLeft(word angle) {                    // 转弯时设计一个较慢的向前速度？
                                            // 需要建立电机转速与转过角度的映射

  setAction();
}
*/
