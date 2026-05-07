# coding=UTF-8
"""方案1：腿部用 motions/gait，手部用 motions，两个独立 endpoint 并行。"""

import asyncio
import os
import threading
import YanAPI

ROBOT_IP = os.getenv("YAN_ROBOT_IP", "192.168.1.21")


def _run_with_event_loop(func, *args, **kwargs):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        func(*args, **kwargs)
    finally:
        loop.close()


def _legs_task():
    ok = YanAPI.sync_do_motion_gait(speed_v=2, speed_h=0, steps=6, period=2, wave=False)
    print("legs done:", ok)


def _arms_task():
    print("arms: wave left")
    YanAPI.sync_play_motion("wave", direction="left")
    print("arms: wave right")
    YanAPI.sync_play_motion("wave", direction="right")
    print("arms: come on both")
    YanAPI.sync_play_motion("come on", direction="both")


def dance():
    YanAPI.yan_api_init(ROBOT_IP)
    YanAPI.sync_play_motion("reset")

    legs_thread = threading.Thread(target=_run_with_event_loop, args=(_legs_task,))
    arms_thread = threading.Thread(target=_run_with_event_loop, args=(_arms_task,))
    legs_thread.start()
    arms_thread.start()
    legs_thread.join()
    arms_thread.join()

    YanAPI.sync_play_motion("reset")


if __name__ == "__main__":
    dance()
