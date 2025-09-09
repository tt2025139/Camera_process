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
)


def run_center_control(shared_state, lock):
    """
    在一个独立线程中运行，负责根据坐标控制云台及激光发射。
    """
    print("[中控线程] 线程已启动。")

    last_coordinates = (FRAME_WIDTH // 2, FRAME_HEIGHT // 2)

    hascanned = False

    while shared_state.get("running", True):
        with lock:
            center_coordinates = shared_state.get("center_coordinates")
            moving = shared_state.get("moving")
            firing = shared_state.get("firing")
            random_move = shared_state.get("random_move", False)
            ifturn = shared_state.get("ifturn")

        if center_coordinates is not None:
            last_coordinates = center_coordinates

        if (
            last_coordinates != (FRAME_WIDTH // 2, FRAME_HEIGHT // 2)
            and last_coordinates is not None
        ):

            error_x = last_coordinates[0] - LIGHT_CENTER[0]
            error_y = last_coordinates[1] - LIGHT_CENTER[1]

            move_x, move_y = moving

            if abs(error_x) > CENTER_TOLERANCE:
                move_x += -3 if error_x > 0 else +3
            if abs(error_y) > CENTER_TOLERANCE:
                move_y += -3 if error_y > 0 else +3

            if (
                abs(last_coordinates[0] - LIGHT_CENTER[0]) <= CENTER_TOLERANCE
                and abs(last_coordinates[1] - LIGHT_CENTER[1]) <= CENTER_TOLERANCE
            ):
                firing = True
            else:
                firing = False

            if move_y < SERVO_Y_MIN:
                    move_y = SERVO_Y_MIN
                    ifturn = 0
                    hascanned = True
                    random_move = True

            if move_y > SERVO_Y_MAX:
                    move_y = SERVO_Y_MIN
                    ifturn = 0
                    hascanned = True
                    random_move = True

            if move_x > SERVO_X_MAX - 20:
                    move_x = SERVO_X_MAX - 20
                    ifturn = 1
                    random_move = False

            if move_x < SERVO_X_MIN + 20:
                    move_x = SERVO_X_MIN + 20
                    ifturn = 2
                    random_move = False

            if hascanned == True:
                # 已扫描过，则开始巡航
                time.sleep(3)  # 停顿3秒
                random_move = False
                ifturn = 0
                hascanned = False

        else:

            if hascanned == True:
                # 已扫描过，则开始巡航
                time.sleep(3)  # 停顿3秒
                random_move = False
                ifturn = 0
                hascanned = False
            else:
                # 定义巡航方向
                if "scan_direction_x" not in shared_state:
                    shared_state["scan_direction_x"] = 1  # 1 表示向右, -1 表示向左

                move_x, move_y = moving

                # 左右扫描
                if shared_state["scan_direction_x"] == 1:
                    if move_x < SERVO_X_MAX:
                        move_x += 5
                    else:
                        shared_state["scan_direction_x"] = -1
                        move_y += 30
                else:
                    if move_x > SERVO_X_MIN:
                        move_x -= 5
                    else:

                        shared_state["scan_direction_x"] = 1
                        move_y += 30

                # 如果 Y 轴到达边界，则复位
                if move_y > SERVO_Y_MAX:
                    move_y = SERVO_Y_MIN
                    ifturn = 0
                    random_move = True
                    hascanned = True



            firing = False

        move_x = clamp(move_x, SERVO_X_MIN, SERVO_X_MAX)
        move_y = clamp(move_y, SERVO_Y_MIN, SERVO_Y_MAX)
        moving = (move_x, move_y)

        last_coordinates = center_coordinates

        with lock:
            shared_state["moving"] = moving
            shared_state["firing"] = firing
            shared_state["random_move"] = random_move
            shared_state["ifturn"] = ifturn

        time.sleep(0.1)

    print("[中控线程] 正在关闭...")


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))
