import random

def randomword(length):
    """Generate a random string of desired length
    """
    return ''.join(random.choice(string.lowercase) for i in range(length))

