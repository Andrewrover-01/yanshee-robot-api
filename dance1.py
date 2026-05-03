# coding=UTF-8
"""
舞蹈程序 —— 使用 YanAPI 控制 Yanshee 机器人跳舞
机器人地址：192.168.1.163  账号：pi  密码：raspberry
"""

import YanAPI
import time

ROBOT_IP = "192.168.1.115"


GAIT_STATUS_EXITED = 7  # Already exit gait ready state
GAIT_STATUS_IDLE = 8    # Idle state (no gait task)
GAIT_POLL_INTERVAL = 0.5  # seconds between status polls
GAIT_TIMEOUT = 30  # seconds before giving up


def march_in_place(steps: int = 4, period: int = 1):
    """抬腿静步走：原地抬腿踏步，speed_v=0、speed_h=0 保持不移动位置。

    Args:
        steps: 踏步总步数（正整数）。
        period: 步态周期，取值 1~5，数值越大节奏越慢。
    """
    YanAPI.control_motion_gait(speed_v=0, speed_h=0, steps=steps, period=period, wave=False)
    time.sleep(GAIT_POLL_INTERVAL)  # 等待步态任务启动
    elapsed = 0.0
    while elapsed < GAIT_TIMEOUT:
        res = YanAPI.get_motion_gait_state()
        status = res.get("data", {}).get("status", GAIT_STATUS_IDLE)
        if status in (GAIT_STATUS_EXITED, GAIT_STATUS_IDLE):
            break
        time.sleep(GAIT_POLL_INTERVAL)
        elapsed += GAIT_POLL_INTERVAL


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

    # 腿部动作：向前走一步再向后退一步
    print("执行动作: walk direction=forward repeat=1")
    YanAPI.sync_play_motion("walk", direction="forward", repeat=1)
    print("执行动作: walk direction=backward repeat=1")
    YanAPI.sync_play_motion("walk", direction="backward", repeat=1)

    # 腿部动作：蹲下再站起
    print("执行动作: crouch")
    YanAPI.sync_play_motion("crouch")
    print("执行动作: reset")
    YanAPI.sync_play_motion("reset")

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
    # 侧步：向左一步再向右一步
    print("执行动作: walk direction=left repeat=1")
    YanAPI.sync_play_motion("walk", direction="left", repeat=1)
    print("执行动作: walk direction=right repeat=1")
    YanAPI.sync_play_motion("walk", direction="right", repeat=1)

    # ── 第三段：步伐 ──────────────────────────────────────────
    YanAPI.set_robot_led("button", "purple", "breath")

    # 向前走一步
    print("执行动作: walk direction=forward repeat=1")
    YanAPI.sync_play_motion("walk", direction="forward", repeat=1)
    # 向左转
    print("执行动作: turn around direction=left")
    YanAPI.sync_play_motion("turn around", direction="left")
    # 向前再走一步
    print("执行动作: walk direction=forward repeat=1")
    YanAPI.sync_play_motion("walk", direction="forward", repeat=1)
    # 向右挥手（原 turn around direction=right 会导致机器人倒地，改用稳定的 wave）
    print("执行动作: wave direction=right")
    YanAPI.sync_play_motion("wave", direction="right")
    # 向前走一步（原 walk direction=backward 会导致机器人倒地，改用稳定的 forward）
    print("执行动作: walk direction=forward repeat=1")
    YanAPI.sync_play_motion("walk", direction="forward", repeat=1)

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
    # 双臂加油 + 双臂举起
    print("执行动作: come on direction=both")
    YanAPI.sync_play_motion("come on", direction="both")
    print("执行动作: raise direction=both")
    YanAPI.sync_play_motion("raise", direction="both")
    # 侧步律动
    print("执行动作: walk direction=left repeat=2")
    YanAPI.sync_play_motion("walk", direction="left", repeat=2)
    print("执行动作: walk direction=right repeat=2")
    YanAPI.sync_play_motion("walk", direction="right", repeat=2)

    # 抬腿静步走：原地踏步 4 步，保持节奏
    print("执行动作: 抬腿静步走 steps=4 period=1")
    march_in_place(steps=4, period=1)

    # ── 第五段：头部律动 ──────────────────────────────────────
    YanAPI.set_robot_led("button", "cyan", "breath")

    print("执行动作: head direction=left")
    YanAPI.sync_play_motion("head", direction="left")
    print("执行动作: head direction=right")
    YanAPI.sync_play_motion("head", direction="right")
    print("执行动作: head direction=forward")
    YanAPI.sync_play_motion("head", direction="forward")

    # ── 第六段：综合展示 ──────────────────────────────────────
    YanAPI.set_robot_led("button", "red", "breath")

    # 双臂举起 + 向前走 + 挥手
    print("执行动作: raise direction=both")
    YanAPI.sync_play_motion("raise", direction="both")
    print("执行动作: walk direction=forward repeat=1")
    YanAPI.sync_play_motion("walk", direction="forward", repeat=1)
    print("执行动作: wave direction=both")
    YanAPI.sync_play_motion("wave", direction="both")
    # 转圈 + 加油 + 伸展
    print("执行动作: turn around direction=left")
    YanAPI.sync_play_motion("turn around", direction="left")
    print("执行动作: come on direction=both")
    YanAPI.sync_play_motion("come on", direction="both")
    print("执行动作: stretch direction=both")
    YanAPI.sync_play_motion("stretch", direction="both")
    print("执行动作: turn around direction=right")
    YanAPI.sync_play_motion("turn around", direction="right")
    # 蹲起收尾
    print("执行动作: crouch")
    YanAPI.sync_play_motion("crouch")
    print("执行动作: reset")
    YanAPI.sync_play_motion("reset")
    print("执行动作: wave direction=both")
    YanAPI.sync_play_motion("wave", direction="both")

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
