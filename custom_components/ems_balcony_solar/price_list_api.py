"""Price list API for EMS Balcony Solar."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def get_combined_price_list(
    hass: HomeAssistant,
    sensor_entity_id: str,
) -> list[dict[str, float | datetime]]:
    """Get combined price list from today and tomorrow attributes.
    
    Args:
        hass: Home Assistant instance.
        sensor_entity_id: Entity ID of the price sensor.
        
    Returns:
        Combined list of price entries from today and tomorrow (if valid).
        Each entry contains: start_time, end_time, and price.
        Returns empty list if sensor not found or attributes missing.
    """
    if not sensor_entity_id:
        return []
    
    state = hass.states.get(sensor_entity_id)
    if state is None:
        return []
    
    attributes = state.attributes
    price_list = []
    
    # Get today's prices
    today_prices = attributes.get("today")
    if today_prices and isinstance(today_prices, list):
        price_list.extend(today_prices)
    
    # Get tomorrow's prices if valid
    tomorrow_valid = attributes.get("tomorrow_valid", False)
    if tomorrow_valid:
        tomorrow_prices = attributes.get("tomorrow")
        if tomorrow_prices and isinstance(tomorrow_prices, list):
            price_list.extend(tomorrow_prices)
    
    return price_list


def get_current_price(
    hass: HomeAssistant,
    sensor_entity_id: str,
) -> float | None:
    """Get the current price from the sensor.
    
    Args:
        hass: Home Assistant instance.
        sensor_entity_id: Entity ID of the price sensor.
        
    Returns:
        Current price as float, or None if not available.
    """
    if not sensor_entity_id:
        return None
    
    state = hass.states.get(sensor_entity_id)
    if state is None or state.state in ("unknown", "unavailable"):
        return None
    
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return None


def get_price_at_time(
    price_list: list[dict[str, float | datetime]],
    target_time: datetime,
) -> float | None:
    """Get the price at a specific time from the price list.
    
    Args:
        price_list: Combined price list from get_combined_price_list.
        target_time: The time to get the price for.
        
    Returns:
        Price at the specified time, or None if not found.
    """
    for entry in price_list:
        start_time = entry.get("start")
        end_time = entry.get("end")
        
        if start_time and end_time:
            if start_time <= target_time < end_time:
                return entry.get("value")
    
    return None


def get_lowest_price_period(
    price_list: list[dict[str, float | datetime]],
    duration_hours: int = 1,
) -> dict[str, float | datetime] | None:
    """Find the period with the lowest average price.
    
    Args:
        price_list: Combined price list from get_combined_price_list.
        duration_hours: Duration in hours for the period to find.
        
    Returns:
        Dictionary with start_time, end_time, and average_price,
        or None if not enough data.
    """
    if not price_list or duration_hours < 1:
        return None
    
    lowest_avg = float("inf")
    lowest_period = None
    
    for i in range(len(price_list) - duration_hours + 1):
        period = price_list[i : i + duration_hours]
        avg_price = sum(entry.get("value", 0) for entry in period) / len(period)
        
        if avg_price < lowest_avg:
            lowest_avg = avg_price
            lowest_period = {
                "start_time": period[0].get("start"),
                "end_time": period[-1].get("end"),
                "average_price": avg_price,
            }
    
    return lowest_period
