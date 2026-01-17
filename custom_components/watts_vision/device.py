from .const import DOMAIN
from homeassistant.helpers.device_registry import DeviceInfo

MANUFACTURER: str = "Watts"
THERMOSTAT_MODEL: str = "BT-D03-RF"
CENTRAL_UNIT_MODEL: str = "BT-CT02-RF"

THERMOSTAT_TRANSLATION_KEY: str = "thermostat"
CENTRAL_UNIT_TRANSLATION_KEY: str = "central_unit"

ATTR_ZONE_LABEL: str = "zone_label"
ATTR_SMART_HOME_NAME: str = "smart_home_name"


def thermostat_device_info(unique_id: str, smart_home_id: str, zone_label: str) -> DeviceInfo:
    return {
        "identifiers": {
            # Serial numbers are unique identifiers within a specific domain
            (DOMAIN, unique_id)
        },
        "manufacturer": MANUFACTURER,
        "translation_key": THERMOSTAT_TRANSLATION_KEY,
        "translation_placeholders": { ATTR_ZONE_LABEL: zone_label },
        "model": THERMOSTAT_MODEL,
        "via_device": (DOMAIN, smart_home_id),
        "suggested_area": zone_label,
    }


def central_unit_device_info(smart_home_id: str, smart_home_name: str, mac_address: str) -> DeviceInfo:
    return {
        "identifiers": {
            # Serial numbers are unique identifiers within a specific domain
            (DOMAIN, smart_home_id)
        },
        "manufacturer": MANUFACTURER,
        "translation_key": CENTRAL_UNIT_TRANSLATION_KEY,
        "translation_placeholders": { ATTR_SMART_HOME_NAME: smart_home_name },
        "model": CENTRAL_UNIT_MODEL,
        "connections": {("mac", mac_address)},
    }

