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

# Entity unique IDs
UNIQUE_ID_SENSOR_CURRENT_ELECTRICITY_PRICE = (
    f"{DOMAIN}_sensor_current_electricity_price"
)
UNIQUE_ID_BINARY_SENSOR_PRICE_RANGE_ACTIVE = (
    f"{DOMAIN}_binary_sensor_price_range_active"
)
UNIQUE_ID_NUMBER_SUBLIST_LENGTH = f"{DOMAIN}_number_sublist_length"
UNIQUE_ID_NUMBER_OF_SUBLISTS = f"{DOMAIN}_number_number_of_sublists"
UNIQUE_ID_SWITCH_EMS_BALCONY_SOLAR = f"{DOMAIN}_switch_ems_balcony_solar"
UNIQUE_ID_SWITCH_DEBUGGING = f"{DOMAIN}_switch_debugging"
