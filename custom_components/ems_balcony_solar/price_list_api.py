"""Price list API for EMS Balcony Solar."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def get_combined_price_list(
    hass: HomeAssistant,
    sensor_entity_id: str,
) -> list:
    """Get combined price list from today and tomorrow attributes.

    Args:
        hass: Home Assistant instance.
        sensor_entity_id: Entity ID of the price sensor.

    Returns:
        Combined list of price entries from today and tomorrow (if valid).
        The format depends on the source sensor - can be:
        - Simple list of floats (Nord Pool sensor)
        - List of dicts with start_time, end_time, value (other sensors)
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


def group_prices_by_hour(
    price_list: list,
) -> list[dict[str, str | float | int]]:
    """Group price list into hourly summaries.

    Takes the combined price list from get_combined_price_list() and
    structures it for easy hour-based access.

    The function handles both formats:
    1. List of dicts with 'start', 'end', 'value' (15-min intervals)
    2. Simple list of floats (hourly prices from Nord Pool)

    Args:
        price_list: Combined price list from get_combined_price_list.

    Returns:
        List of hourly price data with:
        hour: Hour in format "HH:MM"
        date: Date in format "YYYY-MM-DD"
        min: Minimum price of the 4 x 15-minute intervals
        max: Maximum price of the 4 x 15-minute intervals
        avg: Average price of the 4 x 15-minute intervals
        prices: Comma-separated string of the 4 individual 15-minute prices

    """
    if not price_list:
        return []

    result = []
    now = datetime.now().astimezone()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if price_list contains dicts or simple values
    first_entry = price_list[0] if price_list else None

    if isinstance(first_entry, dict):
        # Format 1: List of dicts with start/end/value (15-min intervals)
        hourly_data = {}

        for entry in price_list:
            if not isinstance(entry, dict):
                continue

            start_time = entry.get("start")
            price = entry.get("value")

            if not isinstance(start_time, datetime) or price is None:
                continue

            # Create hour key (rounded down to hour)
            hour_key = start_time.replace(minute=0, second=0, microsecond=0)

            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    "datetime": hour_key,
                    "prices": [],
                }

            hourly_data[hour_key]["prices"].append(price)

        # Calculate statistics for each hour
        for hour_dt, data in sorted(hourly_data.items()):
            prices = data["prices"]
            if not prices:
                continue

            result.append(
                {
                    "date": hour_dt.strftime("%Y-%m-%d"),
                    "hour": hour_dt.strftime("%H:%M"),
                    "price": round(sum(prices) / len(prices), 4),
                }
            )

    else:
        # Format 2: Simple list of floats (15-minute interval prices)
        # Each index represents a 15-minute interval starting from today 00:00
        # 4 consecutive entries = 1 hour
        for i, price in enumerate(price_list):
            if not isinstance(price, (int, float)):
                continue

            # Calculate the datetime for this 15-minute interval
            interval_dt = today_start + timedelta(minutes=i * 15)

            # Round down to the hour to group by hour
            hour_dt = interval_dt.replace(minute=0, second=0, microsecond=0)
            hour_key = hour_dt.strftime("%H:%M")

            # Find or create entry for this hour
            existing = None
            for entry in result:
                if entry["hour"] == hour_key and entry["date"] == hour_dt.strftime(
                    "%Y-%m-%d"
                ):
                    existing = entry
                    break

            if existing:
                # Add price to existing hour
                existing["prices"].append(float(price))
            else:
                # Create new hour entry
                result.append(
                    {
                        "date": hour_dt.strftime("%Y-%m-%d"),
                        "hour": hour_key,
                        "prices": [float(price)],
                    }
                )

        # Calculate statistics for each hour (from 4 x 15-min intervals)
        for entry in result:
            prices = entry["prices"]
            if prices:
                entry["avg"] = round(sum(prices) / len(prices), 4)
                entry["min"] = round(min(prices), 4)
                entry["max"] = round(max(prices), 4)
                # Format prices as a single line string
                entry["prices"] = ", ".join([str(round(p, 4)) for p in prices])

    return result


def find_local_maxima(price_list: list) -> list[int]:
    """Find indices of local maxima in the price list.

    A local maximum is a value that is greater than both its neighbors.

    Args:
        price_list: The input price list.

    Returns:
        List of indices where local maxima occur.

    """
    if not price_list or len(price_list) < 3:
        return []

    maxima_indices = []

    for i in range(1, len(price_list) - 1):
        # Check if current value is numeric
        if not isinstance(price_list[i], (int, float)):
            continue

        prev_val = price_list[i - 1]
        curr_val = price_list[i]
        next_val = price_list[i + 1]

        # Check if neighbors are also numeric
        if not isinstance(prev_val, (int, float)) or not isinstance(
            next_val, (int, float)
        ):
            continue

        # Check if current value is a local maximum
        if curr_val > prev_val and curr_val > next_val:
            maxima_indices.append(i)

    return maxima_indices


def convert_indices_to_time_ranges(
    indices_list: list[list[int]],
    start_time: datetime | None = None,
) -> list[list[str]]:
    """Convert index lists to time ranges.

    Each index represents a 15-minute interval. Index 0 corresponds to 00:00.

    Args:
        indices_list: List of index lists to convert.
        start_time: Start time for index 0. Defaults to today at 00:00.

    Returns:
        List of time range lists, where each time range is formatted as "HH:MM-HH:MM".

    """
    if not indices_list:
        return []

    # Use today at 00:00 if no start_time provided
    if start_time is None:
        now = datetime.now().astimezone()
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

    time_ranges_list = []

    for idx_list in indices_list:
        if not idx_list:
            time_ranges_list.append([])
            continue

        time_ranges = []
        # Group consecutive indices into ranges
        current_range_start = idx_list[0]
        current_range_end = idx_list[0]

        for i in range(1, len(idx_list)):
            if idx_list[i] == current_range_end + 1:
                # Consecutive index, extend the range
                current_range_end = idx_list[i]
            else:
                # Gap found, save current range and start new one
                time_ranges.append(_format_time_range(
                    current_range_start, current_range_end, start_time
                ))
                current_range_start = idx_list[i]
                current_range_end = idx_list[i]

        # Add the last range
        time_ranges.append(_format_time_range(
            current_range_start, current_range_end, start_time
        ))

        time_ranges_list.append(time_ranges)

    return time_ranges_list


def _format_time_range(
    start_idx: int,
    end_idx: int,
    base_time: datetime,
) -> str:
    """Format a time range from indices with day offset.

    Args:
        start_idx: Start index (0 = 00:00).
        end_idx: End index (inclusive).
        base_time: Base time for index 0.

    Returns:
        Formatted time range string "HH:MM+DD-HH:MM+DD" where DD is day offset.
        Examples: "04:00+00-05:15+00", "23:00+00-01:00+01"

    """
    # Each index is 15 minutes
    start_time = base_time + timedelta(minutes=start_idx * 15)
    # End time is at the end of the 15-minute interval
    end_time = base_time + timedelta(minutes=(end_idx + 1) * 15)

    # Calculate day offset from base_time
    start_day_offset = (start_time.date() - base_time.date()).days
    end_day_offset = (end_time.date() - base_time.date()).days

    return (
        f"{start_time.strftime('%H:%M')}+{start_day_offset:02d}-"
        f"{end_time.strftime('%H:%M')}+{end_day_offset:02d}"
    )


def parse_time_range_to_timestamps(
    time_range: str,
    reference_date: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Parse a time range string to start and end timestamps.

    Args:
        time_range: Time range string in format "HH:MM+DD-HH:MM+DD" or "HH:MM-HH:MM".
                   DD is the day offset (00=today, 01=tomorrow, etc.)
        reference_date: Reference date for the timestamps. If None, uses today.

    Returns:
        Tuple of (start_timestamp, end_timestamp) as timezone-aware datetime objects.

    Raises:
        ValueError: If time_range format is invalid.

    Example:
        >>> parse_time_range_to_timestamps("04:00+00-05:15+00")
        (datetime(2025, 10, 22, 4, 0), datetime(2025, 10, 22, 5, 15))
        >>> parse_time_range_to_timestamps("23:00+00-01:00+01")
        (datetime(2025, 10, 22, 23, 0), datetime(2025, 10, 23, 1, 0))

    """
    try:
        # Split time range at the middle dash
        # Format can be: "HH:MM+D-HH:MM+D" or "HH:MM-HH:MM" (legacy)
        parts = time_range.split("-")
        if len(parts) != 2:
            msg = f"Invalid time range format: '{time_range}'"
            raise ValueError(msg)

        start_str, end_str = parts

        # Check if day offset is included (new format)
        if "+" in start_str:
            # New format: "HH:MM+D"
            start_time_str, start_day_str = start_str.split("+")
            start_day_offset = int(start_day_str)
        else:
            # Legacy format: "HH:MM"
            start_time_str = start_str
            start_day_offset = 0

        if "+" in end_str:
            # New format: "HH:MM+D"
            end_time_str, end_day_str = end_str.split("+")
            end_day_offset = int(end_day_str)
        else:
            # Legacy format: "HH:MM"
            end_time_str = end_str
            end_day_offset = 0

        # Parse start and end times
        start_hour, start_min = map(int, start_time_str.split(":"))
        end_hour, end_min = map(int, end_time_str.split(":"))

        # Use reference date or today
        if reference_date is None:
            reference_date = datetime.now().astimezone()

        # Create base date (only date part, timezone-aware)
        base_date = reference_date.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        # Create start and end timestamps with day offsets
        start_timestamp = base_date.replace(
            hour=start_hour, minute=start_min
        ) + timedelta(days=start_day_offset)

        end_timestamp = base_date.replace(
            hour=end_hour, minute=end_min
        ) + timedelta(days=end_day_offset)

        # Legacy support: Handle case where end time is on next day (e.g., "23:00-01:00")
        # Only if no explicit day offsets were provided
        if "+" not in time_range and end_timestamp <= start_timestamp:
            end_timestamp += timedelta(days=1)

        return start_timestamp, end_timestamp

    except (ValueError, AttributeError) as e:
        msg = (
            f"Invalid time range format: '{time_range}'. "
            "Expected format: 'HH:MM+DD-HH:MM+DD' or 'HH:MM-HH:MM'"
        )
        raise ValueError(msg) from e


def split_price_list_at_maxima(
    price_list: list,
    number_of_sublists: int,
    target_sublist_length: int | None = None,
) -> tuple[list[list], list[list[int]]]:
    """Split price list into sublists around local maxima.

    Creates sublists centered around local maxima. Each sublist contains
    the largest values around its maximum and extends until:
    - Maximum length (target_sublist_length) is reached, OR
    - Next value falls below overall list average, OR
    - A local minimum is detected (value starts increasing)

    Args:
        price_list: The input price list to split.
        number_of_sublists: Maximum number of sublists to create.
        target_sublist_length: Maximum length of each sublist (optional).

    Returns:
        Tuple containing:
        - List of sublists, sorted by sum (descending - largest first)
        - List of index lists for each sublist
        Returns ([], []) if input is invalid.

    """
    if not price_list or number_of_sublists <= 0:
        return [], []

    # Calculate overall average
    numeric_values = [val for val in price_list if isinstance(val, (int, float))]
    if not numeric_values:
        return [], []
    overall_average = sum(numeric_values) / len(numeric_values)

    # Find all local maxima
    maxima_indices = find_local_maxima(price_list)
    if not maxima_indices:
        return [], []

    # Build sublists around ALL maxima (not pre-selecting)
    result = []
    indices = []
    used_indices = set()

    for max_idx in maxima_indices:
        if max_idx in used_indices:
            continue

        current_sublist = [price_list[max_idx]]
        current_indices = [max_idx]
        used_indices.add(max_idx)

        # Expand around the maximum, always choosing the larger available value
        forward_idx = max_idx + 1
        backward_idx = max_idx - 1
        
        while True:
            # Check if we've reached the target length
            if target_sublist_length and len(current_sublist) >= target_sublist_length:
                break
            
            # Get available values in both directions
            forward_val = None
            backward_val = None
            can_expand_forward = False
            can_expand_backward = False
            
            # Check forward direction
            if forward_idx < len(price_list) and forward_idx not in used_indices:
                val = price_list[forward_idx]
                # Check if we can expand forward (not below average, not at a used index)
                if isinstance(val, (int, float)) and val >= overall_average:
                    # Check if it's a local minimum
                    if forward_idx < len(price_list) - 1 and val < price_list[forward_idx + 1]:
                        # It's a local minimum - can include it but this will be the last forward step
                        forward_val = val
                        can_expand_forward = True
                    else:
                        forward_val = val
                        can_expand_forward = True
            
            # Check backward direction
            if backward_idx >= 0 and backward_idx not in used_indices:
                val = price_list[backward_idx]
                # Check if we can expand backward (not below average, not at a used index)
                if isinstance(val, (int, float)) and val >= overall_average:
                    # Check if it's a local minimum
                    if backward_idx > 0 and val < price_list[backward_idx - 1]:
                        # It's a local minimum - can include it but this will be the last backward step
                        backward_val = val
                        can_expand_backward = True
                    else:
                        backward_val = val
                        can_expand_backward = True
            
            # If we can't expand in either direction, stop
            if not can_expand_forward and not can_expand_backward:
                break
            
            # Choose the direction with the larger value
            if can_expand_forward and can_expand_backward:
                if forward_val >= backward_val:
                    # Expand forward
                    current_sublist.append(forward_val)
                    current_indices.append(forward_idx)
                    used_indices.add(forward_idx)
                    # Check if it was a local minimum
                    if forward_idx < len(price_list) - 1 and forward_val < price_list[forward_idx + 1]:
                        forward_idx = len(price_list)  # Stop forward expansion
                    else:
                        forward_idx += 1
                else:
                    # Expand backward
                    current_sublist.insert(0, backward_val)
                    current_indices.insert(0, backward_idx)
                    used_indices.add(backward_idx)
                    # Check if it was a local minimum
                    if backward_idx > 0 and backward_val < price_list[backward_idx - 1]:
                        backward_idx = -1  # Stop backward expansion
                    else:
                        backward_idx -= 1
            elif can_expand_forward:
                # Only forward is available
                current_sublist.append(forward_val)
                current_indices.append(forward_idx)
                used_indices.add(forward_idx)
                # Check if it was a local minimum
                if forward_idx < len(price_list) - 1 and forward_val < price_list[forward_idx + 1]:
                    forward_idx = len(price_list)  # Stop forward expansion
                else:
                    forward_idx += 1
            elif can_expand_backward:
                # Only backward is available
                current_sublist.insert(0, backward_val)
                current_indices.insert(0, backward_idx)
                used_indices.add(backward_idx)
                # Check if it was a local minimum
                if backward_idx > 0 and backward_val < price_list[backward_idx - 1]:
                    backward_idx = -1  # Stop backward expansion
                else:
                    backward_idx -= 1

        # Only keep sublists where maximum >= overall average
        max_val = max(val for val in current_sublist if isinstance(val, (int, float)))
        if max_val >= overall_average:
            result.append(current_sublist)
            indices.append(current_indices)

    # Sort ALL sublists by sum (descending - largest first)
    combined = []
    for sublist, idx_list in zip(result, indices, strict=True):
        try:
            total = sum(val for val in sublist if isinstance(val, (int, float)))
        except (TypeError, ValueError):
            total = 0
        combined.append((total, sublist, idx_list))

    combined.sort(key=lambda x: x[0], reverse=True)

    # Select only the top number_of_sublists
    combined = combined[:number_of_sublists]

    # Unpack sorted and filtered results
    result = [item[1] for item in combined]
    indices = [item[2] for item in combined]

    return result, indices


def select_maxima_by_length(
    maxima_indices: list[int],
    count: int,
    target_length: int,
) -> list[int]:
    """Select maxima to create sublists close to target length.

    Args:
        maxima_indices: List of all local maxima indices.
        count: Number of maxima to select.
        target_length: Target length for each sublist.

    Returns:
        List of selected maxima indices, sorted.

    """
    if len(maxima_indices) <= count:
        return sorted(maxima_indices)

    selected = []
    current_pos = 0

    for i in range(count):
        # Calculate ideal position for next split
        ideal_position = current_pos + target_length

        # Find the maximum closest to the ideal position
        remaining_maxima = [m for m in maxima_indices if m > current_pos]
        if not remaining_maxima:
            break

        closest_max = min(
            remaining_maxima,
            key=lambda x: abs(x - ideal_position),
        )

        selected.append(closest_max)
        current_pos = closest_max + 1
        # Remove selected maximum to avoid selecting it again
        maxima_indices = [m for m in maxima_indices if m != closest_max]

    return sorted(selected)


def select_best_maxima(
    maxima_indices: list[int],
    count: int,
    total_length: int,
) -> list[int]:
    """Select the best maxima to use as split points.

    Selects maxima that are roughly evenly distributed across the list.

    Args:
        maxima_indices: List of all local maxima indices.
        count: Number of maxima to select.
        total_length: Total length of the price list.

    Returns:
        List of selected maxima indices, sorted.

    """
    if len(maxima_indices) <= count:
        return sorted(maxima_indices)

    # Calculate ideal spacing between split points
    ideal_spacing = total_length / (count + 1)

    selected = []
    for i in range(count):
        # Calculate ideal position for this split point
        ideal_position = ideal_spacing * (i + 1)

        # Find the maximum closest to the ideal position
        closest_max = min(
            maxima_indices,
            key=lambda x: abs(x - ideal_position),
        )

        selected.append(closest_max)
        # Remove selected maximum to avoid selecting it again
        maxima_indices = [m for m in maxima_indices if m != closest_max]

    return sorted(selected)


def split_price_list(
    price_list: list,
    sublist_length: int,
    number_of_sublists: int,
) -> tuple[list[list], list[list[int]]]:
    """Split price list into sublists at local maxima positions.

    Splits the price list at local maxima to create the specified number
    of sublists, aiming for each sublist to have approximately the specified length.

    Args:
        price_list: The input price list to split.
        sublist_length: Target length of each sublist (number_1).
                       If 0, splits evenly without considering target length.
        number_of_sublists: Number of sublists to create (number_2).

    Returns:
        Tuple containing:
        - List of sublists split at local maxima positions
        - List of index lists corresponding to each sublist
        Returns ([], []) if input is invalid.

    """
    if not price_list or number_of_sublists <= 0:
        return [], []

    # Split at local maxima with optional target length
    if sublist_length > 0:
        return split_price_list_at_maxima(
            price_list, number_of_sublists, sublist_length
        )

    return split_price_list_at_maxima(price_list, number_of_sublists)




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
