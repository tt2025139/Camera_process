# video_processor.py
import time
import cv2
import requests
import numpy as np
from config import VIDEO_STREAM_URL, MIN_CONTOUR_AREA

class CONFIG:
    """
    通过更改此处的参数来控制脚本行为
    """
    # 选项1: 是否启用白平衡 (True/False)
    # 如果图像整体色调偏色（例如偏绿、偏蓝），设置为 True 可以自动校正。
    ENABLE_WHITE_BALANCE = True

    # 选项2: 是否计算并打印 HSV 信息 (True/False)
    # 设置为 True 会为每一帧计算并打印 HSV 的总和、最小值和最大值，用于调试。
    CALCULATE_HSV_INFO = False

    # 选项3: 颜色范围 (HSV)
    # 在这里更改 lower 和 upper 的值来追踪不同颜色的物体。
    LOWER_COLOR_BOUND_1 = np.array([55, 20, 50])  # Example: Brown for a box 示例 (红色低位): np.array([0, 100, 100])
    UPPER_COLOR_BOUND_1= np.array([75, 160, 180]) # Example: Brown for a box 示例 (红色低位): np.array([20, 255, 255])

    LOWER_COLOR_BOUND_2 = None  # 示例 (红色高位): np.array([160, 100, 100])
    UPPER_COLOR_BOUND_2 = None  # 示例 (红色高位): np.array([180, 255, 255])


def apply_white_balance(img):
    """
    应用“灰色世界”假设的白平衡算法来校正图像色偏。
    """
    img_float = img.astype(np.float32)
    avg_b = np.mean(img_float[:, :, 0])
    avg_g = np.mean(img_float[:, :, 1])
    avg_r = np.mean(img_float[:, :, 2])
    
    # 防止除以零
    if avg_b == 0 or avg_g == 0 or avg_r == 0:
        return img
        
    avg_gray = (avg_b + avg_g + avg_r) / 3
    scale_b = avg_gray / avg_b
    scale_g = avg_gray / avg_g
    scale_r = avg_gray / avg_r

    img_float[:, :, 0] *= scale_b
    img_float[:, :, 1] *= scale_g
    img_float[:, :, 2] *= scale_r
    
    return np.clip(img_float, 0, 255).astype(np.uint8)


def run_video_processing(shared_state, lock):
    """
    在一个独立线程中运行，负责连接视频流，检测指定颜色物体，并更新共享的坐标。
    """
    print("[视频线程] 正在连接视频流...")
    try:
        stream = requests.get(VIDEO_STREAM_URL, stream=True, timeout=10)
        if stream.status_code != 200:
            print(f"[视频线程] 错误：无法连接到视频流，状态码: {stream.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"[视频线程] 错误：连接视频流失败: {e}")
        with lock:
            shared_state['running'] = False
        return

    print("[视频线程] 视频流连接成功。")
    bytes_data = b''

    while shared_state.get('running', True):
        try:
            for chunk in stream.iter_content(chunk_size=1024):
                if not shared_state.get('running', True):
                    break

                bytes_data += chunk
                a = bytes_data.find(b'\xff\xd8')
                b = bytes_data.find(b'\xff\xd9')

                if a != -1 and b != -1:
                    jpg = bytes_data[a:b + 2]
                    bytes_data = bytes_data[b + 2:]
                    if jpg:
                        img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if img is None:
                            continue
                        
                        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

                        # --- [条件应用] 白平衡 ---
                        if CONFIG.ENABLE_WHITE_BALANCE:
                            img = apply_white_balance(img)

                        # RGB to HSV
                        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

                        # --- [条件计算] HSV 相关信息 ---
                        if CONFIG.CALCULATE_HSV_INFO:
                            hsv_sum = np.sum(hsv, axis=(0, 1))
                            h_min, s_min, v_min = np.min(hsv, axis=(0, 1))
                            h_max, s_max, v_max = np.max(hsv, axis=(0, 1))
                            print(f"HSV Sums: H={hsv_sum[0]}, S={hsv_sum[1]}, V={hsv_sum[2]}")
                            print(f"HSV Minima: H={h_min}, S={s_min}, V={v_min}")
                            print(f"HSV Maxima: H={h_max}, S={s_max}, V={v_max}")
                        
                        # --- 使用宏定义的颜色范围进行物体检测 ---
                        color_mask1 = cv2.inRange(hsv, CONFIG.LOWER_COLOR_BOUND_1, CONFIG.UPPER_COLOR_BOUND_1)

                        if CONFIG.LOWER_COLOR_BOUND_2 is not None and CONFIG.UPPER_COLOR_BOUND_2 is not None:
                            color_mask2 = cv2.inRange(hsv, CONFIG.LOWER_COLOR_BOUND_2, CONFIG.UPPER_COLOR_BOUND_2)
                            color_mask = cv2.bitwise_or(color_mask1, color_mask2)
                        else:
                            color_mask = color_mask1
                        
                        # morphologyEx
                        kernel = np.ones((5, 5), np.uint8)
                        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
                        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
                        
                        contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        found_object = False
                        if contours:
                            largest_contour = max(contours, key=cv2.contourArea)

                            if cv2.contourArea(largest_contour) > MIN_CONTOUR_AREA:
                                M = cv2.moments(largest_contour)
                                if M["m00"] != 0:
                                    cX = int(M["m10"] / M["m00"])
                                    cY = int(M["m01"] / M["m00"])
                                    
                                    with lock:
                                        shared_state['center_coordinates'] = (cX, cY)
                                    found_object = True

                                    cv2.drawContours(img, [largest_contour], -1, (0, 255, 0), 2)
                                    cv2.circle(img, (cX, cY), 7, (255, 0, 0), -1)
                                    cv2.putText(img, f"({cX}, {cY})", (cX + 10, cY - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        
                        if not found_object:
                            with lock:
                                shared_state['center_coordinates'] = None

                        cv2.imshow('Video Feed', img)
                        cv2.imshow('Color Mask', color_mask)
                        
                        if cv2.waitKey(1) == 27:
                            with lock:
                                shared_state['running'] = False
                            break

            if cv2.getWindowProperty('Video Feed', cv2.WND_PROP_VISIBLE) < 1:
                print("[视频线程] 视频窗口已关闭，正在停止程序...")
                with lock:
                    shared_state['running'] = False
                break

        except Exception as e:
            print(f"[视频线程] 处理视频帧时发生错误: {e}")
            time.sleep(1)

    print("[视频线程] 正在关闭...")
    cv2.destroyAllWindows()