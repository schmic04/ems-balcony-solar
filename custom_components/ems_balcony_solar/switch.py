"""Switch platform for ems_balcony_solar."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import EMSBalconySolarEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import EMSBalconySolarDataUpdateCoordinator
    from .data import EMSBalconySolarConfigEntry

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="ems_balcony_solar",
        name="EMS Balcony Solar",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: EMSBalconySolarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities(
        EMSBalconySolarSwitch(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class EMSBalconySolarSwitch(EMSBalconySolarEntity, SwitchEntity, RestoreEntity):
    """ems_balcony_solar switch class."""

    def __init__(
        self,
        coordinator: EMSBalconySolarDataUpdateCoordinator,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{entity_description.key}"
        self._is_on = True

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        
        # Restore previous state
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == "on"
        
        # Write initial state to ensure it's saved
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        self._is_on = False
        self.async_write_ha_state()
