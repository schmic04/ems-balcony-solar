"""EMS tools for dynamic price list analysis."""

from __future__ import annotations


def is_local_maximum(price_list: list[float], index: int) -> bool:
    """Check if value at given index is a local maximum.

    Args:
        price_list: List of price values
        index: Index to check

    Returns:
        True if value at index is a local maximum

    """
    if index <= 0 or index >= len(price_list) - 1:
        return False
    return (
        price_list[index] > price_list[index - 1]
        and price_list[index] > price_list[index + 1]
    )


def sort_sublists_by_sum(
    sublists: list[list[float]], descending: bool = True
) -> list[list[float]]:
    """Sort a list of sublists by their sum.

    Args:
        sublists: List of sublists to sort
        descending: Sort in descending order (highest sum first) if True

    Returns:
        Sorted list of sublists

    """
    return sorted(sublists, key=sum, reverse=descending)


def dynamic_sublists_with_window(
    price_list: list[float], window: int = 10
) -> tuple[list[list[float]], list[list[int]]]:
    """Create dynamic sublists from price data based on local maxima and average thresholds.

    Args:
        price_list: List of price values to analyze
        window: Maximum length for each sublist (default: 10)

    Returns:
        Tuple containing:
        - List of sublists with price values (max length = window)
        - List of corresponding index lists from original price_list

    """
    if not price_list:
        return [], []

    if len(price_list) < 2:
        return [price_list], [[0]]

    overall_avg = sum(price_list) / len(price_list)
    sublists = []
    index_lists = []
    used_indices = set()

    for i, current_value in enumerate(price_list):
        if i in used_indices:
            continue

        prev_value = price_list[i - 1] if i > 0 else None
        next_value = price_list[i + 1] if i < len(price_list) - 1 else None

        # Check if current value is a local maximum and above average
        is_local_max = (
            (prev_value is None or current_value > prev_value)
            and (next_value is None or current_value > next_value)
            and current_value >= overall_avg
        )

        if is_local_max:
            start_idx = i
            end_idx = i

            # Expand left while values are >= average
            for j in range(i - 1, -1, -1):
                if price_list[j] < overall_avg:
                    break
                start_idx = j

            # Expand right while values are >= average
            for j in range(i + 1, len(price_list)):
                if price_list[j] < overall_avg:
                    break
                end_idx = j

            # Ensure sublist doesn't exceed window length
            if end_idx - start_idx + 1 > window:
                # Truncate from the side that would preserve more high-value elements
                # Check which side (left or right) has higher average values
                left_extension = i - start_idx
                right_extension = end_idx - i

                if left_extension + right_extension + 1 > window:
                    # Need to trim - prioritize the side with higher values
                    max_left = (
                        window - 1 - right_extension
                        if right_extension < window - 1
                        else 0
                    )
                    max_right = (
                        window - 1 - left_extension
                        if left_extension < window - 1
                        else 0
                    )

                    # Calculate which side to prioritize based on average values
                    left_avg = (
                        sum(price_list[max(0, i - max_left) : i]) / max(1, max_left)
                        if max_left > 0
                        else 0
                    )
                    right_avg = (
                        sum(price_list[i + 1 : min(len(price_list), i + 1 + max_right)])
                        / max(1, max_right)
                        if max_right > 0
                        else 0
                    )

                    if left_avg >= right_avg:
                        # Keep more on the left
                        start_idx = max(
                            start_idx,
                            i - (window - 1 - min(right_extension, window - 1)),
                        )
                        end_idx = min(end_idx, start_idx + window - 1)
                    else:
                        # Keep more on the right
                        end_idx = min(
                            end_idx, i + (window - 1 - min(left_extension, window - 1))
                        )
                        start_idx = max(start_idx, end_idx - window + 1)

            # Create sublist and corresponding indices
            sublist_indices = list(range(start_idx, end_idx + 1))
            sublist_values = [price_list[idx] for idx in sublist_indices]

            sublists.append(sublist_values)
            index_lists.append(sublist_indices)
            used_indices.update(sublist_indices)

    return sublists, index_lists


# Example usage and testing
if __name__ == "__main__":
    test_list = [
        0.48,
        0.42,
        0.42,
        0.43,
        1.34,
        3.22,
        4.5,
        4.0,
        0.3,
        -0.06,
        -0.11,
        -0.41,
        -1.0,
        -1.93,
        -1.58,
        -0.45,
        -0.1,
        0.01,
        6.95,
        11.78,
        14.14,
        14.84,
        12.65,
        10.12,
        8.67,
        7.81,
        6.97,
        6.0,
        5.42,
        6.22,
        7.46,
        8.28,
        8.32,
        6.9,
        2.22,
        0.01,
        -0.02,
        -0.23,
        -0.43,
        -0.1,
        0.0,
        5.4,
        6.96,
        8.21,
        8.4,
        9.13,
        9.79,
        8.53,
    ]

    window_sublists, indices = dynamic_sublists_with_window(test_list, window=8)
    sorted_sublists = sort_sublists_by_sum(window_sublists)
    average = sum(test_list) / len(test_list)
