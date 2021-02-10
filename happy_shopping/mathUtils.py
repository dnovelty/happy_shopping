import random


def int_between(left, right):
    return random.randint(left, right)


map = {None: 'none'}
print(map[None])
map[None] = 'None'
print(map[None])
