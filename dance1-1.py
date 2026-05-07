# coding=UTF-8
"""方案1：腿部用 motions/gait，手部用 motions，两个独立 endpoint 并行。"""

import asyncio
import threading
import YanAPI

ROBOT_IP = "192.168.1.21"


def _run_with_event_loop(func, *args, **kwargs):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        func(*args, **kwargs)
    finally:
        loop.close()


def _legs_task():
    # 腿部步态：向前小步走，约 6 步
    ok = YanAPI.sync_do_motion_gait(speed_v=2, speed_h=0, steps=6, period=2, wave=False)
    print("legs done:", ok)


def _arms_task():
    # 手部动作序列（与腿部线程并行）
    print("arms: wave left")
    YanAPI.sync_play_motion("wave", direction="left")
    print("arms: wave right")
    YanAPI.sync_play_motion("wave", direction="right")
    print("arms: come on both")
    YanAPI.sync_play_motion("come on", direction="both")


def dance():
    YanAPI.yan_api_init(ROBOT_IP)
    YanAPI.sync_play_motion("reset")

    t1 = threading.Thread(target=_run_with_event_loop, args=(_legs_task,))
    t2 = threading.Thread(target=_run_with_event_loop, args=(_arms_task,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    YanAPI.sync_play_motion("reset")


if __name__ == "__main__":
    dance()
