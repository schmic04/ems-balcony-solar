"""Constants for ems_balcony_solar."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "ems_balcony_solar"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

# Configuration keys
CONF_SENSOR = "sensor"
CONF_NUMBER_1 = "number_1"
CONF_NUMBER_2 = "number_2"

# Internal entity IDs for created entities
CREATED_SENSOR = "created_sensor"
CREATED_NUMBER_1 = "created_number_1"
CREATED_NUMBER_2 = "created_number_2"
