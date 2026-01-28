import ast
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

from config_system import config
import security

logger = logging.getLogger('Analysis')


def analyze_file(path: Path) -> Dict[str, Any]:
    result = {'path': str(path), 'issues': []}
    try:
        if not path.exists() or not path.is_file():
            result['issues'].append({'severity': 'error', 'message': 'File not found'})
            return result

        if path.suffix not in ('.py', '.txt', '.md'):
            result['issues'].append({'severity': 'info', 'message': 'Non-text file skipped'})
            return result

        src = path.read_text(encoding='utf-8', errors='ignore')

        # AST scan for globals, eval/exec
        try:
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Global):
                    result['issues'].append({'severity': 'warning', 'message': 'global usage found', 'line': node.lineno})
                if isinstance(node, ast.Call) and getattr(node.func, 'id', '') in ('eval', 'exec'):
                    result['issues'].append({'severity': 'error', 'message': f'uses {node.func.id}()', 'line': node.lineno})
        except Exception as e:
            result['issues'].append({'severity': 'warning', 'message': f'AST parse failed: {e}'})

        # Pattern checks
        if 'threading.Thread' in src:
            result['issues'].append({'severity': 'warning', 'message': 'threading.Thread usage'})
        if 'asyncio.to_thread' in src:
            result['issues'].append({'severity': 'info', 'message': 'asyncio.to_thread detected'})
        if 'subprocess' in src:
            result['issues'].append({'severity': 'warning', 'message': 'subprocess usage'})

    except Exception as e:
        result['issues'].append({'severity': 'error', 'message': str(e)})
    return result


def analyze_and_write_report(files: List[str], job_id: str = None) -> Dict[str, Any]:
    report = {'job_id': job_id, 'files': [], 'summary': {}}
    for f in files:
        # validate path
        try:
            p = Path(f)
            # For safety, ensure path is under config.BASE_DIR or absolute validated
            valid = security.validate_path(p)
            if not valid:
                report['files'].append({'path': f, 'issues': [{'severity': 'error', 'message': 'Path not allowed'}]})
                continue
        except Exception:
            report['files'].append({'path': f, 'issues': [{'severity': 'error', 'message': 'Invalid path'}]})
            continue

        res = analyze_file(p)
        report['files'].append(res)

    # summary counts
    counts = {'error': 0, 'warning': 0, 'info': 0}
    for entry in report['files']:
        for iss in entry.get('issues', []):
            sev = iss.get('severity', 'info')
            counts[sev] = counts.get(sev, 0) + 1

    report['summary'] = counts

    out = config.BASE_DIR / '_zena_analisis'
    try:
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(report, fh, indent=2)
    except Exception as e:
        logger.error(f"Failed to write analysis report: {e}")

    return report
