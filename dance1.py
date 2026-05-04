# coding=UTF-8
"""
舞蹈程序 —— 使用 YanAPI 控制 Yanshee 机器人跳舞
机器人地址：192.168.1.163  账号：pi  密码：raspberry
"""

import logging
import threading
import asyncio
import YanAPI
import time

ROBOT_IP = "192.168.1.203"

# 每次 walk 动作对应的步态步数（一次 walk 含左右各一步，共 2 个步态步）
_WALK_REPEAT_TO_STEPS = 2

# exit_gait_and_stand 中等待步态退出的最大轮询次数（每次 0.5 s，共 15 s 超时）
_GAIT_EXIT_MAX_POLLS = 30
# 步态退出完成的最低状态码（7 = 已退出步态就绪, 8 = 空闲）
_GAIT_EXIT_DONE_STATUS = 7

# 步态 API 的方向 → 速度映射（speed_v: 前后, speed_h: 左右）
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
        speeds = _GAIT_SPEED_MAP.get(direction, {"speed_v": 3, "speed_h": 0})
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
    # 等待步态退出完成（_GAIT_EXIT_DONE_STATUS: 7 = 已退出步态就绪, 8 = 空闲）
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


def leg_raise_march_with_arms():
    """抬腿静步走：使用步态 API 的 wave=True 参数，实现行走腿部动作与手臂
    自然摆动同步并发执行。

    向前走 6 步并摆臂，再向后退 6 步回到原位，最后退出步态模式恢复站立。
    """
    # 向前走 6 步，同时摆动手臂（wave=True 使手臂在步行中自然协调摆动）
    print("抬腿静步走: 向前走6步并自然摆臂 (gait wave=True)")
    YanAPI.sync_do_motion_gait(speed_v=3, steps=6, period=1, wave=True)

    # 向后退 6 步回位，同时摆动手臂
    print("抬腿静步走 收尾: 向后走6步回位并摆臂 (gait wave=True)")
    YanAPI.sync_do_motion_gait(speed_v=-3, steps=6, period=1, wave=True)

    # 退出步态模式，恢复站立，准备后续动作
    exit_gait_and_stand()


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
