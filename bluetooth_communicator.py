# bluetooth_communicator.py

import serial
import time
from config import SERIAL_PORT, BAUD_RATE

def run_bluetooth_communication(shared_state, lock):
    """
    在一个独立线程中运行，负责连接蓝牙串口，并周期性地发送更新后的坐标。
    """
    print("[蓝牙线程] 线程已启动。")
    last_sent_coords = None
    ser = None

    while shared_state.get('running', True):
        try:
            if ser is None or not ser.is_open:
                print(f"[蓝牙线程] 正在尝试连接到串口 {SERIAL_PORT}...")
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                print(f"[蓝牙线程] 串口 {SERIAL_PORT} 连接成功。")
                time.sleep(2)

            with lock:
                current_coords = shared_state.get('center_coordinates')
            
            if current_coords and current_coords != last_sent_coords:
                message = f"{current_coords[0]} {current_coords[1]}".encode('ASCII')
                ser.write(message)
                print(f"[蓝牙线程] 已发送坐标: {message.decode().strip()}")
                last_sent_coords = current_coords
            
            time.sleep(0.1)

        except serial.SerialException:
            # 当串口断开或无法连接时，不会打印完整错误，只是安静地尝试重连
            if ser and ser.is_open:
                ser.close()
            ser = None
            time.sleep(5) # 等待5秒后重试
        except Exception as e:
            print(f"[蓝牙线程] 发生未知错误: {e}")
            time.sleep(5)

    if ser and ser.is_open:
        ser.close()
    print("[蓝牙线程] 正在关闭...")