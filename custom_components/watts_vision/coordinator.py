from datetime import timedelta
import logging
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .pywatts import WattsVisionClient
from .pywatts.model import SmartHome
from .pywatts.errors import WattsVisionAuthenticationError, WattsVisionError

from .const import CLIENT_TIMEOUT, CONF_SMART_HOME_ID, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class WattsVisionCoordinator(DataUpdateCoordinator[SmartHome]):

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, client: WattsVisionClient):
        # Fetch configuration interval
        scan_interval_config = config_entry.options.get(CONF_SCAN_INTERVAL)
        scan_interval: timedelta = timedelta(**scan_interval_config) if scan_interval_config else DEFAULT_SCAN_INTERVAL
        
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
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(CLIENT_TIMEOUT):
                _LOGGER.debug("Fetching latest data from Watts Vision API.")
                return await self.client.get_smart_home(self.smart_home_id)
        except WattsVisionAuthenticationError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except WattsVisionError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
