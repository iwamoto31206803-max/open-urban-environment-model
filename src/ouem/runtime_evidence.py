"""Bounded CI metadata report; never import third-party packages or simulators."""

from importlib import metadata
import json
from pathlib import Path
import platform
import re
import sys


PACKAGES = (
    'pip', 'numpy', 'rasterio', 'geopandas', 'shapely', 'pyproj', 'scipy',
    'voxcity', 'numba', 'matplotlib', 'affine', 'pandas', 'pytest',
)
PUBLIC_VOXCITY_URL = 'https://github.com/kunifujiwara/VoxCity.git'


def collect():
    """Return sanitized observations and explicit failures, without raw errors."""
    issues = []
    executable = Path(sys.executable).name
    if not re.fullmatch(r'python(?:\d+(?:\.\d+)*)?(?:\.exe)?', executable, re.I):
        executable = '<redacted>'
    report = {
        'os': platform.system(),
        'python': platform.python_version(),
        'executable': '<python-prefix>/' + executable,
        'packages': {},
    }
    for name in PACKAGES:
        try:
            version = metadata.version(name)
            # Exclude arbitrary local-version/path text from metadata output.
            if not re.fullmatch(r'\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.(?:post|dev)\d+)?', version):
                raise ValueError('Unsupported version representation')
            report['packages'][name] = version
        except Exception:
            report['packages'][name] = 'unavailable'
            issues.append(name + ': version unavailable or withheld')
    try:
        raw = metadata.distribution('voxcity').read_text('direct_url.json')
        if raw is None:
            report['voxcity_origin'] = {'status': 'unavailable'}
            issues.append('voxcity: direct URL metadata absent')
        else:
            origin = json.loads(raw)
            vcs = origin.get('vcs_info', {})
            commit = vcs.get('commit_id', '')
            if (origin.get('url') != PUBLIC_VOXCITY_URL or vcs.get('vcs') != 'git'
                    or not isinstance(commit, str) or not re.fullmatch(r'[0-9a-fA-F]{40}', commit)):
                raise ValueError('Unrecognized origin')
            report['voxcity_origin'] = {'status': 'observed', 'url': PUBLIC_VOXCITY_URL,
                                        'vcs': 'git', 'commit_id': commit}
    except Exception:
        report['voxcity_origin'] = {'status': 'withheld_or_unavailable'}
        issues.append('voxcity: origin unavailable or outside public allowlist')
    report['issues'] = issues
    report['status'] = 'incomplete' if issues else 'observed'
    return report


def main():
    try:
        report = collect()
    except Exception:
        # Never print exception messages, environment variables or traceback paths.
        report = {'status': 'incomplete', 'issues': ['runtime metadata collection failed']}
    print(json.dumps(report, indent=2, sort_keys=True))
    if report['status'] == 'incomplete':
        print('::warning::Runtime evidence is incomplete; inspect sanitized issues above. Pytest remains independent.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
