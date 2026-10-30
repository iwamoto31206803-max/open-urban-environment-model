"""Safety and failure visibility of metadata-only CI reporting."""
import builtins
import json
from types import SimpleNamespace

import pytest

from ouem import runtime_evidence as m


COMMIT = 'fa212656305328a9a657973bae26f352bfe813bc'


@pytest.fixture
def installed(monkeypatch):
    origin = {'url': m.PUBLIC_VOXCITY_URL,
              'vcs_info': {'vcs': 'git', 'commit_id': COMMIT}}
    monkeypatch.setattr(m.metadata, 'version', lambda name: '1.7.0')
    monkeypatch.setattr(m.metadata, 'distribution', lambda name: SimpleNamespace(
        read_text=lambda filename: json.dumps(origin)))
    return origin


def test_metadata_only_public_origin_and_anonymous_executable(installed, monkeypatch):
    monkeypatch.setattr(m.sys, 'executable', '/private/person/token/python3.12')
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        assert name.split('.')[0] not in set(m.PACKAGES) | {'qgis', 'osgeo'}
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', guarded)
    report = m.collect()
    assert report['status'] == 'observed'
    assert report['executable'] == '<python-prefix>/python3.12'
    assert report['voxcity_origin']['commit_id'] == COMMIT
    assert 'private' not in json.dumps(report)


@pytest.mark.parametrize('raw', [None, 'invalid JSON secret', json.dumps({
    'url': 'https://user:secret@github.com/kunifujiwara/VoxCity.git',
    'vcs_info': {'vcs': 'git', 'commit_id': COMMIT}}), json.dumps({
    'url': 'file:///private/secret', 'vcs_info': {}})])
def test_untrusted_origin_never_echoed(installed, monkeypatch, raw):
    monkeypatch.setattr(m.metadata, 'distribution', lambda name: SimpleNamespace(read_text=lambda _: raw))
    report = m.collect()
    assert report['status'] == 'incomplete'
    assert report['issues']
    assert 'secret' not in json.dumps(report)


def test_metadata_failure_is_reported_without_raw_error(installed, monkeypatch, capsys):
    def broken(name):
        raise RuntimeError('secret /private/path')

    monkeypatch.setattr(m.metadata, 'version', broken)
    assert m.main() == 1
    output = capsys.readouterr().out
    assert '::warning::' in output
    assert 'incomplete' in output
    assert 'secret' not in output
    assert '/private/path' not in output


def test_unexpected_failure_is_visible_and_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(m, 'collect', lambda: (_ for _ in ()).throw(ValueError('secret')))
    assert m.main() == 1
    output = capsys.readouterr().out
    assert '::warning::' in output
    assert 'secret' not in output


def test_success_and_unsafe_metadata_version(installed, monkeypatch, capsys):
    assert m.main() == 0
    assert '::warning::' not in capsys.readouterr().out
    monkeypatch.setattr(m.metadata, 'version', lambda name: '1.0+secret')
    monkeypatch.setattr(m.sys, 'executable', '/private/person/custom-secret')
    report = m.collect()
    assert report['status'] == 'incomplete'
    assert 'secret' not in json.dumps(report)
