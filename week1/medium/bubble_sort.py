# Implement Bubble Sort manually rather than using Python's built-in sorting.


def bubble_sort(arr):
    """Sort list in ascending order using Bubble Sort algorithm."""
    nums = list(arr)
    n = len(nums)

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if nums[j] > nums[j + 1]:
                nums[j], nums[j + 1] = nums[j + 1], nums[j]
                swapped = True
        if not swapped:
            break

    return nums


if __name__ == "__main__":
    raw_input = input("Enter numbers separated by spaces: ").strip()
    if raw_input:
        nums = [float(x) for x in raw_input.split()]
        sorted_nums = bubble_sort(nums)
        result = [int(x) if x.is_integer() else x for x in sorted_nums]
        print("Sorted list:", result)
    else:
        print("No numbers provided.")
