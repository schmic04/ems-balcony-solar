"""Price list API for EMS Balcony Solar."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class ExpansionContext(NamedTuple):
    """Context for expanding around maximum."""

    minima_indices_set: set[int]
    overall_average: float
    target_sublist_length: int | None
    used_indices: set[int]


def get_combined_price_list(
    hass: HomeAssistant,
    sensor_entity_id: str,
) -> list:
    """
    Get combined price list from today and tomorrow attributes.

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
    """
    Group price list into hourly summaries.

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

    first_entry = price_list[0] if price_list else None

    if isinstance(first_entry, dict):
        return _process_dict_format_prices(price_list)

    return _process_simple_format_prices(price_list)


def _process_dict_format_prices(price_list: list) -> list[dict[str, str | float | int]]:
    """Process price list in dict format (15-min intervals with start/end/value)."""
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
    result = []
    for hour_dt, data in sorted(hourly_data.items()):
        prices = data["prices"]
        if prices:
            result.append(
                {
                    "date": hour_dt.strftime("%Y-%m-%d"),
                    "hour": hour_dt.strftime("%H:%M"),
                    "price": round(sum(prices) / len(prices), 4),
                }
            )

    return result


def _process_simple_format_prices(
    price_list: list,
) -> list[dict[str, str | float | int]]:
    """Process price list in simple format (list of floats)."""
    now = datetime.now().astimezone()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = []

    for i, price in enumerate(price_list):
        if not isinstance(price, (int, float)):
            continue

        # Calculate the datetime for this 15-minute interval
        interval_dt = today_start + timedelta(minutes=i * 15)
        hour_dt = interval_dt.replace(minute=0, second=0, microsecond=0)
        hour_key = hour_dt.strftime("%H:%M")

        # Find or create entry for this hour
        existing = _find_existing_hour_entry(result, hour_key, hour_dt)

        if existing:
            existing["prices"].append(float(price))
        else:
            result.append(
                {
                    "date": hour_dt.strftime("%Y-%m-%d"),
                    "hour": hour_key,
                    "prices": [float(price)],
                }
            )

    # Calculate statistics for each hour
    _calculate_hour_statistics(result)
    return result


def _find_existing_hour_entry(
    result: list[dict], hour_key: str, hour_dt: datetime
) -> dict | None:
    """Find existing hour entry in result list."""
    for entry in result:
        if entry["hour"] == hour_key and entry["date"] == hour_dt.strftime("%Y-%m-%d"):
            return entry
    return None


def _calculate_hour_statistics(result: list[dict]) -> None:
    """Calculate statistics for each hour entry."""
    for entry in result:
        prices = entry["prices"]
        if prices:
            entry["avg"] = round(sum(prices) / len(prices), 4)
            entry["min"] = round(min(prices), 4)
            entry["max"] = round(max(prices), 4)
            entry["prices"] = ", ".join([str(round(p, 4)) for p in prices])


def find_local_maxima(price_list: list) -> list[int]:
    """
    Find indices of local maxima in the price list.

    A local maximum is a value that is greater than both its neighbors.
    Edge cases (first and last element) are also considered maxima if they
    are greater than their single neighbor.

    Args:
        price_list: The input price list.

    Returns:
        List of indices where local maxima occur.

    """
    if not price_list:
        return []

    maxima_indices = []
    last_idx = len(price_list) - 1

    # Handle single element
    if last_idx == 0:
        return [0] if isinstance(price_list[0], (int, float)) else []

    # Check first element (boundary maximum)
    if (
        isinstance(price_list[0], (int, float))
        and isinstance(price_list[1], (int, float))
        and price_list[0] > price_list[1]
    ):
        maxima_indices.append(0)

    # Check middle elements (local maxima)
    for i in range(1, last_idx):
        if not isinstance(price_list[i], (int, float)):
            continue

        prev_val = price_list[i - 1]
        curr_val = price_list[i]
        next_val = price_list[i + 1]

        if not isinstance(prev_val, (int, float)) or not isinstance(
            next_val, (int, float)
        ):
            continue

        if curr_val > prev_val and curr_val > next_val:
            maxima_indices.append(i)

    # Check last element (boundary maximum)
    if (
        isinstance(price_list[last_idx], (int, float))
        and isinstance(price_list[last_idx - 1], (int, float))
        and price_list[last_idx] > price_list[last_idx - 1]
    ):
        maxima_indices.append(last_idx)

    return maxima_indices


def find_local_minima(price_list: list) -> list[int]:
    """
    Find indices of local minima in the price list.

    A local minimum is a value that is smaller than both its neighbors.
    Edge cases (first and last element) are also considered minima if they
    are smaller than their single neighbor.

    Args:
        price_list: The input price list.

    Returns:
        List of indices where local minima occur.

    """
    if not price_list:
        return []

    minima_indices = []
    last_idx = len(price_list) - 1

    # Handle single element
    if last_idx == 0:
        return [0] if isinstance(price_list[0], (int, float)) else []

    # Check first element (boundary minimum)
    if (
        isinstance(price_list[0], (int, float))
        and isinstance(price_list[1], (int, float))
        and price_list[0] < price_list[1]
    ):
        minima_indices.append(0)

    # Check middle elements (local minima)
    for i in range(1, last_idx):
        if not isinstance(price_list[i], (int, float)):
            continue

        prev_val = price_list[i - 1]
        curr_val = price_list[i]
        next_val = price_list[i + 1]

        if not isinstance(prev_val, (int, float)) or not isinstance(
            next_val, (int, float)
        ):
            continue

        if curr_val < prev_val and curr_val < next_val:
            minima_indices.append(i)

    # Check last element (boundary minimum)
    if (
        isinstance(price_list[last_idx], (int, float))
        and isinstance(price_list[last_idx - 1], (int, float))
        and price_list[last_idx] < price_list[last_idx - 1]
    ):
        minima_indices.append(last_idx)

    return minima_indices


def convert_indices_to_time_ranges(
    indices_list: list[list[int]],
    start_time: datetime | None = None,
) -> list[list[str]]:
    """
    Convert index lists to time ranges.

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
                time_ranges.append(
                    _format_time_range(
                        current_range_start, current_range_end, start_time
                    )
                )
                current_range_start = idx_list[i]
                current_range_end = idx_list[i]

        # Add the last range
        time_ranges.append(
            _format_time_range(current_range_start, current_range_end, start_time)
        )

        time_ranges_list.append(time_ranges)

    return time_ranges_list


def _format_time_range(
    start_idx: int,
    end_idx: int,
    base_time: datetime,
) -> str:
    """
    Format a time range from indices with day offset.

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
    """
    Parse a time range string to start and end timestamps.

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

    def _raise_invalid_format_error(time_range: str) -> None:
        """Raise ValueError for invalid time range format."""
        msg = f"Invalid time range format: '{time_range}'"
        raise ValueError(msg)

    expected_parts_count = 2
    try:
        # Split time range at the middle dash
        # Format can be: "HH:MM+D-HH:MM+D" or "HH:MM-HH:MM" (legacy)
        parts = time_range.split("-")
        if len(parts) != expected_parts_count:
            _raise_invalid_format_error(time_range)

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

        end_timestamp = base_date.replace(hour=end_hour, minute=end_min) + timedelta(
            days=end_day_offset
        )

        # Legacy support: Handle end time on next day (e.g., "23:00-01:00")
        # Only if no explicit day offsets were provided
        if "+" not in time_range and end_timestamp <= start_timestamp:
            end_timestamp += timedelta(days=1)

    except (ValueError, AttributeError) as e:
        msg = (
            f"Invalid time range format: '{time_range}'. "
            "Expected format: 'HH:MM+DD-HH:MM+DD' or 'HH:MM-HH:MM'"
        )
        raise ValueError(msg) from e
    else:
        return start_timestamp, end_timestamp


def split_price_list_at_maxima(
    price_list: list,
    number_of_sublists: int,
    target_sublist_length: int | None = None,
) -> tuple[list[list], list[list[int]]]:
    """
    Split price list into sublists around local maxima.

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

    # Find all local maxima and minima
    maxima_indices = find_local_maxima(price_list)
    if not maxima_indices:
        return [], []

    minima_indices_set = set(find_local_minima(price_list))

    # Build sublists around ALL maxima
    sublists_data = _build_sublists_around_maxima(
        price_list,
        maxima_indices,
        minima_indices_set,
        overall_average,
        target_sublist_length,
    )

    # Sort by total value and select top N
    return _sort_and_select_sublists(sublists_data, number_of_sublists)


def _build_sublists_around_maxima(
    price_list: list,
    maxima_indices: list[int],
    minima_indices_set: set[int],
    overall_average: float,
    target_sublist_length: int | None,
) -> list[tuple[list, list[int]]]:
    """Build sublists around each maximum."""
    result = []
    used_indices = set()

    context = ExpansionContext(
        minima_indices_set=minima_indices_set,
        overall_average=overall_average,
        target_sublist_length=target_sublist_length,
        used_indices=used_indices,
    )

    for max_idx in maxima_indices:
        if max_idx in used_indices:
            continue

        sublist_data = _expand_around_maximum(price_list, max_idx, context)

        if sublist_data:
            current_sublist, current_indices = sublist_data
            result.append((current_sublist, current_indices))

    return result


def _expand_around_maximum(
    price_list: list,
    max_idx: int,
    context: ExpansionContext,
) -> tuple[list, list[int]] | None:
    """Expand around a single maximum to create a sublist."""
    current_sublist = [price_list[max_idx]]
    current_indices = [max_idx]
    context.used_indices.add(max_idx)

    forward_idx = max_idx + 1
    backward_idx = max_idx - 1

    while True:
        if (
            context.target_sublist_length
            and len(current_sublist) >= context.target_sublist_length
        ):
            break

        forward_data = _check_expansion_direction(
            price_list,
            forward_idx,
            context.used_indices,
            context.minima_indices_set,
            context.overall_average,
        )
        backward_data = _check_expansion_direction(
            price_list,
            backward_idx,
            context.used_indices,
            context.minima_indices_set,
            context.overall_average,
        )

        if not forward_data and not backward_data:
            break

        direction = _choose_expansion_direction(forward_data, backward_data)

        if direction == "forward" and forward_data is not None:
            _expand_forward(
                current_sublist, current_indices, context.used_indices, forward_data
            )
            forward_idx += 1
        elif direction == "backward" and backward_data is not None:
            _expand_backward(
                current_sublist, current_indices, context.used_indices, backward_data
            )
            backward_idx -= 1

    return current_sublist, current_indices


def _check_expansion_direction(
    price_list: list,
    idx: int,
    used_indices: set[int],
    minima_indices_set: set[int],
    overall_average: float,
) -> tuple[int, float] | None:
    """Check if we can expand in a given direction."""
    if idx < 0 or idx >= len(price_list) or idx in used_indices:
        return None

    val = price_list[idx]
    if not isinstance(val, (int, float)) or val < overall_average:
        return None

    is_local_minimum = idx in minima_indices_set
    if is_local_minimum and val < overall_average:
        return None

    return idx, val


def _choose_expansion_direction(
    forward_data: tuple[int, float] | None,
    backward_data: tuple[int, float] | None,
) -> str:
    """Choose which direction to expand based on available values."""
    if forward_data and backward_data:
        return "forward" if forward_data[1] >= backward_data[1] else "backward"
    return "forward" if forward_data else "backward"


def _expand_forward(
    current_sublist: list,
    current_indices: list[int],
    used_indices: set[int],
    forward_data: tuple[int, float],
) -> None:
    """Expand sublist in forward direction."""
    idx, val = forward_data
    current_sublist.append(val)
    current_indices.append(idx)
    used_indices.add(idx)


def _expand_backward(
    current_sublist: list,
    current_indices: list[int],
    used_indices: set[int],
    backward_data: tuple[int, float],
) -> None:
    """Expand sublist in backward direction."""
    idx, val = backward_data
    current_sublist.insert(0, val)
    current_indices.insert(0, idx)
    used_indices.add(idx)


def _sort_and_select_sublists(
    sublists_data: list[tuple[list, list[int]]],
    number_of_sublists: int,
) -> tuple[list[list], list[list[int]]]:
    """Sort sublists by sum and select top ones."""
    combined = []
    for sublist, idx_list in sublists_data:
        try:
            total = sum(val for val in sublist if isinstance(val, (int, float)))
        except (TypeError, ValueError):
            total = 0
        combined.append((total, sublist, idx_list))

    combined.sort(key=lambda x: x[0], reverse=True)
    combined = combined[:number_of_sublists]

    result = [item[1] for item in combined]
    indices = [item[2] for item in combined]

    return result, indices


def select_maxima_by_length(
    maxima_indices: list[int],
    count: int,
    target_length: int,
) -> list[int]:
    """
    Select maxima to create sublists close to target length.

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

    for _ in range(count):
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
    """
    Select the best maxima to use as split points.

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
    """
    Split price list into sublists at local maxima positions.

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
    """
    Get the current price from the sensor.

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
    """
    Get the price at a specific time from the price list.

    Args:
        price_list: Combined price list from get_combined_price_list.
        target_time: The time to get the price for.

    Returns:
        Price at the specified time, or None if not found.

    """
    for entry in price_list:
        start_time = entry.get("start")
        end_time = entry.get("end")

        if (
            start_time
            and end_time
            and isinstance(start_time, datetime)
            and isinstance(end_time, datetime)
            and start_time <= target_time < end_time
        ):
            value = entry.get("value")
            return value if isinstance(value, (int, float)) else None

    return None


def get_lowest_price_period(
    price_list: list[dict[str, float | datetime]],
    duration_hours: int = 1,
) -> dict[str, float | datetime] | None:
    """
    Find the period with the lowest average price.

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
        total_price = sum(
            float(value)
            for entry in period
            if isinstance((value := entry.get("value")), (int, float))
        )
        avg_price = total_price / len(period)

        if avg_price < lowest_avg:
            lowest_avg = avg_price
            lowest_period = {
                "start_time": period[0].get("start"),
                "end_time": period[-1].get("end"),
                "average_price": avg_price,
            }

    return lowest_period
