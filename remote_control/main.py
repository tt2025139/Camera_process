import threading
import time
from bluetooth_communicator import run_bluetooth_communication
from remote_control import run_remote_control
# 导入修改后的模块中的新函数
from Html_Processor import init_app, run_app

if __name__ == "__main__":
    # 创建用于线程间通信的共享状态字典和锁
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
        "moving": (0, 0), # 舵机初始位置
        "bottom": 0,
        "firing": 0, # 初始为布尔值或整数都可以，但要统一
        "ifturn": 0,
        "random_move": 0
    }
    lock = threading.Lock()

    # --- 关键修改 ---
    # 在启动Flask线程之前，初始化它，将共享状态和锁传递进去
    init_app(shared_state, lock)

    # 创建线程
    bluetooth_thread = threading.Thread(
        target=run_bluetooth_communication, args=(shared_state, lock)
    )
    remote_control_thread = threading.Thread(
        target=run_remote_control, args=(shared_state, lock)
    )
    # 线程目标修改为 run_app，而不是 gen_video_stream
    html_processor_thread = threading.Thread(
        target=run_app, args=() # run_app 不需要参数，因为它使用全局变量
    )

    # --- 关键修改 ---
    # 将HTML处理线程设置为守护线程
    # 这意味着当主程序退出时，这个线程会被强制终止
    # 从而解决了Ctrl+C无法关闭程序的问题
    html_processor_thread.daemon = True

    print("[主程序] 正在启动线程...")

    # 启动线程
    bluetooth_thread.start()
    remote_control_thread.start()
    html_processor_thread.start()

    print("[主程序] 线程已启动。请在浏览器打开 http://127.0.0.1:5000/display")
    print("[主程序] 在终端按 Ctrl+C 即可退出程序。")

    try:
        while shared_state["running"]:
            if not bluetooth_thread.is_alive() or not remote_control_thread.is_alive():
                print("[主程序] 检测到核心线程已退出，正在关闭程序...")
                with lock:
                    shared_state["running"] = False
                break
            time.sleep(0.5)  # 短暂休眠以降低CPU占用

    except KeyboardInterrupt:
        print("\n[主程序] 检测到 Ctrl+C，正在通知所有线程关闭...")
        with lock:
            shared_state["running"] = False

    finally:
        print("[主程序] 等待子线程结束...")
        # 等待非守护线程结束
        if bluetooth_thread.is_alive():
            bluetooth_thread.join()
        if remote_control_thread.is_alive():
            remote_control_thread.join()
        # 不需要等待守护线程(html_processor_thread)，它会自动退出
        print("[主程序] 所有线程已结束，程序退出。")