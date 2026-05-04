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
    try:
        YanAPI.exit_motion_gait()
    except Exception as e:
        logging.error("exit_motion_gait failed: %s", e)
    for _ in range(_GAIT_EXIT_MAX_POLLS):
        try:
            state = YanAPI.get_motion_gait_state()
            if state.get("data", {}).get("status", 0) >= _GAIT_EXIT_DONE_STATUS:
                break
        except Exception as e:
            logging.warning("get_motion_gait_state failed (retrying): %s", e)
        time.sleep(0.5)
    try:
        YanAPI.sync_play_motion("reset")
    except Exception as e:
        logging.error("reset after gait exit failed: %s", e)


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


def dance():
    # ── 初始化 ─────────────────────────────────────────────────
    YanAPI.yan_api_init(ROBOT_IP)

    # 复位站立
    print("执行动作: reset")
    YanAPI.sync_play_motion("reset")

    # 开场报幕
    YanAPI.sync_do_tts("大家好，我是 Yanshee，现在为大家带来第二支舞蹈，请欣赏！")

    # ── 第一段：热场暖身（手部招手 + 腿部同步行进，约 30 s）────────
    # 每个招手动作均与步态行进同时执行，实现手腿并发。
    YanAPI.set_robot_led("button", "blue", "breath")

    print("[第一段] wave left + walk forward (parallel) × 2")
    play_parallel("wave", {"direction": "left"},
                  "walk", {"direction": "forward", "repeat": 1})
    play_parallel("wave", {"direction": "left"},
                  "walk", {"direction": "forward", "repeat": 1})

    print("[第一段] wave right + walk backward (parallel) × 2")
    play_parallel("wave", {"direction": "right"},
                  "walk", {"direction": "backward", "repeat": 1})
    play_parallel("wave", {"direction": "right"},
                  "walk", {"direction": "backward", "repeat": 1})

    print("[第一段] wave both + walk left (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "left", "repeat": 1})

    print("[第一段] wave both + walk right (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "right", "repeat": 1})

    print("[第一段] head left + walk left (parallel)")
    play_parallel("head", {"direction": "left"},
                  "walk", {"direction": "left", "repeat": 1})

    print("[第一段] head right + walk right (parallel)")
    play_parallel("head", {"direction": "right"},
                  "walk", {"direction": "right", "repeat": 1})

    # ── 第二段：伸展律动（手部伸展 + 腿部同步行进，约 30 s）─────────
    YanAPI.set_robot_led("button", "green", "blink")

    print("[第二段] stretch both + walk forward (parallel) × 2")
    play_parallel("stretch", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})
    play_parallel("stretch", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})

    print("[第二段] raise left + walk left (parallel)")
    play_parallel("raise", {"direction": "left"},
                  "walk", {"direction": "left", "repeat": 1})

    print("[第二段] raise right + walk right (parallel)")
    play_parallel("raise", {"direction": "right"},
                  "walk", {"direction": "right", "repeat": 1})

    print("[第二段] raise both + walk forward (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})

    print("[第二段] come on left + walk backward (parallel)")
    play_parallel("come on", {"direction": "left"},
                  "walk", {"direction": "backward", "repeat": 1})

    print("[第二段] come on right + walk backward (parallel)")
    play_parallel("come on", {"direction": "right"},
                  "walk", {"direction": "backward", "repeat": 1})

    print("[第二段] come on both + walk forward (parallel)")
    play_parallel("come on", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})

    # ── 第三段：侧步律动（手部挥舞 + 腿部侧步同时，约 25 s）─────────
    YanAPI.set_robot_led("button", "yellow", "blink")

    print("[第三段] wave right + walk left × 2 (parallel) × 2")
    play_parallel("wave", {"direction": "right"},
                  "walk", {"direction": "left", "repeat": 2})
    play_parallel("wave", {"direction": "right"},
                  "walk", {"direction": "left", "repeat": 2})

    print("[第三段] wave left + walk right × 2 (parallel) × 2")
    play_parallel("wave", {"direction": "left"},
                  "walk", {"direction": "right", "repeat": 2})
    play_parallel("wave", {"direction": "left"},
                  "walk", {"direction": "right", "repeat": 2})

    print("[第三段] wave both + walk left × 2 (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "left", "repeat": 2})

    print("[第三段] raise both + walk right × 2 (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "right", "repeat": 2})

    # ── 第四段：行进组合（手部指定动作 + 腿部步态同时，约 25 s）──────
    YanAPI.set_robot_led("button", "purple", "breath")

    print("[第四段] raise both + walk forward × 3 (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 3})

    print("[第四段] stretch both + walk backward × 3 (parallel)")
    play_parallel("stretch", {"direction": "both"},
                  "walk", {"direction": "backward", "repeat": 3})

    print("[第四段] come on both + walk left × 2 (parallel)")
    play_parallel("come on", {"direction": "both"},
                  "walk", {"direction": "left", "repeat": 2})

    print("[第四段] wave both + walk right × 2 (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "right", "repeat": 2})

    # ── 第五段：旋转展示（约 20 s）───────────────────────────────
    # turn around 是全身协调动作（手臂与腿部一体旋转），保留为独立动作。
    YanAPI.set_robot_led("button", "cyan", "breath")

    print("[第五段] turn around left × 2")
    YanAPI.sync_play_motion("turn around", direction="left")
    YanAPI.sync_play_motion("turn around", direction="left")

    # 转圈后庆祝：手腿并发
    print("[第五段] raise both + walk forward (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})

    print("[第五段] come on both + walk backward (parallel)")
    play_parallel("come on", {"direction": "both"},
                  "walk", {"direction": "backward", "repeat": 1})

    print("[第五段] wave both + walk left (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "left", "repeat": 1})

    print("[第五段] stretch both + walk right (parallel)")
    play_parallel("stretch", {"direction": "both"},
                  "walk", {"direction": "right", "repeat": 1})

    # ── 第六段：蹲起节拍（约 25 s）───────────────────────────────
    # crouch/reset 为全身姿态动作；每次蹲起前后各加一次手腿并发律动。
    YanAPI.set_robot_led("button", "red", "blink")

    for i in range(3):
        print(f"[第六段] wave both + walk left (parallel) → crouch → reset (cycle {i + 1}/3)")
        play_parallel("wave", {"direction": "both"},
                      "walk", {"direction": "left", "repeat": 1})
        YanAPI.sync_play_motion("crouch")
        YanAPI.sync_play_motion("reset")

    # 收尾：举臂前进 → 挥手后退
    print("[第六段] raise both + walk forward (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 1})
    print("[第六段] wave both + walk backward (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "backward", "repeat": 1})

    # ── 第七段：并发高潮（约 30 s）───────────────────────────────
    YanAPI.set_robot_led("button", "white", "breath")

    print("[第七段] raise both + walk forward × 2 (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "forward", "repeat": 2})

    print("[第七段] come on both + walk left × 2 (parallel)")
    play_parallel("come on", {"direction": "both"},
                  "walk", {"direction": "left", "repeat": 2})

    print("[第七段] stretch both + walk right × 2 (parallel)")
    play_parallel("stretch", {"direction": "both"},
                  "walk", {"direction": "right", "repeat": 2})

    print("[第七段] raise both + walk backward × 2 (parallel)")
    play_parallel("raise", {"direction": "both"},
                  "walk", {"direction": "backward", "repeat": 2})

    print("[第七段] wave both + walk left × 2 (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "left", "repeat": 2})

    print("[第七段] wave both + walk right × 2 (parallel)")
    play_parallel("wave", {"direction": "both"},
                  "walk", {"direction": "right", "repeat": 2})

    # ── 第八段：尾声谢幕（约 10 s）───────────────────────────────
    # bow/reset 为全身姿态动作，保留为独立动作。
    YanAPI.set_robot_led("button", "white", "blink")

    print("[第八段] bow")
    YanAPI.sync_play_motion("bow")
    YanAPI.sync_do_tts("感谢大家观看，第二支舞蹈表演结束，再见！")

    print("[第八段] reset")
    YanAPI.sync_play_motion("reset")
    YanAPI.set_robot_led("button", "white", "on")


if __name__ == "__main__":
    dance()
