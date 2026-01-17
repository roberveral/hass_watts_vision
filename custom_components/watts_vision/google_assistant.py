from typing import Any
import logging

from homeassistant.const import STATE_OFF, STATE_UNKNOWN, ATTR_ENTITY_ID
from homeassistant.components.google_assistant.trait import (
    register_trait,
    ModesTrait,
)
from homeassistant.components import climate

_LOGGER = logging.getLogger(__name__)

@register_trait
class ClimateModesTrait(ModesTrait):
    """Trait to set modes.

    https://developers.google.com/actions/smarthome/traits/modes
    """

    SYNONYMS = {
        "preset mode": [
            { "synonyms": ["preset mode", "preset"], "lang": "en" },
            { "synonyms": ["modo de preajuste", "preajuste"], "lang": "es" },
        ],
        "Comfort": [
            { "synonyms": ["comfort", "manual"], "lang": "en" },
            { "synonyms": ["confort", "manual"], "lang": "es" },
        ],
        "Eco": [
            { "synonyms": ["eco", "economy"], "lang": "en" },
            { "synonyms": ["eco", "económico", "ahorro"], "lang": "es" },
        ],
        "Boost": [
            { "synonyms": ["boost", "quick heat"], "lang": "en" },
            { "synonyms": ["boost", "calentamiento rápido"], "lang": "es" },
        ],
        "Anti-Freeze": [
            { "synonyms": ["anti-freeze", "frost protection"], "lang": "en" },
            { "synonyms": ["antihielo", "protección contra heladas"], "lang": "es" },
        ],
        "Program": [
            { "synonyms": ["program", "schedule", "auto"], "lang": "en" },
            { "synonyms": ["programa", "horario", "automático"], "lang": "es" },
        ],
        "Off": [
            { "synonyms": ["off", "turn off"], "lang": "en" },
            { "synonyms": ["apagado", "apagar"], "lang": "es" },
        ],
    }


    @staticmethod
    def supported(domain, features, device_class, _):
        """Test if state is supported."""

        return domain == climate.DOMAIN and features & climate.ClimateEntityFeature.PRESET_MODE

    def _generate(self, name, settings):
        """Generate a list of modes."""
        mode = {
            "name": name,
            "name_values": [
                {"name_synonym": syn["synonyms"], "lang": syn["lang"]} for syn in self.SYNONYMS.get(name, [])
            ],
            "settings": [],
            "ordered": False,
        }
        for setting in settings:
            mode["settings"].append(
                {
                    "setting_name": setting,
                    "setting_values": [
                        { "setting_synonym": syn["synonyms"], "lang": syn["lang"]} for syn in self.SYNONYMS.get(setting, [])
                    ],
                }
            )
        return mode

    def sync_attributes(self) -> dict[str, Any]:
        """Return mode attributes for a sync request."""
        modes = []

        _LOGGER.debug("Generating ModesTrait SYNC attributes for %s", self.state.entity_id)

        for domain, attr, name in (
            (climate.DOMAIN, climate.ATTR_PRESET_MODES, "preset mode"),
        ):
            if self.state.domain != domain:
                continue

            if (items := self.state.attributes.get(attr)) is not None:
                modes.append(self._generate(name, items))

            # Shortcut since all domains are currently unique
            break

        _LOGGER.debug("ModesTrait SYNC attributes for %s: %s", self.state.entity_id, modes)

        return {"availableModes": modes}

    def query_attributes(self) -> dict[str, Any]:
        """Return current modes."""
        attrs = self.state.attributes
        response: dict[str, Any] = {}
        mode_settings = {}

        _LOGGER.debug("Generating ModesTrait QUERY attributes for %s", self.state.entity_id)

        if self.state.domain == climate.DOMAIN:
            if climate.ATTR_PRESET_MODES in attrs:
                mode_settings["preset mode"] = attrs.get(climate.ATTR_PRESET_MODE)


        if mode_settings:
            response["on"] = self.state.state not in (STATE_OFF, STATE_UNKNOWN)
            response["currentModeSettings"] = mode_settings

        _LOGGER.debug("ModesTrait QUERY attributes for %s: %s", self.state.entity_id, response)

        return response

    async def execute(self, command, data, params, challenge):
        """Execute a SetModes command."""
        settings = params.get("updateModeSettings")

        _LOGGER.debug("Executing ModesTrait command for %s: %s", self.state.entity_id, settings)

        if self.state.domain == climate.DOMAIN:
            preset_mode = settings["preset mode"]
            await self.hass.services.async_call(
                climate.DOMAIN,
                climate.SERVICE_SET_PRESET_MODE,
                {
                    ATTR_ENTITY_ID: self.state.entity_id,
                    climate.ATTR_PRESET_MODE: preset_mode,
                },
                blocking=not self.config.should_report_state,
                context=data.context,
            )
            return


        _LOGGER.info(
            "Received an Options command for unrecognised domain %s",
            self.state.domain,
        )
        return
