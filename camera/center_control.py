"""Center Control Module"""

import time
from config import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LIGHT_CENTER,
    CENTER_TOLERANCE,
    SERVO_X_MIN,
    SERVO_X_MAX,
    SERVO_Y_MIN,
    SERVO_Y_MAX,
    AVG_CAPTURE_LATENCY,
    CONTROL_LOOP_DT,
)
import numpy as np
from filterpy.kalman import KalmanFilter



def create_kalman_filter(dt):
    """创建一个配置好的卡尔曼滤波器对象。"""
    kf = KalmanFilter(dim_x=4, dim_z=2)
    kf.F = np.array([[1, 0, dt, 0], [0, 1, 0, dt],
                       [0, 0, 1, 0], [0, 0, 0, 1]])
    kf.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
    kf.R *= 5
    kf.Q[2:,2:] *= 0.1
    kf.P *= 100
    return kf


def run_center_control(shared_state, lock):
    """
    在一个独立线程中运行，使用卡尔曼滤波器，并对巨大的采集延迟进行补偿，
    以平滑和预测目标位置，并据此控制云台及激光发射。
    """
    print("[中控线程] 线程已启动。")
    
    kf = create_kalman_filter(CONTROL_LOOP_DT)
    kf_initialized = False
    last_update_time = time.time()
    hasscanned = False
    random_move = False


    while shared_state.get("running", True):
        current_time = time.time()
        
        # --- 1. 从共享状态获取数据 ---
        with lock:
            detection_data = shared_state.get("detection_data")
            shared_state["detection_data"] = None 
            moving = shared_state.get("moving")

        # --- 2. 预测到当前时刻 ---
        # 无论有无新数据，我们都需要让滤波器的内部时间前进
        time_since_last_update = current_time - last_update_time
        # 为了防止系统暂停过久导致预测跑飞，可以加一个上限
        time_since_last_update = min(time_since_last_update, 0.5) 
        
        if kf_initialized:
            # 动态调整状态转移矩阵F以匹配真实的时间间隔
            kf.F[0, 2] = time_since_last_update
            kf.F[1, 3] = time_since_last_update
            kf.predict()
        
        last_update_time = current_time

        # --- 3. 用新数据更新滤波器 (如果存在) ---
        if detection_data is not None:
            coords, data_arrival_time = detection_data
            measurement = np.array([[coords[0]], [coords[1]]])
            
            if not kf_initialized:
                kf.x[:2] = measurement
                kf_initialized = True
            else:
                # 核心：这里我们不直接更新，因为数据是陈旧的。
                # 但更新步骤本身有助于校正滤波器的状态。
                # 这一步可以看作是用一个过去的数据来校准现在对过去的估计。
                kf.update(measurement)
        
        # --- 4. 决策逻辑 ---
        firing = False
        if kf_initialized:
            # --- A. 追踪模式 ---
            
            # --- 核心延迟补偿 ---
            # 我们需要预测到未来的哪个时间点？
            # 1. 图像的真实拍摄时间约等于 (数据到达时间 - 平均采集延迟)
            # 2. 我们需要预测的时间 = (当前时间 - 真实拍摄时间)
            # 3. 简化后，总预测时长 = (当前时间 - 数据到达时间) + 平均采集延迟
            
            total_prediction_time = AVG_CAPTURE_LATENCY
            if detection_data is not None:
                # 如果有新数据，就加上处理延迟
                processing_latency = current_time - data_arrival_time
                total_prediction_time += processing_latency

            # 创建一个临时的滤波器副本用于预测，不污染主滤波器的状态
            kf_future = kf.copy()
            kf_future.F[0, 2] = total_prediction_time
            kf_future.F[1, 3] = total_prediction_time
            
            predicted_state = kf_future.predict()
            predicted_coords = (predicted_state[0, 0], predicted_state[1, 0])
            
            # (丢失目标的逻辑可以简化或保留，这里先用简化版)
            if detection_data is None and (current_time - shared_state.get('last_detection_time', 0) > 2.0):
                 kf_initialized = False # 丢失超过2秒，放弃追踪
            else:
                if detection_data is not None:
                    shared_state['last_detection_time'] = data_arrival_time
                
                # 使用这个“未来”的坐标进行控制
                error_x = predicted_coords[0] - LIGHT_CENTER[0]
                error_y = predicted_coords[1] - LIGHT_CENTER[1]
                
                move_x, move_y = moving
                if abs(error_x) > CENTER_TOLERANCE:
                    move_x += -2 if error_x > 0 else +2
                if abs(error_y) > CENTER_TOLERANCE:
                    move_y += -2 if error_y > 0 else +2

                if abs(error_x) <= CENTER_TOLERANCE and abs(error_y) <= CENTER_TOLERANCE:
                    firing = True
                else:
                    firing = False

                ifturn = 0 

                if move_y < SERVO_Y_MIN:
                        move_y = SERVO_Y_MIN
                        ifturn = 0
                        random_move = True
                        hasscanned = True

                if move_y > SERVO_Y_MAX:
                        move_y = SERVO_Y_MAX
                        ifturn = 0
                        random_move = True
                        hasscanned = True


                if move_x > SERVO_X_MAX - 20:
                        move_x = SERVO_X_MAX - 20
                        ifturn = 2
                        random_move = False

                if move_x < SERVO_X_MIN + 20:
                        move_x = SERVO_X_MIN + 20
                        ifturn = 1
                        random_move = False

        
        if not kf_initialized:
            if hasscanned == True:
                # 已扫描过，则开始巡航
                time.sleep(3)  # 停顿3秒
                random_move = False
                ifturn = 0
                hasscanned = False
            else:
                # 定义巡航方向
                if "scan_direction_x" not in shared_state:
                    shared_state["scan_direction_x"] = 1  # 1 表示向右, -1 表示向左

                move_x, move_y = moving

                # 左右扫描
                if shared_state["scan_direction_x"] == 1:
                    if move_x < SERVO_X_MAX:
                        move_x += 3
                        ifturn = 0
                    else:
                        shared_state["scan_direction_x"] = -1
                        move_y += 30
                        ifturn = 0
                else:
                    if move_x > SERVO_X_MIN:
                        move_x -= 3
                        ifturn = 0
                    else:

                        shared_state["scan_direction_x"] = 1
                        move_y += 30
                        ifturn = 0

                # 如果 Y 轴到达边界，则复位
                if move_y > SERVO_Y_MAX:
                    move_y = SERVO_Y_MIN
                    ifturn = 0
                    hasscanned = True
                    random_move = True
            pass 

        # --- 5. 更新最终状态 ---
        move_x = clamp(move_x, SERVO_X_MIN, SERVO_X_MAX)
        move_y = clamp(move_y, SERVO_Y_MIN, SERVO_Y_MAX)
        
        with lock:
            shared_state["moving"] = (move_x, move_y)
            shared_state["firing"] = firing
            shared_state["ifturn"] = ifturn
            shared_state["random_move"] = random_move
        
        # 稳定循环周期
        elapsed_time = time.time() - current_time
        sleep_time = CONTROL_LOOP_DT - elapsed_time
        if sleep_time > 0:
            time.sleep(sleep_time)

    print("[中控线程] 正在关闭...")

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))
