"""Two-tier client: this Python process connects directly to the relational database."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db import query
for row in query('SELECT faculty_name,max_weekly_hours FROM faculty ORDER BY faculty_name'):
    print(f"{row['faculty_name']:<25} {row['max_weekly_hours']} weekly hours")
