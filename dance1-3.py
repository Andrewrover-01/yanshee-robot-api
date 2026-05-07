# coding=UTF-8
"""方案3：使用 version='v2' 的 layer 动作并发。"""

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


def _play_v2(name, **kwargs):
    ok = YanAPI.sync_play_motion(name, version="v2", **kwargs)
    print(f"{name} v2 done:", ok)


def dance():
    YanAPI.yan_api_init(ROBOT_IP)
    YanAPI.sync_play_motion("reset")

    # v2 layer 并发示例：脚步 + 手部
    t1 = threading.Thread(target=_run_with_event_loop, args=(_play_v2, "walk"), kwargs={"direction": "forward", "repeat": 2})
    t2 = threading.Thread(target=_run_with_event_loop, args=(_play_v2, "wave"), kwargs={"direction": "both"})
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    YanAPI.sync_play_motion("reset")


if __name__ == "__main__":
    dance()
