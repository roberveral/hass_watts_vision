"""Climate platform for Watts Vision integration.

This platform integrates Watts Vision thermostat devices into Home Assistant,
allowing users to monitor and control their heating and cooling systems.
"""

from datetime import datetime, timedelta
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    UnitOfTemperature,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import IntegrationError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    ALLOWED_HVAC_TRANSITIONS,
    API_COMMAND_EXPIRATION,
    ATTR_LAST_WATTS_MODE,
    ATTR_WATTS_HVAC_SETTING,
    ATTR_WATTS_MODE,
    ATTR_WATTS_TARGET_TEMPERATURE_SETTING,
    CONF_BOOST_DURATION,
    CONF_SMART_HOME_ID,
    DEFAULT_BOOST_DURATION,
    DOMAIN,
)
from .coordinator import WattsVisionCoordinator
from .device import thermostat_device_info
from .pywatts import WattsVisionClient
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
            entities.append(
                WattsThermostat(
                    coordinator, entry, device.id, device.device_id, zone.label
                )
            )

    async_add_entities(entities)


class WattsThermostat(CoordinatorEntity[WattsVisionCoordinator], ClimateEntity):
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
        config_entry: WattsVisionConfigEntry,
        id: str,
        device_id: str,
        zone_label: str,
    ):
        """Initialize the Watts Vision thermostat entity."""

        super().__init__(coordinator)
        self.client: WattsVisionClient = config_entry.runtime_data.client
        self.config_entry: WattsVisionConfigEntry = config_entry
        self.smart_home_id: str = config_entry.data[CONF_SMART_HOME_ID]
        self.id: str = id
        self.zone_label: str = zone_label
        self.device_id: str = device_id
        self._last_command_time: datetime | None = None
        self._last_device_state: Device | None = None

        # Properties
        self._attr_unique_id = "watts_thermostat_" + self.id
        self._attr_device_info = thermostat_device_info(
            unique_id=self.id,
            smart_home_id=self.smart_home_id,
            zone_label=self.zone_label,
        )

        # Initialize state from coordinator data
        self._update_data_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        has_recent_command = (
            self._last_command_time
            and self._last_command_time + API_COMMAND_EXPIRATION > datetime.now()
        )

        if has_recent_command:
            _LOGGER.debug(
                "Update for thermostat entity %s in recent command grace period since %s. Last device state: %s",
                self.id,
                self._last_command_time,
                self._last_device_state,
            )

        self._update_data_from_coordinator(ignore_unchanged=has_recent_command)
        super()._handle_coordinator_update()

    def _update_data_from_coordinator(self, ignore_unchanged: bool = False) -> None:
        """Update the entity's state based on the coordinator's data."""

        _LOGGER.debug(
            "Updating thermostat entity %s state from coordinator data",
            self.id,
        )

        device: Device = self.coordinator.data.get_device_by_id(self.id)
        if device is None:
            _LOGGER.error("Device with ID %s not found in Smart Home data.", self.id)
            return

        _LOGGER.debug("Thermostat entity %s found device data: %s", self.id, device)

        if ignore_unchanged and self._last_device_state == device:
            _LOGGER.debug(
                "No changes detected for thermostat entity %s; skipping update.",
                self.id,
            )
            return

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

        # Save last device state so we can detect changes while being able to prevent updates right after commands
        self._last_device_state = device

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode.

        When setting the HVAC mode to OFF, the last used Watts Vision mode is restored when turning back on,
        so it supports preset memory. If not, it defaults to COMFORT mode.
        """

        _LOGGER.debug(
            "Setting HVAC mode to %s for thermostat entity %s.",
            hvac_mode,
            self.id,
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

        await self._async_execute_command_with_revert(
            self.client.change_device_mode(
                self.smart_home_id,
                self.device_id,
                mode,
            )
        )

    async def async_turn_on(self):
        """Turn the entity on.

        It sets the HVAC mode to the current Watts Vision HVAC setting (HEAT or COOL),
        and restores the last used mode. Note that if Home Assistant is restarted, it
        will default to COMFORT mode when turn on as memory is not persisted.
        """

        _LOGGER.debug("Turning on thermostat entity %s.", self.id)

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

        _LOGGER.debug("Turning off thermostat entity %s.", self.id)

        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_preset_mode(self, preset_mode: str):
        """Set new target preset mode.

        It changes the current mode of the device in the Watts Vision system. When
        changing to BOOST mode, it uses the boost duration from the configuration.
        """

        _LOGGER.debug(
            "Setting preset mode to %s for thermostat entity %s.",
            preset_mode,
            self.id,
        )

        extra_args = {}

        # Handle boost mode duration from the configuration
        if preset_mode == Mode.BOOST.value:
            boost_time_settings = self.config_entry.options.get(CONF_BOOST_DURATION)
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

        await self._async_execute_command_with_revert(
            self.client.change_device_mode(
                self.smart_home_id,
                self.device_id,
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
            self.id,
            target_temp_setting,
        )

        # Optimistically update the hvac mode until the API confirms the change to avoid UI inconsistencies
        self._attr_target_temperature = value
        self.async_write_ha_state()

        await self._async_execute_command_with_revert(
            self.client.change_device_temperature_setting(
                self.smart_home_id,
                self.device_id,
                target_temp_setting,
                value,
            )
        )

    async def async_set_temperature_setting(
        self,
        temperature_comfort: float | None = None,
        temperature_eco: float | None = None,
        temperature_boost: float | None = None,
        temperature_antifreeze: float | None = None,
        temperature_manual: float | None = None,
    ):
        """Set new temperature settings for the thermostat.

        Implements the 'set_temperature_setting' service for Watts Vision thermostats, allowing
        to change multiple temperature settings at once without changing modes.
        """

        user_unit: UnitOfTemperature = self.hass.config.units.temperature_unit

        settings_to_update: dict[TemperatureSetting, float] = {}
        if temperature_comfort is not None:
            settings_to_update[TemperatureSetting.COMFORT] = clamp(
                TemperatureConverter.convert(
                    temperature_comfort, user_unit, self.temperature_unit
                ),
                self.min_temp,
                self.max_temp,
            )
        if temperature_eco is not None:
            settings_to_update[TemperatureSetting.ECO] = clamp(
                TemperatureConverter.convert(
                    temperature_eco, user_unit, self.temperature_unit
                ),
                self.min_temp,
                self.max_temp,
            )
        if temperature_boost is not None:
            settings_to_update[TemperatureSetting.BOOST] = clamp(
                TemperatureConverter.convert(
                    temperature_boost, user_unit, self.temperature_unit
                ),
                self.min_temp,
                self.max_temp,
            )
        if temperature_antifreeze is not None:
            settings_to_update[TemperatureSetting.ANTI_FREEZE] = clamp(
                TemperatureConverter.convert(
                    temperature_antifreeze, user_unit, self.temperature_unit
                ),
                self.min_temp,
                self.max_temp,
            )
        if temperature_manual is not None:
            settings_to_update[TemperatureSetting.MANUAL] = clamp(
                TemperatureConverter.convert(
                    temperature_manual, user_unit, self.temperature_unit
                ),
                self.min_temp,
                self.max_temp,
            )

        _LOGGER.debug(
            "Setting temperature settings: %s for thermostat entity %s.",
            settings_to_update,
            self.id,
        )

        await self.client.change_device_temperature_settings(
            self.smart_home_id,
            self.device_id,
            settings_to_update,
        )

        await self._record_command_sent()

    def _record_command_sent(self):
        """Record the time when a command was sent to the API."""

        self._last_command_time = datetime.now()

    async def _async_execute_command_with_revert(self, command_coro):
        """Execute a command coroutine and revert if it fails."""

        try:
            await command_coro
            self._record_command_sent()
        except Exception:
            # Revert optimistic update on failure
            self._update_data_from_coordinator()
            self.async_write_ha_state()
            raise
