# Calculate the average of values stored in a list.


def calculate_average(scores):
    """Return the average of the given list of scores."""
    if not scores:
        return 0.0
    total = 0
    for score in scores:
        total += score
    return total / len(scores)


if __name__ == "__main__":
    raw_input = input("Enter scores separated by spaces: ").strip()
    if raw_input:
        scores = [float(x) for x in raw_input.split()]
        avg = calculate_average(scores)
        print(f"Average: {avg}")
    else:
        print("No scores entered.")
