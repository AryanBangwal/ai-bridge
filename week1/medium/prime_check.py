# Determine whether a number is prime efficiently.
import math


def is_prime(n):
    """Determine whether an integer n is prime efficiently."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    limit = math.isqrt(n)
    for i in range(5, limit + 1, 6):
        if n % i == 0 or n % (i + 2) == 0:
            return False

    return True


if __name__ == "__main__":
    num = int(input("Enter an integer: "))
    if is_prime(num):
        print(f"{num} is prime.")
    else:
        print(f"{num} is not prime.")
