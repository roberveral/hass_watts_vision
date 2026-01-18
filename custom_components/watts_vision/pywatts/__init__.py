"""High-level client for Watts Vision system.

Allows to fetch information and control devices in the Watts Vision smart home system,
focusing on climate control functionalities.

It provides an opinionated model that abstracts away the underlying API details,
making it easier to interact with the system, as it provides clearer information
about the state of devices and smart homes.
"""

from datetime import timedelta

import aiohttp

from .api import DEFAULT_LANGUAGE, WATTS_API_BASE_URL, WattsApiClient
from .auth import WattsCredentials
from .converter import (
    convert_change_mode_request,
    convert_smart_home,
    convert_temperature_settings_request,
    convert_user,
)
from .errors import WattsInvalidCredentialsError
from .model import Mode, SmartHome, TemperatureSetting, User


class WattsVisionClient:
    """High-level client for Watts Vision system.

    Allows to fetch information and control devices in the Watts Vision smart home system,
    focusing on climate control functionalities.

    It provides an opinionated model that abstracts away the underlying API details,
    making it easier to interact with the system, as it provides clearer information
    about the state of devices and smart homes.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        credentials: WattsCredentials,
        base_url: str = WATTS_API_BASE_URL,
        language: str = DEFAULT_LANGUAGE,
    ):
        """Initialize the Watts Vision client."""
        self._api_client = WattsApiClient(session, credentials, base_url, language)

    async def has_valid_credentials(self) -> bool:
        """Check if the provided credentials are valid in the Watts Vision system.

        This is done by attempting to fetch user data with the current credentials.
        """

        try:
            await self._api_client.async_get_user_data()
        except WattsInvalidCredentialsError:
            return False
        else:
            return True

    async def get_user(self) -> User:
        """Get the user information from the Watts Vision system.

        User information includes details such as username, email, and associated smart homes.
        This is the first step to access smart home data, as user data contains the list of smart homes,
        needed for the rest of the API calls.
        """
        api_user_data = await self._api_client.async_get_user_data()
        return convert_user(api_user_data)

    async def get_smart_home(self, smart_home_id: str) -> SmartHome:
        """Get the smart home information from the Watts Vision system.

        Smart home information includes details about devices, zones, and central unit configurations.
        """
        api_smart_home_data = await self._api_client.async_get_smart_home_data(
            smart_home_id
        )
        return convert_smart_home(api_smart_home_data)

    async def get_last_connection(self, smart_home_id: str) -> timedelta:
        """Get the delta since the last connection of the central unit in the given smart home to Watts servers.

        A high delta may indicate connectivity issues with the central unit, and will lead to delays in data updates.
        """
        api_last_connection_data = await self._api_client.async_get_last_connection(
            smart_home_id
        )
        return timedelta(seconds=api_last_connection_data["diff"])

    async def change_device_mode(
        self,
        smart_home_id: str,
        device_id: str,
        mode: Mode,
        boost_duration: timedelta = timedelta(),
    ) -> None:
        """Change the current mode of a device in a given smart home in the Watts Vision system.

        The update operation happens asynchronously even when successful, so there may be a delay before
        the change is reflected in subsequent read requests (no read-after-write consistency).
        """
        settings = convert_change_mode_request(mode, boost_duration)

        await self._api_client.async_update_device(smart_home_id, device_id, settings)

    async def change_device_temperature_setting(
        self,
        smart_home_id: str,
        device_id: str,
        temperature_setting: TemperatureSetting,
        temperature: float,
    ) -> None:
        """Change a temperature setting of a device in a given smart home in the Watts Vision system.

        Note that the current target of the device will only change if the target temperature setting
        is updated. But you can update other settings such as the eco or comfort temperatures without
        changing the current target.

        The update operation happens asynchronously even when successful, so there may be a delay before
        the change is reflected in subsequent read requests (no read-after-write consistency).
        """
        await self.change_device_temperature_settings(
            smart_home_id, device_id, {temperature_setting: temperature}
        )

    async def change_device_temperature_settings(
        self,
        smart_home_id: str,
        device_id: str,
        temperature_settings: dict[TemperatureSetting, float],
    ) -> None:
        """Change multiple temperature settings of a device in a given smart home in the Watts Vision system.

        Note that the current target of the device will only change if the target temperature setting
        is updated. But you can update other settings such as the eco or comfort temperatures without
        changing the current target.

        The update operation happens asynchronously even when successful, so there may be a delay before
        the change is reflected in subsequent read requests (no read-after-write consistency).
        """
        settings = convert_temperature_settings_request(temperature_settings)

        await self._api_client.async_update_device(smart_home_id, device_id, settings)
