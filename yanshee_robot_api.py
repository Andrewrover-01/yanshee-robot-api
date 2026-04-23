# coding=UTF-8
from io import StringIO
import sys
import requests
import json
import time
import asyncio
from typing import List, Dict
import logging
import nest_asyncio
from socket import *
import struct
import subprocess
import re
import os
import cv2
from multiprocessing import Process
from enum import Enum, unique

basic_url = "http://127.0.0.1:9090/v1/"
ip = "127.0.0.1"
headers = {'Content-Type': 'application/json'}
nest_asyncio.apply()


@unique
class ChargingState(Enum):
    Uncharged = 0
    Charging = 1


@unique
class RobotLanguage(Enum):
    zh = "zh"
    en = "en"


@unique
class RobotButtonLedColor(Enum):
    white = "white"
    red = "red"
    green = "green"
    blue = "blue"
    yellow = "yellow"
    purple = "purple"
    cyan = "cyan"


@unique
class RobotButtonLedMode(Enum):
    on = "on"
    off = "off"
    blink = "blink"
    breath = "breath"


@unique
class RobotEyeLedColor(Enum):
    red = "red"
    green = "green"
    blue = "blue"


@unique
class RobotEyeLedMode(Enum):
    on = "on"
    off = "off"
    blink = "blink"


@unique
class RobotBuiltInMotion(Enum):
    reset = "reset"
    handsUp = "raise"
    crouch = "crouch"
    comeOn = "come on"
    stretch = "stretch"
    wave = "wave"
    bend = "bend"
    walk = "walk"
    turnAround = "turn around"
    head = "head"
    bow = "bow"


@unique
class RobotMotionDirection(Enum):
    none = ""
    left = "left"
    right = "right"
    both = "both"
    forward = "forward"
    backward = "backward"


@unique
class RobotMotionSpeed(Enum):
    verySlow = "very slow"
    slow = "slow"
    normal = "normal"
    fast = "fast"
    veryFast = "very fast"


@unique
class RobotFaceRecognitionType(Enum):
    tracking = "tracking"
    recognition = "recognition"
    quantity = "quantity"
    age_group = "age_group"
    gender = "gender"
    age = "age"
    expression = "expression"
    mask = "mask"
    glass = "glass"


@unique
class RobotJointType(Enum):
    No1 = "RightShoulderRoll"
    No2 = "RightShoulderFlex"
    No3 = "RightElbowFlex"
    No4 = "LeftShoulderRoll"
    No5 = "LeftShoulderFlex"
    No6 = "LeftElbowFlex"
    No7 = "RightHipLR"
    No8 = "RightHipFB"
    No9 = "RightKneeFlex"
    No10 = "RightAnkleFB"
    No11 = "RightAnkleUD"
    No12 = "LeftHipLR"
    No13 = "LeftHipFB"
    No14 = "LeftKneeFlex"
    No15 = "LeftAnkleFB"
    No16 = "LeftAnkleUD"
    No17 = "NeckLR"


class RobotJointInfo():
    def __init__(self, jointType, angel: int):
        if isinstance(jointType, str):
            strlist = jointType.split('_')
            newStrList = []
            newStr = ""
            if len(strlist) == 1:
                newStr = strlist[0]
            else:
                for strItem in strlist:
                    newStrList.append(strItem.title())
                for strItem in newStrList:
                    newStr = newStr + strItem
            self.jointType = RobotJointType(newStr)
        elif isinstance(jointType, RobotJointType):
            self.jointType = jointType
        else:
            raise ValueError("jointType value error")
        self.angel = angel


class RobotActionFrame():
    def __init__(self, actionFrame: Dict):
        self._actionFrame = {}
        for key, value in actionFrame.items():
            jointInfo = RobotJointInfo(key, value)
            self._actionFrame[jointInfo.jointType.value] = jointInfo

    @property
    def interfaceDict(self):
        ret = {}
        for key, value in self._actionFrame.items():
            ret[key] = value.angel
        return ret

    def __getitem__(self, key):
        if not isinstance(key, str):
            return -1
        jointInfo = self._actionFrame.get(key)
        if not jointInfo:
            return -1
        return jointInfo.angel

    def addOrUpdateJointInfo(self, jointInfo: RobotJointInfo):
        self._actionFrame[jointInfo.jointType.value] = jointInfo

    def delJointInfo(self, jointType: RobotJointType):
        self._actionFrame.pop(jointType.value)


class RobotBatteryInfo():
    def __init__(self, data=None):
        self._batteryPercentage = 0
        self._chargingState = 0
        self._voltage = 0
        if data:
            self.__dict__ = data
            self._batteryPercentage = data["percent"]
            self._chargingState = data["charging"]
            self._voltage = data["voltage"]

    @property
    def batteryPercentage(self):
        return self._batteryPercentage

    @property
    def chargingState(self):
        return self._chargingState

    @property
    def voltage(self):
        return self._voltage


class RobotVersionInfo():
    def __init__(self, data=None):
        self._coreVersion = ""
        self._servoVersion = ""
        self._sn = ""
        if data:
            self.updateWithData(data)

    def updateWithData(self, data: dict):
        if "core" in data:
            self._coreVersion = data["core"]
        if "servo" in data:
            self._servoVersion = data["servo"]
        if "sn" in data:
            self._sn = data["sn"]

    @property
    def core(self):
        return self._coreVersion

    @property
    def servo(self):
        return self._servoVersion

    @property
    def sn(self):
        return self._sn


class RobotLedInfo():
    def __init__(self, data=None):
        self._buttonLedColor = ""
        self._buttonLedMode = ""
        self._eyeLedColor = ""
        self._eyeLedMode = ""
        if not data:
            return
        for item in data:
            if item["type"] == "button":
                self._buttonLedColor = item["color"]
                self._buttonLedMode = item["mode"]
            if item["type"] == "camera":
                self._eyeLedColor = item["color"]
                self._eyeLedMode = item["mode"]

    @property
    def buttonLedColor(self):
        return self._buttonLedColor

    @property
    def buttonLedMode(self):
        return self._buttonLedMode

    @property
    def eyeLedColor(self):
        return self._eyeLedColor

    @property
    def eyeLedMode(self):
        return self._eyeLedMode


class RobotAsrResult():
    def __init__(self, data=None):
        self._question = ""
        self._answer = ""
        if data:
            self._question = data["intent"]["text"]
            self._answer = data["intent"]["answer"]["text"]

    @property
    def retDict(self):
        return {"question": self._question, "answer": self._answer}


async def __wait_result(timestamp, getFuc):
    while True:
        res = getFuc()
        if timestamp == res["timestamp"]:
            status = res["status"]
            if status == "idle":
                return res
            else:
                await asyncio.sleep(1)


async def __wait_result_QR(getFuc, timeOut, checkStream=False):
    timeCount = 0
    beginTime = time.time()
    global PqrStream
    while True:
        res = getFuc()
        if checkStream and not (PqrStream is None) and not PqrStream.is_alive():
            stop_QR_code_recognition()
            return res
        nowTime = time.time()
        if timeOut > 0 and int(nowTime - beginTime) > timeOut:
            stop_QR_code_recognition()
            return res
        if ("idle" == res["status"]) or len(res["data"]["contents"]) != 0:
            if not (PqrStream is None):
                PqrStream.terminate()
                PqrStream = None
            return res
        else:
            timeCount += 1
            await asyncio.sleep(1)


async def __wait_result_common(timestamp, getFuc, args=()):
    while True:
        res = getFuc(*args)
        if timestamp == res["timestamp"]:
            status = res["status"]
            if status == "idle":
                return res
            else:
                await asyncio.sleep(1)


async def __wait_result_music(name, start_time, getFuc):
    while True:
        res = getFuc()
        if res['data']['name'] == "":
            return res
        if res['data']['status'] == 'run' and res['data']['name'] == name:
            await asyncio.sleep(1)
        else:
            return res


async def __wait_result_motion(name, start_time, getFuc):
    while True:
        res = getFuc()
        if res['data']['name'] == "":
            return res
        if res['data']['status'] == 'run' and start_time == res['data']['timestamp']:
            await asyncio.sleep(1)
        else:
            return res


async def __wait_result_layer_motion(name, start_time, getFuc):
    while True:
        res = getFuc()
        find = False
        for i in range(len(res["data"])):
            if res['data'][i]['name'] == str(name + ".layers"):
                if res['data'][i]['status'] == 'run' and start_time == res['data'][i]['timestamp']:
                    await asyncio.sleep(1)
                else:
                    return res
        if find == False:
            return res


async def __wait_result_by_time(time):
    await asyncio.sleep(time)


async def __wait_result_color(type, color, mode, getFuc):
    while True:
        res = getFuc()
        for item in res['data']:
            if item['type'] == type and item['color'] == color and item['mode'] == mode:
                return res
        await asyncio.sleep(1)


async def __wait_result_gait(start_time, type, getFuc):
    while True:
        res = getFuc()
        if res['data']['timestamp'] == start_time:
            if type == "start":
                if 0 <= res['data']['status'] <= 2:
                    await asyncio.sleep(1)
                else:
                    return res
        elif res['data']['timestamp'] > start_time:
            return res


def __resIsSuccess(res):
    if not isinstance(res, Dict):
        return False
    if "code" not in res:
        return False
    return res["code"] == 0


# ──────────────────────────────────────────────────────────────
# Part 4: Basic device API
# ──────────────────────────────────────────────────────────────

def get_ip_address(ifname):
    s = socket(AF_INET, SOCK_DGRAM)
    return inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])


def yan_api_init(robot_ip: str):
    global basic_url
    global ip
    basic_url = "http://" + robot_ip + ":9090/v1/"
    ip = robot_ip
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s %(funcName)s %(levelname)s %(message)s",
        datefmt='%Y-%m-%d  %H:%M:%S %a',
    )


def get_robot_battery_info():
    devices_url = basic_url + "devices/battery"
    response = requests.get(url=devices_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_robot_battery_value():
    devices_url = basic_url + "devices/battery"
    response = requests.get(url=devices_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    if __resIsSuccess(res):
        batteryInfo = RobotBatteryInfo(res["data"])
        return batteryInfo.batteryPercentage
    else:
        return -1


def get_robot_fall_management_state():
    devices_url = basic_url + "devices/fall_management"
    response = requests.get(url=devices_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_robot_fall_management_state(enable: bool):
    devices_url = basic_url + "devices/fall_management"
    param = {"enable": enable}
    json_data = json.dumps(param)
    response = requests.put(url=devices_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_robot_language():
    languages_url = basic_url + "devices/languages"
    response = requests.get(url=languages_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_robot_language(language: str):
    languages_url = basic_url + "devices/languages"
    param = {"language": language}
    json_data = json.dumps(param)
    response = requests.put(url=languages_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def __get_robot_led_info():
    led_url = basic_url + "devices/led"
    response = requests.get(url=led_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    if __resIsSuccess(res):
        ledInfo = RobotLedInfo(res["data"])
        return ledInfo
    else:
        return RobotLedInfo()


def get_button_led_color_value():
    return __get_robot_led_info().buttonLedColor


def get_button_led_mode_value():
    return __get_robot_led_info().buttonLedMode


def get_eye_led_color_value():
    return __get_robot_led_info().eyeLedColor


def get_eye_led_mode_value():
    return __get_robot_led_info().eyeLedMode


def get_robot_led():
    led_url = basic_url + "devices/led"
    response = requests.get(url=led_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_robot_led(type: str, color: str, mode: str):
    led_url = basic_url + "devices/led"
    param = {"type": type, "color": color, "mode": mode}
    json_data = json.dumps(param)
    response = requests.put(url=led_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def sync_set_led(type: str, color: str, mode: str):
    res = set_robot_led(type=type, color=color, mode=mode)
    if res['code'] != 0:
        return False
    coroutine = __wait_result_color(type=type, color=color, mode=mode, getFuc=get_robot_led)
    loop = asyncio.get_event_loop()
    tasks = loop.create_task(coroutine)
    loop.run_until_complete(tasks)
    return True


def get_robot_version_info_value(type: str):
    version_url = basic_url + "devices/versions"
    params = {'type': type}
    response = requests.get(url=version_url, headers=headers, params=params)
    res = json.loads(str(response.content.decode("utf-8")))
    if __resIsSuccess(res):
        versionInfo = RobotVersionInfo(res["data"])
        return getattr(versionInfo, type)
    else:
        return ""


def get_robot_version_info(type: str):
    version_url = basic_url + "devices/versions"
    params = {'type': type}
    response = requests.get(url=version_url, headers=headers, params=params)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_robot_mode():
    request_url = basic_url + "devices/mode"
    response = requests.get(url=request_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_robot_volume_value():
    volume_url = basic_url + "devices/volume"
    response = requests.get(url=volume_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    if not __resIsSuccess(res):
        return -1
    return res["data"]["volume"] if isinstance(res["data"]["volume"], int) else -1


def get_robot_volume():
    volume_url = basic_url + "devices/volume"
    response = requests.get(url=volume_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_robot_volume_value(volume: int):
    volume_url = basic_url + "devices/volume"
    param = {"volume": volume}
    json_data = json.dumps(param)
    response = requests.put(url=volume_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return __resIsSuccess(res)


def set_robot_volume(volume: int):
    volume_url = basic_url + "devices/volume"
    param = {"volume": volume}
    json_data = json.dumps(param)
    response = requests.put(url=volume_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


# ──────────────────────────────────────────────────────────────
# Part 5: Music and media control
# ──────────────────────────────────────────────────────────────

def delete_media_music(name: str):
    music_url = basic_url + "media/music"
    param = {"name": name}
    json_data = json.dumps(param)
    response = requests.delete(url=music_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_media_music_state():
    music_url = basic_url + "media/music"
    response = requests.get(url=music_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def upload_media_music(filePath: str):
    music_url = basic_url + "media/music"
    upload_headers = {'Authorization': 'multipart/form-data'}
    files = {'file': open(filePath, 'rb')}
    response = requests.post(url=music_url, files=files, headers=upload_headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def start_play_music(name: str = ""):
    return __control_media_music(operation='start', name=name)


def stop_play_music():
    return __control_media_music(operation='stop')


def __control_media_music(operation: str, name: str = ""):
    music_url = basic_url + "media/music"
    param = {"operation": operation}
    if len(name) > 0:
        param["name"] = name
    json_data = json.dumps(param)
    response = requests.put(url=music_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_media_music_list():
    music_url = basic_url + "media/music/list"
    response = requests.get(url=music_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def sync_play_music(name: str = ""):
    res = start_play_music(name)
    if res['code'] != 0:
        return False
    coroutine = __wait_result_music(name=name, start_time=None, getFuc=get_media_music_state)
    loop = asyncio.get_event_loop()
    tasks = loop.create_task(coroutine)
    loop.run_until_complete(tasks)
    return True


# ──────────────────────────────────────────────────────────────
# Part 6: Motion file control (dance core)
# ──────────────────────────────────────────────────────────────

def delete_motion(name: str):
    motions_url = basic_url + "motions"
    param = {"name": name}
    json_data = json.dumps(param)
    response = requests.delete(url=motions_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_current_motion_play_state():
    motions_url = basic_url + "motions"
    response = requests.get(url=motions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_current_layer_motion_play_state():
    motions_url = basic_url + "motions/all"
    response = requests.get(url=motions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def __control_motion_play_state(operation: str = "start", name: str = "reset", direction: str = "", speed: str = "normal", repeat: int = 1, timestamp: int = 0, version: str = "v1"):
    motion_url = basic_url + "motions"
    param = {"operation": operation, "motion": {"name": name, "repeat": repeat, "speed": speed}, "timestamp": timestamp, "version": version}
    if len(direction) != 0:
        param["motion"]["direction"] = direction
    json_data = json.dumps(param)
    response = requests.put(url=motion_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def start_play_motion(name: str = "reset", direction: str = "", speed: str = "normal", repeat: int = 1, timestamp: int = 0, version: str = "v1"):
    return __control_motion_play_state(operation="start", name=name, direction=direction, speed=speed, repeat=repeat, timestamp=timestamp, version=version)


def pause_play_motion(name: str = "", timestamp: int = 0, version: str = "v1"):
    return __control_motion_play_state(name=name, operation="pause", timestamp=timestamp, version=version)


def resume_play_motion(name: str = "", timestamp: int = 0, version: str = "v1"):
    return __control_motion_play_state(name=name, operation="resume", timestamp=timestamp, version=version)


def stop_play_motion(name: str = "", timestamp: int = 0, version: str = "v1"):
    return __control_motion_play_state(name=name, operation="stop", timestamp=timestamp, version=version)


def sync_play_motion(name: str = "reset", direction: str = "", speed: str = "normal", repeat: int = 1, version: str = "v1"):
    t = int(time.time() * 1000)
    res = start_play_motion(direction=direction, speed=speed, repeat=repeat, name=name, timestamp=t, version=version)
    if res['code'] != 0:
        return False
    if version == "v1":
        coroutine = __wait_result_motion(name=name, start_time=t, getFuc=get_current_motion_play_state)
    elif version == "v2":
        coroutine = __wait_result_layer_motion(name=name, start_time=t, getFuc=get_current_layer_motion_play_state)
    loop = asyncio.get_event_loop()
    tasks = loop.create_task(coroutine)
    loop.run_until_complete(tasks)
    return True


def upload_motion(filePath: str):
    motions_url = basic_url + "motions"
    upload_headers = {'Authorization': 'multipart/form-data'}
    files = {'file': open(filePath, 'rb')}
    response = requests.post(url=motions_url, files=files, headers=upload_headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_motion_list_value():
    motions_url = basic_url + "motions/list"
    response = requests.get(url=motions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    if not __resIsSuccess(res):
        return []
    motion = []
    for item in res['data']['system_hts_motions']:
        motion.append(item['name'].rsplit('.', 1)[0])
    for item in res['data']['system_layers_motions']:
        motion.append(item['name'].rsplit('.', 1)[0])
    for item in res['data']['user_hts_motions']:
        motion.append(item['name'].rsplit('.', 1)[0])
    for item in res['data']['user_layers_motions']:
        motion.append(item['name'].rsplit('.', 1)[0])
    return motion


def get_motion_list():
    motions_url = basic_url + "motions/list"
    response = requests.get(url=motions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


# ──────────────────────────────────────────────────────────────
# Part 7: Gait & servo direct control
# ──────────────────────────────────────────────────────────────

def control_motion_gait(speed_v: int = 0, speed_h: int = 0, steps: int = 0, period: int = 1, wave: bool = False):
    motion_url = basic_url + "motions/gait"
    timestamp = int(time.time() * 1000)
    param = {
        "speed_v": speed_v,
        "speed_h": speed_h,
        "steps": steps,
        "period": period,
        "timestamp": timestamp,
        "wave": wave
    }
    json_data = json.dumps(param)
    response = requests.put(url=motion_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_motion_gait_state():
    motion_url = basic_url + "motions/gait"
    response = requests.get(url=motion_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def exit_motion_gait():
    motion_url = basic_url + "motions/gait"
    payload = {"timestamp": 0}
    response = requests.delete(url=motion_url, headers=headers, data=json.dumps(payload))
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def sync_do_motion_gait(speed_v: int = 0, speed_h: int = 0, steps: int = 0, period: int = 1, wave: bool = False):
    t = int(time.time() * 1000)
    res = control_motion_gait(speed_v=speed_v, speed_h=speed_h, steps=steps, period=period, wave=wave)
    if res['code'] != 0:
        return False
    coroutine = __wait_result_gait(start_time=t, type='start', getFuc=get_motion_gait_state)
    loop = asyncio.get_event_loop()
    tasks = loop.create_task(coroutine)
    loop.run_until_complete(tasks)
    return True


def get_servo_angle_value(name: str):
    servos_url = basic_url + "servos/angles"
    params = {'names': [name]}
    response = requests.get(url=servos_url, headers=headers, params=params)
    res = json.loads(str(response.content.decode("utf-8")))
    if not __resIsSuccess(res):
        return -1
    values = res["data"].popitem()
    return values[1]


def get_servos_angles(names: List[str]):
    servos_url = basic_url + "servos/angles"
    params = {'names': names}
    response = requests.get(url=servos_url, headers=headers, params=params)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_servos_angles(angles: Dict[str, int], runtime: int = 200):
    servos_url = basic_url + "servos/angles"
    param = {"angles": angles, "runtime": runtime}
    json_data = json.dumps(param)
    response = requests.put(url=servos_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_servos_angles_layers(data: Dict[str, Dict[int, int]]):
    servos_url = basic_url + "servos/angles/layers"
    param = {"data": data}
    json_data = json.dumps(param)
    response = requests.put(url=servos_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def sync_set_servo_rotate(angles: Dict[str, int], runtime: int = 200):
    res = set_servos_angles(angles=angles, runtime=runtime)
    if res['code'] != 0:
        return res
    coroutine = __wait_result_by_time(runtime / 1000)
    loop = asyncio.get_event_loop()
    tasks = loop.create_task(coroutine)
    loop.run_until_complete(tasks)
    return res


def get_servos_mode(names: List[str]):
    servos_url = basic_url + "servos/mode"
    params = {"names": names}
    response = requests.get(url=servos_url, headers=headers, params=params)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_servos_mode(mode: str, servos: List[str]):
    servos_url = basic_url + "servos/mode"
    param = {"mode": mode, "servos": []}
    for i in range(len(servos)):
        param["servos"].append({"name": servos[i]})
    json_data = json.dumps(param)
    response = requests.put(url=servos_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


# ──────────────────────────────────────────────────────────────
# Part 8: Sensor reading
# ──────────────────────────────────────────────────────────────

def sensor_calibration(id: int):
    __set_sensors(operation="Calibrate", type="gyro", id=id)


def __set_sensors(operation: str, id: int, type: str, value: int = 0):
    sensors_url = basic_url + "sensors"
    param = {"operation": operation, "sensor":
             {"id": id, "type": type, "value": value}}
    json_data = json.dumps(param)
    response = requests.put(url=sensors_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_sensors_list_value():
    sensor_url = basic_url + "sensors/list"
    response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    if not __resIsSuccess(res):
        return []
    sensors = res["data"]["sensors"]
    sensorsName = []
    for sensor in sensors:
        sensorName = sensor.get("type")
        if sensorName:
            sensorsName.append(sensorName)
    return sensorsName


def get_sensors_list():
    sensor_url = basic_url + "sensors/list"
    response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_sensors_environment_value():
    res = get_sensors_environment()
    if not __resIsSuccess(res):
        return "获取环境传感器值失败！"
    values = res["data"]["environment"]
    if len(values) == 0:
        return "没有连接到传感器！"
    return values[0]


def get_sensors_environment():
    sensor_url = basic_url + "sensors/environment"
    response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_sensors_gyro():
    sensor_url = basic_url + "sensors/gyro"
    response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_sensors_infrared_value():
    res = get_sensors_infrared()
    if not __resIsSuccess(res):
        return "获取红外距离传感器值失败！"
    values = res["data"]["infrared"]
    if len(values) == 0:
        return "没有连接到传感器！"
    return values[0]["value"]


def get_sensors_infrared(id: List[int] = None, slot: List[int] = None):
    sensor_url = basic_url + "sensors/infrared"
    if (id is not None) and (slot is None):
        params = {"id": id}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is None) and (slot is not None):
        params = {"slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is not None) and (slot is not None):
        params = {"id": id, "slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    else:
        response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_sensors_pressure_value():
    res = get_sensors_pressure()
    if not __resIsSuccess(res):
        return "获取压力传感器值失败！"
    values = res["data"]["pressure"]
    if len(values) == 0:
        return "没有连接到传感器！"
    return values[0]["value"]


def get_sensors_pressure(id: List[int] = None, slot: List[int] = None):
    sensor_url = basic_url + "sensors/pressure"
    if (id is not None) and (slot is None):
        params = {"id": id}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is None) and (slot is not None):
        params = {"slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is not None) and (slot is not None):
        params = {"id": id, "slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    else:
        response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_sensors_touch_value():
    res = get_sensors_touch()
    if not __resIsSuccess(res):
        return "获取压力传感器值失败！"
    values = res["data"]["touch"]
    if len(values) == 0:
        return "没有连接到传感器！"
    return values[0]["value"]


def get_sensors_touch(id: int = None, slot: List[int] = None):
    sensor_url = basic_url + "sensors/touch"
    if (id is not None) and (slot is None):
        params = {"id": id}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is None) and (slot is not None):
        params = {"slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is not None) and (slot is not None):
        params = {"id": id, "slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    else:
        response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_sensors_ultrasonic_value():
    res = get_sensors_ultrasonic()
    if not __resIsSuccess(res):
        return "获取超声传感器值失败！"
    values = res["data"]["ultrasonic"]
    if len(values) == 0:
        return "没有连接到传感器！"
    return values[0]["value"]


def get_sensors_ultrasonic(id=None, slot=None):
    sensor_url = basic_url + "sensors/ultrasonic"
    if (id is not None) and (slot is None):
        params = {"id": id}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is None) and (slot is not None):
        params = {"slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    elif (id is not None) and (slot is not None):
        params = {"id": id, "slot": slot}
        response = requests.get(url=sensor_url, headers=headers, params=params)
    else:
        response = requests.get(url=sensor_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


# ──────────────────────────────────────────────────────────────
# Part 9: Vision recognition and photo management
# ──────────────────────────────────────────────────────────────

def start_color_recognition(timestamp: int = 0):
    """开始颜色识别"""
    return __control_visual_task(option='color', type="color_detect", operation='start', timestamp=timestamp)


def stop_color_recognition(timestamp: int = 0):
    """停止颜色识别"""
    return __control_visual_task(option='color', type="color_detect", operation='stop', timestamp=timestamp)


def sync_do_color_recognition():
    """执行颜色识别,识别完成后返回"""
    timestamp = int(time.time())
    res = start_color_recognition(timestamp)
    if res['code'] != 0:
        logging.error("do color recognition failed error code = %d msg = %s",
                      res.get("code", -1), res.get("msg", "unknow error"))
        return res
    coroutine = __wait_result_common(timestamp=timestamp, getFuc=get_visual_task_result,
                                     args=("color", "color_detect"))
    loop = asyncio.get_event_loop()
    tasks = loop.create_task(coroutine)
    loop.run_until_complete(tasks)
    return tasks.result()


def start_object_recognition(timestamp: int = 0):
    """开始物体识别"""
    return __control_visual_task(option='object', type="recognition", operation='start', timestamp=timestamp)


def stop_object_recognition(timestamp: int = 0):
    """停止物体识别"""
    return __control_visual_task(option='object', type="recognition", operation='stop', timestamp=timestamp)


def sync_do_object_recognition():
    """执行物体识别,识别完成后返回"""
    timestamp = int(time.time())
    res = start_object_recognition(timestamp)
    if res['code'] != 0:
        logging.error("do object recognition failed error code = %d msg = %s",
                      res.get("code", -1), res.get("msg", "unknow error"))
        return res
    coroutine = __wait_result_common(timestamp=timestamp, getFuc=get_visual_task_result,
                                     args=("object", "recognition"))
    loop = asyncio.get_event_loop()
    tasks = loop.create_task(coroutine)
    loop.run_until_complete(tasks)
    return tasks.result()


def do_face_entry(name: str):
    """进行人脸录入"""
    res = take_vision_photo()
    if not __resIsSuccess(res):
        logging.error("do face entry failed error code = %d msg = %s",
                      res.get("code", -1), res.get("msg", "unknow error"))
        return False
    path = "./"
    get_vision_photo(res["data"]["name"], path)
    photo = path + res["data"]["name"]
    photo_name = res["data"]["name"]
    res = upload_vision_photo_sample(photo)
    if os.path.exists(photo) and os.path.isfile(photo):
        os.remove(photo)
    if not __resIsSuccess(res):
        logging.error("do face entry failed error code = %d msg = %s",
                      res.get("code", -1), res.get("msg", "unknow error"))
        return False
    res = set_vision_tag([photo_name], name)
    if not __resIsSuccess(res):
        logging.error("do face entry failed error code = %d msg = %s",
                      res.get("code", -1), res.get("msg", "unknow error"))
        return False
    return True


def delete_vision_photo(name: str):
    """删除指定名称的图片"""
    visions_url = basic_url + "visions/photos"
    param = {"name": name}
    json_data = json.dumps(param)
    response = requests.delete(url=visions_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_vision_photo(name: str, savePath: str = "./"):
    """获取指定名称的照片"""
    visions_url = basic_url + "visions/photos"
    params = {'body': name}
    response = requests.get(url=visions_url, headers=headers, params=params)
    res = response.content
    with open(savePath + name, "wb") as fp:
        fp.write(res)
    return res


def take_vision_photo(resolution: str = "640x480"):
    """拍一张照片"""
    visions_url = basic_url + "visions/photos"
    param = {"resolution": resolution}
    json_data = json.dumps(param)
    response = requests.post(url=visions_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_vision_photo_list():
    """获取机器人照片列表"""
    visions_url = basic_url + "visions/photos/list"
    response = requests.get(url=visions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def delete_vision_photo_sample(name: str):
    """删除指定名称的样本照片"""
    visions_url = basic_url + "visions/photosamples"
    param = {"name": name}
    json_data = json.dumps(param)
    response = requests.delete(url=visions_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_vision_photo_samples():
    """获取样本照片列表"""
    visions_url = basic_url + "visions/photosamples"
    response = requests.get(url=visions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def upload_vision_photo_sample(filePath: str):
    """上传样本图片到特定文件夹"""
    visions_url = basic_url + "visions/photosamples"
    upload_headers = {'Authorization': 'multipart/form-data'}
    files = {'file': open(filePath, 'rb')}
    response = requests.post(url=visions_url, files=files, headers=upload_headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def open_vision_stream(resolution: str = "640x480"):
    """打开摄像头网络视频流"""
    visions_url = basic_url + "visions/streams"
    param = {"resolution": resolution}
    json_data = json.dumps(param)
    response = requests.post(url=visions_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def close_vision_stream():
    """关闭摄像头网络视频流"""
    visions_url = basic_url + "visions/streams"
    response = requests.delete(url=visions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def delete_vision_tag(tag: str, mode: str = "all"):
    """删除指定标签"""
    visions_url = basic_url + "visions/tags"
    param = {"tags": tag, "mode": mode}
    json_data = json.dumps(param)
    response = requests.delete(url=visions_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def get_vision_tags():
    """获取样本标签列表"""
    visions_url = basic_url + "visions/tags"
    response = requests.get(url=visions_url, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def set_vision_tag(resources: List[str], tag: str):
    """给已有样本图片打标签"""
    visions_url = basic_url + "visions/tags"
    param = {"resources": resources, "tags": tag}
    json_data = json.dumps(param)
    response = requests.put(url=visions_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    return res


def do_visions_visible(operation, task):
    """开启或关闭视觉任务视频流"""
    vision_visible_url = basic_url + "visions_visible"
    param = {"operation": operation, "type": task}
    json_data = json.dumps(param)
    response = requests.put(url=vision_visible_url, data=json_data, headers=headers)
    res = json.loads(str(response.content.decode("utf-8")))
    if operation == 'start':
        try:
            print("url --> %s" % res['data']['url'])
        except Exception:
            pass
    return res


def show_visions_result(operation):
    """显示视觉任务视频流"""
    global ip
    counter = 0
    try:
        res = do_visions_visible('start', operation)
        if res['code'] == 20003:
            if ip != "127.0.0.1":
                port = res['data']['url'][7:][res['data']['url'][7:].find(':') + 1:]
                url = "http://" + ip + ":" + port
            else:
                url = res['data']['url']
        elif res['code'] == 0:
            url = res['data']['url']
        else:
            print(res['msg'])
            return
    except Exception:
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        do_visions_visible('stop', operation)
        return
    camera = cv2.VideoCapture(url)
    ret = camera.isOpened()
    if not ret:
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        do_visions_visible('stop', operation)
        return
    try:
        while ret:
            ret, frame = camera.read()
            if not ret:
                if counter > 2:
                    cv2.destroyAllWindows()
                    cv2.waitKey(1)
                    camera.release()
                    exit(0)
                else:
                    cv2.destroyAllWindows()
                    cv2.waitKey(1)
                    camera.release()
                    counter += 1
                    try:
                        res = do_visions_visible('start', operation)
                        url = res['data']['url']
                        ret = 1
                    except Exception:
                        exit(0)
                    camera = cv2.VideoCapture(url)
                    continue
            else:
                counter = 0
            cv2.imshow(operation, frame)
            cv2.waitKey(1)
            if cv2.getWindowProperty(operation, cv2.WND_PROP_VISIBLE) <= 0:
                break
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        do_visions_visible('stop', operation)
    except Exception:
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        do_visions_visible('stop', operation)
