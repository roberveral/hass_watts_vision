"""Base entity classes for Watts Vision integration."""

import logging

from homeassistant.core import callback
from homeassistant.exceptions import IntegrationError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SMART_HOME_ID
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
        self._smart_home_id: str = self._entry.data[CONF_SMART_HOME_ID]


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

        _LOGGER.debug(
            "Updating thermostat entity %s state from coordinator data",
            self.unique_id,
        )

        self._update_entity_from_coordinator()
        super()._handle_coordinator_update()

    def _update_entity_from_coordinator(self) -> None:
        """Update the entity's state based on the coordinator's data.

        When has_recent_command is True, ignore updates if no changes detected since last update,
        preserving optimistic updates made by the entity.
        """

        # Obtain the latest device data from the coordinator
        device: Device = self.coordinator.data.get_device_by_id(self._id)
        if device is None:
            _LOGGER.error("Device with ID %s not found in Smart Home data.", self._id)
            raise IntegrationError(f"Device with ID {self._id} not found.")

        # Update the entity state from the device data
        self._update_entity_from_device(device)

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""


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
