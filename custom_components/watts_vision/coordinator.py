"""Data update coordinator for Watts Vision integration.

This coordinator is responsible for fetching data from the Watts Vision API
at regular intervals and updating the Home Assistant entities accordingly, without doing
redundant API calls.
"""

import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CLIENT_TIMEOUT, CONF_SMART_HOME_ID, DEFAULT_SCAN_INTERVAL
from .pywatts import WattsVisionClient
from .pywatts.errors import WattsVisionAuthenticationError, WattsVisionError
from .pywatts.model import SmartHome

_LOGGER = logging.getLogger(__name__)


class WattsVisionCoordinator(DataUpdateCoordinator[SmartHome]):
    """Data update coordinator for Watts Vision integration.

    This coordinator is responsible for fetching data from the Watts Vision API
    at regular intervals and updating the Home Assistant entities accordingly, without doing
    redundant API calls.

    It fetches the SmartHome object from the API, which contains all the required information
    about the smart home and its devices.
    """

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, client: WattsVisionClient
    ):
        """Initialize the Watts Vision data update coordinator."""

        # Fetch configuration interval
        scan_interval_config = config_entry.options.get(CONF_SCAN_INTERVAL)
        scan_interval: timedelta = (
            timedelta(**scan_interval_config)
            if scan_interval_config
            else DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name="Watts Vision",
            config_entry=config_entry,
            update_interval=scan_interval,
            always_update=False,
        )
        self.client = client
        self.smart_home_id = config_entry.data.get(CONF_SMART_HOME_ID)

    async def _async_update_data(self):
        """Fetch data from Watts Vision API endpoint."""

        try:
            async with asyncio.timeout(CLIENT_TIMEOUT):
                _LOGGER.debug("Fetching latest data from Watts Vision API.")
                return await self.client.get_smart_home(self.smart_home_id)
        except WattsVisionAuthenticationError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except WattsVisionError as err:
            raise UpdateFailed("Error communicating with Watts Vision API") from err
