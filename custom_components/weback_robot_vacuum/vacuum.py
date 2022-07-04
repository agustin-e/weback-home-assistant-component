"""Support for Weback Robot Vacuums."""
import logging
import datetime
from functools import partial
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.vacuum import (    
    StateVacuumEntity,
    VacuumEntityFeature,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_CLEANING,
    STATE_RETURNING,
    STATE_DOCKED,
    STATE_ERROR
)


from homeassistant.helpers.icon import icon_for_battery_level

from . import (DOMAIN, SCAN_INTERVAL)

_LOGGER = logging.getLogger(__name__)

from . import RobotController


STATE_MAPPING = {        
    # STATE_CLEANING
    RobotController.CLEAN_MODE_AUTO         : STATE_CLEANING,
    RobotController.CLEAN_MODE_EDGE         : STATE_CLEANING,
    RobotController.CLEAN_MODE_EDGE_DETECT  : STATE_CLEANING,
    RobotController.CLEAN_MODE_SPOT         : STATE_CLEANING,
    RobotController.CLEAN_MODE_SINGLE_ROOM  : STATE_CLEANING,
    RobotController.CLEAN_MODE_MOP          : STATE_CLEANING,
    RobotController.CLEAN_MODE_SMART        : STATE_CLEANING,
    RobotController.ROBOT_PLANNING_LOCATION : STATE_CLEANING,
    RobotController.CLEAN_MODE_Z            : STATE_CLEANING,
    RobotController.DIRECTION_CONTROL       : STATE_CLEANING,
    RobotController.EDGE_DETECT             : STATE_CLEANING,
    RobotController.RELOCATION              : STATE_CLEANING,

    # STATE_DOCKED
    RobotController.CHARGE_MODE_CHARGING        : STATE_DOCKED,
    RobotController.CHARGE_MODE_DOCK_CHARGING   : STATE_DOCKED,
    RobotController.CHARGE_MODE_DIRECT_CHARGING : STATE_DOCKED,
    
    # STATE_PAUSED

    # STATE_IDLE
    RobotController.CLEAN_MODE_STOP         : STATE_IDLE,
    RobotController.CHARGE_MODE_IDLE        : STATE_IDLE,
    RobotController.CHARGE_MODE_CHARGE_DONE : STATE_IDLE,

    # STATE_RETURNING
    RobotController.CHARGE_MODE_RETURNING   : STATE_RETURNING,

    # STATE_ERROR
    RobotController.ROBOT_ERROR             : STATE_ERROR
}


SERVICE_GOTO_LOCATION = 'go_to_location'
ATTR_POINT = "point"

from homeassistant.helpers import entity_platform

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Weback robot vacuums."""
    vacuums = []
    for device in hass.data[DOMAIN]:
        vacuums.append(WebackVacuumRobot(device, SCAN_INTERVAL))    

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
            SERVICE_GOTO_LOCATION, 
            {  
                vol.Required(ATTR_POINT): cv.string,
            }, "async_goto_location"
    )
    

    _LOGGER.debug("Adding Weback Vacuums to Home Assistant: %s", vacuums)
    async_add_entities(vacuums, True)


class WebackVacuumRobot(StateVacuumEntity):
    """Weback Vacuums such as ABIR XS-X6."""

    def __init__(self, device: RobotController, scan_interval: datetime.timedelta):
        """Initialize the Weback Vacuum."""
        self.device = device
        
        self._attr_supported_features = (
            VacuumEntityFeature.TURN_ON
            | VacuumEntityFeature.TURN_OFF
            | VacuumEntityFeature.STATUS
            | VacuumEntityFeature.BATTERY
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.FAN_SPEED
            | VacuumEntityFeature.CLEAN_SPOT
            | VacuumEntityFeature.LOCATE
            | VacuumEntityFeature.START
        )
        
        device.register_update_callback(self.device_updated)

        _LOGGER.debug("Vacuum initialized: %s", self.name)


    def device_updated(self, status):
        _LOGGER.debug("device_updated", status)
        self.device.status = status
        self.schedule_update_ha_state(True)


    async def async_update(self):
        _LOGGER.debug("Vacuum: async_update")

        """Update device's state"""
        await self.device.update()        

    @property 
    def error(self):
        _LOGGER.debug("error")
        return self.device.error_info            

    @property
    def should_poll(self) -> bool:        
        _LOGGER.debug("should_poll")
        _LOGGER.debug(self.device.raw_status)
        return True

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        _LOGGER.debug("Vacuum: unique_id", self.device.name)
        return self.device.name

    @property
    def is_on(self):
        _LOGGER.debug("Vacuum: is_on", self.device.is_cleaning)
        """Return true if vacuum is currently cleaning."""
        return self.device.is_cleaning

    @property
    def available(self):
        _LOGGER.debug("Vacuum: available", self.device.is_available)
        """Returns true if vacuum is online"""
        return self.device.is_available

    @property
    def is_charging(self):
        _LOGGER.debug("Vacuum: is_charging", self.device.is_charging)
        """Return true if vacuum is currently charging."""
        return self.device.is_charging

    @property
    def name(self):
        _LOGGER.debug("Vacuum: name", self.device.nickname)
        """Return the name of the device."""
        return self.device.nickname

    @property
    def state(self):
        _LOGGER.debug("Vacuum: STATE; Mapear el valor de " + self.device.current_mode)
        """Return the current state of the vacuum."""
        
        try:
            _LOGGER.debug("MAPEADO ES: " + STATE_MAPPING[self.device.current_mode])
            return STATE_MAPPING[self.device.current_mode]
        except KeyError:
            _LOGGER.error(
                "STATE not supported, state_code: %s",
                self.device.current_mode,
            )
            return None

    def return_to_base(self, **kwargs):
        _LOGGER.debug("Vacuum: return_to_base")
        """Set the vacuum cleaner to return to the dock."""
        self.device.return_home()

    @property
    def battery_icon(self):
        _LOGGER.debug("Vacuum: battery_icon")
        """Return the battery icon for the vacuum cleaner."""
        return icon_for_battery_level(
            battery_level=self.battery_level, charging=self.is_charging
        )


    @property
    def battery_charging(self):
        _LOGGER.debug("Vacuum: battery_charging", self.is_charging)
        """Returns true when robot is charging"""
        return self.is_charging

    @property
    def battery_level(self):
        _LOGGER.debug("Vacuum: battery_level", self.device.battery_level)
        """Return the battery level of the vacuum cleaner."""
        return self.device.battery_level

    @property
    def fan_speed(self):
        _LOGGER.debug("Vacuum: fan_speed", self.device.fan_status)
        """Return the fan speed of the vacuum cleaner."""
        return self.device.fan_status

    @property
    def fan_speed_list(self):
        _LOGGER.debug("Vacuum: fan_speed_list", self.device.fan_speed_list)
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return self.device.fan_speed_list
        
    async def async_set_fan_speed(self, fan_speed, **kwargs):
        _LOGGER.debug("Vacuum: set_fan_speed", fan_speed)
        await self.device.set_fan_speed(fan_speed)

    async def async_pause(self):
        _LOGGER.debug("Vacuum: async_pause")
        await self.device.pause()

    async def async_start(self):
        """Turn the vacuum on and start cleaning."""
        _LOGGER.debug("Vacuum: async_start")
        await self.device.turn_on()
        
    async def turn_on(self, **kwargs):
        """Turn the vacuum on and start cleaning."""
        _LOGGER.debug("Vacuum: turn_on")
        await self.device.turn_on()
        
    def turn_off(self, **kwargs):
        _LOGGER.debug("Vacuum: turn_off")
        """Turn the vacuum off stopping the cleaning and returning home."""
        self.return_to_base()

    async def async_stop(self, **kwargs):
        _LOGGER.debug("Vacuum: stop")
        """Stop the vacuum cleaner."""
        await self.device.pause()

    async def async_clean_spot(self, **kwargs):
        _LOGGER.debug("Vacuum: clean_spot")
        """Perform a spot clean-up."""
        await self.device.clean_spot()

    async def async_locate(self, **kwargs) -> None:
        """Locate the vacuum cleaner."""
        _LOGGER.debug("Vacuum: locate")
        await self.device.locate()
        
    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        _LOGGER.debug("Vacuum: async_return_to_base")
        await self.device.return_to_base()
        
    async def async_goto_location(self, point: str):
        _LOGGER.debug("*** async_goto_location location: " + point)
        await self.device.goto(point)