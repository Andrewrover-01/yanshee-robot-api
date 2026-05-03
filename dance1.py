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

FALL_EULER_THRESHOLD = 65.0  # degrees; |euler-x| or |euler-y| > this => fallen
                              # 提高至 65° 以避免正常舞蹈动作（弯腰、走步等）被误判为摔倒
FALL_CONFIRM_SAMPLES = 3      # 连续读取次数；所有读数均超阈值才判定为摔倒（去抖动）
FALL_CONFIRM_DELAY = 0.1      # seconds between confirmation reads
FALL_RECOVER_WAIT = 6.0       # seconds to wait after issuing reset to let robot stand
                              # 延长至 6 s，给机器人足够时间从地面完成站起动作
FALL_MAX_RETRIES = 3          # maximum recovery attempts before giving up


def _read_euler():
    """从陀螺仪读取一次 Euler 角，返回 (pitch, roll) 元组。

    Yanshee 陀螺仪坐标约定：euler-x 为俯仰角（前后倾斜），euler-y 为横滚角（左右倾斜）。

    Returns:
        tuple[float, float]: (pitch, roll) 角度值，单位为度；读取失败时返回 (0.0, 0.0)。
    """
    try:
        res = YanAPI.get_sensors_gyro()
        gyro_list = res.get("data", {}).get("gyro", [])
        if gyro_list:
            sensor = gyro_list[0]
            return sensor.get("euler-x", 0.0), sensor.get("euler-y", 0.0)
    except Exception:
        pass
    return 0.0, 0.0


def is_robot_fallen() -> bool:
    """通过陀螺仪 Euler 角判断机器人是否摔倒。

    连续读取 FALL_CONFIRM_SAMPLES 次传感器数据，只有**所有**读数均显示
    俯仰角或横滚角超过 FALL_EULER_THRESHOLD 时才返回 True。
    这样既避免了单次传感器波动导致的误判，也避免了机器人在正常动作过程中
    因暂时倾斜而被误认为摔倒。

    Returns:
        bool: True 表示机器人已确认摔倒，False 表示正常站立或数据不足。
    """
    fallen_count = 0
    for i in range(FALL_CONFIRM_SAMPLES):
        pitch, roll = _read_euler()
        if abs(pitch) > FALL_EULER_THRESHOLD or abs(roll) > FALL_EULER_THRESHOLD:
            fallen_count += 1
        if i < FALL_CONFIRM_SAMPLES - 1:
            time.sleep(FALL_CONFIRM_DELAY)
    # 只有所有采样均超过阈值，才确认摔倒
    return fallen_count >= FALL_CONFIRM_SAMPLES


def recover_from_fall():
    """检测到机器人摔倒后尝试站起，最多重试 FALL_MAX_RETRIES 次。

    根据摔倒方向（euler-x 正值 → 前倒，负值 → 后倒）打印提示，
    之后调用 YanAPI.sync_play_motion("reset") 执行站起动作，
    并等待 FALL_RECOVER_WAIT 秒确认恢复。

    注意：此函数直接调用 YanAPI.sync_play_motion("reset") 而非 safe_play_motion，
    以避免与 safe_play_motion → recover_from_fall 之间产生无限递归。

    Returns:
        bool: True 表示恢复成功，False 表示多次尝试后仍未站起。
    """
    for attempt in range(1, FALL_MAX_RETRIES + 1):
        # 读取摔倒方向，辅助调试（仅在角度明显偏离时才推断方向）
        pitch, roll = _read_euler()
        if abs(pitch) > FALL_EULER_THRESHOLD or abs(roll) > FALL_EULER_THRESHOLD:
            if abs(pitch) >= abs(roll):
                direction = "前方" if pitch > 0 else "后方"
            else:
                direction = "左侧" if roll > 0 else "右侧"
        else:
            direction = "未知方向"
        print(f"检测到机器人向{direction}摔倒，尝试站起（第 {attempt} 次）...")

        YanAPI.sync_do_tts("检测到摔倒，正在站起")
        time.sleep(1.0)  # 等待机器人稳定后再发指令

        # 执行复位动作，让机器人尝试站起
        YanAPI.sync_play_motion("reset")  # 直接调用，避免循环递归
        time.sleep(FALL_RECOVER_WAIT)     # 等待站起动作完成

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
            if not recover_from_fall():
                print("步态执行中摔倒且无法站起，终止踏步动作。")
                return
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
