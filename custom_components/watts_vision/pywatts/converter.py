from datetime import timedelta

from .api import *
from .model import *

#region Constants

# From: https://smarthome.wattselectronics.com/api/v0.1/human/mobile/read_demo/
DEVICE_MODE_TO_MODEL: dict[str, (Mode, TemperatureSetting)] = {
    NVGV_MODE_CONFORT: (Mode.COMFORT, TemperatureSetting.COMFORT),
    NVGV_MODE_OFF: (Mode.OFF, TemperatureSetting.NONE),
    NVGV_MODE_HORS_GEL: (Mode.ANTI_FREEZE, TemperatureSetting.ANTI_FREEZE),
    NVGV_MODE_ECO: (Mode.ECO, TemperatureSetting.ECO),
    NVGV_MODE_BOOST: (Mode.BOOST, TemperatureSetting.BOOST),
    NVGV_MODE_AUTO_CONFORT: (Mode.PROGRAM, TemperatureSetting.COMFORT),
    NVGV_MODE_AUTO_ECO: (Mode.PROGRAM, TemperatureSetting.ECO),
    NVGV_MODE_ON: (Mode.COMFORT, TemperatureSetting.NONE),
    NVGV_MODE_AUTO: (Mode.PROGRAM, TemperatureSetting.NONE),
    NVGV_MODE_DESACTIVE: (Mode.OFF, TemperatureSetting.NONE),
}

# Potentially use a call to get errors which includes more detail
# if new possible errors arise without error codes changing.
# https://smarthome.wattselectronics.com/api/v0.1/human/smarthome/get_errors/
ERROR_CODE_TO_MODEL: dict[int, ErrorCode] = {
    0: ErrorCode.NONE,
    1: ErrorCode.BATTERY_LOW,
}

TEMPERATURE_UNIT_FACTOR: float = 10.0
DEFAULT_BOOST_DURATION: timedelta = timedelta(seconds=7200)

#endregion

#region Helpers

def parse_temperature(value: str, unit_factor: float = TEMPERATURE_UNIT_FACTOR) -> float:
    return float(value) / unit_factor


def write_temperature(value: float, unit_factor: float = TEMPERATURE_UNIT_FACTOR) -> str:
    return str(int(value * unit_factor))


def write_duration(duration: timedelta) -> str:
    return str(int(duration.total_seconds()))


def parse_duration(value: str) -> timedelta:
    return timedelta(seconds=int(value))


#endregion

#region API to Model Converters

def convert_device(device_data: WattsApiDevice) -> Device:
    # Determine HVAC setting based on whether the device is in heating or cooling mode
    hvac_setting = HVACSetting.COOL if device_data["heat_cool"] == "1" else HVACSetting.HEAT

    # Map device mode and target temperature setting from API gv_mode
    mode, target_temp_setting = DEVICE_MODE_TO_MODEL.get(
        device_data["gv_mode"],
        (Mode.OFF, TemperatureSetting.NONE)
    )

    # Build temperature settings dictionary with current settings
    temperature_settings = {
        TemperatureSetting.COMFORT: parse_temperature(device_data["consigne_confort"]),
        TemperatureSetting.ECO: parse_temperature(device_data["consigne_eco"]),
        TemperatureSetting.BOOST: parse_temperature(device_data["consigne_boost"]),
        TemperatureSetting.ANTI_FREEZE: parse_temperature(device_data["consigne_hg"]),
        TemperatureSetting.MANUAL: parse_temperature(device_data["consigne_manuel"]),
    }

    # Determine target temperature based on current mode and settings
    target_temperature = None
    if target_temp_setting != TemperatureSetting.NONE:
        target_temperature = temperature_settings[target_temp_setting]
    
    # Determine current status of the device
    status = Status.OFF
    if device_data["heating_up"] == "1" and hvac_setting == HVACSetting.HEAT:
        status = Status.HEATING
    elif device_data["heating_up"] == "1" and hvac_setting == HVACSetting.COOL:
        status = Status.COOLING
    elif device_data["heating_up"] == "0" and mode != Mode.OFF:
        status = Status.IDLE

    return Device(
        id=device_data["id"],
        device_id=device_data["id_device"],
        label=device_data["label_interface"],
        hvac_setting=hvac_setting,
        mode=mode,
        target_temperature_setting=target_temp_setting,
        target_temperature=target_temperature,
        temperature_settings=temperature_settings,
        current_temperature_air=parse_temperature(device_data["temperature_air"]),
        current_temperature_floor=parse_temperature(device_data["temperature_sol"]),
        min_set_point=parse_temperature(device_data["min_set_point"]),
        max_set_point=parse_temperature(device_data["max_set_point"]),
        status=status,
        error_code=ERROR_CODE_TO_MODEL.get(device_data["error_code"], ErrorCode.NONE),
    )


def convert_zone(zone_data: WattsApiZone) -> Zone:
    devices = [convert_device(device) for device in zone_data["devices"]]

    return Zone(
        id=zone_data["num_zone"],
        label=zone_data["zone_label"],
        devices=devices
    )


def convert_smart_home(home_data: WattsApiSmartHomeData) -> SmartHome:
    devices = [convert_device(device) for device in home_data["devices"]]
    zones = [convert_zone(zone) for zone in home_data["zones"]]

    return SmartHome(
        id=home_data["smarthome_id"],
        label=home_data["label"],
        latitude=float(home_data["latitude"]),
        longitude=float(home_data["longitude"]),
        address=home_data.get("address", ""),
        mac_address=home_data["mac_address"],
        hvac_setting=HVACSetting.COOL if home_data["param_c_f"] == "f" else HVACSetting.HEAT,
        devices=devices,
        zones=zones
    )


def convert_smart_home_summary(home_summary_data: WattsApiSmartHomeSummary) -> SmartHomeSummary:
    return SmartHomeSummary(
        id=home_summary_data["smarthome_id"],
        label=home_summary_data["label"],
        latitude=float(home_summary_data["latitude"]),
        longitude=float(home_summary_data["longitude"]),
        address=home_summary_data.get("address", ""),
        mac_address=home_summary_data["mac_address"],
        hvac_setting=HVACSetting.COOL if home_summary_data["param_c_f"] == "f" else HVACSetting.HEAT,
    )


def convert_user(user_data: WattsApiUserData) -> User:
    smart_homes = [convert_smart_home_summary(home) for home in user_data["smarthomes"]]

    return User(
        id=user_data["user_id"],
        email=user_data["email"],
        smart_homes=smart_homes
    )

#endregion

#region Model to API Converters

def convert_mode_to_api(mode: Mode) -> str:
    for api_mode, (model_mode, _) in DEVICE_MODE_TO_MODEL.items():
        if model_mode == mode:
            return api_mode
    
    return None


def convert_temperature_setting_to_api(temperature_setting: TemperatureSetting) -> str:
    if temperature_setting == TemperatureSetting.COMFORT:
        return "consigne_confort"
    elif temperature_setting == TemperatureSetting.ECO:
        return "consigne_eco"
    elif temperature_setting == TemperatureSetting.BOOST:
        return "consigne_boost"
    elif temperature_setting == TemperatureSetting.ANTI_FREEZE:
        return "consigne_hg"
    elif temperature_setting == TemperatureSetting.MANUAL:
        return "consigne_manuel"
    
    return None


def convert_change_mode_request(mode: Mode, boost_duration: timedelta = timedelta()) -> dict:
    api_mode: str = convert_mode_to_api(mode)

    settings = {
        "gv_mode": api_mode,
        "nv_mode": api_mode,
        "time_boost": write_duration(boost_duration),
    }

    return settings


def convert_temperature_settings_request(temperature_settings: dict[TemperatureSetting, float]) -> dict:
    settings = {}
    for temperature_setting, temperature in temperature_settings.items():
        setting_key = convert_temperature_setting_to_api(temperature_setting)
        settings[setting_key] = str(temperature * TEMPERATURE_UNIT_FACTOR)

    return settings

#endregion
