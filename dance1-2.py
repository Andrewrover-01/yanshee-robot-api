# coding=UTF-8
"""方案2：直接使用 gait 的 wave=True，腿和手由底层步态引擎统一同步。"""

import YanAPI

ROBOT_IP = "192.168.1.21"


def dance():
    YanAPI.yan_api_init(ROBOT_IP)
    YanAPI.sync_play_motion("reset")

    print("gait+arms: wave=True")
    ok = YanAPI.sync_do_motion_gait(speed_v=2, speed_h=0, steps=8, period=2, wave=True)
    print("done:", ok)

    YanAPI.sync_play_motion("reset")


if __name__ == "__main__":
    dance()
