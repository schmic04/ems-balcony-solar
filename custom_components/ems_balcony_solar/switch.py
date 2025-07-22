from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, MANUFACTURER


async def async_setup_entry(hass, entry, async_add_entities):
    for i in range(2):
        device_id = f"switch_device_{i}"
        switches = []
        for j in range(2):
            switches.append(MeinSwitch(f"Switch {j}", device_id, entry))
        async_add_entities(switches)


class MeinSwitch(SwitchEntity):
    def __init__(self, name, device_id, entry):
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{name.lower().replace(' ', '_')}"
        self._device_id = device_id
        self._entry = entry
        self._is_on = False

    @property
    def is_on(self):
        return self._is_on

    def turn_on(self, **kwargs):
        self._is_on = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        self._is_on = False
        self.schedule_update_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"Gerät {self._device_id}",
            manufacturer=MANUFACTURER,
            model="Switch-Modell Y",
            via_device=(DOMAIN, self._entry.entry_id),
        )

