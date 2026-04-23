import time
import os

from yanshee_robot_api import (
    RobotBuiltInMotion,
    RobotMotionDirection,
    RobotMotionSpeed,
    sync_play_motion,
    yan_api_init,
)


# Robot connection info.
ROBOT_IP = "192.168.1.163"
ROBOT_USER = os.getenv("YAN_ROBOT_USER", "pi")
ROBOT_PASSWORD = os.getenv("YAN_ROBOT_PASSWORD", "")


DANCE_STEPS = [
    (RobotBuiltInMotion.wave.value, RobotMotionDirection.left.value, RobotMotionSpeed.fast.value, 1, 0.2),
    (RobotBuiltInMotion.wave.value, RobotMotionDirection.right.value, RobotMotionSpeed.fast.value, 1, 0.2),
    (RobotBuiltInMotion.comeOn.value, RobotMotionDirection.none.value, RobotMotionSpeed.normal.value, 1, 0.2),
    (RobotBuiltInMotion.stretch.value, RobotMotionDirection.none.value, RobotMotionSpeed.normal.value, 1, 0.2),
    (RobotBuiltInMotion.turnAround.value, RobotMotionDirection.left.value, RobotMotionSpeed.normal.value, 1, 0.2),
    (RobotBuiltInMotion.handsUp.value, RobotMotionDirection.none.value, RobotMotionSpeed.fast.value, 1, 0.2),
    (RobotBuiltInMotion.bend.value, RobotMotionDirection.none.value, RobotMotionSpeed.normal.value, 1, 0.2),
    (RobotBuiltInMotion.head.value, RobotMotionDirection.none.value, RobotMotionSpeed.fast.value, 1, 0.2),
]


def run_one_minute_dance(duration_seconds: int = 60) -> bool:
    yan_api_init(ROBOT_IP)

    start = time.time()
    step_index = 0

    while time.time() - start < duration_seconds:
        name, direction, speed, repeat, pause = DANCE_STEPS[step_index % len(DANCE_STEPS)]
        ok = sync_play_motion(
            name=name,
            direction=direction,
            speed=speed,
            repeat=repeat,
            version="v1",
        )
        if not ok:
            print(f"Motion execution failed: {name}")
            return False

        remaining = duration_seconds - (time.time() - start)
        if remaining <= 0:
            break
        time.sleep(min(pause, remaining))
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
    success = run_one_minute_dance()
    if success:
        print("dance1 completed (about 60 seconds).")
