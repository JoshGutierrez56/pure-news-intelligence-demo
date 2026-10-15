"""Balanced, brand-blinded analyst evaluation. No generated human ratings."""
import argparse
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
import difflib
import hashlib
import html
import json
import math
from pathlib import Path
import random
import re
from statistics import mean,median

METHODS=('filing_diff','source_search','extractive_summary','pure_news')
RATING_FIELDS=('task_id','reviewer_id','reviewer_kind','prior_familiarity','adjudicator_id',
               'factual_claims','supported_claims','gold_changes','identified_gold_changes',
               'abstained','usefulness_1_5','elapsed_seconds','comments')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assignments(case_ids,reviewer_ids,seed):
    """One presentation per reviewer/case; every case balanced across methods."""
    if len(case_ids)<2 or len(set(case_ids))!=len(case_ids):raise ValueError('Use at least two unique cases')
    if len(reviewer_ids)<8 or len(reviewer_ids)%4 or len(set(reviewer_ids))!=len(reviewer_ids):
        raise ValueError('Use unique reviewer slots in multiples of four, at least eight')
    rng=random.Random(seed);cases=list(case_ids);reviewers=list(reviewer_ids);methods=list(METHODS)
    rng.shuffle(cases);rng.shuffle(reviewers);rng.shuffle(methods)
    output=[]
    for i,reviewer in enumerate(reviewers):
        tasks=[{'reviewer_id':reviewer,'source_case_id':case,'condition':methods[(i+j)%4],
                'case_id':f'CASE-{j+1:03d}'} for j,case in enumerate(cases)]
        rng.shuffle(tasks)
        for order,task in enumerate(tasks,1):
            token=hashlib.sha256(f'{seed}|{reviewer}|{task["source_case_id"]}'.encode()).hexdigest()[:16]
            output.append({**task,'task_id':'TASK-'+token,'order':order})
    return output


def calibration_cases(root):
    """Use only already-public excerpts; these can NEVER become unseen test cases."""
    cases=[]
    for filename in ('rh.json','dvn.json','efx_rejection.json'):
        path=root/'demo/data/research_ideas/v2'/filename
        packet=json.loads(path.read_text(encoding='utf-8'));identity=packet['identity']
        if not packet.get('public_safe'):raise ValueError('Only public-safe calibration inputs are permitted')
        if 'source_evidence' in packet:
            evidence=packet['source_evidence'];prior=evidence['prior_excerpt'];current=evidence['current_excerpt']
            analysis=[]
            for fact in packet['interpretation_layers']['facts']:analysis.append('Evidence-linked statement: '+fact['wording'])
            for hypothesis in packet['research_hypotheses']:
                analysis.extend(['Research hypothesis, not established fact: '+hypothesis['hypothesis'],
                    'What would support it: '+'; '.join(hypothesis.get('confirmation_conditions',[])),
                    'What would weaken it: '+'; '.join(hypothesis.get('falsification_conditions',[]))])
            analysis.append('Alternative explanation: '+packet['economic_mechanism']['counterargument'])
        else:
            review=packet['full_prior_evidence_review']
            prior=review['prior_top_up_evidence']['text']
            current=review['settlement_finality_evidence']['text']+'\n'+review['deposit_evidence']['text']
            analysis=['Defensible update: '+'; '.join(packet['final_result']['defensible_update']),
                'Do not infer: '+'; '.join(packet['final_result']['rejected_claims']),
                'Quantity interpretation: '+'; '.join(x['amount']+' = '+x['correct_role'] for x in review['quantity_roles'])]
        common=f"Issuer: {identity['issuer']}\nCurrent filing date: {identity['filing_date']}\n\nPRIOR SOURCE EXCERPT\n{prior}\n\nCURRENT SOURCE EXCERPT\n{current}"
        sentences=lambda text:re.split(r'(?<=[.!?])\s+',text.strip())
        diff='\n'.join(difflib.unified_diff(sentences(prior),sentences(current),fromfile='prior excerpt',tofile='current excerpt',lineterm=''))
        synopsis='Prior extract: '+' '.join(sentences(prior)[:2])+'\nCurrent extract: '+' '.join(sentences(current)[:2])
        conditions={
            'filing_diff':{'body':'SOURCE COMPARISON\n'+diff+'\n\n'+common,'search':False},
            'source_search':{'body':common,'search':True},
            'extractive_summary':{'body':'QUICK EXTRACTIVE SYNOPSIS\n'+synopsis+'\n\n'+common,'search':False},
            'pure_news':{'body':'RESEARCH NOTES\n'+'\n\n'.join(analysis)+'\n\n'+common,'search':False}}
        cases.append({'case_id':identity['ticker'],'already_public':True,'source_file':str(path.relative_to(root)),
                      'source_sha256':digest(path),'source_url':identity['sec_url'],'conditions':conditions})
    return cases


PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Disclosure review — __REVIEWER__</title><style>
*{box-sizing:border-box}body{margin:0 auto;padding:28px 20px;max-width:1080px;font:16px/1.55 system-ui,sans-serif;color:#18333d;background:#faf9f6}h1{line-height:1.15}button,input,textarea,select{font:inherit}button{padding:10px 16px;border:1px solid #087b78;border-radius:6px;background:#087b78;color:white;cursor:pointer}button:disabled{opacity:.55;cursor:default}nav{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}nav button{background:white;color:#18333d}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.6 system-ui;background:white;padding:24px;border:1px solid #d8dedb}label{display:block;margin-top:16px;font-weight:600}input,textarea,select{width:100%;padding:9px;border:1px solid #74888c;background:white;border-radius:4px}textarea{min-height:120px}.status{padding:12px;background:#edf3f1;border-left:4px solid #087b78}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:20px}:focus-visible{outline:3px solid #b07c44;outline-offset:3px}[hidden]{display:none!important}mark{background:#ffed9f}
</style><main><p>Research workflow evaluation · __PURPOSE__</p><h1>What changed, and what deserves investigation?</h1>
<p>Review only your assigned cases. Do not compare formats with other participants. Use the provided evidence; distinguish supported facts from hypotheses. This is not an investment recommendation exercise.</p>
<p class="status">No answers are sent anywhere. Export a local JSON file when finished. The timer counts active review time while this page is visible; pauses and hidden-tab time are excluded. Save your export before closing.</p>
<nav aria-label="Assigned cases" id="nav"></nav><h2 id="title"></h2><p><a id="source" target="_blank" rel="noopener noreferrer">Open current filing source</a> · Opening another tab pauses the visible-page timer; report external reading time separately.</p>
<div class="row"><button id="start">Start / resume review</button><button id="pause" disabled>Pause</button><span id="clock" aria-live="polite">Not started</span></div>
<section id="material" hidden><label id="searchLabel" hidden>Find text in the supplied excerpts<input id="search" type="search"></label><pre id="body"></pre></section>
<form id="form"><label>Supported findings and source references<textarea id="findings" required></textarea></label><label>Important uncertainty, possible missed changes, and next research step<textarea id="uncertainty" required></textarea></label>
<label>Would you abstain from drawing a substantive change conclusion?<select id="abstained"><option value="">Select</option><option value="true">Yes — insufficient evidence / no substantive change</option><option value="false">No — I can identify a supported change</option></select></label>
<label>Usefulness for this task (1 = not useful, 5 = highly useful)<select id="usefulness"><option value="">Select</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
<label>Were you already familiar with this case?<select id="familiar"><option value="">Select</option><option value="true">Yes</option><option value="false">No</option></select></label>
<label>Additional source-reading time outside this page, in seconds<input id="external" type="number" min="0" value="0" required></label>
<div class="row"><button type="submit">Save this review locally</button><button type="button" id="export">Export saved reviews</button><span id="status" role="status"></span></div></form>
</main><script type="application/json" id="data">__DATA__</script><script>
const data=JSON.parse(document.querySelector('#data').textContent),reviews={},drafts={},timers={},$=id=>document.getElementById(id);let active=-1,running=false,started=0;
function stop(){if(running){timers[active]=(timers[active]||0)+(performance.now()-started)/1000;running=false}$('pause').disabled=true}
function highlight(){const text=data.tasks[active].body,q=$('search').value.trim();$('body').replaceChildren();if(!q){$('body').textContent=text;return}let from=0,at;const lower=text.toLowerCase(),term=q.toLowerCase();while((at=lower.indexOf(term,from))!==-1){$('body').append(document.createTextNode(text.slice(from,at)));const mark=document.createElement('mark');mark.textContent=text.slice(at,at+q.length);$('body').append(mark);from=at+q.length}$('body').append(document.createTextNode(text.slice(from)))}
function show(i){stop();if(active>=0)drafts[active]=Object.fromEntries(['findings','uncertainty','abstained','usefulness','familiar','external'].map(k=>[k,$(k).value]));active=i;const t=data.tasks[i];$('title').textContent=`${t.case_id} · ${i+1} of ${data.tasks.length}`;$('source').href=t.source_url;$('material').hidden=true;$('searchLabel').hidden=!t.search;$('search').value='';$('body').textContent=t.body;$('form').reset();const draft=drafts[i];if(draft)Object.entries(draft).forEach(([k,v])=>$(k).value=v);$('status').textContent=reviews[t.task_id]?'Previously saved; save again after editing.':draft?'Draft restored; save when complete.':'';paintClock()}
function paintClock(){const sec=(timers[active]||0)+(running?(performance.now()-started)/1000:0);$('clock').textContent=`${Math.floor(sec)} active seconds${running?' · running':' · paused'}`}
data.tasks.forEach((t,i)=>{const b=document.createElement('button');b.textContent=t.case_id;b.onclick=()=>show(i);$('nav').append(b)});
$('start').onclick=()=>{if(!running){started=performance.now();running=true}$('pause').disabled=false;$('material').hidden=false};$('pause').onclick=stop;document.addEventListener('visibilitychange',()=>{if(document.hidden)stop()});$('search').oninput=highlight;
$('form').onsubmit=e=>{e.preventDefault();stop();if(!$('abstained').value||!$('usefulness').value||!$('familiar').value){$('status').textContent='Complete each selection.';return}const external=Number($('external').value),seconds=timers[active]||0;if(!Number.isFinite(external)||external<0||seconds<=0){$('status').textContent='Start the review and enter valid external reading time.';return}const t=data.tasks[active];reviews[t.task_id]={task_id:t.task_id,reviewer_id:data.reviewer_id,findings:$('findings').value,uncertainty:$('uncertainty').value,abstained:$('abstained').value==='true',usefulness_1_5:Number($('usefulness').value),prior_familiarity:$('familiar').value==='true',active_seconds:seconds,external_seconds:external,elapsed_seconds:seconds+external,saved_at:new Date().toISOString()};$('status').textContent=`Saved ${Object.keys(reviews).length} of ${data.tasks.length}. Export before closing.`};
$('export').onclick=()=>{const blob=new Blob([JSON.stringify({study_id:data.study_id,purpose:data.purpose,reviewer_id:data.reviewer_id,adjudication_status:'PENDING',reviews:Object.values(reviews)},null,2)],{type:'application/json'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=data.reviewer_id+'-reviews.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)};show(0);setInterval(paintClock,1000);
</script></html>'''


def prepare(cases,reviewers,output,seed=241015,purpose='calibration'):
    if purpose not in ('calibration','prospective'):raise ValueError('Unknown study purpose')
    if purpose=='prospective' and (len(cases)<12 or any(c['already_public'] for c in cases)):
        raise ValueError('Prospective study requires at least 12 unexposed cases; do not relabel calibration inputs')
    if any(set(c['conditions'])!=set(METHODS) for c in cases):raise ValueError('Each case must supply all four frozen conditions')
    if any(not c['source_url'].startswith('https://www.sec.gov/Archives/') for c in cases):
        raise ValueError('Review source link is not an approved public filing')
    if output.exists():raise ValueError('Study directory already exists; frozen assignments cannot be overwritten')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',r) for r in reviewers):raise ValueError('Use pseudonymous filename-safe reviewer IDs')
    tasks=assignments([c['case_id'] for c in cases],reviewers,seed)
    by_case={c['case_id']:c for c in cases};output.mkdir(parents=True)
    study_id=f'pure-news-{purpose}-{seed}'
    source_hashes={c['case_id']:c['source_sha256'] for c in cases}
    key={'study_id':study_id,'purpose':purpose,'seed':seed,'reviewer_slots':reviewers,'tasks':tasks,
         'source_hashes':source_hashes,'human_results_collected':0,
         'created_utc':datetime.now(timezone.utc).isoformat()}
    for reviewer in reviewers:
        visible=[]
        for t in tasks:
            if t['reviewer_id']!=reviewer:continue
            c=by_case[t['source_case_id']]
            visible.append({k:t[k] for k in ('task_id','case_id','order')}|{'source_url':c['source_url']}|c['conditions'][t['condition']])
        payload={'study_id':study_id,'purpose':purpose,'reviewer_id':reviewer,'tasks':visible}
        safe=json.dumps(payload,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        page=PAGE.replace('__REVIEWER__',html.escape(reviewer)).replace('__PURPOSE__',purpose).replace('__DATA__',safe)
        (output/(reviewer+'.html')).write_text(page,encoding='utf-8')
    with (output/'adjudicated_ratings.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=RATING_FIELDS);writer.writeheader()
        writer.writerows({'task_id':t['task_id'],'reviewer_id':t['reviewer_id']} for t in tasks)
    key['packet_sha256']={r:digest(output/(r+'.html')) for r in reviewers}
    (output/'PRIVATE_ASSIGNMENT_KEY.json').write_text(json.dumps(key,indent=2),encoding='utf-8')
    return key


def integer(row,key):
    value=row[key]
    if isinstance(value,bool) or not re.fullmatch(r'\d+',str(value)):raise ValueError('Expected nonnegative integer: '+key)
    return int(value)


def boolean(value):
    if str(value).lower() not in ('true','false'):raise ValueError('Expected explicit true/false')
    return str(value).lower()=='true'


def percentile(values,q):
    x=sorted(values);at=(len(x)-1)*q;lo=int(at);hi=min(lo+1,len(x)-1)
    return x[lo]+(x[hi]-x[lo])*(at-lo)


def score(key,ratings,mode='human',bootstrap_samples=2000,seed=141015):
    if mode not in ('human','synthetic_qa'):raise ValueError('Explicit human or synthetic_qa mode required')
    if not 100<=bootstrap_samples<=10000:raise ValueError('Bounded bootstrap size required')
    tasks={t['task_id']:t for t in key['tasks']}
    if len(ratings)!=len(tasks) or {r['task_id'] for r in ratings}!=set(tasks):
        raise ValueError('All assigned tasks must be accounted for exactly once; no silent complete-case deletion')
    rows=[]
    for r in ratings:
        t=tasks[r['task_id']]
        if r['reviewer_id']!=t['reviewer_id']:raise ValueError('Reviewer does not match assignment')
        if r['reviewer_kind']!=mode:raise ValueError('Synthetic/unknown ratings cannot be presented as human evidence')
        if not r['adjudicator_id'] or r['adjudicator_id']==r['reviewer_id']:raise ValueError('Separate adjudication identity required')
        familiar=boolean(r['prior_familiarity'])
        if key['purpose']=='prospective' and familiar:raise ValueError('Prior familiarity violates prospective eligibility; report and replace under protocol, never silently drop')
        claims,supported,gold,found=[integer(r,k) for k in ('factual_claims','supported_claims','gold_changes','identified_gold_changes')]
        if supported>claims or found>gold:raise ValueError('Supported/found counts exceed their denominators')
        usefulness=integer(r,'usefulness_1_5');elapsed=float(r['elapsed_seconds']);abstained=boolean(r['abstained'])
        if not 1<=usefulness<=5 or not math.isfinite(elapsed) or elapsed<=0:raise ValueError('Invalid usefulness or task time')
        if abstained and (claims or found):raise ValueError('Abstention and substantive reported findings conflict')
        rows.append({**t,'precision':supported/claims if claims else None,'recall':found/gold if gold else None,'missed_changes':gold-found,
            'usefulness':usefulness,'elapsed_seconds':elapsed,'abstention_accuracy':float(abstained==(gold==0)),
            'factual_claims':claims,'supported_claims':supported,'gold_changes':gold,'identified_gold_changes':found})
    by_case=defaultdict(list)
    for r in rows:by_case[r['source_case_id']].append(r)
    for case,items in by_case.items():
        if len({r['gold_changes'] for r in items})!=1:raise ValueError('Adjudicated gold-change count differs within a case')
        if set(r['condition'] for r in items)!=set(METHODS) or set(Counter(r['condition'] for r in items).values())!={len(key['reviewer_slots'])//4}:
            raise ValueError('Case-condition assignment is not balanced')
    metrics=('precision','recall','missed_changes','usefulness','elapsed_seconds','abstention_accuracy')
    summary={};agreement={}
    for method in METHODS:
        items=[r for r in rows if r['condition']==method]
        summary[method]={'tasks':len(items),'adjudicated_counts_across_tasks':{name:sum(r[name] for r in items) for name in ('factual_claims','supported_claims','gold_changes','identified_gold_changes','missed_changes')}}
        for metric in metrics:
            values=[r[metric] for r in items if r[metric] is not None]
            summary[method][metric]={'mean':mean(values) if values else None,'median':median(values) if values else None,'defined_tasks':len(values)}
        differences=[]
        for case in by_case:
            v=[r['usefulness'] for r in by_case[case] if r['condition']==method]
            differences.extend(abs(a-b) for i,a in enumerate(v) for b in v[i+1:])
        agreement[method]={'usefulness_pairwise_mean_absolute_difference':mean(differences),'paired_ratings':len(differences)}
    comparisons={};rng=random.Random(seed)
    for baseline in METHODS[:-1]:
        comparisons[baseline]={}
        for metric in metrics:
            paired=[]
            for items in by_case.values():
                treatment=[r[metric] for r in items if r['condition']=='pure_news' and r[metric] is not None]
                control=[r[metric] for r in items if r['condition']==baseline and r[metric] is not None]
                if treatment and control:paired.append(mean(treatment)-mean(control))
            if len(paired)<2:
                comparisons[baseline][metric]={'status':'undefined: fewer than two paired cases','paired_cases':len(paired)};continue
            boot=[mean(rng.choices(paired,k=len(paired))) for _ in range(bootstrap_samples)]
            comparisons[baseline][metric]={'mean_difference':mean(paired),'paired_cases':len(paired),
                'descriptive_case_bootstrap_95_interval':[percentile(boot,.025),percentile(boot,.975)]}
    return {'study_id':key['study_id'],'purpose':key['purpose'],'rating_mode':mode,'completed_tasks':len(rows),
        'human_ratings':len(rows) if mode=='human' else 0,'effectiveness_claim_allowed':False,
        'status':'SYNTHETIC SOFTWARE QA — NOT HUMAN EVIDENCE' if mode=='synthetic_qa' else ('CALIBRATION ONLY — PREVIOUSLY PUBLIC CASES' if key['purpose']=='calibration' else 'HUMAN STUDY ANALYSIS — REQUIRES PROTOCOL/ADJUDICATION REVIEW'),
        'by_condition':summary,'reviewer_disagreement':agreement,'pure_news_minus_baseline':comparisons,
        'bootstrap':{'samples':bootstrap_samples,'seed':seed,'unit':'paired case means; reviewers treated as fixed',
            'limitations':'Descriptive intervals, not reviewer-population inference or multiplicity-adjusted significance. Zero claim/gold denominators remain undefined, never perfect scores.'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('prepare-calibration');build.add_argument('--output',type=Path,required=True)
    analyze=sub.add_parser('score');analyze.add_argument('--key',type=Path,required=True);analyze.add_argument('--ratings',type=Path,required=True)
    analyze.add_argument('--mode',choices=('human','synthetic_qa'),required=True);analyze.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if args.command=='prepare-calibration':
        output=args.output.resolve()
        if output==root or output.is_relative_to(root):raise ValueError('Keep reviewer packets and assignment key outside the public repository')
        key=prepare(calibration_cases(root),[f'REVIEWER-{i:02d}' for i in range(1,9)],output)
        print(json.dumps({'study_id':key['study_id'],'purpose':key['purpose'],'reviewer_slots':8,'tasks':len(key['tasks']),'human_results':0}))
    else:
        if args.output.exists():raise ValueError('Never overwrite a prior analysis')
        key=json.loads(args.key.read_text(encoding='utf-8'))
        with args.ratings.open(encoding='utf-8',newline='') as f:ratings=list(csv.DictReader(f))
        report=score(key,ratings,args.mode)
        report['input_hashes']={'key':digest(args.key),'ratings':digest(args.ratings)}
        args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({k:report[k] for k in ('status','completed_tasks','human_ratings')}))


if __name__=='__main__':main()
