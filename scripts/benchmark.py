#!/usr/bin/env python3
"""Measure a reproducible five-participant continuity scenario in a disposable home."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    calls=[]
    with tempfile.TemporaryDirectory(prefix='harness-benchmark-') as temporary:
        root=Path(temporary).resolve();project=root/'project';project.mkdir()
        env=dict(os.environ,HARNESS_HOME=str(root/'state'),PYTHONPATH='')
        script=ROOT/'skills/harness-task/scripts/harness.py'
        def call(op,data=None,code=0):
            data=data or {}
            started=time.perf_counter()
            raw=json.dumps(data,ensure_ascii=False)
            result=subprocess.run([sys.executable,str(script),op,'--project',str(project),'--data',raw],env=env,cwd=root,capture_output=True,text=True)
            elapsed=time.perf_counter()-started
            if result.returncode != code:
                raise RuntimeError(result.stdout+result.stderr)
            value=json.loads(result.stdout)
            calls.append({'operation':op,'milliseconds':round(elapsed*1000,3),'input_json_chars':len(raw),'output_json_chars':len(result.stdout),'exit_code':code})
            return value
        call('init')
        participants=[]
        for index in range(5):
            name=f'chapter-{index+1}.md'
            (project/name).write_text(f'# Chapter {index+1}\nChecked draft.\n')
            participants.append(call('task.start',{'objective':f'Check chapter {index+1}','resources':[name],'request_id':f'participant-{index+1}'}))
        for index in range(4):
            call('task.checkpoint',{'session_id':participants[index]['session']['id'],'summary':f'Chapter {index+1} draft checked.','evidence':[f'chapter-{index+1}.md'],'next_action':'Verify the remaining source.' if index==3 else 'Editorial acceptance pending.','status':'blocked' if index==3 else 'delivered','request_id':f'checkpoint-{index+1}'})
        for index in range(10):
            call('remember',{'title':f'Archive source {index}','summary':f'Archive {index} provenance.','content':f'Archive {index} details are in the cited chapter.','kind':'hypothesis' if index%2 else 'fact','sources':['chapter-1.md'],'scope':'project','aliases':[f'fonte{index}'],'request_id':f'memory-{index}'})
        overview=call('consolidate')
        assert len(overview['contributions'])==5
        assert len(overview['claims'])==2
        conflict=call('task.start',{'objective':'Consolidate all chapters','resources':['.'],'request_id':'consolidation'},code=2)
        assert not conflict['success']
        recall=call('recall',{'query':'fonte3','limit':3,'budget_chars':3000})
        assert len(recall['entries'])==1
        call('hydrate',{'id':recall['entries'][0]['id'],'budget_chars':5000})
        call('changes',{'since':0,'limit':3,'budget_chars':3000})
        before=[p.read_bytes() for p in (root/'state/projects').glob('*/state.json')]
        call('maintain');call('maintain')
        assert before==[p.read_bytes() for p in (root/'state/projects').glob('*/state.json')]
        state_bytes=sum(p.stat().st_size for p in (root/'state/projects').glob('*/state.json'))
    descriptions={}
    for skill in sorted((ROOT/'skills').glob('*/SKILL.md')):
        text=skill.read_text();front=text.split('---',2)[1]
        descriptions[skill.parent.name]={'metadata_chars':len(front.strip()),'body_chars':len(text.split('---',2)[2].strip())}
    report={'scenario':'five participants, three delivered, one blocked, one active, ten knowledge records','python':sys.version.split()[0],'platform':platform.system(),'measure':'Unicode characters in JSON, not model tokens; subprocess wall-clock latency','calls':calls,'call_count':len(calls),'total_input_json_chars':sum(c['input_json_chars'] for c in calls),'total_output_json_chars':sum(c['output_json_chars'] for c in calls),'median_call_ms':round(statistics.median(c['milliseconds'] for c in calls),3),'consolidation_output_chars':next(c['output_json_chars'] for c in calls if c['operation']=='consolidate'),'state_bytes':state_bytes,'skill_chars':descriptions,'limits':'One local fixture; not a model-quality benchmark, token measurement or throughput guarantee.'}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
