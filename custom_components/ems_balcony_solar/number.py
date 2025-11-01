"""Number platform for EMS Balcony Solar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_NUMBER_OF_SUBLISTS,
    CONF_SUBLIST_LENGTH,
    CREATED_NUMBER_OF_SUBLISTS,
    CREATED_SUBLIST_LENGTH,
    UNIQUE_ID_NUMBER_OF_SUBLISTS,
    UNIQUE_ID_NUMBER_SUBLIST_LENGTH,
)
from .entity import EMSBalconySolarEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import EMSBalconySolarConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: EMSBalconySolarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    entities = []

    # Create sublist_length entity if no existing entity was selected
    if CONF_SUBLIST_LENGTH not in entry.data or not entry.data[CONF_SUBLIST_LENGTH]:
        entities.append(
            EMSBalconySolarNumber(
                entry=entry,
                number_id=CREATED_SUBLIST_LENGTH,
                name="Sublist Length",
                unique_id=UNIQUE_ID_NUMBER_SUBLIST_LENGTH,
            )
        )

    # Create number_of_sublists entity if no existing entity was selected
    if (
        CONF_NUMBER_OF_SUBLISTS not in entry.data
        or not entry.data[CONF_NUMBER_OF_SUBLISTS]
    ):
        entities.append(
            EMSBalconySolarNumber(
                entry=entry,
                number_id=CREATED_NUMBER_OF_SUBLISTS,
                name="Number of Sublists",
                unique_id=UNIQUE_ID_NUMBER_OF_SUBLISTS,
            )
        )

    if entities:
        async_add_entities(entities)


class EMSBalconySolarNumber(EMSBalconySolarEntity, NumberEntity, RestoreEntity):
    """EMS Balcony Solar Number class."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1000.0
    _attr_native_step = 1.0

    def __init__(
        self,
        entry: EMSBalconySolarConfigEntry,
        number_id: str,
        name: str,
        unique_id: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(entry.runtime_data.coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._number_id = number_id
        self._attr_native_value = 0
        self._entry = entry

    async def async_added_to_hass(self) -> None:
        """Restore the last state when entity is added to hass."""
        await super().async_added_to_hass()

        # Restore last state
        if (
            last_state := await self.async_get_last_state()
        ) is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._attr_native_value = int(float(last_state.state))
            except (ValueError, TypeError):
                self._attr_native_value = 0

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = int(value)
        self.async_write_ha_state()
