from typing import TypedDict, TypeVar, Generic
import logging
import aiohttp

from .auth import WattsAuthenticationClient, WattsCredentials, WattsAuthentication
from .errors import WattsVisionAuthenticationError, WattsVisionApiCodeError, WattsVisionApiStatusError

T = TypeVar("T")

#region Constants

WATTS_API_BASE_URL = "https://smarthome.wattselectronics.com/api"
DEFAULT_LANGUAGE = "en_GB"
DEFAULT_UPDATE_EXPIRATION = 20000

#region Bundle

BUNDLE_CLIMATE = "1"
BUNDLE_SENSOR = "2"
BUNDLE_LIGHT = "3"
BUNDLE_ONOFF = "4"

#endregion

#region NVGV Modes

NVGV_MODE_CONFORT = "0"
NVGV_MODE_OFF = "1"
NVGV_MODE_HORS_GEL = "2"
NVGV_MODE_ECO = "3"
NVGV_MODE_BOOST = "4"
NVGV_MODE_AUTO_CONFORT = "8"
NVGV_MODE_AUTO_ECO = "11"
NVGV_MODE_ON = "12"
NVGV_MODE_AUTO = "13"
NVGV_MODE_DESACTIVE = "14"

#endregion

#region Entity Types

TYPE_DEVICE = "1"
TYPE_SMART_HOME = "2"
TYPE_ZONE = "3"
TYPE_QUERY = "4"
TYPE_USER = "5"
TYPE_SANDBOX = "9"
TYPE_STATS = "10"

#endregion

#endregion

#region API Response Types

class WattsApiResponseCode(TypedDict):
    code: str
    key: str
    value: str

    @staticmethod
    def is_successful(value) -> bool:
        return "OK" in value["key"]


class WattsApiResponse(Generic[T], TypedDict):
    code: WattsApiResponseCode
    data: T | None


class WattsApiDevice(TypedDict):
    id: str
    id_device: str
    nom_appareil: str
    programme: str
    consigne_confort: str
    consigne_hg: str
    consigne_eco: str
    consigne_boost: str
    consigne_manuel: str
    min_set_point: str
    max_set_point: str
    time_boost: str
    nv_mode: str
    temperature_air: str
    temperature_sol: str
    on_off: str | None
    gv_mode: str
    puissance_app: str
    label_interface: str
    heating_up: str
    heat_cool: str
    fan_speed: int
    error_code: int
    bit_override: str
    fan_error: str
    bundle_id: str
    num_zone: str


class WattsApiZone(TypedDict):
    devices: list[WattsApiDevice]
    zone_label: str
    num_zone: str
    label_zone_type: str
    picto_zone_type: str
    zone_img_id: str


class WattsApiSmartHomeSummary(TypedDict):
    label: str
    latitude: str
    longitude: str
    smarthome_id: str
    mac_address: str
    general_mode: str
    holiday_mode: str
    param_c_f: str
    address_position: str


class WattsApiUserSummary(TypedDict):
    user_email: str
    user_id: str


class WattsApiUserData(TypedDict):
    email: str
    smarthomes: list[WattsApiSmartHomeSummary]
    user_id: str
    cgu_id: str
    lang_code: str
    optin_stats: str


class WattsApiSmartHomeData(TypedDict):
    devices: list[WattsApiDevice]
    zones: list[WattsApiZone]
    users: list[WattsApiUserSummary]
    modes: list # ??
    smarthome_id: str
    label: str
    mac_address: str
    general_mode: str
    holiday_mode: str
    holiday_start: str
    holiday_end: str
    param_c_f: str
    jet_lag: int
    address_position: str


class WattsApiLastConnectionDiff(TypedDict):
    days: int
    hours: int
    minutes: int
    seconds: int


class WattsApiLastConnectionData(TypedDict):
    diff: int
    diffObj: WattsApiLastConnectionDiff

#endregion

_LOGGER = logging.getLogger(__name__)

class WattsApiClient:
    
    def __init__(self, session: aiohttp.ClientSession, credentials: WattsCredentials, base_url: str = WATTS_API_BASE_URL, language: str = DEFAULT_LANGUAGE):
        self._session = session
        self._base_url = base_url
        self._language = language
        self._auth_client: WattsAuthenticationClient = WattsAuthenticationClient(session, credentials)
        self._authentication: WattsAuthentication = None


    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._authentication.access_token}"
        }
    

    async def _perform_request(self, endpoint: str, payload: dict) -> T:
        self._authentication = await self._auth_client.async_create_or_refresh_authentication(self._authentication)

        url = f"{self._base_url}{endpoint}"

        _LOGGER.debug("Performing Watts API request to %s with payload: %s", endpoint, payload)

        async with self._session.post(url, headers=self._get_headers(), data=payload) as response:
            if response.status == 401:
                _LOGGER.error("Watts API request failed with status code 401")
                raise WattsVisionAuthenticationError()
            if response.status != 200:
                _LOGGER.error("Watts API request failed with status code %d: %s", response.status, await response.text())
                raise WattsVisionApiStatusError(response.status)
            
            api_response: WattsApiResponse[T] = await response.json()

            _LOGGER.debug("Watts API request to %s succeeded with response: %s", endpoint, api_response)
        
            if not WattsApiResponseCode.is_successful(api_response["code"]):
                _LOGGER.error("Watts API request returned error code: %s", api_response["code"])
                raise WattsVisionApiCodeError(
                    code=api_response["code"]["code"],
                    key=api_response["code"]["key"],
                    value=api_response["code"]["value"],
                )


            return api_response["data"]



    async def async_get_user_data(self) -> WattsApiUserData:
        payload = {
            "token": "true",
            "lang": self._language,
            "email": self._auth_client._credentials.username,
        }

        return await self._perform_request("/v0.1/human/user/read/", payload)


    async def async_get_smart_home_data(self, smart_home_id: str) -> WattsApiSmartHomeData:
        payload = {
            "token": "true",
            "smarthome_id": smart_home_id,
            "lang": self._language,
        }

        return await self._perform_request("/v0.1/human/smarthome/read/", payload)
    

    async def async_get_last_connection(self, smart_home_id: str) -> WattsApiLastConnectionData:
        payload = {
            "token": "true",
            "smarthome_id": smart_home_id,
            "lang": self._language,
        }

        return await self._perform_request("/v0.1/human/sandbox/check_last_connexion/", payload)


    async def async_push_data(self, smart_home_id: str, settings: dict, entity_type: str, expiration: int = DEFAULT_UPDATE_EXPIRATION) -> None:
        payload = {
            "token": "true",
            "context": entity_type,
            "smarthome_id": smart_home_id,
            "lang": self._language,
            "peremption": str(expiration),
        }
        # Add settings to payload
        for key, value in settings.items():
            payload[f"query[{key}]"] = value

        await self._perform_request("/v0.1/human/query/push/", payload)


    async def async_update_smart_home(self, smart_home_id: str, settings: dict, expiration: int = DEFAULT_UPDATE_EXPIRATION) -> None:
        await self.async_push_data(smart_home_id, settings, TYPE_SMART_HOME, expiration)


    async def async_update_device(self, smart_home_id: str, device_id: str, settings: dict, expiration: int = DEFAULT_UPDATE_EXPIRATION) -> None:
        await self.async_push_data(smart_home_id, settings={"id_device": device_id, **settings}, entity_type=TYPE_DEVICE, expiration=expiration)