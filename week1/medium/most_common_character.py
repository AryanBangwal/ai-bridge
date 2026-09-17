# Find the character that occurs most frequently in a string.


def most_common_character(text, ignore_spaces=False):
    """Find the character that occurs most frequently in a string.

    Returns a tuple (character, count). If string is empty, returns (None, 0).
    """
    if ignore_spaces:
        text = text.replace(" ", "")

    if not text:
        return None, 0

    counts = {}
    max_char = None
    max_count = 0

    for char in text:
        counts[char] = counts.get(char, 0) + 1
        if counts[char] > max_count:
            max_count = counts[char]
            max_char = char

    return max_char, max_count


if __name__ == "__main__":
    text = input("Enter a string: ")
    char, count = most_common_character(text)
    if char is not None:
        print(f"Most common character: '{char}' (appeared {count} times)")
    else:
        print("String is empty.")
