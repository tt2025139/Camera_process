"""Remote control module"""

import time

from config import (
    SERVO_X_MIN, 
    SERVO_X_MAX ,
    SERVO_Y_MIN ,
    SERVO_Y_MAX 
)

def run_remote_control(shared_state, lock):
    """
    对前端收集到的遥控数据进行处理，传输信息
    """
    print("[遥控线程] 线程已启动。")
    

    while shared_state.get("running", True):
        
        # --- 从共享状态获取数据 ---
        with lock:
            bottom_move = (
                shared_state.get('bottom_forward'),
                shared_state.get('bottom_backward'),
                shared_state.get('bottom_left'),
                shared_state.get('bottom_right'),
            )
            watching_move = (
                 shared_state.get('watching_up'),
                 shared_state.get('watching_down'),
                 shared_state.get('watching_left'),
                 shared_state.get('watching_right'),
            )
            iffiring = (
                shared_state.get('isfiring'),
                shared_state.get('nofiring'),
            )
            move_x, move_y = shared_state.get('moving')
            firing = shared_state.get('firing')
            bottom = shared_state.get('bottom')
            ifturn = 0

        # --- 底盘前进后退左转右转 ---
        if bottom_move == (0, 0, 0, 0):
                bottom = 0
                time.sleep(0.05)

        elif bottom_move == (1, 0, 0, 0):
                bottom = 2
                time.sleep(0.05)

        elif bottom_move == (0, 1, 0, 0):
                bottom = 3
                time.sleep(0.05)

        elif bottom_move == (0, 0, 1, 0):
                bottom = 4
                time.sleep(0.05)

        elif bottom_move == (0, 0, 0, 1):
                bottom = 5
                time.sleep(0.05)
        
        else:
              bottom = 0
              time.sleep(0.05)

        # --- 云台上下左右  ---

        if watching_move == (1, 0, 0, 0):
              move_y += 5
        
        elif watching_move == (0, 1, 0, 0):
              move_y -= 5
        
        elif watching_move == (0, 0, 1, 0):
              move_x -= 5
        
        elif watching_move == (0, 0, 0, 1):
              move_x += 5

            
        # --- 控制是否开火  ---

        if iffiring == (1, 0):
              firing = 1

        if iffiring == (0, 1):
              firing = 0



        move_x = clamp(move_x, SERVO_X_MIN, SERVO_X_MAX)
        move_y = clamp(move_y, SERVO_Y_MIN, SERVO_Y_MAX)

        
        with lock:
            shared_state["moving"] = (move_x, move_y)
            shared_state["firing"] = firing
            shared_state["ifturn"] = ifturn
            shared_state["random_move"] = bottom
        

    print("[遥控线程] 正在关闭...")

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))