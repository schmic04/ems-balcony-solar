"""Custom types for ems_balcony_solar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import EMSBalconySolarApiClient
    from .coordinator import EMSBalconySolarDataUpdateCoordinator


type EMSBalconySolarConfigEntry = ConfigEntry[EMSBalconySolarData]


@dataclass
class EMSBalconySolarData:
    """Data for the EMSBalconySolar integration."""

    client: EMSBalconySolarApiClient
    coordinator: EMSBalconySolarDataUpdateCoordinator
    integration: Integration
