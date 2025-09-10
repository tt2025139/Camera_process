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

            moving = shared_state.get('moving',(0,0))
            firing = shared_state.get('firing')
            bottom = shared_state.get('bottom')
            ifturn = 0
            move_x = moving[0]
            move_y = moving[1]

            # --- 底盘前进后退左转右转 ---
            if bottom_move is not None:
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
            if watching_move is not None:
                  # 检查 "上升" 信号
                  if watching_move[0] == 1:
                        move_y += 10
                        shared_state['watching_up'] = 0
                  
                  # 检查 "下降" 信号
                  elif watching_move[1] == 1:
                        move_y -= 10
                        shared_state['watching_down'] = 0
                  
                  # 检查 "左转" 信号
                  elif watching_move[2] == 1:
                        move_x += 30
                        shared_state['watching_left'] = 0
                  
                  # 检查 "右转" 信号
                  elif watching_move[3] == 1:
                        move_x -= 30
                        shared_state['watching_right'] = 0

                  
            # --- 控制是否开火  ---
            if iffiring is not None:

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


        time.sleep(0.02)
        

    print("[遥控线程] 正在关闭...")

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))