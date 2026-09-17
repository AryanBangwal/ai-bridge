# Reverse a list without simply using a built-in reverse function.


def reverse_list(items):
    """Reverse a list in-place using two pointers without built-in reverse."""
    arr = list(items)
    left = 0
    right = len(arr) - 1

    while left < right:
        arr[left], arr[right] = arr[right], arr[left]
        left += 1
        right -= 1

    return arr


if __name__ == "__main__":
    raw_input = input("Enter list items separated by spaces: ").strip()
    items = raw_input.split() if raw_input else []
    reversed_items = reverse_list(items)
    print("Reversed list:", reversed_items)
