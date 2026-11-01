"""Hadoop Streaming mapper. Input: department<TAB>hours. No Hadoop dependency for local testing."""
import sys
for line in sys.stdin:
    department,hours=line.rstrip('\n').split('\t')
    print(f'{department}\t{float(hours)}')
