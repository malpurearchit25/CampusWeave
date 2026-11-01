"""Hadoop Streaming reducer. Input must be shuffled/sorted by department."""
import sys
from itertools import groupby
records=(line.rstrip('\n').split('\t') for line in sys.stdin)
for department,items in groupby(records,key=lambda x:x[0]):
    print(f'{department}\t{sum(float(item[1]) for item in items):g}')
