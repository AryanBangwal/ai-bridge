# Find two elements whose sum equals a given target.


def two_sum(numbers, target):
    """Find the indices of two elements whose sum equals target.

    Returns a tuple of indices (i, j) if found, else None.
    """
    seen = {}
    for index, num in enumerate(numbers):
        complement = target - num
        if complement in seen:
            return seen[complement], index
        seen[num] = index
    return None


if __name__ == "__main__":
    raw_input = input("Enter numbers separated by spaces: ").strip()
    if raw_input:
        nums = [int(x) for x in raw_input.split()]
        target = int(input("Enter target sum: "))
        result = two_sum(nums, target)
        if result:
            i, j = result
            print(f"Pair found at indices ({i}, {j}): {nums[i]} + {nums[j]} = {target}")
        else:
            print(f"No pair found that sums to {target}.")
    else:
        print("No numbers provided.")
