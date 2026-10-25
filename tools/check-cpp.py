import json
from pathlib import Path
import subprocess
from tree_sitter import Language, Parser
import tree_sitter_cpp

bundle = Path(__file__).resolve().parents[1]
root = bundle / 'tdesktop'
parser = Parser(Language(tree_sitter_cpp.language()))


def errors(node):
    found = []
    if node.type == 'ERROR' or node.is_missing:
        found.append({'type': node.type, 'line': node.start_point[0] + 1})
    for child in node.children:
        found.extend(errors(child))
    return found


results = []
for repo in (root, root / 'Telegram/lib_ui'):
    names = set(subprocess.check_output(['git', 'diff', '--name-only'], cwd=repo, text=True).splitlines())
    names.update(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=repo, text=True).splitlines())
    for name in sorted(names):
        path = repo / name
        if not path.is_file() or path.suffix not in ('.cpp', '.h'):
            continue
        current = errors(parser.parse(path.read_bytes()).root_node)
        try:
            original = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=repo, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            original = b''
        baseline = errors(parser.parse(original).root_node)
        results.append({'file': str(path.relative_to(root)), 'parse_errors': current,
                        'upstream_parse_errors': baseline, 'no_added_errors': len(current) <= len(baseline)})
report = {'scope': 'C++ grammar only; no native compilation or type checking; Objective-C++ is not covered', 'results': results}
(bundle / 'evidence/source-syntax.json').write_text(json.dumps(report, indent=2) + '\n')
assert all(item['no_added_errors'] for item in results)
print('No additional C++ grammar errors:', len(results), 'files. Native compilation is still required.')
