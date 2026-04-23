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
