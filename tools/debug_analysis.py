from pathlib import Path
from zena_mode.analysis import analyze_and_write_report
import security

p = Path("debug_sample.py")
p.write_text("""import subprocess\ndef foo():\n    eval('1+1')\n""")
print("validate_path:", security.validate_path(p))
print(analyze_and_write_report([str(p)], job_id="dbg"))
