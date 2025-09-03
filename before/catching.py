import cv2
import requests
import numpy as np
import time
import serial 
import datetime 

def get_video_stream():
    # 替换为 ESP32-CAM 的视频流 URL
    url = "http://192.168.69.89:81/stream"
    print(f"Connecting to video feed at {url}")
    # 通过 HTTP 请求获取视频流
    stream = requests.get(url, stream=True)
    return stream

# Camera IP address and URL for video stream
camera_ip = "http://192.168.69.89"
url = "http://192.168.69.89:81/stream"

# Get video stream via HTTP request
stream = get_video_stream()
last_print_time = time.time()

def process_video_stream(center_coordinates=None):
    global last_print_time
    global status 
    global take_screenshot 

    if stream.status_code == 200:
        bytes_data = b'' # 更改变量名以避免与 bytes() 内置函数混淆
        for chunk in stream.iter_content(chunk_size=1024):
            bytes_data += chunk
            a = bytes_data.find(b'\xff\xd8') # JPEG start
            b = bytes_data.find(b'\xff\xd9') # JPEG end
            if a != -1 and b != -1:
                jpg = bytes_data[a:b+2]
                bytes_data = bytes_data[b+2:]
                if jpg:
                    img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    # 翻转或旋转图像以匹配实际方向
                    # img = cv2.flip(img, 0) # 如果需要上下翻转
                    img = cv2.rotate(img, cv2.ROTATE_180) # 如果需要旋转180度

                    # --- 图像处理部分：检测红色物体 ---
                    
                    # 1. 颜色空间转换: BGR 到 HSV
                    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

                    # 2. 定义红色范围
                    # 红色在 HSV 色调环中横跨 0 度，所以需要两个范围
                    # 红色下限 (0-10)
                    lower_red1 = np.array([0, 100, 100])
                    upper_red1 = np.array([10, 255, 255])
                    # 红色上限 (170-180)
                    lower_red2 = np.array([170, 100, 100])
                    upper_red2 = np.array([180, 255, 255])

                    # 3. 创建掩膜 (Mask)
                    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
                    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
                    red_mask = cv2.bitwise_or(mask1, mask2)

                    # 4. 形态学操作 (可选，但推荐)
                    # 定义一个核，用于形态学操作
                    kernel = np.ones((5, 5), np.uint8)
                    # 开运算：先腐蚀后膨胀，去除小噪点
                    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
                    # 闭运算：先膨胀后腐蚀，连接断开的区域
                    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)

                    # 5. 查找轮廓
                    # cv2.findContours 返回两个值：轮廓和层级结构
                    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    # 6. 遍历轮廓并计算中心
                    for contour in contours:
                        # 过滤掉过小的轮廓（可能是噪声）
                        if cv2.contourArea(contour) > 500: # 你可以调整这个
                            # 计算轮廓的矩
                            M = cv2.moments(contour)
                            if M["m00"] != 0:
                                # 计算中心点 (Cx, Cy)
                                cX = int(M["m10"] / M["m00"])
                                cY = int(M["m01"] / M["m00"])
                                center_coordinates = (cX, cY)

                                # 7. 绘制轮廓和中心点
                                cv2.drawContours(img, [contour], -1, (0, 255, 0), 2) 
                                cv2.circle(img, (cX, cY), 7, (255, 0, 0), -1) 
                                cv2.putText(img, f"Center: ({cX}, {cY})", (cX - 50, cY - 20),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                
                                # 这里你可以添加处理中心点坐标的逻辑
                                print(f"红色物体中心点: ({cX}, {cY})")

                    # --- 显示处理后的图像 ---
                    cv2.imshow('Video with Red Object Detection', img)
                    cv2.imshow('Red Mask', red_mask)

                    # Exit on pressing ESC key
                    if cv2.waitKey(1) == 27:
                        break
    else:
        print(f"Failed to connect to the video feed, status code: {stream.status_code}")

try:
    process_video_stream()
except KeyboardInterrupt:
    print("Exiting program")
finally:
    cv2.destroyAllWindows()