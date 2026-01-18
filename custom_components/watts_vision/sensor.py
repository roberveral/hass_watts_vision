"""Sensor platform for the Watts Vision integration.

This module defines sensor entities that represent various data points
from Watts Vision devices, such as temperature sensors and HVAC settings.

It exposes both diagnostic and regular sensors to Home Assistant, allowing users
to monitor their Watts Vision system effectively.
"""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SMART_HOME_ID
from .coordinator import WattsVisionCoordinator
from .device import central_unit_device_info, thermostat_device_info
from .pywatts.model import Device, HVACSetting
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
    entities.append(WattsCentralHVACSettingSensor(coordinator, entry))
    entities.append(WattsCentralCommunicationSensor(coordinator, entry))
    for zone in coordinator.data.zones:
        for device in zone.devices:
            _LOGGER.debug(
                "Found device %s in zone %s for sensor entity.", device.id, zone.label
            )
            entities.append(
                WattsTemperatureSensor(
                    coordinator, entry, device.id, device.device_id, zone.label
                )
            )
            entities.append(
                WattsHVACSettingSensor(
                    coordinator, entry, device.id, device.device_id, zone.label
                )
            )

    async_add_entities(entities)


class WattsTemperatureSensor(CoordinatorEntity[WattsVisionCoordinator], SensorEntity):
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
        config_entry: WattsVisionConfigEntry,
        id: str,
        device_id: str,
        zone_label: str,
    ) -> None:
        """Initialize the temperature sensor."""

        super().__init__(coordinator)
        self.id = id
        self.device_id = device_id
        self.zone_label = zone_label
        self.smart_home_id: str = config_entry.data[CONF_SMART_HOME_ID]
        self.client = config_entry.runtime_data.client
        self.config_entry = config_entry

        # Properties
        self._attr_unique_id = "watts_temperature_sensor_" + self.id
        self._attr_device_info = thermostat_device_info(
            unique_id=self.id,
            smart_home_id=self.smart_home_id,
            zone_label=self.zone_label,
        )

        self._update_value_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._update_value_from_coordinator()
        super()._handle_coordinator_update()

    def _update_value_from_coordinator(self):
        """Update the entity's state based on the coordinator's data."""

        _LOGGER.debug(
            "Updating temperature sensor entity %s state from coordinator data.",
            self.id,
        )

        device: Device = self.coordinator.data.get_device_by_id(self.id)
        if device is None:
            _LOGGER.error("Device with ID %s not found in Smart Home data.", self.id)
            return

        self._attr_native_value = device.current_temperature_air


class WattsHVACSettingSensor(CoordinatorEntity[WattsVisionCoordinator], SensorEntity):
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
        config_entry: WattsVisionConfigEntry,
        id: str,
        device_id: str,
        zone_label: str,
    ) -> None:
        """Initialize the temperature sensor."""

        super().__init__(coordinator)
        self.id = id
        self.device_id = device_id
        self.zone_label = zone_label
        self.smart_home_id: str = config_entry.data[CONF_SMART_HOME_ID]
        self.client = config_entry.runtime_data.client
        self.config_entry = config_entry

        # Properties
        self._attr_unique_id = "watts_hvac_setting_sensor_" + self.id
        self._attr_device_info = thermostat_device_info(
            unique_id=self.id,
            smart_home_id=self.smart_home_id,
            zone_label=self.zone_label,
        )

        self._update_value_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._update_value_from_coordinator()
        super()._handle_coordinator_update()

    def _update_value_from_coordinator(self):
        """Update the entity's state based on the coordinator's data."""

        _LOGGER.debug(
            "Updating HVAC setting sensor entity %s state from coordinator data.",
            self.id,
        )

        device: Device = self.coordinator.data.get_device_by_id(self.id)
        if device is None:
            _LOGGER.error("Device with ID %s not found in Smart Home data.", self.id)
            return

        self._attr_native_value = device.hvac_setting.value


class WattsCentralHVACSettingSensor(
    CoordinatorEntity[WattsVisionCoordinator], SensorEntity
):
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
        self, coordinator: WattsVisionCoordinator, config_entry: WattsVisionConfigEntry
    ) -> None:
        """Initialize the temperature sensor."""

        super().__init__(coordinator)
        self.smart_home_id: str = config_entry.data[CONF_SMART_HOME_ID]
        self.client = config_entry.runtime_data.client
        self.config_entry = config_entry

        # Properties
        self._attr_unique_id = "watts_central_hvac_setting_sensor_" + self.smart_home_id
        self._attr_device_info = central_unit_device_info(
            smart_home_id=self.smart_home_id,
            smart_home_name=self.coordinator.data.label,
            mac_address=self.coordinator.data.mac_address,
        )

        self._update_value_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._update_value_from_coordinator()
        super()._handle_coordinator_update()

    def _update_value_from_coordinator(self):
        """Update the entity's state based on the coordinator's data."""

        _LOGGER.debug(
            "Updating Central HVAC setting sensor entity %s state from coordinator data.",
            self.smart_home_id,
        )

        self._attr_native_value = self.coordinator.data.hvac_setting.value


class WattsCentralCommunicationSensor(SensorEntity):
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
        self, coordinator: WattsVisionCoordinator, config_entry: WattsVisionConfigEntry
    ) -> None:
        """Initialize the temperature sensor."""

        self.smart_home_id: str = config_entry.data[CONF_SMART_HOME_ID]
        self.client = config_entry.runtime_data.client
        self.config_entry = config_entry
        self.coordinator = coordinator

        # Properties
        self._attr_unique_id = (
            "watts_central_communication_sensor_" + self.smart_home_id
        )
        self._attr_device_info = central_unit_device_info(
            smart_home_id=self.smart_home_id,
            smart_home_name=self.coordinator.data.label,
            mac_address=self.coordinator.data.mac_address,
        )

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""

        _LOGGER.debug(
            "Updating Central Communication sensor entity %s state from client data.",
            self.smart_home_id,
        )

        time_since_last_connection = (
            await self.config_entry.runtime_data.client.get_last_connection(
                self.smart_home_id
            )
        )
        self._attr_native_value = time_since_last_connection.total_seconds()
