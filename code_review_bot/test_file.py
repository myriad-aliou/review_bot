import os, sys # multiple imports on same line (style issue)

def greet(name):
 print("Hello, " + name) # indentation error + use of + instead of f-string

def secret():
    password = "123456"  # hardcoded password (security issue - Bandit will flag this)
    return password

def unused_function():  # unused function (code smell)
    pass

greet('Aliou'
