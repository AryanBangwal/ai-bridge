# Find the longest consecutive sequence of the same value.


def find_longest_streak(items):
    """Find the value and length of the longest consecutive sequence of identical elements.

    Returns a tuple: (value, max_length). If items is empty, returns (None, 0).
    """
    if not items:
        return None, 0

    max_item = items[0]
    max_streak = 1

    current_item = items[0]
    current_streak = 1

    for item in items[1:]:
        if item == current_item:
            current_streak += 1
        else:
            current_item = item
            current_streak = 1

        if current_streak > max_streak:
            max_streak = current_streak
            max_item = current_item

    return max_item, max_streak


if __name__ == "__main__":
    raw_input = input("Enter elements separated by spaces: ").strip()
    items = raw_input.split() if raw_input else []
    val, streak = find_longest_streak(items)
    if streak > 0:
        print(f"Longest streak is '{val}' with length {streak}.")
    else:
        print("List is empty.")
