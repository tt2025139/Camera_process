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
    # ... 原有选项保持不变 ...
    ENABLE_WHITE_BALANCE = False
    CALCULATE_HSV_INFO = False
    ENHANCE_CONTRAST = False
    SHAPE_ANALYSIS_ENABLED = False
    MIN_ASPECT_RATIO = 0.3
    MAX_ASPECT_RATIO = 3.0

    # True:  使用下面的 H_MIN/MAX, S_MIN/MAX, 并动态计算V通道的阈值。 (推荐)
    # False: 使用下面传统的 LOWER/UPPER_COLOR_BOUND_1 固定阈值。
    ADAPTIVE_V_CHANNEL = False
    V_TOLERANCE = 60  # V通道动态阈值的容差范围


    # --- 传统固定阈值 (当 ADAPTIVE_V_CHANNEL = False 时生效) ---
    # LOWER_COLOR_BOUND_1 = np.array([40, 70, 10])
    # UPPER_COLOR_BOUND_1 = np.array([70, 140, 70])
    # LOWER_COLOR_BOUND_2 = None  
    # UPPER_COLOR_BOUND_2 = None  
    LOWER_COLOR_BOUND_1 = np.array([0, 100, 20])
    UPPER_COLOR_BOUND_1 = np.array([30, 255, 255])
    LOWER_COLOR_BOUND_2 = np.array([150, 100, 20])  # 可选第二个范围
    UPPER_COLOR_BOUND_2 = np.array([180, 255, 255])

    # LOWER_COLOR_BOUND_1 = np.array([90, 100, 50])
    # UPPER_COLOR_BOUND_1 = np.array([150, 255, 255])
    # LOWER_COLOR_BOUND_2 = None  # 可选第二个范围
    # UPPER_COLOR_BOUND_2 = None


# ... apply_white_balance 函数保持不变 ...
def apply_white_balance(img):
    """
    应用“灰色世界”假设的白平衡算法来校正图像色偏。
    """
    img_float = img.astype(np.float32)
    avg_b = np.mean(img_float[:, :, 0])
    avg_g = np.mean(img_float[:, :, 1])
    avg_r = np.mean(img_float[:, :, 2])
    
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


# --- [新增函数] ---
def is_box_like(contour):
    """
    通过分析轮廓的几何形状，判断它是否像一个箱子（四边形）。
    """
    if not CONFIG.SHAPE_ANALYSIS_ENABLED:
        return True # 如果禁用了形状分析，则直接返回True

    # 1. 轮廓近似: 找到轮廓的近似多边形
    # cv2.arcLength 计算轮廓的周长
    # 0.04 * peri 是一个阈值，用于决定近似的精度
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

    # 2. 顶点数判断: 一个好的箱子轮廓近似后应该是4个顶点
    if len(approx) == 4:
        # 3. 长宽比判断: 计算外接矩形的长宽比，排除过于细长的形状
        (x, y, w, h) = cv2.boundingRect(approx)
        aspect_ratio = float(w) / h if h != 0 else 0
        
        # 确保长宽比在合理范围内 (同时考虑宽/高和高/宽)
        if (CONFIG.MIN_ASPECT_RATIO < aspect_ratio < CONFIG.MAX_ASPECT_RATIO) or \
           (CONFIG.MIN_ASPECT_RATIO < (1/aspect_ratio if aspect_ratio != 0 else 0) < CONFIG.MAX_ASPECT_RATIO):
            return True # 如果顶点为4且长宽比合适，则判定为箱子
            
    return False # 其他情况都不是箱子


def run_video_processing(shared_state, lock):
    """
    在一个独立线程中运行，负责连接视频流，检测指定颜色物体，并更新共享的坐标。
    """
    # ... (视频流连接部分代码保持不变) ...
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


    # 创建一个字典来存储鼠标的当前位置和对应点的HSV值
    mouse_data = {'hsv': None}


    # 定义鼠标回调函数
    def get_hsv_on_mouse_move(event, x, y, flags, param):
        # param 参数在这里就是每一帧的 hsv 图像
        # 当鼠标在窗口上移动时 (EVENT_MOUSEMOVE)
        if event == cv2.EVENT_MOUSEMOVE:
            # 从 hsv 图像中获取 (y, x) 坐标的像素值
            # 注意OpenCV的坐标是 (y, x) 而不是 (x, y)
            hsv_pixel = param[y, x]
            mouse_data['hsv'] = tuple(hsv_pixel)


    cv2.namedWindow('Video Feed')
    
    cv2.setMouseCallback('Video Feed', get_hsv_on_mouse_move, param=None)


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

                        if CONFIG.ENABLE_WHITE_BALANCE:
                            img = apply_white_balance(img)

                        # RGB to HSV
                        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                        
                        # --- [修改] 应用对比度增强 ---
                        if CONFIG.ENHANCE_CONTRAST:
                            h, s, v = cv2.split(hsv)
                            v = cv2.equalizeHist(v) # 仅对亮度通道V进行直方图均衡化
                            hsv = cv2.merge([h, s, v])

                        # ... (HSV 信息打印部分保持不变) ...
                        # 每次循环时，都更新回调函数的 param 参数为最新的 hsv 图像
                        cv2.setMouseCallback('Video Feed', get_hsv_on_mouse_move, param=hsv)
                        
                        # 如果 mouse_data 中有值，就将其绘制在图像上
                        if mouse_data['hsv'] is not None:
                            h, s, v = mouse_data['hsv']
                            hsv_text = f'HSV: ({h}, {s}, {v})'
                            # 将文字绘制在左上角
                            cv2.putText(img, hsv_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 
                                        0.6, (255, 255, 0), 2, cv2.LINE_AA)
                        
                        # --- 使用宏定义的颜色范围进行物体检测 ---
                        if CONFIG.ADAPTIVE_V_CHANNEL:
                            # 1. 对 BOUND_1 进行HS初筛 (更清晰的写法)
                            lower_hs1 = np.array([CONFIG.LOWER_COLOR_BOUND_1[0], CONFIG.LOWER_COLOR_BOUND_1[1], 100])
                            upper_hs1 = np.array([CONFIG.UPPER_COLOR_BOUND_1[0], CONFIG.UPPER_COLOR_BOUND_1[1], 230])
                            hs_mask1 = cv2.inRange(hsv, lower_hs1, upper_hs1)
                            
                            combined_hs_mask = hs_mask1
                            
                            # (如果存在) 对 BOUND_2 进行HS初筛并合并
                            if CONFIG.LOWER_COLOR_BOUND_2 is not None and CONFIG.UPPER_COLOR_BOUND_2 is not None:
                                lower_hs2 = np.array([CONFIG.LOWER_COLOR_BOUND_2[0], CONFIG.LOWER_COLOR_BOUND_2[1], 100])
                                upper_hs2 = np.array([CONFIG.UPPER_COLOR_BOUND_2[0], CONFIG.UPPER_COLOR_BOUND_2[1], 230])
                                hs_mask2 = cv2.inRange(hsv, lower_hs2, upper_hs2)
                                combined_hs_mask = cv2.bitwise_or(hs_mask1, hs_mask2)

                            # 2. 在所有可能区域内计算平均V值
                            if cv2.countNonZero(combined_hs_mask) > 0:
                                avg_v = cv2.mean(hsv[:,:,2], mask=combined_hs_mask)[0]
                            else:
                                avg_v = 128
                            
                            # 3. [修复] 动态计算V阈值并强制转换为整数
                            v_lower = int(max(0, avg_v - CONFIG.V_TOLERANCE))
                            v_upper = int(min(255, avg_v + CONFIG.V_TOLERANCE))
                            
                            # 4. 使用动态V值生成最终掩码
                            final_lower1 = np.array([CONFIG.LOWER_COLOR_BOUND_1[0], CONFIG.LOWER_COLOR_BOUND_1[1], v_lower])
                            final_upper1 = np.array([CONFIG.UPPER_COLOR_BOUND_1[0], CONFIG.UPPER_COLOR_BOUND_1[1], v_upper])
                            color_mask = cv2.inRange(hsv, final_lower1, final_upper1)

                            if CONFIG.LOWER_COLOR_BOUND_2 is not None and CONFIG.UPPER_COLOR_BOUND_2 is not None:
                                final_lower2 = np.array([CONFIG.LOWER_COLOR_BOUND_2[0], CONFIG.LOWER_COLOR_BOUND_2[1], v_lower])
                                final_upper2 = np.array([CONFIG.UPPER_COLOR_BOUND_2[0], CONFIG.UPPER_COLOR_BOUND_2[1], v_upper])
                                color_mask2 = cv2.inRange(hsv, final_lower2, final_upper2)
                                color_mask = cv2.bitwise_or(color_mask, color_mask2)
                        else:
                            # 传统的固定阈值方法
                            color_mask = cv2.inRange(hsv, CONFIG.LOWER_COLOR_BOUND_1, CONFIG.UPPER_COLOR_BOUND_1)
                            if CONFIG.LOWER_COLOR_BOUND_2 is not None and CONFIG.UPPER_COLOR_BOUND_2 is not None:
                                color_mask2 = cv2.inRange(hsv, CONFIG.LOWER_COLOR_BOUND_2, CONFIG.UPPER_COLOR_BOUND_2)
                                color_mask = cv2.bitwise_or(color_mask, color_mask2)
                        # ... (形态学操作保持不变) ...
                        kernel = np.ones((5, 5), np.uint8)
                        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel)
                        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel)
                        
                        contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        found_object = False
                        if contours:
                            largest_contour = max(contours, key=cv2.contourArea)

                            # --- [修改] 在处理最大轮廓前，先进行形状判断 ---
                            if cv2.contourArea(largest_contour) > MIN_CONTOUR_AREA and is_box_like(largest_contour):
                                M = cv2.moments(largest_contour)
                                if M["m00"] != 0:
                                    cX = int(M["m10"] / M["m00"])
                                    cY = int(M["m01"] / M["m00"])
                                    
                                    with lock:
                                        shared_state['detection_data'] = ((cX, cY),time.time())
                                    found_object = True

                                    # 用绿色绘制通过所有检查的最终轮廓
                                    cv2.drawContours(img, [largest_contour], -1, (0, 255, 0), 2)
                                    cv2.circle(img, (cX, cY), 7, (255, 0, 0), -1)
                                    cv2.putText(img, f"BOX ({cX}, {cY})", (cX + 10, cY - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        
                        if not found_object:
                            with lock:
                                shared_state['detection_data'] = None

                        cv2.imshow('Video Feed', img)
                        cv2.imshow('Color Mask', color_mask)
                        
                        if cv2.waitKey(1) == 27:
                            with lock:
                                shared_state['running'] = False
                            break

            # ... (窗口关闭处理部分保持不变) ...
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