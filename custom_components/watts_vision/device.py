"""Defines device information for Watts Vision devices."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

# region Constants

MANUFACTURER: str = "Watts"
THERMOSTAT_MODEL: str = "BT-D03-RF"
CENTRAL_UNIT_MODEL: str = "BT-CT02-RF"

THERMOSTAT_TRANSLATION_KEY: str = "thermostat"
CENTRAL_UNIT_TRANSLATION_KEY: str = "central_unit"

ATTR_ZONE_LABEL: str = "zone_label"
ATTR_SMART_HOME_NAME: str = "smart_home_name"

# endregion


def thermostat_device_info(
    unique_id: str, smart_home_id: str, zone_label: str
) -> DeviceInfo:
    """Return device info for a Watts Vision thermostat device.

    It provides information for a Watts Vision BT-D03-RF thermostat device.
    (https://www.watts.eu/es/products/eu/smart-home-and-controls/vision-wireless/thermostat-bt-d03-rf)

    User Manual: https://www.watts.eu/es/technical-support/manuals/electronics/9579
    """
    return {
        "identifiers": {
            # Serial numbers are unique identifiers within a specific domain
            (DOMAIN, unique_id)
        },
        "manufacturer": MANUFACTURER,
        "translation_key": THERMOSTAT_TRANSLATION_KEY,
        "translation_placeholders": {ATTR_ZONE_LABEL: zone_label},
        "model": THERMOSTAT_MODEL,
        "via_device": (DOMAIN, smart_home_id),
        "suggested_area": zone_label,
    }


def central_unit_device_info(
    smart_home_id: str, smart_home_name: str, mac_address: str
) -> DeviceInfo:
    """Return device info for a Watts Vision central unit device.

    It provides information for a Watts Vision BT-CT02-RF central unit device.
    (https://www.watts.eu/es/products/eu/smart-home-and-controls/vision-wireless/central-unit-bt-ct02-rf-capacitive)

    User Manual: https://www.watts.eu/es/technical-support/manuals/electronics/6614
    """
    return {
        "identifiers": {
            # Serial numbers are unique identifiers within a specific domain
            (DOMAIN, smart_home_id)
        },
        "manufacturer": MANUFACTURER,
        "translation_key": CENTRAL_UNIT_TRANSLATION_KEY,
        "translation_placeholders": {ATTR_SMART_HOME_NAME: smart_home_name},
        "model": CENTRAL_UNIT_MODEL,
        "connections": {("mac", mac_address)},
    }
