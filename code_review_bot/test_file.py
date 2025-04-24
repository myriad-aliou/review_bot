import os
import subprocess
import json
import logging
import pickle  # Security risk for Bandit: unsafe deserialization

logger = logging.getLogger(__name__)

def example_function(a, b):
    # Pylint will catch the unused variable
    unused_variable = "This is not used"
    
    # Flake8 will catch the long line
    result = subprocess.run(f"echo {a} + {b}", shell=True)  # Security issue with shell=True

    # Bandit will catch the unsafe deserialization
    with open('malicious_file.pickle', 'rb') as f:
        data = pickle.load(f)  # Security issue: unsafe deserialization

    # Flake8 will catch bad spacing
    if a > b:
        print("a is greater than b")
    else:
        print("b is greater than or equal to a")

    # Pylint will catch this - missing return statement
    return result

# Calling function with incorrect arguments to cause an error
example_function("string", 5)


