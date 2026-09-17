# Calculate the sum of all integers from 1 through N.


def sum_1_to_n(n):
    """Return the sum of all integers from 1 through n using a loop."""
    total = 0
    for i in range(1, n + 1):
        total += i
    return total


if __name__ == "__main__":
    n = int(input("Enter an integer N: "))
    print(f"Sum from 1 to {n}: {sum_1_to_n(n)}")
