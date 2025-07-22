from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN, MANUFACTURER


async def async_setup_entry(hass, entry, async_add_entities):
    for i in range(2):
        device_id = f"device_{i}"
        sensors = []
        for j in range(2):
            sensors.append(MeineSensor(f"Sensor {j}", device_id, entry))
        async_add_entities(sensors)


class MeineSensor(SensorEntity):
    def __init__(self, name, device_id, entry):
        self._attr_name = name
        self._attr_unique_id = f"{device_id}_{name.lower().replace(' ', '_')}"
        self._device_id = device_id
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"Gerät {self._device_id}",
            manufacturer=MANUFACTURER,
            model="Modell X",
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def native_value(self):
        return 42

