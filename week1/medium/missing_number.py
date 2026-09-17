# Find the missing number from a sequence containing numbers from 1 to N.


def find_missing_number(numbers, n=None):
    """Find the missing number from a sequence containing numbers from 1 to N.

    If n is not provided, it is assumed to be len(numbers) + 1.
    """
    if n is None:
        n = len(numbers) + 1
    expected_sum = n * (n + 1) // 2
    actual_sum = sum(numbers)
    return expected_sum - actual_sum


if __name__ == "__main__":
    raw_input = input("Enter the sequence numbers separated by spaces: ").strip()
    if raw_input:
        nums = [int(x) for x in raw_input.split()]
        missing = find_missing_number(nums)
        print(f"The missing number from 1 to {len(nums) + 1} is: {missing}")
    else:
        print("No numbers provided.")
