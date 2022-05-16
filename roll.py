from random import randint
from functools import partial

def roll3d6():
    return sum(randint(1, 6) for i in range(3))

def roll4d6dl1():
    dice = sorted(randint(1, 6) for i in range(4))
    return sum(dice[1:])

def genchar(roll_method=roll4d6dl1):
    return [roll_method() for i in range(6)]
