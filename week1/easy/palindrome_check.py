# Determine whether a string reads the same forwards and backwards.


def is_palindrome(text):
    """Check if the string is a palindrome using two pointers."""
    left = 0
    right = len(text) - 1

    while left < right:
        if text[left] != text[right]:
            return False
        left += 1
        right -= 1

    return True


if __name__ == "__main__":
    user_input = input("Enter a string: ")
    if is_palindrome(user_input):
        print(f"'{user_input}' is a palindrome.")
    else:
        print(f"'{user_input}' is not a palindrome.")
