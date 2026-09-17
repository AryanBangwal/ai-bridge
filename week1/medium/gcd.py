# Find the greatest common divisor of two numbers.


def gcd(a, b):
    """Calculate the greatest common divisor using Euclidean algorithm."""
    a, b = abs(a), abs(b)
    while b != 0:
        a, b = b, a % b
    return a


if __name__ == "__main__":
    a = int(input("Enter first integer: "))
    b = int(input("Enter second integer: "))
    print(f"GCD of {a} and {b} is {gcd(a, b)}.")
