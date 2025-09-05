# video_processor.py
import time
import cv2
import requests
import numpy as np
from config import VIDEO_STREAM_URL, MIN_CONTOUR_AREA

def run_video_processing(shared_state, lock):
    """
    在一个独立线程中运行，负责连接视频流，检测红色物体，并更新共享的坐标。
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


                        # RGB to HSV
                        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

                        # define Red
                        lower_red1 = np.array([0, 100, 100])
                        upper_red1 = np.array([20, 255, 255])

                        lower_red2 = np.array([160, 100, 100])
                        upper_red2 = np.array([180, 255, 255])

                        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                        red_mask = cv2.bitwise_or(mask1, mask2)
                        
                        # morphologyEx
                        kernel = np.ones((5, 5), np.uint8)
                        
                        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)

                        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
                        
                        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
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
                        cv2.imshow('Red Mask', red_mask)
                        
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