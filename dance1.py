import time
import os

from yanshee_robot_api import (
    RobotBuiltInMotion,
    RobotMotionDirection,
    RobotMotionSpeed,
    sync_play_motion,
    yan_api_init,
)


# Robot API endpoint IP.
ROBOT_IP = os.getenv("YAN_ROBOT_IP", "192.168.1.163")
DEFAULT_PAUSE_SECONDS = 0.2


DANCE_STEPS = [
    (RobotBuiltInMotion.wave.value, RobotMotionDirection.left.value, RobotMotionSpeed.fast.value, 1, DEFAULT_PAUSE_SECONDS),
    (RobotBuiltInMotion.wave.value, RobotMotionDirection.right.value, RobotMotionSpeed.fast.value, 1, DEFAULT_PAUSE_SECONDS),
    (RobotBuiltInMotion.comeOn.value, RobotMotionDirection.none.value, RobotMotionSpeed.normal.value, 1, DEFAULT_PAUSE_SECONDS),
    (RobotBuiltInMotion.stretch.value, RobotMotionDirection.none.value, RobotMotionSpeed.normal.value, 1, DEFAULT_PAUSE_SECONDS),
    (RobotBuiltInMotion.turnAround.value, RobotMotionDirection.left.value, RobotMotionSpeed.normal.value, 1, DEFAULT_PAUSE_SECONDS),
    (RobotBuiltInMotion.handsUp.value, RobotMotionDirection.none.value, RobotMotionSpeed.fast.value, 1, DEFAULT_PAUSE_SECONDS),
    (RobotBuiltInMotion.bend.value, RobotMotionDirection.none.value, RobotMotionSpeed.normal.value, 1, DEFAULT_PAUSE_SECONDS),
    (RobotBuiltInMotion.head.value, RobotMotionDirection.none.value, RobotMotionSpeed.fast.value, 1, DEFAULT_PAUSE_SECONDS),
]


def run_timed_dance(duration_seconds: int = 60) -> bool:
    """Initialize robot API and run dance motions for the specified duration."""
    try:
        yan_api_init(ROBOT_IP)
    except Exception as exc:
        print(f"Robot initialization failed: {exc}")
        return False

    start = time.time()
    step_index = 0

    while time.time() - start < duration_seconds:
        motion_name, direction, speed, repeat, pause = DANCE_STEPS[step_index % len(DANCE_STEPS)]
        ok = sync_play_motion(
            name=motion_name,
            direction=direction,
            speed=speed,
            repeat=repeat,
            version="v1",
        )
        if not ok:
            print(f"Motion execution failed: {motion_name}")
            return False

        remaining_after_motion = duration_seconds - (time.time() - start)
        if remaining_after_motion <= 0:
            break
        time.sleep(min(pause, remaining_after_motion))
        step_index += 1

    reset_ok = sync_play_motion(
        name=RobotBuiltInMotion.reset.value,
        direction=RobotMotionDirection.none.value,
        speed=RobotMotionSpeed.normal.value,
        repeat=1,
        version="v1",
    )
    if not reset_ok:
        print("Warning: reset motion failed.")
    return True


if __name__ == "__main__":
    run_seconds = 60
    success = run_timed_dance(run_seconds)
    if success:
        print(f"dance1 completed ({run_seconds} seconds).")
    else:
        print("dance1 failed.")
