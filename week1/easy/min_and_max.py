# Find the smallest and largest values without relying on built-in min/max.


def find_min_and_max(numbers):
    """Find minimum and maximum in a list without using min() or max()."""
    if not numbers:
        return None, None

    min_val = numbers[0]
    max_val = numbers[0]

    for val in numbers[1:]:
        if val < min_val:
            min_val = val
        if val > max_val:
            max_val = val

    return min_val, max_val


if __name__ == "__main__":
    raw_input = input("Enter numbers separated by spaces: ").strip()
    if raw_input:
        nums = [float(x) for x in raw_input.split()]
        min_val, max_val = find_min_and_max(nums)
        min_disp = int(min_val) if min_val.is_integer() else min_val
        max_disp = int(max_val) if max_val.is_integer() else max_val
        print(f"Minimum: {min_disp}")
        print(f"Maximum: {max_disp}")
    else:
        print("No numbers provided.")
