# coding=UTF-8
"""
舞蹈程序 —— 使用 YanAPI 控制 Yanshee 机器人跳舞
机器人地址：192.168.1.163  账号：pi  密码：raspberry
"""

import threading
import asyncio
import YanAPI
import time

ROBOT_IP = "192.168.1.203"


def _run_motion_in_thread(name, kwargs):
    """在独立线程中执行 sync_play_motion，每个线程使用独立的 asyncio 事件循环。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        YanAPI.sync_play_motion(name, **kwargs)
    finally:
        loop.close()


def play_parallel(arm_name, arm_kwargs, leg_name, leg_kwargs):
    """同时执行手部动作和腿部动作，两个动作在独立线程中并行运行，全部完成后返回。"""
    t_arm = threading.Thread(target=_run_motion_in_thread, args=(arm_name, arm_kwargs))
    t_leg = threading.Thread(target=_run_motion_in_thread, args=(leg_name, leg_kwargs))
    t_arm.start()
    t_leg.start()
    t_arm.join()
    t_leg.join()


def leg_raise_march_with_arms():
    """抬腿静步走：每迈一步配合手部摆动动作，模拟自然行进中的手臂协调摆动效果。

    通过交替调用 walk（迈步）和 wave/raise/come on（手部动作）实现：
      节拍1  左手挥手 + 向前迈步
      节拍2  右手挥手 + 向前迈步
      节拍3  左臂举起 + 向前迈步
      节拍4  右臂举起 + 向前迈步
      节拍5  双手加油 + 向前迈步
      节拍6  左手挥手 + 向前迈步
      收尾    双手挥手 + 后退回位
    """
    # 节拍1：左手挥手 + 向前迈步（同时执行）
    print("抬腿静步走 节拍1: wave left + walk forward")
    play_parallel("wave", {"direction": "left"},
                  "walk", {"direction": "forward", "repeat": 1})

    # 节拍2：右手挥手 + 向前迈步（同时执行）
    print("抬腿静步走 节拍2: wave right + walk forward")
    play_parallel("wave", {"direction": "right"},
                  "walk", {"direction": "forward", "repeat": 1})

    # 节拍3：左臂举起 + 向前迈步（同时执行）
    print("抬腿静步走 节拍3: raise left + walk forward")
    play_parallel("raise", {"direction": "left"},
                  "walk", {"direction": "forward", "repeat": 1})

    # 节拍4：右臂举起 + 向前迈步（同时执行）
    print("抬腿静步走 节拍4: raise right + walk forward")
    play_parallel("raise", {"direction": "right"},
                  "walk", {"direction": "forward", "repeat": 1})

    # 节拍5：双手加油 + 向前迈步（同时执行）
    print("抬腿静步走 节拍5: come on both + walk forward")
    play_parallel("come on", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})

    # 节拍6：左手再次挥手 + 向前迈步（同时执行）
    print("抬腿静步走 节拍6: wave left + walk forward")
    play_parallel("wave", {"direction": "left"},
                  "walk", {"direction": "forward", "repeat": 1})

    # 收尾：双手挥手 + 后退回位（同时执行）
    print("抬腿静步走 收尾: wave both + walk backward")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "backward", "repeat": 6})


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

    # 抬腿静步走（手动实现：迈步配合手部动作）
    print("执行抬腿静步走动作组合")
    leg_raise_march_with_arms()

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

    # ── 第五段：头部律动 ──────────────────────────────────────
    YanAPI.set_robot_led("button", "cyan", "breath")

    print("执行动作: head direction=left")
    YanAPI.sync_play_motion("head", direction="left")
    print("执行动作: head direction=right")
    YanAPI.sync_play_motion("head", direction="right")
    print("执行动作: head direction=forward")
    YanAPI.sync_play_motion("head", direction="forward")

    # 后仰动作：双臂高举，躯干自然后倾，再复位
    print("执行动作: 后仰 - raise direction=both")
    YanAPI.sync_play_motion("raise", direction="both")
    print("执行动作: 后仰复位 - reset")
    YanAPI.sync_play_motion("reset")

    # ── 第六段：综合展示 ──────────────────────────────────────
    YanAPI.set_robot_led("button", "red", "breath")

    # 双臂举起 + 向前走（同时执行）
    print("执行动作: raise direction=both + walk direction=forward repeat=1")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})
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
