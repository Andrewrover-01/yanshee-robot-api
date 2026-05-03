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

FALL_EULER_THRESHOLD = 45.0  # degrees; |euler-x| or |euler-y| > this => fallen
FALL_RECOVER_WAIT = 3.0       # seconds to wait after issuing reset to let robot stand
FALL_MAX_RETRIES = 3          # maximum recovery attempts before giving up


def is_robot_fallen() -> bool:
    """通过陀螺仪 Euler 角判断机器人是否摔倒。

    Returns:
        bool: True 表示机器人已摔倒（俯仰角或横滚角超过阈值），False 表示正常站立。
    """
    try:
        res = YanAPI.get_sensors_gyro()
        gyro_list = res.get("data", {}).get("gyro", [])
        if not gyro_list:
            return False
        sensor = gyro_list[0]
        pitch = sensor.get("euler-x", 0.0)  # 俯仰角
        roll = sensor.get("euler-y", 0.0)   # 横滚角
        return abs(pitch) > FALL_EULER_THRESHOLD or abs(roll) > FALL_EULER_THRESHOLD
    except Exception:
        return False


def recover_from_fall():
    """检测到机器人摔倒后尝试站起，最多重试 FALL_MAX_RETRIES 次。

    Returns:
        bool: True 表示恢复成功，False 表示多次尝试后仍未站起。
    """
    for attempt in range(1, FALL_MAX_RETRIES + 1):
        print(f"检测到机器人摔倒，尝试站起（第 {attempt} 次）...")
        YanAPI.sync_do_tts("检测到摔倒，正在站起")
        time.sleep(1.0)  # 等待机器人稳定后再发指令
        YanAPI.sync_play_motion("reset")
        time.sleep(FALL_RECOVER_WAIT)
        if not is_robot_fallen():
            print("恢复站立成功，继续表演。")
            return True
        print(f"第 {attempt} 次站起尝试未成功，稍后重试...")
    print("多次尝试后仍无法站起，停止表演。")
    return False


def safe_play_motion(name: str, **kwargs) -> bool:
    """在执行动作前先检测是否摔倒，若摔倒则先恢复站立，再执行指定动作。

    Args:
        name: 动作名称，与 YanAPI.sync_play_motion 的 name 参数相同。
        **kwargs: 透传给 YanAPI.sync_play_motion 的其余参数（direction、repeat 等）。

    Returns:
        bool: True 表示动作执行成功，False 表示恢复失败或动作执行失败。
    """
    if is_robot_fallen():
        if not recover_from_fall():
            return False
    return YanAPI.sync_play_motion(name, **kwargs)


def march_in_place(steps: int = 4, period: int = 1):
    """抬腿静步走：原地抬腿踏步，speed_v=0、speed_h=0 保持不移动位置。

    执行前自动检测是否摔倒并尝试恢复。

    Args:
        steps: 踏步总步数（正整数）。
        period: 步态周期，取值 1~5，数值越大节奏越慢。
    """
    if is_robot_fallen():
        if not recover_from_fall():
            return
    YanAPI.control_motion_gait(speed_v=0, speed_h=0, steps=steps, period=period, wave=False)
    time.sleep(GAIT_POLL_INTERVAL)  # 等待步态任务启动
    elapsed = 0.0
    while elapsed < GAIT_TIMEOUT:
        if is_robot_fallen():
            YanAPI.exit_motion_gait()
            recover_from_fall()
            break
        res = YanAPI.get_motion_gait_state()
        status = res.get("data", {}).get("status", GAIT_STATUS_IDLE)
        if status in (GAIT_STATUS_EXITED, GAIT_STATUS_IDLE):
            break
        time.sleep(GAIT_POLL_INTERVAL)
        elapsed += GAIT_POLL_INTERVAL


def dance():
    # 初始化 API
    YanAPI.yan_api_init(ROBOT_IP)

    # 开启机器人内置摔倒管理
    YanAPI.set_robot_fall_management_state(True)

    # 复位站立
    print("执行动作: reset")
    safe_play_motion("reset")

    # 开场白
    YanAPI.sync_do_tts("大家好，我要开始跳舞了，请欣赏！")

    # ── 第一段：热身 ──────────────────────────────────────────
    # 眼灯呼吸蓝光，营造氛围
    YanAPI.set_robot_led("button", "blue", "breath")

    # 向左挥手 → 向右挥手 → 双手挥手
    print("执行动作: wave direction=left")
    safe_play_motion("wave", direction="left")
    print("执行动作: wave direction=right")
    safe_play_motion("wave", direction="right")
    print("执行动作: wave direction=both")
    safe_play_motion("wave", direction="both")

    # 腿部动作：向前走一步再向后退一步
    print("执行动作: walk direction=forward repeat=1")
    safe_play_motion("walk", direction="forward", repeat=1)
    print("执行动作: walk direction=backward repeat=1")
    safe_play_motion("walk", direction="backward", repeat=1)

    # 腿部动作：蹲下再站起
    print("执行动作: crouch")
    safe_play_motion("crouch")
    print("执行动作: reset")
    safe_play_motion("reset")

    # ── 第二段：伸展 ──────────────────────────────────────────
    YanAPI.set_robot_led("button", "green", "blink")

    # 双臂伸展
    print("执行动作: stretch direction=both")
    safe_play_motion("stretch", direction="both")
    # 左臂举起 → 右臂举起
    print("执行动作: raise direction=left")
    safe_play_motion("raise", direction="left")
    print("执行动作: raise direction=right")
    safe_play_motion("raise", direction="right")
    # 双臂加油
    print("执行动作: come on direction=both")
    safe_play_motion("come on", direction="both")
    # 侧步：向左一步再向右一步
    print("执行动作: walk direction=left repeat=1")
    safe_play_motion("walk", direction="left", repeat=1)
    print("执行动作: walk direction=right repeat=1")
    safe_play_motion("walk", direction="right", repeat=1)

    # ── 第三段：步伐 ──────────────────────────────────────────
    YanAPI.set_robot_led("button", "purple", "breath")

    # 向前走一步
    print("执行动作: walk direction=forward repeat=1")
    safe_play_motion("walk", direction="forward", repeat=1)
    # 向左转
    print("执行动作: turn around direction=left")
    safe_play_motion("turn around", direction="left")
    # 向前再走一步
    print("执行动作: walk direction=forward repeat=1")
    safe_play_motion("walk", direction="forward", repeat=1)
    # 向右挥手（原 turn around direction=right 会导致机器人倒地，改用稳定的 wave）
    print("执行动作: wave direction=right")
    safe_play_motion("wave", direction="right")
    # 向前走一步（原 walk direction=backward 会导致机器人倒地，改用稳定的 forward）
    print("执行动作: walk direction=forward repeat=1")
    safe_play_motion("walk", direction="forward", repeat=1)

    # ── 第四段：律动 ──────────────────────────────────────────
    YanAPI.set_robot_led("button", "yellow", "blink")

    # 向左挥手 → 向右挥手（原 bend 动作会导致机器人倒地，改用稳定的 wave）
    print("执行动作: wave direction=left")
    safe_play_motion("wave", direction="left")
    print("执行动作: wave direction=right")
    safe_play_motion("wave", direction="right")
    # 蹲下 → 站起（crouch 为蹲下动作）
    print("执行动作: crouch")
    safe_play_motion("crouch")
    print("执行动作: reset")
    safe_play_motion("reset")
    # 双臂加油 + 双臂举起
    print("执行动作: come on direction=both")
    safe_play_motion("come on", direction="both")
    print("执行动作: raise direction=both")
    safe_play_motion("raise", direction="both")
    # 侧步律动
    print("执行动作: walk direction=left repeat=2")
    safe_play_motion("walk", direction="left", repeat=2)
    print("执行动作: walk direction=right repeat=2")
    safe_play_motion("walk", direction="right", repeat=2)

    # 抬腿静步走：原地踏步 4 步，保持节奏
    print("执行动作: 抬腿静步走 steps=4 period=1")
    march_in_place(steps=4, period=1)

    # ── 第五段：头部律动 ──────────────────────────────────────
    YanAPI.set_robot_led("button", "cyan", "breath")

    print("执行动作: head direction=left")
    safe_play_motion("head", direction="left")
    print("执行动作: head direction=right")
    safe_play_motion("head", direction="right")
    print("执行动作: head direction=forward")
    safe_play_motion("head", direction="forward")

    # ── 第六段：综合展示 ──────────────────────────────────────
    YanAPI.set_robot_led("button", "red", "breath")

    # 双臂举起 + 向前走 + 挥手
    print("执行动作: raise direction=both")
    safe_play_motion("raise", direction="both")
    print("执行动作: walk direction=forward repeat=1")
    safe_play_motion("walk", direction="forward", repeat=1)
    print("执行动作: wave direction=both")
    safe_play_motion("wave", direction="both")
    # 转圈 + 加油 + 伸展
    print("执行动作: turn around direction=left")
    safe_play_motion("turn around", direction="left")
    print("执行动作: come on direction=both")
    safe_play_motion("come on", direction="both")
    print("执行动作: stretch direction=both")
    safe_play_motion("stretch", direction="both")
    print("执行动作: turn around direction=right")
    safe_play_motion("turn around", direction="right")
    # 蹲起收尾
    print("执行动作: crouch")
    safe_play_motion("crouch")
    print("执行动作: reset")
    safe_play_motion("reset")
    print("执行动作: wave direction=both")
    safe_play_motion("wave", direction="both")

    # ── 尾声：谢幕 ────────────────────────────────────────────
    YanAPI.set_robot_led("button", "white", "blink")

    # 鞠躬致谢
    print("执行动作: bow")
    safe_play_motion("bow")
    YanAPI.sync_do_tts("谢谢大家，表演结束！")

    # 复位，灯光恢复常亮白色
    print("执行动作: reset")
    safe_play_motion("reset")
    YanAPI.set_robot_led("button", "white", "on")


if __name__ == "__main__":
    dance()
