# Count how many times a target value appears in a list.


def count_matches(items, target):
    """Count occurrences of target in items using a loop."""
    count = 0
    for item in items:
        if item == target:
            count += 1
    return count


if __name__ == "__main__":
    raw_input = input("Enter list elements separated by spaces: ").strip()
    items = raw_input.split() if raw_input else []
    target = input("Enter target value to search for: ").strip()

    result = count_matches(items, target)
    print(f"'{target}' appears {result} time(s).")
