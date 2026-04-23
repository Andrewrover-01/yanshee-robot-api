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
