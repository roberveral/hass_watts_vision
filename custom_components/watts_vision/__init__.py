"""The Watts Vision integration."""

import logging

from homeassistant.components.google_assistant.trait import (
    TRAITS,
    TemperatureSettingTrait,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .coordinator import WattsVisionCoordinator
from .google_assistant import ActiveModeAwareTemperatureSettingTrait, ClimateModesTrait
from .pywatts import WattsVisionClient
from .pywatts.auth import WattsCredentials
from .types import WattsData, WattsVisionConfigEntry

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Watts Vision component."""

    _LOGGER.debug("Initializing Watts Vision integration.")

    # Ensure Google Assistant traits are registered
    # Workaround so the integration with Google Assistant supports:
    #   - Preset modes through ModesTrait
    #   - Active thermostat mode through TemperatureSettingTrait to show HVAC action correctly
    if ClimateModesTrait in TRAITS:
        _LOGGER.debug("Google Assistant ClimateModesTrait loaded.")

    if ActiveModeAwareTemperatureSettingTrait in TRAITS:
        _LOGGER.debug("Google Assistant ActiveModeAwareTemperatureSettingTrait loaded.")
        if TemperatureSettingTrait in TRAITS:
            _LOGGER.debug(
                "Removing Google Assistant TemperatureSettingTrait to avoid conflicts."
            )
            TRAITS.remove(TemperatureSettingTrait)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: WattsVisionConfigEntry) -> bool:
    """Configures the Watts Vision integration from a config entry."""

    _LOGGER.debug(
        "Setting up Watts Vision integration for entry_id: %s", entry.entry_id
    )

    # Create the API client
    credentials = WattsCredentials(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    session = async_get_clientsession(hass)
    client = WattsVisionClient(session, credentials)

    # Create the coordinator
    coordinator = WattsVisionCoordinator(hass, entry, client)

    # Store everything in the runtime data
    entry.runtime_data = WattsData(client=client, coordinator=coordinator)

    # Initialize the coordinator (fetch initial data)
    await coordinator.async_config_entry_first_refresh()

    # Launch the creation of the different platforms and its entities
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WattsVisionConfigEntry
) -> bool:
    """Unloads a config entry that has been removed or disabled."""

    _LOGGER.debug("Unloading Watts Vision integration for entry_id: %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
