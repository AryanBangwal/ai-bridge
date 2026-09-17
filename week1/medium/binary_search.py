# Efficiently find an element in a sorted list by repeatedly halving the search space.


def binary_search(arr, target):
    """Perform iterative binary search on a sorted list.

    Returns the index of target if found, else -1.
    """
    low = 0
    high = len(arr) - 1

    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1

    return -1


if __name__ == "__main__":
    raw_input = input("Enter sorted numbers separated by spaces: ").strip()
    if raw_input:
        nums = [int(x) for x in raw_input.split()]
        target = int(input("Enter target number to search: "))
        index = binary_search(nums, target)
        if index != -1:
            print(f"Found {target} at index {index}.")
        else:
            print(f"{target} not found in the list.")
    else:
        print("Empty list provided.")
