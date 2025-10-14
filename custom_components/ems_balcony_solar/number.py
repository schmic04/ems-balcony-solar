"""Number platform for EMS Balcony Solar."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory

from .const import CONF_NUMBER_1, CONF_NUMBER_2, CREATED_NUMBER_1, CREATED_NUMBER_2
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

    # Create number entity 1 if no existing entity was selected
    if CONF_NUMBER_1 not in entry.data or not entry.data[CONF_NUMBER_1]:
        entities.append(
            EMSBalconySolarNumber(
                entry=entry,
                number_id=CREATED_NUMBER_1,
                name="Number 1",
                unique_id_suffix="number_1",
            )
        )

    # Create number entity 2 if no existing entity was selected
    if CONF_NUMBER_2 not in entry.data or not entry.data[CONF_NUMBER_2]:
        entities.append(
            EMSBalconySolarNumber(
                entry=entry,
                number_id=CREATED_NUMBER_2,
                name="Number 2",
                unique_id_suffix="number_2",
            )
        )

    if entities:
        async_add_entities(entities)


class EMSBalconySolarNumber(EMSBalconySolarEntity, NumberEntity):
    """EMS Balcony Solar Number class."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 1000
    _attr_native_step = 1

    def __init__(
        self,
        entry: EMSBalconySolarConfigEntry,
        number_id: str,
        name: str,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(entry.runtime_data.coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"
        self._number_id = number_id
        self._attr_native_value = 0

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()
