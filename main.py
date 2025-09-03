# main.py

import threading
from video_processor import run_video_processing
from bluetooth_communicator import run_bluetooth_communication

if __name__ == "__main__":
    # 创建用于线程间通信的共享状态字典和锁
    shared_state = {
        'center_coordinates': None,
        'running': True
    }
    lock = threading.Lock()

    # 创建线程
    video_thread = threading.Thread(target=run_video_processing, args=(shared_state, lock))
    bluetooth_thread = threading.Thread(target=run_bluetooth_communication, args=(shared_state, lock))

    print("[主程序] 正在启动线程...")
    
    # 启动线程
    video_thread.start()
    bluetooth_thread.start()
    
    print("[主程序] 线程已启动。在视频窗口按 ESC 键即可退出程序。")

    # 等待子线程结束，这样主程序就不会提前退出
    video_thread.join()
    bluetooth_thread.join()

    print("[主程序] 所有线程已结束，程序退出。")