from dataclasses import dataclass
from enum import StrEnum


class HVACSetting(StrEnum):
    """
    Contains the available settings in the Watts system. The system
    is either configured to COOL or HEAT mode. This is a system-wide setting
    that cannot be changed by the API, it requires a manual operation and a
    change on the central unit.
    """

    COOL = "Cool"
    HEAT = "Heat"


class Mode(StrEnum):
    """
    Contains the available modes in the Watts system
    """

    OFF = "Off"
    COMFORT = "Comfort"
    ECO = "Eco"
    PROGRAM = "Program"
    BOOST = "Boost"
    ANTI_FREEZE = "Anti-Freeze"


class TemperatureSetting(StrEnum):
    """
    Contains the available target temperatures in the Watts system.

    Watts allows to configure different temperature settings, that are used in different modes.
    However, is not a 1:1 mapping between modes and temperature settings, as 
    the program mode may target different temperature settings depending on the time of day.
    """

    NONE = "None"
    COMFORT = "Comfort"
    ECO = "Eco"
    BOOST = "Boost"
    ANTI_FREEZE = "Anti-Freeze"
    MANUAL = "Manual"


class Status(StrEnum):
    """
    Contains the available status values in the Watts system.
    """

    IDLE = "Idle"
    HEATING = "Heating"
    COOLING = "Cooling"
    OFF = "Off"


class ErrorCode(StrEnum):
    """
    Contains the available error codes in the Watts system.
    """

    NONE = "None"
    BATTERY_LOW = "Battery Low"


@dataclass
class Device:
    id: str
    device_id: str
    label: str
    hvac_setting: HVACSetting
    mode: Mode
    target_temperature_setting: TemperatureSetting
    status: Status
    target_temperature: float
    temperature_settings: dict[TemperatureSetting, float]
    current_temperature_air: float
    current_temperature_floor: float
    min_set_point: float
    max_set_point: float
    error_code: ErrorCode


@dataclass
class Zone:
    id: str
    label: str
    devices: list[Device]

    def get_device_by_id(self, device_id: str) -> Device | None:
        for device in self.devices:
            if device.id == device_id:
                return device
        
        return None


@dataclass
class SmartHome:
    id: str
    label: str
    latitude: float
    longitude: float
    address: str
    mac_address: str
    hvac_setting: HVACSetting
    devices: list[Device]
    zones: list[Zone]


    def get_device_by_id(self, device_id: str) -> Device | None:
        for device in self.devices:
            if device.id == device_id:
                return device
        
        return None


    def get_zone_by_id(self, zone_id: str) -> Zone | None:
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        
        return None


@dataclass
class SmartHomeSummary:
    id: str
    label: str
    latitude: float
    longitude: float
    address: str
    mac_address: str
    hvac_setting: HVACSetting


@dataclass
class User:
    id: str
    email: str
    smart_homes: list[SmartHomeSummary]


