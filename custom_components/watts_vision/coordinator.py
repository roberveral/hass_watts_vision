"""Data update coordinator for Watts Vision integration.

This coordinator is responsible for fetching data from the Watts Vision API
at regular intervals and updating the Home Assistant entities accordingly, without doing
redundant API calls.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CLIENT_TIMEOUT,
    CONF_SMART_HOME_ID,
    CONF_UPDATE_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPDATE_DELAY,
    OPTIMISTIC_UPDATE_GRACE_PERIOD,
)
from .pywatts import WattsVisionClient
from .pywatts.errors import WattsVisionAuthenticationError, WattsVisionError
from .pywatts.model import Device, Mode, SmartHome, TemperatureSetting

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
        # Helpers for optimistic updates
        self._pending_updates: list[_OptimisticDeviceUpdate] = []
        self._lock = asyncio.Lock()

    async def _async_update_data(self):
        """Fetch data from Watts Vision API endpoint."""

        try:
            async with asyncio.timeout(CLIENT_TIMEOUT):
                _LOGGER.debug("Fetching latest data from Watts Vision API.")
                data = await self.client.get_smart_home(self.smart_home_id)
        except WattsVisionAuthenticationError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except WattsVisionError as err:
            raise UpdateFailed("Error communicating with Watts Vision API") from err
        else:
            async with self._lock:
                # Apply optimistic updates
                expired_updates = []
                for optimistic_update in self._pending_updates:
                    if optimistic_update.is_valid_for_home(data):
                        optimistic_update.apply_to_home(data)
                    else:
                        expired_updates.append(optimistic_update)

                # Clean-up expired updates
                for update in expired_updates:
                    _LOGGER.debug("Optimistic update expired: %s", update)
                    self._pending_updates.remove(update)

            return data

    async def change_device_temperature_setting(
        self,
        device_id: str,
        temperature_setting: TemperatureSetting,
        temperature: float,
    ):
        """Change a temperature setting of a device in a given smart home in the Watts Vision system."""

        async with self._lock:
            # Perform the update against the system.
            await self.client.change_device_temperature_setting(
                self.smart_home_id, device_id, temperature_setting, temperature
            )

            # Store pending write to apply optimistically
            optimistic_update = _TemperatureSettingOptimisticDeviceUpdate(
                device_id,
                datetime.now() + self._update_waiting_time(),
                temperature_setting,
                temperature,
            )
            self._pending_updates.append(optimistic_update)

            # Set updated data inmediately
            optimistic_update.apply_to_home(self.data)
            self.async_set_updated_data(self.data)

    async def change_device_mode(
        self,
        device_id: str,
        mode: Mode,
        boost_duration: timedelta = timedelta(),
    ):
        """Change the current mode of a device in a given smart home in the Watts Vision system."""

        async with self._lock:
            # Perform the update against the system.
            await self.client.change_device_mode(
                self.smart_home_id, device_id, mode, boost_duration
            )

            # Store pending write to apply optimistically
            optimistic_update = _ModeOptimisticDeviceUpdate(
                device_id,
                datetime.now() + self._update_waiting_time(),
                mode,
                boost_duration,
            )
            self._pending_updates.append(optimistic_update)

            # Set updated data inmediately
            optimistic_update.apply_to_home(self.data)
            self.async_set_updated_data(self.data)

    def _update_waiting_time(self) -> timedelta:
        queue_delay_config = self.config_entry.options.get(CONF_UPDATE_DELAY)
        queue_delay = (
            timedelta(**queue_delay_config)
            if queue_delay_config
            else DEFAULT_UPDATE_DELAY
        )
        return self.client.worker_size() * queue_delay + OPTIMISTIC_UPDATE_GRACE_PERIOD


@dataclass
class _OptimisticDeviceUpdate:
    device_id: str
    expiration: datetime

    def apply_to_home(self, smart_home: SmartHome):
        device = smart_home.get_device_by_device_id(self.device_id)
        self.apply(device)
        for zone in smart_home.zones:
            self.apply(zone.get_device_by_id(device.id))
        _LOGGER.debug("Optimistic update applied: %s; Result: %s", self, device)

    def is_valid_for_home(self, smart_home: SmartHome):
        device = smart_home.get_device_by_device_id(self.device_id)
        return device and not self.is_applied(device) and not self.is_expired()

    def apply(self, device: Device):
        return

    def is_applied(self, device: Device) -> bool:
        return False

    def is_expired(self) -> bool:
        return datetime.now() >= self.expiration


@dataclass
class _TemperatureSettingOptimisticDeviceUpdate(_OptimisticDeviceUpdate):
    temperature_setting: TemperatureSetting
    temperature: float

    def apply(self, device: Device):
        if not device or device.device_id != self.device_id:
            return

        device.temperature_settings[self.temperature_setting] = self.temperature
        if self.temperature_setting == device.target_temperature_setting:
            device.target_temperature = self.temperature

    def is_applied(self, device: Device) -> bool:
        return (
            device.temperature_settings.get(self.temperature_setting)
            == self.temperature
        )


@dataclass
class _ModeOptimisticDeviceUpdate(_OptimisticDeviceUpdate):
    mode: Mode
    boost_duration: float

    def apply(self, device: Device):
        if not device or device.device_id != self.device_id:
            return

        device.mode = self.mode
        device.boost_duration_remaining = self.boost_duration

        # Align the target temperature with the selected mode.
        if self.mode == Mode.COMFORT:
            device.target_temperature_setting = TemperatureSetting.COMFORT
        elif self.mode == Mode.ECO:
            device.target_temperature_setting = TemperatureSetting.ECO
        elif self.mode == Mode.BOOST:
            device.target_temperature_setting = TemperatureSetting.BOOST
        elif self.mode == Mode.ANTI_FREEZE:
            device.target_temperature_setting = TemperatureSetting.ANTI_FREEZE
        elif self.mode == Mode.PROGRAM:
            device.target_temperature_setting = TemperatureSetting.COMFORT
        elif self.mode == Mode.OFF:
            device.target_temperature_setting = TemperatureSetting.NONE

        device.target_temperature = device.temperature_settings.get(
            device.target_temperature_setting, None
        )

    def is_applied(self, device: Device) -> bool:
        return device.mode == self.mode
