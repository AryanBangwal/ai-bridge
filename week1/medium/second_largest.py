# Find the second-largest distinct value without sorting the entire list.


def find_second_largest(numbers):
    """Find the second-largest distinct value in O(N) without sorting.

    Returns None if fewer than 2 distinct values exist.
    """
    first = None
    second = None

    for num in numbers:
        if first is None or num > first:
            second = first
            first = num
        elif num != first and (second is None or num > second):
            second = num

    return second


if __name__ == "__main__":
    raw_input = input("Enter numbers separated by spaces: ").strip()
    if raw_input:
        nums = [float(x) for x in raw_input.split()]
        result = find_second_largest(nums)
        if result is not None:
            disp = int(result) if result.is_integer() else result
            print(f"Second-largest distinct value: {disp}")
        else:
            print("Could not find a distinct second-largest value.")
    else:
        print("No numbers provided.")
