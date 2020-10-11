"""Support for smartmeter sensors."""
import logging

from homeassistant.helpers.entity import Entity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the smart meter platform."""
    if discovery_info is None:
        return

    smartmeter = hass.data[DOMAIN]

    obis = smartmeter.get_list_of_sensors()
    _LOGGER.debug("Setting up sensors: %s", repr(obis))


    sensors = []
    for sensor_obis in obis:
        sensors.append(MeterSensor(smartmeter, sensor_obis, "Verbrauch", "mdi:flash"))
    
    async_add_entities(sensors)


class MeterSensor(Entity):
    """The entity class for smart meter sensors."""

    def __init__(self, smartmeter, obis, name, icon, device_class=None):
        """Initialize the smartmeter sensor."""
        self._smartmeter = smartmeter
        self._obis = obis
        self._name = name
        self._icon = icon
        self._unit = None
        self._device_class = device_class

        self._state = None
        self._attributes = {}

    @property
    def should_poll(self):
        """Deactivate polling. Data updated by smartmeter."""
        return False

    @property
    def unique_id(self):
        """Return the unique ID of the binary sensor."""
        return f"{self._smartmeter.device_id}_{self._obis}"

    @property
    def name(self):
        """Return the name of the device."""
        names={
                '1-0:1.8.0*255':'Consumption',
                '1-0:2.8.0*255':'Generation'
             }
        name = names.get(self._obis,"unknown")

        return f"{self._smartmeter.device_name} {name}"

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._device_class

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Get the unit of measurement."""
        return self._unit

    @property
    def device_state_attributes(self):
        """Return the state attributes of the binary sensor."""
        return self._attributes

    async def async_update(self):
        """Get latest cached states from the device."""
        self._state, self._unit = self._smartmeter.get_value(self._obis)

    def update_callback(self):
        """Schedule a state update."""
        self.async_schedule_update_ha_state(True)

    async def async_added_to_hass(self):
        """Add update callback after being added to hass."""
        self._smartmeter.add_update_listener(self.update_callback)
