"""Constants for ems_balcony_solar."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "ems_balcony_solar"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

# Configuration keys
CONF_SENSOR = "sensor"
CONF_SUBLIST_LENGTH = "sublist_length"
CONF_NUMBER_OF_SUBLISTS = "number_of_sublists"

# Old configuration keys for migration
CONF_NUMBER_1 = "number_1"
CONF_NUMBER_2 = "number_2"

# Internal entity IDs for created entities
CREATED_SENSOR = "created_sensor"
CREATED_SUBLIST_LENGTH = "created_sublist_length"
CREATED_NUMBER_OF_SUBLISTS = "created_number_of_sublists"

# Old entity IDs for migration
CREATED_NUMBER_1 = "created_number_1"
CREATED_NUMBER_2 = "created_number_2"
