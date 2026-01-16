"""Constants for the Watts Vision integration."""

from datetime import timedelta
from homeassistant.components.climate.const import HVACMode

from .pywatts.model import HVACSetting

# Domain and Manufacturer
DOMAIN: str = "watts_vision"
MANUFACTURER: str = "Watts"
THERMOSTAT_MODEL: str = "BT-D03-RF"
CENTRAL_UNIT_MODEL: str = "BT-CT02-RF"

# Configuration Keys
CONF_SMART_HOME_ID: str = "smart_home_id"
CONF_BOOST_DURATION: str = "boost_duration"

# Attribute Keys
ATTR_WATTS_HVAC_SETTING: str = "watts_hvac_setting"
ATTR_WATTS_MODE: str = "watts_mode"
ATTR_LAST_WATTS_MODE: str = "last_watts_mode"
ATTR_WATTS_TARGET_TEMPERATURE_SETTING: str = "watts_target_temperature_setting"

# Defaults
DEFAULT_SCAN_INTERVAL: timedelta = timedelta(seconds=15)
DEFAULT_BOOST_DURATION: timedelta = timedelta(hours=2)

# HVAC Modes
ALLOWED_HVAC_TRANSITIONS = {
    HVACSetting.HEAT: [HVACMode.HEAT, HVACMode.OFF],
    HVACSetting.COOL: [HVACMode.COOL, HVACMode.OFF],
}

# API Constants
CLIENT_TIMEOUT: int = 10  # seconds
API_COMMAND_DELAY: timedelta = timedelta(seconds=5)  # Delay after sending a command before next read
