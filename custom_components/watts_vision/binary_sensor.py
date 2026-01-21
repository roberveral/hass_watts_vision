"""Binary Sensor platform for Watts Vision integration.

This platform integrates battery status sensors from Watts Vision thermostat devices
into Home Assistant, allowing users to monitor the battery health of their devices.
"""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .coordinator import WattsVisionCoordinator
from .entity import WattsThermostatEntity
from .pywatts.model import Device, ErrorCode
from .types import WattsVisionConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: WattsVisionConfigEntry, async_add_entities
):
    """Configures the BINARY_SENSOR platform for the Watts Vision integration."""

    _LOGGER.debug("Setting up binary sensor entities for Watts Vision integration.")

    # Retrieve the rutime data for this entry
    coordinator = entry.runtime_data.coordinator

    # Create sensor entities for each thermostat device in the configured smart home
    entities = []
    for zone in coordinator.data.zones:
        for device in zone.devices:
            _LOGGER.debug(
                "Found device %s in zone %s for sensor entity.", device.id, zone.label
            )
            entities.append(WattsBatterySensor(coordinator, entry, device, zone.label))

    async_add_entities(entities)


class WattsBatterySensor(WattsThermostatEntity, BinarySensorEntity):
    """Representation of a Battery Sensor from a Watts Vision Thermostat.

    This sensor indicates whether the battery level of the thermostat device is low.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        device: Device,
        suggested_area: str | None = None,
    ) -> None:
        """Initialize the battery sensor."""

        super().__init__(coordinator, entry, device, suggested_area)

        # Properties
        self._attr_unique_id = f"watts_battery_sensor_{self._id}"

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""

        self._attr_is_on = device.error_code == ErrorCode.BATTERY_LOW
