"""Configuration of some constants"""

# --- 视频流配置 ---
VIDEO_STREAM_URL = "http://192.168.188.89:81/stream"

# --- 蓝牙串口配置 ---
SERIAL_PORT = "COM3"  # 请根据你的设备管理器修改
BAUD_RATE = 9600  # 请确保与你的 HC-06 模块波特率一致

# --- 图像处理配置 ---

MIN_CONTOUR_AREA = 20  # 识别为目标的最小轮廓面积
FRAME_WIDTH = 240       # 视频帧宽度
FRAME_HEIGHT = 320      # 视频帧高度

LIGHT_CENTER = (155, 185)  # 近似激光中心点
CENTER_TOLERANCE = 10  # 允许的中心误差范围（像素）


# --- 舵机限位配置 ---

SERVO_X_MIN = 0
SERVO_X_MAX = 300
SERVO_Y_MIN = 0
SERVO_Y_MAX = 90
