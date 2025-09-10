# 运行此脚本后打开网址http://127.0.0.1:5000/display进行操作

# 需要安装Flask和OpenCV库：pip install flask opencv-python
from flask import Flask, Response, send_from_directory, request
import cv2
import os
import time
import requests
import threading
import numpy as np
from config import VIDEO_STREAM_URL, MIN_CONTOUR_AREA

app = Flask(__name__)

# 全局变量，用于从main.py接收共享状态和锁
shared_state = {
        "running": True,  # 明确设置启动状态
        "bottom_forward": 0,
        "bottom_backward": 0,
        "bottom_left": 0,
        "bottom_right": 0,
        "watching_up": 0,
        "watching_down": 0,
        "watching_left": 0,
        "watching_right": 0,
        "isfiring": 0,
        "nofiring": 1, # 默认停止发射
        "moving": (150, 0), # 舵机初始位置
        "bottom": 0,
        "firing": 0, # 初始为布尔值或整数都可以，但要统一
        "ifturn": 0,
        "random_move": 0
}

lock = None

def init_app(state, app_lock):
    """初始化Flask应用，接收共享状态和锁"""
    global shared_state, lock
    shared_state = state
    lock = app_lock

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


# 视频流生成器，现在它会使用全局的shared_state和lock
def gen_video_stream():
    print("[前端线程] 正在连接视频流...")
    try:
        stream = requests.get(VIDEO_STREAM_URL, stream=True, timeout=10)
        if stream.status_code != 200:
            print(f"[前端线程] 错误：无法连接到视频流，状态码: {stream.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"[前端线程] 错误：连接视频流失败: {e}")
        with lock:
            shared_state['running'] = False
        return

    print("[前端线程] 视频流连接成功。")
    bytes_data = b''

    # 这里使用全局变量
    while shared_state.get('running', True):
        try:
            # 增加一个小的超时，避免在没有数据时永久阻塞
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
                        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                        img = apply_white_balance(img)
                        if img is not None:
                             _, jpeg = cv2.imencode('.jpg', img)
                             yield (b'--frame\r\n'
                                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            if not shared_state.get('running', True):
                break
        except Exception as e:
            print(f"[前端线程] 处理视频帧时发生错误: {e}")
            break # 发生错误时跳出循环
    print("[前端线程] 视频流生成器已停止。")


@app.route('/video_feed')
def video_feed():
	return Response(gen_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/display')
def display():
	html_dir = os.path.dirname(os.path.abspath(__file__))
	return send_from_directory(html_dir, 'Display.html')


@app.route('/action', methods=['POST'])
def action():
    global shared_state, lock
    data = request.get_json()
    action_type = data.get('action')
    print(f"收到前端操作: {action_type}")

    with lock:
        # 底盘控制
        if action_type == '0': # 前进
            shared_state['bottom_forward'] = 1
            shared_state['bottom_backward'] = shared_state['bottom_left'] = shared_state['bottom_right'] = 0
        elif action_type == '1': # 底盘左转
            shared_state['bottom_left'] = 1
            shared_state['bottom_forward'] = shared_state['bottom_backward'] = shared_state['bottom_right'] = 0
        elif action_type == '2': # 底盘右转
            shared_state['bottom_right'] = 1
            shared_state['bottom_forward'] = shared_state['bottom_backward'] = shared_state['bottom_left'] = 0
        elif action_type == '3': # 后退
            shared_state['bottom_backward'] = 1
            shared_state['bottom_forward'] = shared_state['bottom_left'] = shared_state['bottom_right'] = 0
        # 云台控制
        elif action_type == '4': # 上升
            shared_state['watching_up'] = 1
            shared_state['watching_down'] = 0
        elif action_type == '5': # 云台左转
            shared_state['watching_left'] = 1
            shared_state['watching_right'] = 0
        elif action_type == '6': # 云台右转
            shared_state['watching_right'] = 1
            shared_state['watching_left'] = 0
        elif action_type == '7': # 下降
            shared_state['watching_down'] = 1
            shared_state['watching_up'] = 0
        # 激光控制
        elif action_type == '8': # 发射
            shared_state['isfiring'] = 1
            shared_state['nofiring'] = 0
        elif action_type == '9': # 停止
            shared_state['nofiring'] = 1
            shared_state['isfiring'] = 0
        elif action_type == '10': # 停止所有动作
            shared_state['bottom_forward'] = 0
            shared_state['bottom_backward'] = 0
            shared_state['bottom_left'] = 0
            shared_state['bottom_right'] = 0

    return '', 204

def run_app():
    """此函数用于在单独的线程中启动Flask应用"""
    print("[前端线程] Flask服务器正在启动...")
    # use_reloader=False 对于在子线程中运行Flask至关重要
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
