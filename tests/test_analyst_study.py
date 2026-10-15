from collections import Counter,defaultdict
import copy
import json
from pathlib import Path

import pytest

from research_ops.study import METHODS,assignments,calibration_cases,prepare,score


def key_and_ratings():
    slots=[f'R{i}' for i in range(8)]
    tasks=assignments(['C1','C2','C3','C4'],slots,19)
    key={'study_id':'synthetic-fixture','purpose':'calibration','reviewer_slots':slots,'tasks':tasks}
    ratings=[]
    for task in tasks:
        improved=task['condition']=='pure_news'
        ratings.append({'task_id':task['task_id'],'reviewer_id':task['reviewer_id'],
            'reviewer_kind':'synthetic_qa','prior_familiarity':'false','adjudicator_id':'QA-GOLD',
            'factual_claims':'2','supported_claims':'2' if improved else '1',
            'gold_changes':'2','identified_gold_changes':'2' if improved else '1',
            'abstained':'false','usefulness_1_5':'5' if improved else '3',
            'elapsed_seconds':'60' if improved else '120','comments':'Invented software fixture, never human evidence'})
    return key,ratings


def test_counterbalance_has_two_ratings_per_case_method_and_no_case_carryover():
    tasks=assignments([f'C{i}' for i in range(12)],[f'R{i}' for i in range(8)],241015)
    assert len(tasks)==96 and len({t['task_id'] for t in tasks})==96
    pairs=Counter((t['source_case_id'],t['condition']) for t in tasks)
    assert len(pairs)==48 and set(pairs.values())=={2}
    for reviewer in {t['reviewer_id'] for t in tasks}:
        own=[t for t in tasks if t['reviewer_id']==reviewer]
        assert len({t['source_case_id'] for t in own})==12
        assert set(Counter(t['condition'] for t in own).values())=={3}
    assert tasks==assignments([f'C{i}' for i in range(12)],[f'R{i}' for i in range(8)],241015)


def test_hand_computed_metrics_and_constant_paired_differences():
    key,ratings=key_and_ratings();report=score(key,ratings,'synthetic_qa',bootstrap_samples=100)
    assert report['human_ratings']==0 and not report['effectiveness_claim_allowed']
    assert report['by_condition']['pure_news']['precision']['mean']==1
    assert report['by_condition']['filing_diff']['precision']['mean']==.5
    assert report['by_condition']['pure_news']['elapsed_seconds']['median']==60
    comparison=report['pure_news_minus_baseline']['filing_diff']
    for metric,difference in [('precision',.5),('recall',.5),('usefulness',2.),('elapsed_seconds',-60.)]:
        assert comparison[metric]['mean_difference']==difference
        assert comparison[metric]['descriptive_case_bootstrap_95_interval']==[difference,difference]


def test_zero_denominators_do_not_become_perfect_accuracy():
    key,ratings=key_and_ratings()
    for row in ratings:
        row.update(factual_claims='0',supported_claims='0',gold_changes='0',identified_gold_changes='0',abstained='true')
    report=score(key,ratings,'synthetic_qa',bootstrap_samples=100)
    for method in METHODS:
        assert report['by_condition'][method]['precision']['mean'] is None
        assert report['by_condition'][method]['recall']['mean'] is None
        assert report['by_condition'][method]['abstention_accuracy']['mean']==1
    assert report['pure_news_minus_baseline']['filing_diff']['precision']['paired_cases']==0


@pytest.mark.parametrize('mutation',['missing','duplicate','wrong_reviewer','fake_human','self_adjudication','denominator','nonfinite_time','missing_gold','inconsistent_gold'])
def test_invalid_or_incomplete_ratings_cannot_produce_a_usefulness_claim(mutation):
    key,ratings=key_and_ratings()
    if mutation=='missing':ratings.pop()
    elif mutation=='duplicate':ratings[-1]=ratings[0].copy()
    elif mutation=='wrong_reviewer':ratings[0]['reviewer_id']='OTHER'
    elif mutation=='fake_human':ratings[0]['reviewer_kind']='human'
    elif mutation=='self_adjudication':ratings[0]['adjudicator_id']=ratings[0]['reviewer_id']
    elif mutation=='denominator':ratings[0]['supported_claims']='3'
    elif mutation=='nonfinite_time':ratings[0]['elapsed_seconds']='nan'
    elif mutation=='missing_gold':ratings[0]['gold_changes']=''
    elif mutation=='inconsistent_gold':ratings[0]['gold_changes']='3'
    with pytest.raises(ValueError):score(key,ratings,'synthetic_qa',bootstrap_samples=100)


def test_human_mode_never_silently_accepts_software_fixture():
    key,ratings=key_and_ratings()
    with pytest.raises(ValueError,match='human evidence'):score(key,ratings,'human')
    for row in ratings:row['reviewer_kind']='human'
    report=score(key,ratings,'human',bootstrap_samples=100)
    assert report['human_ratings']==32 and report['status'].startswith('CALIBRATION ONLY')
    assert not report['effectiveness_claim_allowed']  # a flag is not independent verification of the people


def test_prior_familiarity_invalidates_prospective_analysis_instead_of_dropping_rows():
    key,ratings=key_and_ratings();key['purpose']='prospective';ratings[0]['prior_familiarity']='true'
    with pytest.raises(ValueError,match='Prior familiarity'):score(key,ratings,'synthetic_qa')


def test_actual_calibration_source_hashes_and_brand_blinded_packets(tmp_path):
    root=Path(__file__).resolve().parents[1];cases=calibration_cases(root);folder=tmp_path/'study'
    before={c['source_file']:(root/c['source_file']).read_bytes() for c in cases}
    key=prepare(cases,[f'R{i}' for i in range(8)],folder)
    assert len(key['tasks'])==24 and key['human_results_collected']==0
    for reviewer in key['reviewer_slots']:
        page=(folder/(reviewer+'.html')).read_text(encoding='utf-8')
        payload=page.split('<script type="application/json" id="data">')[1].split('</script>')[0]
        data=json.loads(payload)
        assert len(data['tasks'])==3
        assert all('condition' not in task and 'source_case_id' not in task for task in data['tasks'])
        assert 'PRIVATE_ASSIGNMENT_KEY' not in page
    assert all((root/p).read_bytes()==b for p,b in before.items())
    with pytest.raises(ValueError,match='already exists'):prepare(cases,key['reviewer_slots'],folder)
    with pytest.raises(ValueError,match='unexposed'):prepare(cases,key['reviewer_slots'],tmp_path/'prospective',purpose='prospective')


def test_unsafe_reviewer_names_and_unbalanced_design_are_rejected(tmp_path):
    cases=calibration_cases(Path(__file__).resolve().parents[1])
    with pytest.raises(ValueError,match='filename-safe'):prepare(cases,['../outside']+[f'R{i}' for i in range(7)],tmp_path/'bad')
    with pytest.raises(ValueError,match='multiples of four'):assignments(['A','B'],['R1','R2'],1)
