# example_bad_code.py

import os
import sys

def my_function():
    x=  1
    y =2
    print(x + y) # manque espace avant et après '+'
    password = "123456"  # mot de passe en dur (security issue)
    eval("print('Danger!')")  # usage dangereux de eval

my_function()

def unused_function():
    pass  # fonction définie mais jamais utilisée
