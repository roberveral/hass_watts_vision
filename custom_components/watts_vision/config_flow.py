from datetime import timedelta
import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .pywatts.auth import WattsCredentials
from .pywatts.model import User
from .pywatts import WattsVisionClient

from .const import (
    DOMAIN,
    CONF_SMART_HOME_ID,
    CONF_BOOST_DURATION,
    DEFAULT_BOOST_DURATION,
    DEFAULT_SCAN_INTERVAL,
)
from .utils import timedelta_to_dict

_LOGGER = logging.getLogger(__name__)

class WattsVisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self):
        self.auth_data = {}
        self.client: WattsVisionClient | None = None
        self.smart_home_id: str | None = None


    async def async_step_user(self, user_input: dict | None = None):
        """Defines the first configuration step where the user provides authentication details."""

        errors = {}
        if user_input is not None:

            _LOGGER.debug("Received user input for authentication in Watts Vision integration.")
            # Initialize the Watts Vision client with provided credentials
            session = async_get_clientsession(self.hass)
            self.client = WattsVisionClient(
                session,
                credentials=WattsCredentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            )

            # Validate credentials against the Watts Vision API
            if await self.client.has_valid_credentials():
                _LOGGER.debug("Authentication successful for user: %s", user_input[CONF_USERNAME])
                self.auth_data = user_input
                return await self.async_step_select_home()
            else:
                _LOGGER.warning("Authentication failed for user: %s", user_input[CONF_USERNAME])
                errors["base"] = "invalid_auth"

        _LOGGER.debug("Displaying user authentication form for Watts Vision integration.")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )


    async def async_step_select_home(self, user_input: dict | None = None):
        """Defines the step where the user selects a Smart Home to configure after authentication."""

        if user_input is not None:
            self.smart_home_id = user_input[CONF_SMART_HOME_ID]

            _LOGGER.debug("Selected Smart Home ID: %s", self.smart_home_id)

            return self.async_create_entry(
                title=f"Watts Vision: {self.auth_data[CONF_USERNAME]} - {self.smart_home_id}",
                data={**self.auth_data, **user_input}
            )

        _LOGGER.debug("Fetching list of Smart Homes for user: %s", self.auth_data.get(CONF_USERNAME))

        # Fetch user details to get its Smart Homes from the Watts Vision API
        user: User = await self.client.get_user()

        return self.async_show_form(
            step_id="select_home",
            data_schema=vol.Schema({
                vol.Required(CONF_SMART_HOME_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[{"value": home.id, "label": home.label} for home in user.smart_homes],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WattsVisionOptionsFlow()
    

class WattsVisionOptionsFlow(config_entries.OptionsFlowWithReload):

    async def async_step_init(self, user_input: dict | None = None):
        """Handles the options that can be changed for the integration."""

        if user_input is not None:
            _LOGGER.debug("Updating options for Watts Vision integration: %s", user_input)
            return self.async_create_entry(data=user_input)

        _LOGGER.debug("Displaying options form for Watts Vision integration.")

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=timedelta_to_dict(DEFAULT_SCAN_INTERVAL)
                    ): selector.DurationSelector(selector.DurationSelectorConfig(enable_day=False)),
                    vol.Optional(
                        CONF_BOOST_DURATION,
                        default=timedelta_to_dict(DEFAULT_BOOST_DURATION)
                    ): selector.DurationSelector(selector.DurationSelectorConfig(enable_day=False, enable_millisecond=False)),
                }),
                self.config_entry.options
            )
        )

