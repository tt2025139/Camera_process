# 运行此脚本后打开网址http://127.0.0.1:5000/display进行操作

# 需要安装Flask和OpenCV库：pip install flask opencv-python
from flask import Flask, Response, send_from_directory, request
import cv2
import os
import time
import requests
import threading
import numpy as np
from video_processor import CONFIG, apply_white_balance, is_box_like
from config import VIDEO_STREAM_URL, MIN_CONTOUR_AREA

app = Flask(__name__)

shared_state = {
    "center_coordinates": None,
    "firing": False,
    "moving": (0, 0),
    "scan_direction_x": 1,
    "running": True,
    "random_move": False,
}
lock = threading.Lock()

# 视频流生成器，集成video_processor.py的处理流程
def gen_video_stream(shared_state, lock):
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
                print("[视频线程] 收到视频数据块。")
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
                        print("[视频线程] 收到视频帧。")
                        _, jpeg = cv2.imencode('.jpg', img)
                        yield (b'--frame\r\n'
							   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                        if img is None:
                            continue

        except Exception as e:
            print(f"[视频线程] 处理视频帧时发生错误: {e}")
            time.sleep(1)


# MJPEG视频流接口
@app.route('/video_feed')
def video_feed():
	return Response(gen_video_stream(shared_state, lock), mimetype='multipart/x-mixed-replace; boundary=frame')

# 直接返回Display.html页面
@app.route('/display')
def display():
	html_dir = os.path.dirname(os.path.abspath(__file__))
	return send_from_directory(html_dir, 'Display.html')


# 前端按钮操作反馈路由
@app.route('/action', methods=['POST'])
def action():
	data = request.get_json()
	action_type = data.get('action')
	print(f"收到前端操作: {action_type}")
	# 可在此处添加硬件控制或其他逻辑
	return '', 204

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, debug=True)
