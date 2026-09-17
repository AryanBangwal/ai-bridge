# Determine whether two strings contain the same characters with the same frequencies.


def is_anagram(str1, str2):
    """Return True if str1 and str2 are anagrams, ignoring spaces and case."""
    s1 = str1.replace(" ", "").lower()
    s2 = str2.replace(" ", "").lower()

    if len(s1) != len(s2):
        return False

    counts = {}
    for char in s1:
        counts[char] = counts.get(char, 0) + 1

    for char in s2:
        if char not in counts:
            return False
        counts[char] -= 1
        if counts[char] < 0:
            return False

    return True


if __name__ == "__main__":
    first = input("Enter first string: ")
    second = input("Enter second string: ")
    if is_anagram(first, second):
        print(f"'{first}' and '{second}' are anagrams.")
    else:
        print(f"'{first}' and '{second}' are not anagrams.")
