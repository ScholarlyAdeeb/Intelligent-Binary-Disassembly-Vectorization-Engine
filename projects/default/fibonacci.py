def fibonacci(n):
    """
    Generates the Fibonacci sequence up to n terms (inclusive).
    The sequence starts with 0 and 1.
    """
    if n <= 0:
        return []
    if n == 1:
        return [0]
    
    sequence = [0, 1]
    while len(sequence) < n:
        next_fib = sequence[-1] + sequence[-2]
        sequence.append(next_fib)
    return sequence

if __name__ == "__main__":
    try:
        # Get the number of terms from the user
        terms = int(input("Enter the number of Fibonacci terms to generate: "))
        
        if terms < 0:
            print("Please enter a non-negative number.")
        else:
            result = fibonacci(terms)
            print("\nFibonacci Sequence:")
            print(", ".join(map(str, result)))

    except ValueError:
        print("Invalid input. Please enter an integer.")