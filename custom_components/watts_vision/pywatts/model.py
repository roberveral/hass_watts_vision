"""Model definitions for the Watts Vision system.

Provides data classes and enumerations to represent the core entities
in the Watts Vision ecosystem, including smart homes, devices, zones,
users, and their associated settings and statuses.

This is a high-level representation of the Watts Vision system, abstracting
the underlying API data structures into more manageable Python objects.
"""

from dataclasses import dataclass
from enum import StrEnum


class HVACSetting(StrEnum):
    """Current sustem HVAC configuration for a Watts Vision thermostat and/or central unit.

    The system is either configured to COOL or HEAT mode. This is a system-wide setting
    that cannot be changed by the API. It may require a manual operation on the heating system,
    and a change on the central unit.
    """

    COOL = "Cool"
    HEAT = "Heat"


class Mode(StrEnum):
    """The mode that a thermostat device is currently set to in the Watts system.

    The mode determines how the thermostat controls the heating/cooling system, including
    target temperatures and behavior (e.g., Comfort, Eco, Program, Boost, etc.).
    """

    OFF = "Off"
    COMFORT = "Comfort"
    ECO = "Eco"
    PROGRAM = "Program"
    BOOST = "Boost"
    ANTI_FREEZE = "Anti-Freeze"


class TemperatureSetting(StrEnum):
    """A temperature setting in the Watts system.

    Watts allows to configure different temperature settings, that are used in different modes.
    However, is not a 1:1 mapping between modes and temperature settings, as
    the program mode may target different temperature settings depending on the time of day.

    A thermostat device may have multiple temperature settings configured, but is only targeting
    one temperature setting at a time.
    """

    NONE = "None"
    COMFORT = "Comfort"
    ECO = "Eco"
    BOOST = "Boost"
    ANTI_FREEZE = "Anti-Freeze"
    MANUAL = "Manual"


class Status(StrEnum):
    """Current status of a thermostat device in the Watts system.

    The status indicates whether the device is actively heating, cooling, idle, or turned off.
    While the mode indicates the desired operation, the status reflects the actual state
    of the device based on current conditions.
    """

    IDLE = "Idle"
    HEATING = "Heating"
    COOLING = "Cooling"
    OFF = "Off"


class ErrorCode(StrEnum):
    """Indicates an error reported by a Watts device.

    Represents specific error conditions, such as low battery.
    """

    NONE = "None"
    BATTERY_LOW = "Battery Low"


@dataclass
class Device:
    """A thermostat device in the Watts Vision system.

    Represents a thermostat device with its configuration, status, and settings.
    A thermostat controls the heating/cooling system in a paritcular zone of the smart home.
    It measures current temperatures and adjusts the system based on the configured mode
    and target temperature settings.

    It can also be programmed (e.g., program mode) to follow a schedule of temperature settings.
    Right now the program is not included in the model.
    """

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
    """A zone in the Watts Vision system.

    A zone represents a specific area or room in the smart home that is
    controlled by one or more thermostat devices.
    """

    id: str
    label: str
    devices: list[Device]

    def get_device_by_id(self, device_id: str) -> Device | None:
        """Get a device in the zone by its ID."""

        for device in self.devices:
            if device.id == device_id:
                return device

        return None


@dataclass
class SmartHome:
    """A smart home in the Watts Vision system.

    A smart home is associated with a Watts Vision central unit, which manages
    the connected devices and zones within that home.
    """

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
        """Get a device in the smart home by its ID."""

        for device in self.devices:
            if device.id == device_id:
                return device

        return None

    def get_zone_by_id(self, zone_id: str) -> Zone | None:
        """Get a zone in the smart home by its ID."""

        for zone in self.zones:
            if zone.id == zone_id:
                return zone

        return None


@dataclass
class SmartHomeSummary:
    """A summary of a smart home in the Watts Vision system.

    A smart home summary provides basic information about the smart home,
    without detailed device and zone information.
    """

    id: str
    label: str
    latitude: float
    longitude: float
    address: str
    mac_address: str
    hvac_setting: HVACSetting


@dataclass
class User:
    """A user in the Watts Vision system.

    Represents a user account with associated smart homes.
    """

    id: str
    email: str
    smart_homes: list[SmartHomeSummary]
