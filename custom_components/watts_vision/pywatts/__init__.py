from datetime import timedelta

import aiohttp

from .converter import convert_user, convert_smart_home, convert_change_mode_request, convert_temperature_settings_request
from .api import WattsApiClient, WATTS_API_BASE_URL, DEFAULT_LANGUAGE
from .auth import WattsCredentials
from .model import User, SmartHome, Mode, TemperatureSetting


class WattsVisionClient:

    def __init__(self, session: aiohttp.ClientSession, credentials: WattsCredentials, base_url: str = WATTS_API_BASE_URL, language: str = DEFAULT_LANGUAGE):
        self._api_client = WattsApiClient(session, credentials, base_url, language)


    async def has_valid_credentials(self) -> bool:
        try:
            await self._api_client.async_get_user_data()
            return True
        except:
            return False


    async def get_user(self) -> User:
        api_user_data = await self._api_client.async_get_user_data()
        return convert_user(api_user_data)


    async def get_smart_home(self, smart_home_id: str) -> SmartHome:
        api_smart_home_data = await self._api_client.async_get_smart_home_data(smart_home_id)
        return convert_smart_home(api_smart_home_data)


    async def get_last_connection(self, smart_home_id: str) -> timedelta:
        api_last_connection_data = await self._api_client.async_get_last_connection(smart_home_id)
        return timedelta(seconds=api_last_connection_data["diff"])
    

    async def change_device_mode(self, smart_home_id: str, device_id: str, mode: Mode, boost_duration: timedelta = timedelta()) -> None:
        settings = convert_change_mode_request(mode, boost_duration)

        await self._api_client.async_update_device(smart_home_id, device_id, settings)
    

    async def change_device_temperature_setting(self, smart_home_id: str, device_id: str, temperature_setting: TemperatureSetting, temperature: float) -> None:
        await self.change_device_temperature_settings(smart_home_id, device_id, { temperature_setting: temperature })
    

    async def change_device_temperature_settings(self, smart_home_id: str, device_id: str, temperature_settings: dict[TemperatureSetting, float]) -> None:
        settings = convert_temperature_settings_request(temperature_settings)

        await self._api_client.async_update_device(smart_home_id, device_id, settings)

