"""Binary sensor platform for ems_balcony_solar."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import EMSBalconySolarConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EMSBalconySolarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    # No binary sensors to add - this platform is kept for future use
    _ = hass, entry, async_add_entities  # Mark as used to avoid linter warnings

