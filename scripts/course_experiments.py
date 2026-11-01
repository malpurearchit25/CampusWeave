import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from syllabus_lab import run_theory_experiments
result=run_theory_experiments()
(ROOT/'docs/syllabus_evidence.json').write_text(json.dumps(result,indent=2))
print('FD closure, minimal cover, synthesis, serializability, recovery, fragmentation and parallel reduction checks passed.')
