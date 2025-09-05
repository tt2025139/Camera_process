# bluetooth_communicator.py

import serial
import time
from config import FRAME_HEIGHT, FRAME_WIDTH, LIGHT_CENTER, CENTER_TOLERANCE, SERVO_X_MIN, SERVO_X_MAX, SERVO_Y_MIN, SERVO_Y_MAX

def run_center_control(shared_state, lock):
    """
    在一个独立线程中运行，负责根据坐标控制云台及激光发射。
    """
    print("[中控线程] 线程已启动。")
    last_moving = (0,0)
    last_firing = False

    while shared_state.get('running', True):
        with lock:
            center_coordinates = shared_state.get('center_coordinates')
            moving = shared_state.get('moving')
            firing = shared_state.get('firing')

        if center_coordinates[0] is not None and center_coordinates[1] is not None:
            if center_coordinates[0] >= LIGHT_CENTER[0] + CENTER_TOLERANCE:
                moving = (moving[0] + 1, moving[1])
            if center_coordinates[0] <= LIGHT_CENTER[0] - CENTER_TOLERANCE:
                moving = (moving[0] - 1, moving[1])
            if center_coordinates[1] >= LIGHT_CENTER[1] + CENTER_TOLERANCE:
                moving = (moving[0], moving[1] + 1)
            if center_coordinates[1] <= LIGHT_CENTER[1] - CENTER_TOLERANCE:
                moving = (moving[0], moving[1] - 1)
            if (abs(center_coordinates[0] - LIGHT_CENTER[0]) <= CENTER_TOLERANCE and
                abs(center_coordinates[1] - LIGHT_CENTER[1]) <= CENTER_TOLERANCE):
                firing = True
            else:
                firing = False            
        else:
            moving = (moving[0] + 1, moving[1] + 1)
            firing = False

        if moving[0] < SERVO_X_MIN:
            moving = (SERVO_X_MIN, moving[1])
        if moving[0] > SERVO_X_MAX:
            moving = (SERVO_X_MAX, moving[1])
        if moving[1] < SERVO_Y_MIN:
            moving = (moving[0], SERVO_Y_MIN)
        if moving[1] > SERVO_Y_MAX:
            moving = (moving[0], SERVO_Y_MAX)

        time.sleep(0.1)

    print("[中控线程] 正在关闭...")