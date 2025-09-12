#ifndef BLUETOOTH_H
#define BLUETOOTH_H

#include "SoftwareSerial.h"
#include <Arduino.h>

enum class ReadState {
  EMPTY, PREPARE_START, STARTED, ACCIDENTALLY_START_BYTE
};

struct Packet {
  uint16_t lower_angle; // the two angle are little-endian
  uint16_t upper_angle; 
  uint8_t enable_laser; // 0 - Disable Laser; 1 - Enable Laser
  uint8_t enable_move;
  uint8_t rotate_state;
};

constexpr unsigned long BLUETOOTH_BAUD = 9600U;
constexpr unsigned int LASER_PIN = 4U;
constexpr uint8_t START_BYTE = 0xF0U;
constexpr size_t PACKET_LEN = 7U;
constexpr unsigned long LASER_LENGTH = 1000U;

void process_packet(Packet* packet);
void setup_bluetooth(SoftwareSerial& bluetooth, ReadState& bluetoothReadState, size_t& i_read_buf, uint8_t* buffer, unsigned long& laserTimer);
void loop_process_bluetooth(SoftwareSerial& bluetooth, ReadState& bluetoothReadState, size_t& i_read_buf, uint8_t* buffer, unsigned long& laserTimer);
uint8_t moveornot();
uint8_t getRotateState();
#endif
