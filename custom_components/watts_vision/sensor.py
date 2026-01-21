"""Sensor platform for the Watts Vision integration.

This module defines sensor entities that represent various data points
from Watts Vision devices, such as temperature sensors and HVAC settings.

It exposes both diagnostic and regular sensors to Home Assistant, allowing users
to monitor their Watts Vision system effectively.
"""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant

from .coordinator import WattsVisionCoordinator
from .entity import WattsCentralUnitEntity, WattsThermostatEntity
from .pywatts.model import Device, HVACSetting, SmartHome
from .types import WattsVisionConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: WattsVisionConfigEntry, async_add_entities
):
    """Configures the SENSOR platform for the Watts Vision integration."""

    _LOGGER.debug("Setting up sensor entities for Watts Vision integration.")

    # Retrieve the rutime data for this entry
    coordinator = entry.runtime_data.coordinator

    # Create sensor entities for each thermostat device in the configured smart home
    entities = []
    entities.append(WattsCentralHVACSettingSensor(coordinator, entry, coordinator.data))
    entities.append(
        WattsCentralCommunicationSensor(coordinator, entry, coordinator.data)
    )
    for zone in coordinator.data.zones:
        for device in zone.devices:
            _LOGGER.debug(
                "Found device %s in zone %s for sensor entity.", device.id, zone.label
            )
            entities.append(
                WattsTemperatureSensor(coordinator, entry, device, zone.label)
            )
            entities.append(
                WattsFloorTemperatureSensor(coordinator, entry, device, zone.label)
            )
            entities.append(
                WattsHVACSettingSensor(coordinator, entry, device, zone.label)
            )

    async_add_entities(entities)


class WattsTemperatureSensor(WattsThermostatEntity, SensorEntity):
    """Representation of a Temperature Sensor from a Watts Vision Thermostat.

    While the thermostat device itself is represented as a climate entity, it is
    also useful to expose the current temperature as a separate sensor entity so it
    can be used without requiring the whole climate platform.
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        device: Device,
        suggested_area: str | None = None,
    ) -> None:
        """Initialize the temperature sensor."""

        super().__init__(coordinator, entry, device, suggested_area)

        # Properties
        self._attr_unique_id = f"watts_temperature_sensor_{self._id}"

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""

        self._attr_native_value = device.current_temperature_air


class WattsFloorTemperatureSensor(WattsThermostatEntity, SensorEntity):
    """Representation of a Floor Temperature Sensor from a Watts Vision Thermostat.

    It exposes the current floor temperature as a separate diagnostic sensor entity, as
    reported by the thermostat device.
    """

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "floor_temperature"

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        device: Device,
        suggested_area: str | None = None,
    ) -> None:
        """Initialize the temperature sensor."""

        super().__init__(coordinator, entry, device, suggested_area)

        # Properties
        self._attr_unique_id = f"watts_floor_temperature_sensor_{self._id}"

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""

        self._attr_native_value = device.current_temperature_floor


class WattsHVACSettingSensor(WattsThermostatEntity, SensorEntity):
    """Representation of a HVAC setting sensor from a Watts Vision Thermostat.

    This diagnostic sensor gives visibility into the current HVAC setting (heat or cool) of
    the thermostat device. This enables actions like setting temperature settings based on
    the season.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "hvac_setting"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [setting.value for setting in HVACSetting]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        device: Device,
        suggested_area: str | None = None,
    ) -> None:
        """Initialize the HVAC setting sensor."""

        super().__init__(coordinator, entry, device, suggested_area)

        # Properties
        self._attr_unique_id = f"watts_hvac_setting_sensor_{self._id}"

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""

        self._attr_native_value = device.hvac_setting.value


class WattsCentralHVACSettingSensor(WattsCentralUnitEntity, SensorEntity):
    """Representation of a HVAC setting sensor from a Watts Vision Thermostat.

    This diagnostic sensor gives visibility into the current HVAC setting (heat or cool) of
    the central unit, and therefore the whole system. Thermostat devices will inherit this
    setting.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "hvac_setting"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [setting.value for setting in HVACSetting]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        smart_home: SmartHome,
    ) -> None:
        """Initialize the temperature sensor."""

        super().__init__(coordinator, entry, smart_home)

        # Properties
        self._attr_unique_id = (
            f"watts_central_hvac_setting_sensor_{self._smart_home_id}"
        )

    def _update_entity_from_smart_home(self, smart_home: SmartHome) -> None:
        """Update the entity's state based on the provided smart home data."""
        self._attr_native_value = smart_home.hvac_setting.value


class WattsCentralCommunicationSensor(WattsCentralUnitEntity, SensorEntity):
    """Representation of a last communication sensor from a Watts Vision Thermostat.

    This diagnostic sensor gives visibility into the delta since the last successful communication
    of the central unit to the Watts servers. A high delta may indicate connectivity issues with
    the central unit, and will lead to delays in data updates.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "communication_delay"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        smart_home: SmartHome,
    ) -> None:
        """Initialize the temperature sensor."""

        super().__init__(coordinator, entry, smart_home)

        # Properties
        self._attr_unique_id = (
            f"watts_central_communication_sensor_{self._smart_home_id}"
        )

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""

        # TODO: fetch last communication when fetching SmartHome data so communicaiton is
        # centralized.

        _LOGGER.debug(
            "Updating Central Communication sensor entity %s state from client data.",
            self.smart_home_id,
        )

        time_since_last_connection = (
            await self.config_entry.runtime_data.client.get_last_connection(
                self._smart_home_id
            )
        )
        self._attr_native_value = time_since_last_connection.total_seconds()


# TODO: add diagnostic sensor for boost time.
