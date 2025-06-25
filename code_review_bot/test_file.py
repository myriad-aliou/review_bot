import os

def insecure_function():
    password = "admin123"
    print("Logging in with password: " + password)
    eval("print('Executing dangerous code')")

def unused_function():
    x = 1
    y = 2
    return

def badly_formatted_code():
    a=1
    b=2
    print(a+b)

insecure_function()

#Modify file