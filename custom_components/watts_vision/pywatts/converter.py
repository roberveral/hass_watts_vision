"""Converters between Watts Vision API data and high-level models.

Provides functions to convert data received back and forth from the Watts Vision API
into high-level, easy-to-use model.
"""

from datetime import timedelta

from .api import (
    NVGV_MODE_AUTO,
    NVGV_MODE_AUTO_CONFORT,
    NVGV_MODE_AUTO_ECO,
    NVGV_MODE_BOOST,
    NVGV_MODE_CONFORT,
    NVGV_MODE_DESACTIVE,
    NVGV_MODE_ECO,
    NVGV_MODE_HORS_GEL,
    NVGV_MODE_OFF,
    NVGV_MODE_ON,
    WattsApiDevice,
    WattsApiLastConnectionData,
    WattsApiSmartHomeData,
    WattsApiSmartHomeSummary,
    WattsApiUserData,
    WattsApiZone,
)
from .model import (
    Device,
    ErrorCode,
    HVACSetting,
    Mode,
    SmartHome,
    SmartHomeSummary,
    Status,
    TemperatureSetting,
    User,
    Zone,
)

# region Constants

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

TEMPERATURE_SETTING_TO_API_FIELD: dict[TemperatureSetting, str] = {
    TemperatureSetting.COMFORT: "consigne_confort",
    TemperatureSetting.ECO: "consigne_eco",
    TemperatureSetting.BOOST: "consigne_boost",
    TemperatureSetting.ANTI_FREEZE: "consigne_hg",
    TemperatureSetting.MANUAL: "consigne_manuel",
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

# endregion

# region Helpers


def parse_temperature(
    value: str, unit_factor: float = TEMPERATURE_UNIT_FACTOR
) -> float:
    """Parse a temperature value from the Watts Vision API into a float in °F.

    API temperatures are strings in ºF with one decimal place multiplied by 10.
    For example, "215" represents 21.5ºF.
    """
    return float(value) / unit_factor


def write_temperature(
    value: float, unit_factor: float = TEMPERATURE_UNIT_FACTOR
) -> str:
    """Write a temperature value from a float in °F into the Watts Vision API format.

    API temperatures are strings in ºF with one decimal place multiplied by 10.
    For example, "215" represents 21.5ºF.
    """
    return str(int(value * unit_factor))


def write_duration(duration: timedelta) -> str:
    """Write a duration value from a timedelta into the Watts Vision API format.

    API durations are strings representing the total number of seconds.
    For example, "7200" represents 2 hours.
    """
    return str(int(duration.total_seconds()))


def parse_duration(value: str) -> timedelta:
    """Parse a duration value from the Watts Vision API into a timedelta.

    API durations are strings representing the total number of seconds.
    For example, "7200" represents 2 hours.
    """
    return timedelta(seconds=int(value))


# endregion

# region API to Model Converters


def convert_device(device_data: WattsApiDevice) -> Device:
    """Convert a Watts Vision API device data into a Device model."""

    # Determine HVAC setting based on whether the device is in heating or cooling mode
    hvac_setting = (
        HVACSetting.COOL if device_data["heat_cool"] == "1" else HVACSetting.HEAT
    )

    # Map device mode and target temperature setting from API gv_mode
    mode, target_temp_setting = DEVICE_MODE_TO_MODEL.get(
        device_data["gv_mode"], (Mode.OFF, TemperatureSetting.NONE)
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
        boost_duration_remaining=parse_duration(device_data["time_boost"]),
    )


def convert_zone(zone_data: WattsApiZone) -> Zone:
    """Convert a Watts Vision API zone data into a Zone model."""

    devices = [convert_device(device) for device in zone_data["devices"]]

    return Zone(
        id=zone_data["num_zone"], label=zone_data["zone_label"], devices=devices
    )


def convert_smart_home(
    home_data: WattsApiSmartHomeData, last_connection_data: WattsApiLastConnectionData
) -> SmartHome:
    """Convert a Watts Vision API smart home data into a SmartHome model."""

    devices = [convert_device(device) for device in home_data["devices"]]
    zones = [convert_zone(zone) for zone in home_data["zones"]]

    # Calculate current system HVAC setting
    hvac_setting = (
        HVACSetting.COOL
        if any(d.hvac_setting == HVACSetting.COOL for d in devices)
        else HVACSetting.HEAT
    )

    return SmartHome(
        id=home_data["smarthome_id"],
        label=home_data["label"],
        latitude=float(home_data["latitude"]),
        longitude=float(home_data["longitude"]),
        address=home_data.get("address", ""),
        mac_address=home_data["mac_address"],
        hvac_setting=hvac_setting,
        devices=devices,
        zones=zones,
        connection_delay=timedelta(seconds=last_connection_data["diff"]),
    )


def convert_smart_home_summary(
    home_summary_data: WattsApiSmartHomeSummary,
) -> SmartHomeSummary:
    """Convert a Watts Vision API smart home summary data into a SmartHomeSummary model."""

    # Calculate current system HVAC setting
    hvac_setting = (
        HVACSetting.COOL if home_summary_data["param_c_f"] == "f" else HVACSetting.HEAT
    )

    return SmartHomeSummary(
        id=home_summary_data["smarthome_id"],
        label=home_summary_data["label"],
        latitude=float(home_summary_data["latitude"]),
        longitude=float(home_summary_data["longitude"]),
        address=home_summary_data.get("address", ""),
        mac_address=home_summary_data["mac_address"],
        hvac_setting=hvac_setting,
    )


def convert_user(user_data: WattsApiUserData) -> User:
    """Convert a Watts Vision API user data into a User model."""

    smart_homes = [convert_smart_home_summary(home) for home in user_data["smarthomes"]]

    return User(
        id=user_data["user_id"], email=user_data["email"], smart_homes=smart_homes
    )


# endregion

# region Model to API Converters


def convert_mode_to_api(mode: Mode) -> str:
    """Convert a Mode model into the corresponding Watts Vision API NVGV mode."""

    for api_mode, (model_mode, _) in DEVICE_MODE_TO_MODEL.items():
        if model_mode == mode:
            return api_mode

    return None


def convert_change_mode_request(
    mode: Mode, boost_duration: timedelta = timedelta()
) -> dict:
    """Convert a Mode model and boost duration into a Watts Vision API change mode request.

    Time boost duration is only relevant when the mode is set to BOOST, burt included here as
    you always want to enter the boost duration when activating boost mode.
    """
    api_mode: str = convert_mode_to_api(mode)

    return {
        "gv_mode": api_mode,
        "nv_mode": api_mode,
        "time_boost": write_duration(boost_duration),
    }


def convert_temperature_settings_request(
    temperature_settings: dict[TemperatureSetting, float],
) -> dict:
    """Convert temperature settings into a Watts Vision API temperature settings request."""

    settings = {}
    for temperature_setting, temperature in temperature_settings.items():
        setting_key = TEMPERATURE_SETTING_TO_API_FIELD.get(temperature_setting)
        settings[setting_key] = str(temperature * TEMPERATURE_UNIT_FACTOR)

    return settings


# endregion
