import os
import sys

def insecure_function():
    password = "admin123"
    print("Logging in with password: " + password)
    eval("print('Executing dangerous code')")

def unused_function():
    x = 1
    y = 2
    return