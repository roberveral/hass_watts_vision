import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .pywatts.model import Device, ErrorCode

from .types import WattsVisionConfigEntry
from .const import CONF_SMART_HOME_ID, DOMAIN, MANUFACTURER, THERMOSTAT_MODEL
from .coordinator import WattsVisionCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: WattsVisionConfigEntry, async_add_entities):
    """Configures the BINARY_SENSOR platform for the Watts Vision integration."""
    
    _LOGGER.debug("Setting up binary sensor entities for Watts Vision integration.")

    # Retrieve the rutime data for this entry
    coordinator = entry.runtime_data.coordinator

    # Create sensor entities for each thermostat device in the configured smart home
    entities = []
    for zone in coordinator.data.zones:
        for device in zone.devices:
            _LOGGER.debug(f"Found device {device.id} in zone {zone.label} for sensor entity.")
            entities.append(WattsBatterySensor(coordinator, entry, device.id, device.device_id, zone.label))
    
    async_add_entities(entities)


class WattsBatterySensor(CoordinatorEntity[WattsVisionCoordinator], BinarySensorEntity):
    """Representation of a Battery Sensor from a Watts Vision Thermostat."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WattsVisionCoordinator, config_entry: WattsVisionConfigEntry, id: str, device_id: str, zone_label: str) -> None:
        """Initialize the battery sensor."""

        super().__init__(coordinator)
        self.id = id
        self.device_id = device_id
        self.zone_label = zone_label
        self.smart_home_id: str = config_entry.data[CONF_SMART_HOME_ID]
        self.client = config_entry.runtime_data.client
        self.config_entry = config_entry

        # Properties
        self._attr_unique_id = "watts_battery_sensor_" + self.id
        self._attr_name = self.zone_label + " Battery"

        self._update_value_from_coordinator()


    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.id)
            },
            "manufacturer": MANUFACTURER,
            "name": "Thermostat " + self.zone_label,
            "model": THERMOSTAT_MODEL,
            "via_device": (DOMAIN, self.smart_home_id),
            "suggested_area": self.zone_label,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._update_value_from_coordinator()
        super()._handle_coordinator_update()


    def _update_value_from_coordinator(self):
        """Update the entity's state based on the coordinator's data."""
        
        _LOGGER.debug(f"Updating battery sensor entity {self.id} state from coordinator data.")

        device: Device = self.coordinator.data.get_device_by_id(self.id)
        if device is None:
            _LOGGER.error(f"Device with ID {self.id} not found in Smart Home data.")
            return
        
        self._attr_is_on = device.error_code == ErrorCode.BATTERY_LOW
