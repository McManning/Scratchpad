# Lazy debugging/timing
import os
from time import perf_counter

start = 0
stop = 0

op_start = 0
op_stop = 0

IS_DEBUG = os.environ.get('SCRATCHPAD_DEBUG')

if IS_DEBUG:
    def init_log(event: str):
        global start, op_start
        start = op_start = perf_counter()
        print('*********** {} ***********'.format(event))

    def log(event: str):
        global start, stop
        stop = perf_counter()
        print('[{:.4f}s]\t\t{}'.format(stop - start, event))
        start = perf_counter()
        
    def op_log(event: str): 
        global op_start, op_stop, start
        op_stop = perf_counter()
        duration = op_stop - op_start
        print('[{:.4f}s {:.4f} fps]\t{}'.format(duration, 1.0 / duration, event))
        op_start = perf_counter()
        start = perf_counter() # reset start as well, from a previous op
        
    def debug(*args):
        """Print to console while in debug mode"""
        print(args)
else:
    def init_log(event: str): pass
    def log(event: str): pass
    def op_log(event: str): pass
    def debug(*args): pass
