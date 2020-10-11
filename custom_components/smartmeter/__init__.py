"""Support for D0 smart meters."""
import asyncio
from homeassistant.core import callback
import logging
import serial_asyncio
import re

import voluptuous as vol

from homeassistant.const import CONF_HOST
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "smartmeter"
CONF_PORT = "port"
CONF_OBIS = "obis"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_PORT, default="/dev/ttyUSB0"): cv.string,
                vol.Optional(CONF_OBIS, default=[]): vol.All(
                    cv.ensure_list, vol.Length(min=1), [cv.string]
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

START_CHAR = b'/'
END_CHAR = b'!'

async def async_setup(hass, config):
    """Check connectivity and version of smartmeter."""
    port = config[DOMAIN][CONF_PORT]
    obis = config[DOMAIN][CONF_OBIS]
    meter = Meter(hass, port, obis)
    hass.data[DOMAIN] = meter

    # Wait for smartmeter setup complete (initial values loaded)
    if not await meter.setup():
        _LOGGER.error("Could not find a meter device at %s", port)
        return False

    # Load components
    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    return True


class Meter():
    """Representation of a smartmeter connection."""

    def __init__(self, hass, port, list_of_sensors):
        """Initialize charging station connection."""

        self._list_of_sensors = list_of_sensors
        self._update_listeners = []
        self._hass = hass
        self._port = port
        self._values = {}
        self._units = {}
        self.device_name = "smartmeter"  # correct device name will be set in setup()
        self.device_id = "smartmeter_"  # correct device id will be set in setup()

        self.regex_data_set = re.compile(r"^(.+)\((.*)\)")
        self.regex_data_set_data = re.compile(r"^(.*)\*(.*)")

    def get_list_of_sensors(self):
        return self._list_of_sensors

    async def setup(self, loop=None):
        """Initialize smartmeter object."""

        # start serial connection
        loop = asyncio.get_event_loop() if loop is None else loop
        transport, protocol = await serial_asyncio.create_serial_connection(loop, D0Reader, self._port, baudrate=9600)
        protocol.set_callback(self.hass_callback)
    
        return True

    def get_value(self, address):

        value = self._values.get(address, None)
        unit = self._units.get(address, None)
        return value, unit

    def hass_callback(self, data):
        """Handle component notification via callback."""

        # Analyse and preprocess received data blob
        for line in data.splitlines(True):

            first_match = self.regex_data_set.search(line)
            if first_match:
                address = first_match.group(1)
                second_match = self.regex_data_set_data.search(first_match.group(2))
                if second_match:
                    self._values[address] = float(second_match.group(1))
                    self._units[address] = second_match.group(2)
                    _LOGGER.debug("extracted %s with value %s with unit %s", address, self._values[address], self._units[address])

        # Inform entities about updated values
        for listener in self._update_listeners:
            listener()

        _LOGGER.debug("Notifying %d listeners", len(self._update_listeners))

    def add_update_listener(self, listener):
        """Add a listener for update notifications."""
        self._update_listeners.append(listener)

        # initial data is already loaded, thus update the component
        listener()

class D0Reader(asyncio.Protocol):

    def __init__(self) -> None:
        super().__init__()
        self._data = ""

    def set_callback(self, callback):
        self._callback = callback

    def connection_made(self, transport):
        self.transport = transport
        _LOGGER.debug("port opened %s", transport)

    def data_received(self, data):

        # Reset buffer if new start byte received
        if START_CHAR in data:
            _LOGGER.debug("new start found")
            self._data = ""
        
        # Buffer content and fetch data
        # TODO: change data type to bytearray and convert to string afterwards
        self._data += data.decode("latin-1")

        # Callback if ending byte found(complete message received)
        if END_CHAR in data:
            _LOGGER.debug("end found, run callback")
            # TODO: check CRC
            self._callback(self._data)

    def connection_lost(self, exc):
        _LOGGER.debug("serial connection closed: %s", exc)
        self.transport.loop.stop()
