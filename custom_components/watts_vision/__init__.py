"""The Watts Vision integration."""

from dataclasses import dataclass
import logging

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .pywatts import WattsVisionClient
from .pywatts.auth import WattsCredentials

from .coordinator import WattsVisionCoordinator
from .types import WattsData, WattsVisionConfigEntry

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: WattsVisionConfigEntry) -> bool:
    """Configures the Watts Vision integration from a config entry."""
    
    _LOGGER.debug("Setting up Watts Vision integration for entry_id: %s", entry.entry_id)

    # Create the API client
    credentials = WattsCredentials(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    session = async_get_clientsession(hass)
    client = WattsVisionClient(session, credentials)
    
    # Create the coordinator
    coordinator = WattsVisionCoordinator(hass, entry, client)
    
    # Store everything in the runtime data
    entry.runtime_data = WattsData(
        client=client,
        coordinator=coordinator
    )

    # Initialize the coordinator (fetch initial data)
    await coordinator.async_config_entry_first_refresh()

    # Launch the creation of the different platforms and its entities
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: WattsVisionConfigEntry) -> bool:
    """Unloads a config entry that has been removed or disabled."""

    _LOGGER.debug("Unloading Watts Vision integration for entry_id: %s", entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
