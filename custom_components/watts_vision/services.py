"""Defines the services exposed by the Watts Vision integration.

These services allow users to perform specific actions on Watts Vision devices
within Home Assistant, such as setting temperature settings on thermostats.
"""

import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service

from .const import DOMAIN

# Entity Service: set_temperature_setting

SERVICE_SET_TEMPERATURE_SETTING = "set_temperature_setting"
SERVICE_ATTR_TEMPERATURE_COMFORT = "temperature_comfort"
SERVICE_ATTR_TEMPERATURE_ECO = "temperature_eco"
SERVICE_ATTR_TEMPERATURE_BOOST = "temperature_boost"
SERVICE_ATTR_TEMPERATURE_ANTIFREEZE = "temperature_antifreeze"
SERVICE_ATTR_TEMPERATURE_MANUAL = "temperature_manual"
SET_TEMPERATURE_SETTING_SCHEMA = {
    vol.Optional(SERVICE_ATTR_TEMPERATURE_COMFORT): vol.All(vol.Coerce(float)),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_ECO): vol.All(vol.Coerce(float)),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_BOOST): vol.All(vol.Coerce(float)),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_ANTIFREEZE): vol.All(vol.Coerce(float)),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_MANUAL): vol.All(vol.Coerce(float)),
}


def async_register_services(hass: HomeAssistant) -> None:
    """Registers the services exposed by the Watts Vision integration."""

    # Register the set_temperature_setting service.
    # It targets the climate domain entities, making them implement the
    # async_set_temperature_setting function.
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SET_TEMPERATURE_SETTING,
        entity_domain=CLIMATE_DOMAIN,
        func="async_set_temperature_setting",
        schema=SET_TEMPERATURE_SETTING_SCHEMA,
    )
