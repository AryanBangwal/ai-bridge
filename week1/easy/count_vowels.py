# Count the number of vowels in a string.


def count_vowels(text):
    """Return the count of vowels (a, e, i, o, u) in text."""
    vowels = "aeiouAEIOU"
    count = 0
    for char in text:
        if char in vowels:
            count += 1
    return count


if __name__ == "__main__":
    text = input("Enter a string: ")
    print(f"Number of vowels: {count_vowels(text)}")
