"""Type definitions for Watts Vision integration."""

from asyncio import Task
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

from .coordinator import WattsVisionCoordinator
from .pywatts import WattsVisionClient


@dataclass
class WattsData:
    """Runtime data for Watts Vision integration.

    Contains the API client and data coordinator for the integration, which is
    included in the Home Assistant config entry data.
    """

    client: WattsVisionClient
    coordinator: WattsVisionCoordinator
    worker_task: Task


type WattsVisionConfigEntry = ConfigEntry[WattsData]
