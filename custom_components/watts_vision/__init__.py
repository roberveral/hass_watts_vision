"""The Watts Vision integration."""

from datetime import timedelta
import logging

from homeassistant.components.google_assistant.trait import TRAITS
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_DEBOUNCE_DURATION,
    CONF_UPDATE_DELAY,
    DEFAULT_DEBOUNCE_DURATION,
    DEFAULT_UPDATE_DELAY,
)
from .coordinator import WattsVisionCoordinator
from .google_assistant import ClimateModesTrait
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
    if ClimateModesTrait in TRAITS:
        _LOGGER.debug("Google Assistant ClimateModesTrait loaded.")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: WattsVisionConfigEntry) -> bool:
    """Configures the Watts Vision integration from a config entry."""

    _LOGGER.debug(
        "Setting up Watts Vision integration for entry_id: %s", entry.entry_id
    )

    # Create the API client
    credentials = WattsCredentials(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    session = async_get_clientsession(hass)
    debounce_delay_config = entry.options.get(CONF_DEBOUNCE_DURATION)
    queue_delay_config = entry.options.get(CONF_UPDATE_DELAY)
    client = WattsVisionClient(
        session,
        credentials,
        debounce_delay=timedelta(**debounce_delay_config).total_seconds()
        if debounce_delay_config
        else DEFAULT_DEBOUNCE_DURATION,
        queue_delay=timedelta(**queue_delay_config).total_seconds()
        if queue_delay_config
        else DEFAULT_UPDATE_DELAY,
    )

    # Create the coordinator
    coordinator = WattsVisionCoordinator(hass, entry, client)

    # Create the task to process batched updates
    task = entry.async_create_background_task(
        hass, client.async_update_worker(), "watts_vision_update_worker"
    )

    # Store everything in the runtime data
    entry.runtime_data = WattsData(
        client=client, coordinator=coordinator, worker_task=task
    )

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

    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    # Graceful shutdown draining pending updates
    await entry.runtime_data.client.async_worker_shutdown()
    if entry.runtime_data.worker_task:
        await entry.runtime_data.worker_task

    return True
