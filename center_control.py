# center_control.py

import serial
import time
from config import FRAME_HEIGHT, FRAME_WIDTH, LIGHT_CENTER, CENTER_TOLERANCE, SERVO_X_MIN, SERVO_X_MAX, SERVO_Y_MIN, SERVO_Y_MAX

def run_center_control(shared_state, lock):
    """
    在一个独立线程中运行，负责根据坐标控制云台及激光发射。
    """
    print("[中控线程] 线程已启动。")

    last_coordinates = (FRAME_WIDTH // 2, FRAME_HEIGHT // 2)

    while shared_state.get('running', True):
        with lock:
            center_coordinates = shared_state.get('center_coordinates')
            moving = shared_state.get('moving')
            firing = shared_state.get('firing')

        if center_coordinates is not None:
            
            error_x = center_coordinates[0] - LIGHT_CENTER[0]
            error_y = center_coordinates[1] - LIGHT_CENTER[1]

            move_x, move_y = moving

            
            if abs(error_x) > CENTER_TOLERANCE:
                move_x += 1 if error_x > 0 else -1
            if abs(error_y) > CENTER_TOLERANCE:
                move_y += 1 if error_y > 0 else -1


            
            if (abs(center_coordinates[0] - LIGHT_CENTER[0]) <= CENTER_TOLERANCE and
                abs(center_coordinates[1] - LIGHT_CENTER[1]) <= CENTER_TOLERANCE):
                firing = True
            else:
                firing = False

        else:
            # 定义巡航方向
            if 'scan_direction_x' not in shared_state:
                shared_state['scan_direction_x'] = 1  # 1 表示向右, -1 表示向左

            move_x, move_y = moving

            # 左右扫描
            if shared_state['scan_direction_x'] == 1:
                if move_x < SERVO_X_MAX:
                    move_x += 1
                else:
                    shared_state['scan_direction_x'] = -1
                    move_y += 5  
            else: 
                if move_x > SERVO_X_MIN:
                    move_x -= 1
                else:

                    shared_state['scan_direction_x'] = 1
                    move_y += 5
                        
            # 如果 Y 轴到达边界，则复位
            if move_y > SERVO_Y_MAX:
                    move_y = SERVO_Y_MIN

            firing = False    

        move_x = clamp(move_x, SERVO_X_MIN, SERVO_X_MAX)
        move_y = clamp(move_y, SERVO_Y_MIN, SERVO_Y_MAX)
        moving = (move_x, move_y)

        last_coordinates = center_coordinates

        with lock:
            shared_state['moving'] = moving
            shared_state['firing'] = firing

        time.sleep(0.1)

    print("[中控线程] 正在关闭...")

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))