#ifndef MOTOR_H
#define MOTOR_H

#include <Arduino.h>

// CDS5500 指令定义
#define INST_WRITE  0x03      // 写指令（立即执行）
#define REG_WRITE   0x04      // 异步写
#define ACTION      0x05      // 执行所有异步写的指令


//舵机ID定义
#define SERVO_ID1 0x01
#define SERVO_ID2 0x02       // 谁是1谁是2好像有讲究，将连接电源板的舵机设为2才能同步动？
#define SERVO_ID3 0x04       // 此处必须为4365的顺序
#define SERVO_ID4 0x03
#define SERVO_ID5 0x05
#define SERVO_ID6 0x06

// 寄存器地址定义
#define ANGLE_CLOCKWISE_L 0x06  // 顺时针角度限制低位
#define ANGLE_CLOCKWISE_H 0x07  // 顺时针角度限制高位
#define ANGLE_ANTICLOCKWISE_L 0x08 // 逆时针角度限制低位
#define ANGLE_ANTICLOCKWISE_H 0X09 // 逆时针角度限制高位
#define GOAL_POSITION_L 0x1E  // 目标位置低字节地址
#define GOAL_POSITION_h 0X1F  // 目标位置高字节地址
#define GOAL_SPEED_L 0x20    // 目标速度低字节地址（舵机模式下表示转动到目标位置的速度，最大为1023）
#define GOAL_SPEED_H 0x21    // 目标速度高字节地址

constexpr uint16_t MAX_SPEED = 1023U;


// 其他参数定义
#define Compesate 30         // 补偿因硬件连接引起的左右轮速度不一致

// 函数定义
byte Id2Order(byte id);
word angle2pos(word angle);
byte checkSum(byte buf[], byte length);
void setAction(byte order);
void sendCommand(byte id, byte instruction, byte parameter[], byte paramLength, byte order);
void setMotorSpeed(byte id, word speed) ;
void Forward(word speed);
void Stop();
void TurnLeft(word angle);
void Motor_Start();
void ServoInit(byte id, word clockwise, word anticlockwise);
void setServoPos(byte id, word pos, word speed);
void setServoAngle(byte id, word angle, word speed);
void MotorInit(byte id);
void Forward1(word speed);
void Forward_1(word speed);
void Forward_2(word speed);
void ClockWise(word speed);
void AntiClockWise(word speed);
uint8_t moveornot(uint8_t moving);
void serialEnd();

#endif
