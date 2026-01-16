import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN

from .const import DOMAIN

# set_temperature_setting

SERVICE_SET_TEMPERATURE_SETTING = "set_temperature_setting"
SERVICE_ATTR_TEMPERATURE_COMFORT = "temperature_comfort"
SERVICE_ATTR_TEMPERATURE_ECO = "temperature_eco"
SERVICE_ATTR_TEMPERATURE_BOOST = "temperature_boost"
SERVICE_ATTR_TEMPERATURE_ANTIFREEZE = "temperature_antifreeze"
SERVICE_ATTR_TEMPERATURE_MANUAL = "temperature_manual"
SET_TEMPERATURE_SETTING_SCHEMA = {
    vol.Optional(SERVICE_ATTR_TEMPERATURE_COMFORT): vol.All(
        vol.Coerce(float)
    ),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_ECO): vol.All(
        vol.Coerce(float)
    ),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_BOOST): vol.All(
        vol.Coerce(float)
    ),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_ANTIFREEZE): vol.All(
        vol.Coerce(float)
    ),
    vol.Optional(SERVICE_ATTR_TEMPERATURE_MANUAL): vol.All(
        vol.Coerce(float)
    ),
}


def async_register_services(hass: HomeAssistant) -> None:
    """Register services for the Watts Vision integration."""
    
    # Register the set_temperature_setting service.
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SET_TEMPERATURE_SETTING,
        entity_domain=CLIMATE_DOMAIN,
        func="async_set_temperature_setting",
        schema=SET_TEMPERATURE_SETTING_SCHEMA
    )

