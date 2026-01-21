"""Climate platform for Watts Vision integration.

This platform integrates Watts Vision thermostat devices into Home Assistant,
allowing users to monitor and control their heating and cooling systems.
"""

from datetime import timedelta
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    UnitOfTemperature,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import IntegrationError

from .const import (
    ALLOWED_HVAC_TRANSITIONS,
    ATTR_LAST_WATTS_MODE,
    ATTR_WATTS_HVAC_SETTING,
    ATTR_WATTS_MODE,
    ATTR_WATTS_TARGET_TEMPERATURE_SETTING,
    CONF_BOOST_DURATION,
    DEFAULT_BOOST_DURATION,
    DOMAIN,
)
from .coordinator import WattsVisionCoordinator
from .entity import WattsThermostatEntity
from .pywatts.model import Device, HVACSetting, Mode, Status, TemperatureSetting
from .types import WattsVisionConfigEntry
from .utils import clamp

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: WattsVisionConfigEntry, async_add_entities
):
    """Configures the CLIMATE platform for the Watts Vision integration."""

    _LOGGER.debug("Setting up climate entities for Watts Vision integration.")

    # Retrieve the rutime data for this entry
    coordinator = entry.runtime_data.coordinator

    # Create climate entities for each thermostat device in the configured smart home
    entities = []
    for zone in coordinator.data.zones:
        for device in zone.devices:
            _LOGGER.debug(
                "Found device %s in zone %s for climate entity.", device.id, zone.label
            )
            entities.append(WattsThermostat(coordinator, entry, device, zone.label))

    async_add_entities(entities)


class WattsThermostat(WattsThermostatEntity, ClimateEntity):
    """Representation of a Watts Vision thermostat device as a Climate entity.

    This class integrates a Watts Vision thermostat device into Home Assistant,
    allowing users to monitor and control the device's heating and cooling functions.

    It supports the basic HVAC modes (HEAT, COOL, OFF), preset modes (COMFORT, ECO, BOOST, etc.),
    and target temperature settings. The entity's state is kept in sync with the Watts Vision API
    through the WattsVisionCoordinator.

    While it could be argued that HVACMode.AUTO should be supported, and mapped to the
    Watts Vision PROGRAM mode, this is not implemented as it may be misleading due to Watts Vision
    not being able to switch automatically between heating and cooling based on temperature.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "thermostat"
    _attr_hvac_mode = HVACMode.HEAT
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
    _attr_preset_mode = Mode.COMFORT.value
    _attr_preset_modes = [mode.value for mode in Mode]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_extra_state_attributes = {}

    def __init__(
        self,
        coordinator: WattsVisionCoordinator,
        entry: WattsVisionConfigEntry,
        device: Device,
        suggested_area: str | None = None,
    ):
        """Initialize the Watts Vision thermostat entity."""

        super().__init__(coordinator, entry, device, suggested_area)

        # Properties
        self._attr_unique_id = f"watts_thermostat_{self._id}"

    def _update_entity_from_device(self, device: Device) -> None:
        """Update the entity's state based on the provided device data."""

        # Update attributes based on device data
        self._attr_current_temperature = device.current_temperature_air
        self._attr_min_temp = device.min_set_point
        self._attr_max_temp = device.max_set_point

        # Determine HVAC Mode based on system setting
        self._attr_hvac_mode = HVACMode.OFF
        if device.mode != Mode.OFF:
            if device.hvac_setting == HVACSetting.COOL:
                self._attr_hvac_mode = HVACMode.COOL
            else:
                self._attr_hvac_mode = HVACMode.HEAT

        # Determine HVAC Action based on current status
        self._attr_hvac_action = HVACAction.OFF
        if device.status == Status.HEATING:
            self._attr_hvac_action = HVACAction.HEATING
        elif device.status == Status.COOLING:
            self._attr_hvac_action = HVACAction.COOLING
        elif device.status == Status.IDLE:
            self._attr_hvac_action = HVACAction.IDLE

        # Determine Preset Mode
        self._attr_preset_mode = device.mode.value
        self._attr_target_temperature = device.target_temperature

        # Extra data for future reference...
        self.extra_state_attributes[ATTR_WATTS_HVAC_SETTING] = device.hvac_setting
        self.extra_state_attributes[ATTR_WATTS_MODE] = device.mode
        if device.mode != Mode.OFF:
            self.extra_state_attributes[ATTR_LAST_WATTS_MODE] = device.mode
        self.extra_state_attributes[ATTR_WATTS_TARGET_TEMPERATURE_SETTING] = (
            device.target_temperature_setting
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode.

        When setting the HVAC mode to OFF, the last used Watts Vision mode is restored when turning back on,
        so it supports preset memory. If not, it defaults to COMFORT mode.
        """

        _LOGGER.debug(
            "Setting HVAC mode to %s for thermostat entity %s.",
            hvac_mode,
            self._id,
        )

        hvac_setting: HVACSetting = self.extra_state_attributes.get(
            ATTR_WATTS_HVAC_SETTING
        )

        if hvac_mode not in ALLOWED_HVAC_TRANSITIONS.get(hvac_setting, []):
            raise IntegrationError(
                translation_domain=DOMAIN,
                translation_key="invalid_hvac_transition",
                translation_placeholders={
                    "hvac_mode": hvac_mode,
                    "hvac_setting": hvac_setting,
                },
            )

        mode: Mode = (
            Mode.OFF
            if hvac_mode == HVACMode.OFF
            else self.extra_state_attributes.get(ATTR_LAST_WATTS_MODE, Mode.COMFORT)
        )

        # Optimistically update the hvac mode until the API confirms the change to avoid UI inconsistencies
        self._attr_hvac_mode = hvac_mode
        self._attr_preset_mode = mode.value
        self.async_write_ha_state()

        await self._async_execute_watts_command(
            self._api_client.change_device_mode(
                self._smart_home_id,
                self._device_id,
                mode,
            )
        )

    async def async_turn_on(self):
        """Turn the entity on.

        It sets the HVAC mode to the current Watts Vision HVAC setting (HEAT or COOL),
        and restores the last used mode. Note that if Home Assistant is restarted, it
        will default to COMFORT mode when turn on as memory is not persisted.
        """

        _LOGGER.debug("Turning on thermostat entity %s.", self._id)

        watts_hvac_setting: HVACSetting = self.extra_state_attributes.get(
            ATTR_WATTS_HVAC_SETTING
        )

        if watts_hvac_setting == HVACSetting.COOL:
            await self.async_set_hvac_mode(HVACMode.COOL)
        else:
            await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        """Turn the entity off.

        It sets the HVAC mode to OFF.
        """

        _LOGGER.debug("Turning off thermostat entity %s.", self._id)

        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str):
        """Set new target preset mode.

        It changes the current mode of the device in the Watts Vision system. When
        changing to BOOST mode, it uses the boost duration from the configuration.
        """

        _LOGGER.debug(
            "Setting preset mode to %s for thermostat entity %s.",
            preset_mode,
            self._id,
        )

        extra_args = {}

        # Handle boost mode duration from the configuration
        if preset_mode == Mode.BOOST.value:
            boost_time_settings = self._entry.options.get(CONF_BOOST_DURATION)
            extra_args["boost_time"] = (
                timedelta(**boost_time_settings)
                if boost_time_settings
                else DEFAULT_BOOST_DURATION
            )

        # Optimistically update the preset mode until the API confirms the change to avoid UI inconsistencies
        self._attr_preset_mode = preset_mode
        if preset_mode == Mode.OFF.value:
            self._attr_hvac_mode = HVACMode.OFF
        self.async_write_ha_state()

        await self._async_execute_watts_command(
            self._api_client.change_device_mode(
                self._smart_home_id,
                self._device_id,
                Mode(preset_mode),
                **extra_args,
            )
        )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature.

        It will adjust the target temperature setting of the thermostat device in the Watts Vision system,
        clamped within the allowed min and max set points.

        This means that, for instance, when the thermostat mode is PROGRAM, it will change the temperature
        for the current active temperature setting (e.g., COMFORT or ECO).
        """

        if ATTR_TEMPERATURE not in kwargs:
            return

        value: float = float(kwargs[ATTR_TEMPERATURE])
        value = clamp(value, self.min_temp, self.max_temp)

        target_temp_setting: TemperatureSetting = self.extra_state_attributes.get(
            ATTR_WATTS_TARGET_TEMPERATURE_SETTING
        )

        _LOGGER.debug(
            "Setting target temperature to %s for thermostat entity %s, using temperature setting %s.",
            value,
            self._id,
            target_temp_setting,
        )

        # Optimistically update the hvac mode until the API confirms the change to avoid UI inconsistencies
        self._attr_target_temperature = value
        self.async_write_ha_state()

        await self._async_execute_watts_command(
            self._api_client.change_device_temperature_setting(
                self._smart_home_id,
                self._device_id,
                target_temp_setting,
                value,
            )
        )
