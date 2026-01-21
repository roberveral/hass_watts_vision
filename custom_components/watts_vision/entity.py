"""Base entity classes for Watts Vision integration."""

import asyncio
from datetime import datetime
import logging
from types import CoroutineType

from homeassistant.core import callback
from homeassistant.exceptions import IntegrationError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import API_COMMAND_EXPIRATION, CONF_SMART_HOME_ID
from .coordinator import WattsVisionCoordinator
from .device import central_unit_device_info, thermostat_device_info
from .pywatts.model import Device, SmartHome
from .types import WattsVisionConfigEntry

_LOGGER = logging.getLogger(__name__)


class WattsVisionEntity(CoordinatorEntity[WattsVisionCoordinator]):
    """Base class for Watts Vision entities."""

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
    ) -> None:
        """Initialize the Watts Vision entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._api_client = self._entry.runtime_data.client
        self._smart_home_id: str = self._entry.data[CONF_SMART_HOME_ID]
        self._last_command_time: datetime | None = None

    def _has_recent_command(self) -> bool:
        """Check if there was a recent command within the API command expiration period."""
        return (
            self._last_command_time
            and self._last_command_time + API_COMMAND_EXPIRATION > datetime.now()
        )


class WattsThermostatEntity(WattsVisionEntity):
    """Base class for Watts Vision Thermostat device entities.

    Entities that are part of a thermostat device should inherit from this class.
    It handles optimistic updates and state consistency after commands are sent to the API.
    """

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        device: Device,
        suggested_area: str | None = None,
    ) -> None:
        """Initialize the Watts Vision Thermostat device entity."""
        super().__init__(coordinator, entry)
        self._id = device.id
        self._device_id = device.device_id
        self._last_device_state: Device | None = device

        # Properties
        self._attr_device_info = thermostat_device_info(
            device.id,
            self._smart_home_id,
            suggested_area,
        )

        self._update_entity_from_device(device)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        has_recent_command = self._has_recent_command()

        if has_recent_command:
            _LOGGER.debug(
                "Update for thermostat entity %s in recent command grace period since %s. Last device state: %s",
                self.unique_id,
                self._last_command_time,
                self._last_device_state,
            )
        else:
            _LOGGER.debug(
                "Updating thermostat entity %s state from coordinator data",
                self.unique_id,
            )

        self._update_entity_from_coordinator(has_recent_command)
        super()._handle_coordinator_update()

    def _update_entity_from_coordinator(self, has_recent_command: bool = False) -> None:
        """Update the entity's state based on the coordinator's data.

        When has_recent_command is True, ignore updates if no changes detected since last update,
        preserving optimistic updates made by the entity.
        """

        # Obtain the latest device data from the coordinator
        device: Device = self.coordinator.data.get_device_by_id(self._id)
        if device is None:
            _LOGGER.error("Device with ID %s not found in Smart Home data.", self._id)
            raise IntegrationError(f"Device with ID {self._id} not found.")

        # Ignore updates if within grace period and no changes detected
        if has_recent_command and self._last_device_state == device:
            _LOGGER.debug(
                "No changes detected for thermostat entity %s; skipping update.",
                self._id,
            )
            return

        # Update the entity state from the device data
        self._update_entity_from_device(device)

        # Cache the last known device state
        self._last_device_state = device

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""

    async def _async_execute_watts_command(self, command_coro: CoroutineType) -> None:
        """Execute a Watts Vision API command.

        Handles optimistic updates and ensures state consistency after command execution,
        accounting for API eventual consistency. If the command fails, the entity state is refreshed
        from the coordinator to remove any optimistic updates.
        """

        try:
            self._last_command_time = datetime.now()
            await command_coro
            # Add delay to allow for API eventual consistency
            await asyncio.sleep(API_COMMAND_EXPIRATION)
        finally:
            # If failure or after delay, refresh state from coordinator removing optimistic updates
            self._update_entity_from_coordinator()
            self.async_write_ha_state()


class WattsCentralUnitEntity(WattsVisionEntity):
    """Base class for Watts Vision Central Unit device entities.

    Entities that represent the central unit of a smart home should inherit from this class.
    """

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        smart_home: SmartHome,
    ) -> None:
        """Initialize the Watts Vision Central Unit device entity."""
        super().__init__(coordinator, entry)
        self._smart_home_id = smart_home.id

        # Properties
        self._attr_device_info = central_unit_device_info(
            smart_home.id,
            smart_home.label,
            smart_home.mac_address,
        )

        self._update_entity_from_smart_home(smart_home)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        _LOGGER.debug(
            "Updating Central Unit entity %s state from coordinator data.",
            self.unique_id,
        )

        self._update_entity_from_smart_home(self.coordinator.data)
        super()._handle_coordinator_update()

    def _update_entity_from_smart_home(self, smart_home: SmartHome) -> None:
        """Update the entity's state based on the provided smart home data."""
