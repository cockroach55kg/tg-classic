#!/usr/bin/env python3
"""Run the current UI fixes and retained regressions in one empty-profile app."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parts = []
scenarios = [('R4', 'mac-ui-r4-scenario.cpp'), ('R3', 'mac-ui-r3-scenario.cpp'),
             ('Modal', 'mac-regression-scenario.cpp'), ('Startup', 'mac-smoke-scenario.cpp')]
for name, filename in scenarios:
    source = (root / 'tools' / filename).read_text()
    assert source.count('namespace Test {') == 1, filename
    parts.append(source.replace('namespace Test {', 'namespace Test::' + name + ' {', 1))
parts.append('#ifdef _DEBUG\nnamespace Test {\nvoid SetupScenario(not_null<Runner*> runner) {\n'
             + ''.join(name + '::SetupScenario(runner);\n' for name, _ in scenarios)
             + '}\n}\n#endif\n')
overlay = root / 'local-mac/mac-r4-combined-scenario.cpp'
overlay.write_text('\n'.join(parts))
subprocess.run([sys.executable, str(root / 'tools/run-mac-smoke.py'), '--overlay', str(overlay),
                '--evidence', str(root / 'evidence/mac-r4-regressions')], check=True)
