# config.py

# --- 视频流配置 ---
VIDEO_STREAM_URL = "http://192.168.69.89:81/stream"

# --- 蓝牙串口配置 ---
SERIAL_PORT = 'COM21'  # 请根据你的设备管理器修改
BAUD_RATE = 115200      # 请确保与你的 HC-06 模块波特率一致

# --- 图像处理配置 ---
MIN_CONTOUR_AREA = 500  # 识别为目标的最小轮廓面积