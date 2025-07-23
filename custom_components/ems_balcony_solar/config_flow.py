from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN


class MeineIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                    title="EMS Balcony Solar", data=user_input
                    )

        schema = vol.Schema({
            vol.Required("host"): str,
            vol.Optional("port", default=1234): int,
        })

        return self.async_show_form(step_id="user", data_schema=schema)
