"""Publish quotes against the latest tree without overwriting other snapshots."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


def git(*args, input=None, env=None, check=True):
    return subprocess.run(['git', *args], input=input, text=True,
                          capture_output=True, check=check, env=env)


def merge_quotes(current, incoming):
    # A morning run may have completed since collection. Keep its newer quotes
    # and historical series while adding only this run's current quote fields.
    merged = dict(current)
    for group in ('indices', 'commodities'):
        merged[group] = dict(current.get(group, {}))
        for label, item in incoming.get(group, {}).items():
            old = merged[group].get(label, {})
            if (item.get('market_time') or 0) >= (old.get('market_time') or 0):
                fields = {k: v for k, v in item.items() if not k.startswith('history')}
                merged[group][label] = {**old, **fields}
    item = incoming.get('treasury_10y', {})
    if (item.get('market_time') or 0) >= (current.get('treasury_10y', {}).get('market_time') or 0):
        merged['treasury_10y'] = item
    for key in ('intraday_checked_at', 'intraday_refresh_status'):
        merged[key] = incoming[key]
    merged['updated_at'] = max(current.get('updated_at', ''), incoming.get('updated_at', ''))
    return merged


def main():
    incoming = json.loads(Path('market_data.json').read_text(encoding='utf-8'))
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    for attempt in range(4):
        git('fetch', '--no-tags', 'origin', 'main')
        head = git('rev-parse', 'origin/main').stdout.strip()
        current = json.loads(git('show', head + ':market_data.json').stdout)
        data = merge_quotes(current, incoming)
        html = git('show', head + ':index.html').stdout
        payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
        snapshot = '<!-- MARKET_SNAPSHOT_START -->\n<script id="market-snapshot" type="application/json">' + payload + '</script>\n<!-- MARKET_SNAPSHOT_END -->'
        html, count = re.subn(r'<!-- MARKET_SNAPSHOT_START -->.*?<!-- MARKET_SNAPSHOT_END -->',
                              lambda _: snapshot, html, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Missing market snapshot markers')
        files = {'market_data.json': json.dumps(data, ensure_ascii=False, indent=2) + '\n',
                 'index.html': html}
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(folder) / 'index'))
            git('read-tree', head, env=env)
            for path, content in files.items():
                blob = git('hash-object', '-w', '--stdin', input=content).stdout.strip()
                git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + path, env=env)
            tree = git('write-tree', env=env).stdout.strip()
            commit = git('commit-tree', tree, '-p', head, input='Refresh intraday market quotes\n').stdout.strip()
            if git('push', 'origin', commit + ':refs/heads/main', check=False).returncode == 0:
                print('Published quotes and matching embedded snapshot')
                return
    raise RuntimeError('Concurrent publication prevented quote update')


if __name__ == '__main__':
    main()
