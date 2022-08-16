"""Support for WeBack robot vacuums."""

from datetime import timedelta
import logging
import random
import string

import voluptuous as vol


from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN        = "weback_robot_vacuum"
SCAN_INTERVAL = timedelta(seconds=60)
CONF_REGION   = 'region'

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_REGION): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


from .RobotController import RobotController
from .WebackVacuumApi import WebackVacuumApi

async def async_setup(hass, config):
    """Set up the Weback component."""
    _LOGGER.debug("Creating new Weback Vacuum Robot component")

    hass.data[DOMAIN] = []

    weback_api = WebackVacuumApi(
        config[DOMAIN].get(CONF_USERNAME), 
        config[DOMAIN].get(CONF_PASSWORD),
        config[DOMAIN].get(CONF_REGION),
    )

    _LOGGER.debug("Weback vacuum robots: login started")
    await weback_api.login()    
    robots = await weback_api.robot_list()
    
    _LOGGER.debug("Weback vacuum robots: %s", robots)

    for robot in robots:
        _LOGGER.info(
            "Discovered Weback robot %s with nickname %s",
            robot["thing_name"],
            robot["thing_nickname"],
        )

        robot_controller = RobotController(robot["thing_name"], robot["thing_nickname"], robot["sub_type"], robot["thing_status"], weback_api.clone())
        hass.data[DOMAIN].append(robot_controller)

    if hass.data[DOMAIN]:
        _LOGGER.debug("Starting vacuum robot components")
        hass.helpers.discovery.load_platform("vacuum", DOMAIN, {}, config)

    return True

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )
