from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .coordinator import WattsVisionCoordinator
from .pywatts import WattsVisionClient


@dataclass
class WattsData:
    client: WattsVisionClient
    coordinator: WattsVisionCoordinator


type WattsVisionConfigEntry = ConfigEntry[WattsData]

