import asyncio
import time
import json
import logging

_LOGGER = logging.getLogger(__name__)


class RobotController:

    CLEAN_MODE_AUTO = 'AutoClean'
    CLEAN_MODE_EDGE = 'EdgeClean'
    CLEAN_MODE_EDGE_DETECT = 'EdgeDetect'
    CLEAN_MODE_SPOT = 'SpotClean'
    CLEAN_MODE_SINGLE_ROOM = 'RoomClean'
    CLEAN_MODE_MOP   = 'MopClean'
    CLEAN_MODE_SMART = 'SmartClean'
    CLEAN_MODE_Z     = 'ZmodeClean'
    
    
    DIRECTION_CONTROL = 'DirectionControl'
    RELOCATION = 'Relocation'

    CLEAN_MODE_STOP  = 'Standby'

    FAN_DISABLED     = 'Pause'
    FAN_SPEED_QUIET  = 'Quiet'
    FAN_SPEED_NORMAL = 'Normal'
    FAN_SPEED_HIGH   = 'Strong'
    FAN_SPEEDS = {FAN_SPEED_QUIET, FAN_SPEED_NORMAL, FAN_SPEED_HIGH}

    CHARGE_MODE_RETURNING = 'BackCharging'

    CHARGE_MODE_CHARGING = 'Charging'
    CHARGE_MODE_DOCK_CHARGING = 'PileCharging'
    CHARGE_MODE_DIRECT_CHARGING = 'DirCharging'

    CHARGE_MODE_IDLE = 'Hibernating'
    CHARGE_MODE_CHARGE_DONE = 'ChargeDone'

    MOP_DISABLED     = 'None'
    MOP_SPEED_LOW    = 'Low'
    MOP_SPEED_NORMAL = 'Default'
    MOP_SPEED_HIGH   = 'High'
    MOP_SPEEDS       = {MOP_SPEED_LOW, MOP_SPEED_NORMAL, MOP_SPEED_HIGH}

    ROBOT_ERROR = "Malfunction"

    ROBOT_LOCATION_SOUND = 'LocationAlarm'
    ROBOT_PLANNING_LOCATION = 'PlanningLocation'
    ROBOT_PLANNING_RECT = 'PlanningRect'

    CLEANING_STATES = {DIRECTION_CONTROL, ROBOT_PLANNING_RECT, RELOCATION, CLEAN_MODE_Z, CLEAN_MODE_AUTO, CLEAN_MODE_EDGE, CLEAN_MODE_EDGE_DETECT, CLEAN_MODE_SPOT, CLEAN_MODE_SINGLE_ROOM, CLEAN_MODE_MOP, CLEAN_MODE_SMART}
    CHARGING_STATES = {CHARGE_MODE_CHARGING, CHARGE_MODE_DOCK_CHARGING, CHARGE_MODE_DIRECT_CHARGING}
    DOCKED_STATES   = {CHARGE_MODE_IDLE, CHARGE_MODE_CHARGING, CHARGE_MODE_DOCK_CHARGING, CHARGE_MODE_DIRECT_CHARGING}


    def __init__(self, thing_name, thing_nickname, sub_type, thing_status, weback_api):
        self.name = thing_name
        self.nickname = thing_nickname
        self.sub_type = sub_type
        self.weback_api = weback_api
        self.status = thing_status

    async def update(self): 
        _LOGGER.debug("RobotController.update")
        await self.weback_api.update_status(self.name, self.sub_type)

    @property
    def current_mode(self) -> str:
        try:
            _LOGGER.debug("RobotController.current_mode: " + self.status['working_status'])
        except KeyError:
            _LOGGER.debug("RobotController.current_mode - working status didnt exist -> setting to idle until I receive an update")
            self.status['working_status'] = self.CHARGE_MODE_IDLE     
            self.status['battery_level'] = 100
            self.status['fan_status'] = self.FAN_SPEED_NORMAL
            
            
        return self.status['working_status']

    @property
    def raw_status(self) -> str:
        _LOGGER.debug("RobotController.raw_status ", self.status)
        return self.status 

    @property
    def is_cleaning(self) -> bool:
        _LOGGER.debug("RobotController.is_cleaning", self.current_mode)
        return self.current_mode in self.CLEANING_STATES
        
    @property
    def is_available(self):
        _LOGGER.debug("Connected: " + self.status['connected'] )
        _LOGGER.debug("RobotController.is_available: ", self.status['connected'] == 'true')
        return self.status['connected'] == 'true'

    @property
    def is_charging(self):
        return self.current_mode in self.CHARGING_STATES

    @property
    def fan_status(self):
        return self.status["fan_status"]

    @property
    def error_info(self):
        return self.status["error_info"]

    @property
    def battery_level(self):
        return int(self.status["battery_level"])

    @property
    def fan_speed_list(self):
        return [self.FAN_SPEED_QUIET, self.FAN_SPEED_NORMAL, self.FAN_SPEED_HIGH]

    @property
    def is_on(self):
        """Return true if vacuum is currently cleaning."""
        _LOGGER.debug("IS ON?" )
        return False

    async def set_fan_speed(self, speed):
        _LOGGER.debug("RobotController.set_fan_speed", speed)
        await self.send_message('fan_status', speed)
        
    async def turn_on(self):
        _LOGGER.debug("RobotController.turn_on")
        await self.send_message('working_status', self.CLEAN_MODE_AUTO)

    async def turn_off(self):
        _LOGGER.debug("RobotController.turn_off")
        await self.send_message('working_status', self.CHARGE_MODE_RETURNING)

    async def pause(self):
        _LOGGER.debug("RobotController.pause")
        await self.send_message('working_status', self.CLEAN_MODE_STOP)

    async def clean_spot(self):
        _LOGGER.debug("RobotController.clean_spot")
        await self.send_message('working_status', self.CLEAN_MODE_SPOT)

    async def locate(self):
        _LOGGER.debug("RobotController.locate")
        await self.send_message('working_status', self.ROBOT_LOCATION_SOUND)

    async def return_to_base(self):
        _LOGGER.debug("RobotController.return_to_base")
        await self.send_message('working_status', self.CHARGE_MODE_RETURNING)

    async def send_message(self, key, value):
        _LOGGER.debug("RobotController.send_message", self.weback_api)
        await self.weback_api.send_command(self.name, self.sub_type, key, value)

    def register_update_callback(self, callback):
        self.weback_api.register_update_callback(callback)

    async def goto(self, point: str):
        _LOGGER.debug("*** Goto (X,Y) location: " + point)
        await self.weback_api.goto_command(self.name, self.sub_type, point)

    async def clean_rect(self, rectangle: str):
        _LOGGER.debug("*** Clean rect: " + rectangle)
        await self.weback_api.clean_rectangle_command(self.name, self.sub_type, rectangle)
