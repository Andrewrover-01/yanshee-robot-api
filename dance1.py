# coding=UTF-8
"""
舞蹈程序 —— 使用 YanAPI 控制 Yanshee 机器人跳舞
机器人地址：192.168.1.163  账号：pi  密码：raspberry
"""

import YanAPI
import time

ROBOT_IP = "192.168.1.163"


def dance():
    # 初始化 API
    YanAPI.yan_api_init(ROBOT_IP)

    # 复位站立
    print("执行动作: reset")
    YanAPI.sync_play_motion("reset")

    # 开场白
    YanAPI.sync_do_tts("大家好，我要开始跳舞了，请欣赏！")

    # ── 第一段：热身 ──────────────────────────────────────────
    # 眼灯呼吸蓝光，营造氛围
    YanAPI.set_robot_led("button", "blue", "breath")

    # 向左挥手 → 向右挥手 → 双手挥手
    print("执行动作: wave direction=left")
    YanAPI.sync_play_motion("wave", direction="left")
    print("执行动作: wave direction=right")
    YanAPI.sync_play_motion("wave", direction="right")
    print("执行动作: wave direction=both")
    YanAPI.sync_play_motion("wave", direction="both")

    # ── 第二段：伸展 ──────────────────────────────────────────
    YanAPI.set_robot_led("button", "green", "blink")

    # 双臂伸展
    print("执行动作: stretch direction=both")
    YanAPI.sync_play_motion("stretch", direction="both")
    # 左臂举起 → 右臂举起
    print("执行动作: raise direction=left")
    YanAPI.sync_play_motion("raise", direction="left")
    print("执行动作: raise direction=right")
    YanAPI.sync_play_motion("raise", direction="right")
    # 双臂加油
    print("执行动作: come on direction=both")
    YanAPI.sync_play_motion("come on", direction="both")

    # ── 第三段：步伐 ──────────────────────────────────────────
    YanAPI.set_robot_led("button", "purple", "breath")

    # 向前走两步
    print("执行动作: walk direction=forward repeat=2")
    YanAPI.sync_play_motion("walk", direction="forward", repeat=2)
    # 向左转
    print("执行动作: turn around direction=left")
    YanAPI.sync_play_motion("turn around", direction="left")
    # 向前再走两步
    print("执行动作: walk direction=forward repeat=2")
    YanAPI.sync_play_motion("walk", direction="forward", repeat=2)
    # 向右转，回到原方向
    print("执行动作: turn around direction=right")
    YanAPI.sync_play_motion("turn around", direction="right")

    # ── 第四段：律动 ──────────────────────────────────────────
    YanAPI.set_robot_led("button", "yellow", "blink")

    # 向左挥手 → 向右挥手（原 bend 动作会导致机器人倒地，改用稳定的 wave）
    print("执行动作: wave direction=left")
    YanAPI.sync_play_motion("wave", direction="left")
    print("执行动作: wave direction=right")
    YanAPI.sync_play_motion("wave", direction="right")
    # 蹲下 → 站起（crouch 为蹲下动作）
    print("执行动作: crouch")
    YanAPI.sync_play_motion("crouch")
    print("执行动作: reset")
    YanAPI.sync_play_motion("reset")

    # ── 第五段：头部律动 ──────────────────────────────────────
    YanAPI.set_robot_led("button", "cyan", "breath")

    print("执行动作: head direction=left")
    YanAPI.sync_play_motion("head", direction="left")
    print("执行动作: head direction=right")
    YanAPI.sync_play_motion("head", direction="right")
    print("执行动作: head direction=forward")
    YanAPI.sync_play_motion("head", direction="forward")

    # ── 尾声：谢幕 ────────────────────────────────────────────
    YanAPI.set_robot_led("button", "white", "blink")

    # 鞠躬致谢
    print("执行动作: bow")
    YanAPI.sync_play_motion("bow")
    YanAPI.sync_do_tts("谢谢大家，表演结束！")

    # 复位，灯光恢复常亮白色
    print("执行动作: reset")
    YanAPI.sync_play_motion("reset")
    YanAPI.set_robot_led("button", "white", "on")


if __name__ == "__main__":
    dance()
