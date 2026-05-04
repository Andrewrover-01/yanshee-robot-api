# coding=UTF-8
"""
舞蹈程序2 —— 使用 YanAPI 控制 Yanshee 机器人跳舞（第二支舞）
舞蹈时长：≥ 2 分钟
机器人地址：192.168.1.203  账号：pi  密码：raspberry
"""

import asyncio
import logging
import threading
import time

import YanAPI

ROBOT_IP = "192.168.1.203"

# 每次 walk 动作对应的步态步数（一次 walk 含左右各一步，共 2 个步态步）
_WALK_REPEAT_TO_STEPS = 2

# exit_gait_and_stand 中等待步态退出的最大轮询次数（每次 0.5 s，共 15 s 超时）
_GAIT_EXIT_MAX_POLLS = 30
# 步态退出完成的最低状态码（7 = 已退出步态就绪, 8 = 空闲）
_GAIT_EXIT_DONE_STATUS = 7

# 步态 API 的方向 → 速度映射（speed_v: 前后, speed_h: 左右）
_GAIT_DEFAULT_SPEED = {"speed_v": 3, "speed_h": 0}
_GAIT_SPEED_MAP = {
    "forward":  {"speed_v":  3, "speed_h":  0},
    "backward": {"speed_v": -3, "speed_h":  0},
    "left":     {"speed_v":  0, "speed_h": -3},
    "right":    {"speed_v":  0, "speed_h":  3},
}


def _run_motion_in_thread(name, kwargs):
    """在独立线程中执行 sync_play_motion，每个线程使用独立的 asyncio 事件循环。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        YanAPI.sync_play_motion(name, **kwargs)
    except Exception as e:
        logging.error("motion '%s' failed in thread: %s", name, e)
    finally:
        loop.close()


def _run_gait_in_thread(direction, steps, wave=False):
    """在独立线程中用步态 API（PUT /motions/gait）执行行走动作。

    步态 API 与动作 API（PUT /motions）使用不同的端点，两者可同时运行
    而互不干扰，从而实现腿部和手部动作的真正并发。
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        speeds = _GAIT_SPEED_MAP.get(direction, _GAIT_DEFAULT_SPEED)
        YanAPI.sync_do_motion_gait(
            speed_v=speeds["speed_v"],
            speed_h=speeds["speed_h"],
            steps=steps,
            period=1,
            wave=wave,
        )
    except Exception as e:
        logging.error("gait walk direction='%s' failed: %s", direction, e)
    finally:
        loop.close()


def exit_gait_and_stand():
    """退出步态模式，等待机器人完全站立后再复位。"""
    YanAPI.exit_motion_gait()
    for _ in range(_GAIT_EXIT_MAX_POLLS):
        state = YanAPI.get_motion_gait_state()
        if state.get("data", {}).get("status", 0) >= _GAIT_EXIT_DONE_STATUS:
            break
        time.sleep(0.5)
    YanAPI.sync_play_motion("reset")


def play_parallel(motion1_name, motion1_kwargs, motion2_name, motion2_kwargs):
    """同时执行两个动作，全部完成后返回。

    当其中一个动作为 walk 时，自动改用步态 API（PUT /motions/gait）执行，
    以避免与动作 API（PUT /motions）共用同一端点造成互相取消的问题。
    步态部分结束后自动退出步态模式并恢复站立。
    """
    uses_gait = False

    if motion1_name == "walk":
        direction = motion1_kwargs.get("direction", "forward")
        repeat = motion1_kwargs.get("repeat", 1)
        t1 = threading.Thread(target=_run_gait_in_thread,
                              args=(direction, repeat * _WALK_REPEAT_TO_STEPS))
        t2 = threading.Thread(target=_run_motion_in_thread,
                              args=(motion2_name, motion2_kwargs))
        uses_gait = True
    elif motion2_name == "walk":
        direction = motion2_kwargs.get("direction", "forward")
        repeat = motion2_kwargs.get("repeat", 1)
        t1 = threading.Thread(target=_run_motion_in_thread,
                              args=(motion1_name, motion1_kwargs))
        t2 = threading.Thread(target=_run_gait_in_thread,
                              args=(direction, repeat * _WALK_REPEAT_TO_STEPS))
        uses_gait = True
    else:
        t1 = threading.Thread(target=_run_motion_in_thread,
                              args=(motion1_name, motion1_kwargs))
        t2 = threading.Thread(target=_run_motion_in_thread,
                              args=(motion2_name, motion2_kwargs))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    if uses_gait:
        exit_gait_and_stand()


def gait_march_with_arms(direction, steps):
    """步态行进配合摆臂：使用 wave=True 同步行走与手臂自然摆动。"""
    speeds = _GAIT_SPEED_MAP.get(direction, _GAIT_DEFAULT_SPEED)
    YanAPI.sync_do_motion_gait(
        speed_v=speeds["speed_v"],
        speed_h=speeds["speed_h"],
        steps=steps,
        period=1,
        wave=True,
    )
    exit_gait_and_stand()


def dance():
    # ── 初始化 ─────────────────────────────────────────────────
    YanAPI.yan_api_init(ROBOT_IP)

    # 复位站立
    print("执行动作: reset")
    YanAPI.sync_play_motion("reset")

    # 开场报幕
    YanAPI.sync_do_tts("大家好，我是 Yanshee，现在为大家带来第二支舞蹈，请欣赏！")

    # ── 第一段：热场暖身（约 25 s）──────────────────────────────
    YanAPI.set_robot_led("button", "blue", "breath")

    # 左右分别招手三次，营造友好开场
    print("[第一段] wave left × 3")
    YanAPI.sync_play_motion("wave", direction="left")
    YanAPI.sync_play_motion("wave", direction="left")
    YanAPI.sync_play_motion("wave", direction="left")

    print("[第一段] wave right × 3")
    YanAPI.sync_play_motion("wave", direction="right")
    YanAPI.sync_play_motion("wave", direction="right")
    YanAPI.sync_play_motion("wave", direction="right")

    print("[第一段] wave both × 2")
    YanAPI.sync_play_motion("wave", direction="both")
    YanAPI.sync_play_motion("wave", direction="both")

    # 左右点头
    print("[第一段] head left / right / forward")
    YanAPI.sync_play_motion("head", direction="left")
    YanAPI.sync_play_motion("head", direction="right")
    YanAPI.sync_play_motion("head", direction="forward")

    # ── 第二段：伸展律动（约 20 s）──────────────────────────────
    YanAPI.set_robot_led("button", "green", "blink")

    print("[第二段] stretch both × 2")
    YanAPI.sync_play_motion("stretch", direction="both")
    YanAPI.sync_play_motion("stretch", direction="both")

    print("[第二段] raise left → right → both")
    YanAPI.sync_play_motion("raise", direction="left")
    YanAPI.sync_play_motion("raise", direction="right")
    YanAPI.sync_play_motion("raise", direction="both")

    print("[第二段] come on left → right → both")
    YanAPI.sync_play_motion("come on", direction="left")
    YanAPI.sync_play_motion("come on", direction="right")
    YanAPI.sync_play_motion("come on", direction="both")

    # ── 第三段：侧步律动（约 20 s）──────────────────────────────
    YanAPI.set_robot_led("button", "yellow", "blink")

    # 左右侧步各 2 次，并穿插招手
    print("[第三段] walk left × 2 + wave right")
    YanAPI.sync_play_motion("walk", direction="left", repeat=2)
    YanAPI.sync_play_motion("wave", direction="right")

    print("[第三段] walk right × 2 + wave left")
    YanAPI.sync_play_motion("walk", direction="right", repeat=2)
    YanAPI.sync_play_motion("wave", direction="left")

    # 再来一轮侧步
    print("[第三段] walk left × 2 + wave both")
    YanAPI.sync_play_motion("walk", direction="left", repeat=2)
    YanAPI.sync_play_motion("wave", direction="both")

    print("[第三段] walk right × 2 + raise both")
    YanAPI.sync_play_motion("walk", direction="right", repeat=2)
    YanAPI.sync_play_motion("raise", direction="both")

    # ── 第四段：行进组合（约 20 s）──────────────────────────────
    YanAPI.set_robot_led("button", "purple", "breath")

    # 向前走配合摆臂，再向后退回
    print("[第四段] gait forward 6 steps with wave arms")
    gait_march_with_arms("forward", 6)

    print("[第四段] gait backward 6 steps with wave arms")
    gait_march_with_arms("backward", 6)

    # 转向侧走
    print("[第四段] gait left 4 steps with wave arms")
    gait_march_with_arms("left", 4)

    print("[第四段] gait right 4 steps with wave arms")
    gait_march_with_arms("right", 4)

    # ── 第五段：旋转展示（约 15 s）──────────────────────────────
    YanAPI.set_robot_led("button", "cyan", "breath")

    print("[第五段] turn around left × 2")
    YanAPI.sync_play_motion("turn around", direction="left")
    YanAPI.sync_play_motion("turn around", direction="left")

    print("[第五段] turn around right × 2")
    YanAPI.sync_play_motion("turn around", direction="right")
    YanAPI.sync_play_motion("turn around", direction="right")

    # 转圈后高举双臂庆祝
    print("[第五段] raise both + come on both")
    YanAPI.sync_play_motion("raise", direction="both")
    YanAPI.sync_play_motion("come on", direction="both")

    # ── 第六段：蹲起节拍（约 20 s）──────────────────────────────
    YanAPI.set_robot_led("button", "red", "blink")

    # 蹲下 → 站起 三个循环，模拟律动节拍
    for i in range(3):
        print(f"[第六段] crouch + reset (cycle {i + 1}/3)")
        YanAPI.sync_play_motion("crouch")
        YanAPI.sync_play_motion("reset")

    # 蹲起后左右挥手庆祝
    print("[第六段] wave left + wave right + wave both")
    YanAPI.sync_play_motion("wave", direction="left")
    YanAPI.sync_play_motion("wave", direction="right")
    YanAPI.sync_play_motion("wave", direction="both")

    # ── 第七段：并发高潮（约 20 s）──────────────────────────────
    YanAPI.set_robot_led("button", "white", "breath")

    # 举臂同时前进
    print("[第七段] raise both + walk forward × 2 (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 2})

    # 加油同时侧走左
    print("[第七段] come on both + walk left × 2 (parallel)")
    play_parallel("come on", {"direction": "both"},
                  "walk", {"direction": "left", "repeat": 2})

    # 伸展同时侧走右
    print("[第七段] stretch both + walk right × 2 (parallel)")
    play_parallel("stretch", {"direction": "both"},
                  "walk", {"direction": "right", "repeat": 2})

    # 举臂同时后退回位
    print("[第七段] raise both + walk backward × 2 (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "backward", "repeat": 2})

    # 并发段收尾：双手挥舞
    print("[第七段] wave both × 2")
    YanAPI.sync_play_motion("wave", direction="both")
    YanAPI.sync_play_motion("wave", direction="both")

    # ── 第八段：尾声谢幕（约 10 s）──────────────────────────────
    YanAPI.set_robot_led("button", "white", "blink")

    # 鞠躬致谢
    print("[第八段] bow")
    YanAPI.sync_play_motion("bow")
    YanAPI.sync_do_tts("感谢大家观看，第二支舞蹈表演结束，再见！")

    # 复位，灯光恢复常亮
    print("[第八段] reset")
    YanAPI.sync_play_motion("reset")
    YanAPI.set_robot_led("button", "white", "on")


if __name__ == "__main__":
    dance()
