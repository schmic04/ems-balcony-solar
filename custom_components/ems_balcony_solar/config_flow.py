"""Config flow for EMS Balcony Solar integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_HOURS_OF_OPERATING,
    CONF_NORDPOOL_SENSOR,
    CONF_WINDOW_SENSOR,
    DOMAIN,
)


class EMSBalconySolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EMS Balcony Solar."""

    VERSION = 1

    def _get_nordpool_sensor_entities(self) -> list[str]:
        """Get list of potential Nordpool sensor entities."""
        sensor_entities = []
        for entity_id in self.hass.states.async_entity_ids(SENSOR_DOMAIN):
            # Filter for entities that might be Nordpool sensors
            if any(
                keyword in entity_id.lower()
                for keyword in ("nordpool", "price", "electricity")
            ):
                state = self.hass.states.get(entity_id)
                if state is not None:
                    # Check if entity has today/tomorrow attributes typical for Nordpool
                    if hasattr(state, "attributes") and (
                        "today" in state.attributes or "tomorrow" in state.attributes
                    ):
                        sensor_entities.append(entity_id)

        # If no specific Nordpool sensors found, return all sensors
        if not sensor_entities:
            for entity_id in self.hass.states.async_entity_ids(SENSOR_DOMAIN):
                state = self.hass.states.get(entity_id)
                if state is not None:
                    sensor_entities.append(entity_id)

        return sorted(sensor_entities)

    def _get_input_number_entities(self) -> list[str]:
        """Get list of input_number entities suitable for numeric values."""
        input_number_entities = []
        for entity_id in self.hass.states.async_entity_ids(INPUT_NUMBER_DOMAIN):
            state = self.hass.states.get(entity_id)
            if state is not None:
                input_number_entities.append(entity_id)
        return sorted(input_number_entities)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate that selected entities exist
            nordpool_entity = user_input[CONF_NORDPOOL_SENSOR]
            window_entity = user_input[CONF_WINDOW_SENSOR]
            hours_entity = user_input[CONF_HOURS_OF_OPERATING]

            if not self.hass.states.get(nordpool_entity):
                errors[CONF_NORDPOOL_SENSOR] = "entity_not_found"

            if not self.hass.states.get(window_entity):
                errors[CONF_WINDOW_SENSOR] = "entity_not_found"

            if not self.hass.states.get(hours_entity):
                errors[CONF_HOURS_OF_OPERATING] = "entity_not_found"

            if not errors:
                # Create unique ID based on nordpool sensor
                await self.async_set_unique_id(nordpool_entity)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"EMS Balcony Solar ({nordpool_entity.split('.')[-1]})",
                    data=user_input,
                )

        # Get available entities for dropdowns
        nordpool_entities = self._get_nordpool_sensor_entities()
        input_number_entities = self._get_input_number_entities()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NORDPOOL_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SENSOR_DOMAIN,
                        include_entities=nordpool_entities or [],
                    )
                ),
                vol.Required(CONF_WINDOW_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=INPUT_NUMBER_DOMAIN,
                        include_entities=input_number_entities or [],
                    )
                ),
                vol.Required(CONF_HOURS_OF_OPERATING): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=INPUT_NUMBER_DOMAIN,
                        include_entities=input_number_entities or [],
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
