"""Number platform for the Watts Vision integration.

This module defines number entities that represent temperature settings
from Watts Vision thermostat devices, allowing to configure the setpoints
independently from the climate entity.
"""

import logging

from custom_components.watts_vision.utils import clamp
from homeassistant.components.number import NumberDeviceClass, NumberEntity
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant

from .coordinator import WattsVisionCoordinator
from .entity import WattsThermostatEntity
from .pywatts.model import Device, TemperatureSetting
from .types import WattsVisionConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: WattsVisionConfigEntry, async_add_entities
):
    """Configures the NUMBER platform for the Watts Vision integration."""

    _LOGGER.debug("Setting up number entities for Watts Vision integration.")

    # Retrieve the runtime data for this entry
    coordinator = entry.runtime_data.coordinator

    # Create number entities for each thermostat device in the configured smart home
    entities = []
    for zone in coordinator.data.zones:
        for device in zone.devices:
            _LOGGER.debug(
                "Found device %s in zone %s for number entity.", device.id, zone.label
            )

            entities.extend(
                WattsTemperatureSetting(
                    coordinator,
                    entry,
                    device,
                    temperature_setting,
                    suggested_area=zone.label,
                )
                for temperature_setting in device.temperature_settings
            )

    async_add_entities(entities)


class WattsTemperatureSetting(WattsThermostatEntity, NumberEntity):
    """Representation of a Temperature Setting Number from a Watts Vision Thermostat.

    This number entity allows setting the desired temperature setpoint on the thermostat device,
    without altering the current climate mode and/or preset.
    """

    _attr_has_entity_name = True
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_step = 0.9  # 0.5 °C in °F increments

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        device: Device,
        temperature_setting: TemperatureSetting,
        suggested_area: str | None = None,
    ) -> None:
        """Initialize the Temperature Setting Number."""

        self._temperature_setting = temperature_setting
        super().__init__(coordinator, entry, device, suggested_area)

        # Properties
        self._attr_unique_id = f"watts_temperature_setting_{self._temperature_setting.name.lower()}_{self._id}"
        self._attr_translation_key = (
            "temperature_setting_" + self._temperature_setting.name.lower()
        )

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""

        self._attr_native_value = device.temperature_settings.get(
            self._temperature_setting
        )
        self._attr_native_min_value = device.min_set_point
        self._attr_native_max_value = device.max_set_point

    async def async_set_native_value(self, value: float) -> None:
        """Set new value to the temperature setting on the thermostat device."""

        value = clamp(value, self.native_min_value, self.native_max_value)

        # Optimistic update so UI is aligned while data is being updated asynchronously
        self._attr_native_value = value
        self.async_write_ha_state()

        await self._async_execute_watts_command(
            self._api_client.set_device_temperature_setting(
                smart_home_id=self._smart_home_id,
                device_id=self._device_id,
                temperature_setting=self._temperature_setting,
                value=value,
            )
        )
