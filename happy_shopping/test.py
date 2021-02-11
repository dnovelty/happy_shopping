def foo():
    _list = range(4)
    for i in _list:
        print('run in loop')
        yield i
    print('run in func')
gen = foo()

for i in gen:
    pass