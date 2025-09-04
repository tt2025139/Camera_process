# main.py

import threading
import time
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
    
    print("[主程序] 线程已启动。在视频窗口按 ESC 键或在终端按 Ctrl+C 即可退出程序。")

    try:
        # 主线程现在在一个循环中等待，这样才能响应 KeyboardInterrupt
        # 并检查子线程是否因为其他原因（如关闭视频窗口）而退出
        while shared_state['running']:
            if not video_thread.is_alive():
                print("[主程序] 视频线程已退出，正在关闭程序...")
                with lock:
                    shared_state['running'] = False
                break
            if not bluetooth_thread.is_alive():
                print("[主程序] 蓝牙线程已退出，正在关闭程序...")
                with lock:
                    shared_state['running'] = False
                break
            time.sleep(0.5) #短暂休眠以降低CPU占用

    except KeyboardInterrupt:
        print("\n[主程序] 检测到 Ctrl+C，正在优雅地关闭所有线程...")
        # 捕获到 Ctrl+C 后，设置 'running' 为 False，通知子线程退出
        with lock:
            shared_state['running'] = False

    finally:
        # 等待子线程完全结束
        print("[主程序] 等待子线程结束...")
        video_thread.join()
        bluetooth_thread.join()
        print("[主程序] 所有线程已结束，程序退出。")