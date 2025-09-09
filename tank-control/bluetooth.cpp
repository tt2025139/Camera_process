#include "bluetooth.h"
#include "Motor.h"

#define DEBUG_MSG

uint8_t  moving = 0;
uint8_t moveornot(){
    return moving;
}


/**
 * @brief process the packet, and do some actions
 * @param packet the packet to be processed
 */
void process_packet(Packet* packet, unsigned long& laserTimer) {
#ifdef DEBUG_MSG
  Serial.print("(");
  Serial.print(packet->lower_angle);
  Serial.print(", ");
  Serial.print(packet->upper_angle);
  Serial.print(", ");
  Serial.print(packet->enable_laser);
  Serial.println(")");
#endif
  setServoAngle(SERVO_ID1, packet->upper_angle, MAX_SPEED);
  setServoAngle(SERVO_ID2, packet->lower_angle, MAX_SPEED);
  if (packet->enable_laser != 0) {
    laserTimer = millis() + LASER_LENGTH;
  }
  moving = packet->enable_move;
}

/**
  * @brief set up bluetooth
  * @param bluetooth the bluetooth serial
  * @param bluetoothReadState the state to be initialized
  * @param buffer some memory to store bytes sent by bluetooth, and should have been allocated at least 5 bytes before.
  */
void setup_bluetooth(SoftwareSerial& bluetooth, ReadState& bluetoothReadState, size_t& i_read_buf, uint8_t* buffer, unsigned long& laserTimer) {
  bluetooth.begin(BLUETOOTH_BAUD);
  pinMode(LASER_PIN, OUTPUT);
  bluetoothReadState = ReadState::EMPTY;
  i_read_buf = 0;
}

/**
  * @brief process bluetooth messages, called every loop(). If no message come, the function will do nothing without being blocked.
  * @param bluetooth the bluetooth serial
  * @param bluetoothReadState the state to be tracked. DO NOT modify it outside the function.
  * @param buffer some memory to store bytes sent by bluetooth, and should have been allocated at least 5 bytes before.
  */
void loop_process_bluetooth(SoftwareSerial& bluetooth, ReadState& bluetoothReadState, size_t& i_read_buf, uint8_t* buffer, unsigned long& laserTimer) {
  bluetooth.listen();
  delay(50); // wtf? why we need this?
  while (bluetooth.available() > 0) {
    // ^ FIXME: packet loss when 0xF0 0x00 occurs in packet
    uint8_t ch = bluetooth.read();
    if (bluetoothReadState == ReadState::EMPTY) { // No infomation about the byte flow
                                                  // Need to judge the start of a packet
      if (ch != START_BYTE) { // Not part of starting bytes... Skip!
        continue;
      }
      bluetoothReadState = ReadState::PREPARE_START;
    } else if (bluetoothReadState == ReadState::PREPARE_START) { // Accepted START_BYTE
       if (ch != 0x00) { // Oops, not started!
        bluetoothReadState = ReadState::EMPTY;
        continue;
       }
       i_read_buf = 0;
       bluetoothReadState = ReadState::STARTED;
    } else if (bluetoothReadState == ReadState::STARTED) { // Accepted START_BYTE, 0x00, reading...
      if (ch == START_BYTE) {
        bluetoothReadState = ReadState::ACCIDENTALLY_START_BYTE; // Oops, is it part of packet or another start bytes?
        continue;
      }
      buffer[i_read_buf] = ch; // Just a normal byte, add in buffer...
      ++i_read_buf;
      if (i_read_buf >= PACKET_LEN) { // packet end!
        process_packet(reinterpret_cast<Packet*>(buffer), laserTimer);
        bluetoothReadState = ReadState::EMPTY;
      }
    } else /* if (bluetoothReadState == ReadState::ACCIDENTALLY_START_BYTE) */ {
      if (ch == 0x00) { // Accidentally start bytes: Throw the packet!
        i_read_buf = 0;
        bluetoothReadState = ReadState::STARTED;
        continue;
      }
      // Then, START_BYTE and ch are two normal bytes, but is START_BYTE the last byte of the packet?
      buffer[i_read_buf] = START_BYTE;
      ++i_read_buf;
      if (i_read_buf >= PACKET_LEN) {
        process_packet(reinterpret_cast<Packet*>(buffer), laserTimer);
        bluetoothReadState = ch == START_BYTE ? ReadState::PREPARE_START : ReadState::EMPTY;
        continue;
      }
      if (ch != START_BYTE) {
        buffer[i_read_buf] = ch;
        ++i_read_buf;
        if (i_read_buf >= PACKET_LEN) {
          bluetoothReadState = ReadState::EMPTY;
          process_packet(reinterpret_cast<Packet*>(buffer), laserTimer);
          continue;
        }
        bluetoothReadState = ReadState::STARTED;
      } else {
        // Do nothing...
        // Next state is still ReadState::ACCIDENTALLY_START_BYTE
      }
    }
  }
}
