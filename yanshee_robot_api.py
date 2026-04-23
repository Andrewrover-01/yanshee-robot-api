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
