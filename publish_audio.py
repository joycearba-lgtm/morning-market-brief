"""Publish only audio files on the latest main tree, retrying concurrent writes.

No rebase of generated binaries; never replace a newer briefing's recording.
"""
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from audio_content import content_hash


def git(*args, input=None, env=None, check=True):
    return subprocess.run(['git', *args], input=input, text=True,
                          capture_output=True, env=env, check=check)


def read_at(ref, path):
    result=git('show', ref+':'+path, check=False)
    try:
        return json.loads(result.stdout) if result.returncode==0 else {}
    except ValueError:
        return {}


def matches(manifest, brief):
    return (manifest.get('status')=='ok'
            and manifest.get('date')==brief.get('date')
            and manifest.get('content_hash')==content_hash(brief)
            and manifest.get('coverage')=='full_editorial'
            and manifest.get('file')=='audio/morning-brief.mp3')


def main():
    today=datetime.now(ZoneInfo('Asia/Jerusalem')).date().isoformat()
    brief=json.loads(Path('macro_brief.json').read_text(encoding='utf-8'))
    attempt_hash=content_hash(brief)
    manifest_path=Path('daily_audio.json')
    audio_path=Path('audio/morning-brief.mp3')
    try:
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError,ValueError):
        manifest={}
    complete=(os.environ.get('SYNTH_OUTCOME')=='success'
              and matches(manifest,brief) and brief.get('date')==today
              and audio_path.is_file() and audio_path.stat().st_size>1000)
    if not complete:
        reason=('dependency_installation_failed' if os.environ.get('INSTALL_OUTCOME')!='success'
                else 'audio_generation_failed')
        manifest={'date':today,'status':'unavailable','reason':reason,
                  'checked_at':datetime.now(ZoneInfo('Asia/Jerusalem')).isoformat()}
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    paths=['daily_audio.json']+(['audio/morning-brief.mp3'] if complete else [])
    blobs={path:git('hash-object','-w',path).stdout.strip() for path in paths}
    git('config','user.name','github-actions[bot]')
    git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    for attempt in range(4):
        git('fetch','--no-tags','origin','main')
        head=git('rev-parse','origin/main').stdout.strip()
        current=read_at(head,'macro_brief.json')
        if current.get('date')!=today or content_hash(current)!=attempt_hash:
            print('Brief changed during synthesis; leaving current audio untouched')
            return
        existing=read_at(head,'daily_audio.json')
        if matches(existing,current):
            print('Matching recording already published; preserving it')
            return
        with tempfile.TemporaryDirectory() as directory:
            env=dict(os.environ,GIT_INDEX_FILE=str(Path(directory)/'index'))
            git('read-tree',head,env=env)
            for path,blob in blobs.items():
                git('update-index','--add','--cacheinfo','100644,'+blob+','+path,env=env)
            tree=git('write-tree',env=env).stdout.strip()
            if tree==git('rev-parse',head+'^{tree}').stdout.strip():
                break
            commit=git('commit-tree',tree,'-p',head,input='Publish matching Hebrew audio\n').stdout.strip()
            result=git('push','origin',commit+':refs/heads/main',check=False)
            if result.returncode==0:
                print('Published recording' if complete else 'Published diagnostic status')
                break
            print('Branch advanced; retrying audio-only publication',attempt+1)
    else:
        raise RuntimeError('Audio publication could not obtain current branch head')
    if not complete:
        raise SystemExit('Audio synthesis failed; diagnostic status published')


if __name__=='__main__':
    main()
