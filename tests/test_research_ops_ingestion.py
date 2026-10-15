"""Failure/recovery contracts for public acquisition; no external request in CI."""
from datetime import datetime,timedelta,timezone
import hashlib
import sqlite3

import pytest

from research_ops.ingestion import AcquisitionError,CacheIntegrityError,PublicDocumentCache,Response,canonical_url,select_annual_pair

URL='https://data.sec.gov/submissions/CIK0000320193.json'


class Clock:
    def __init__(self):self.at=datetime(2026,10,14,tzinfo=timezone.utc);self.elapsed=0.;self.waits=[]
    def now(self):return self.at
    def monotonic(self):return self.elapsed
    def sleep(self,seconds):self.waits.append(seconds);self.elapsed+=seconds;self.at+=timedelta(seconds=seconds)


def cache(tmp_path,responses):
    clock=Clock();requests=[];queue=iter(responses)
    def transport(url,headers):
        requests.append((url,dict(headers)))
        result=next(queue)
        if isinstance(result,Exception):raise result
        return result
    value=PublicDocumentCache(tmp_path,'Research project https://github.com/example',transport=transport,
                               now=clock.now,sleep=clock.sleep,monotonic=clock.monotonic)
    return value,clock,requests


def good(body=b'{"filings":{}}'):
    return Response(200,{'content-type':'application/json','etag':'version-one'},body)


def test_conditional_revalidation_preserves_blob_and_original_retrieval(tmp_path):
    c,clock,requests=cache(tmp_path,[good(),Response(304,{},b'')])
    body,first=c.fetch(URL);clock.sleep(60);again,second=c.fetch(URL)
    assert body==again
    assert second['retrieved_at']==first['retrieved_at']
    assert second['checked_at']!=first['checked_at']
    assert requests[1][1]['If-None-Match']=='version-one'
    assert len(list((tmp_path/'blobs').iterdir()))==1
    assert [a['outcome'] for a in c.attempts()]==['acquired','not_modified']


def test_access_denial_does_not_relabel_cached_evidence_fresh(tmp_path):
    c,clock,requests=cache(tmp_path,[good(),Response(403,{},b'Forbidden')])
    _,first=c.fetch(URL);clock.sleep(5)
    with pytest.raises(AcquisitionError,match='403'):c.fetch(URL)
    _,saved=c.read_cached(URL,10)
    assert saved['checked_at']==first['checked_at']
    assert saved['last_attempt_status']==403 and saved['age_seconds']==5
    assert len(requests)==2
    clock.sleep(10)
    with pytest.raises(AcquisitionError,match='stale'):c.read_cached(URL,10)


def test_corruption_stops_before_network_and_is_not_overwritten(tmp_path):
    c,_,requests=cache(tmp_path,[good()]);_,saved=c.fetch(URL)
    blob=tmp_path/'blobs'/saved['sha256'];blob.write_bytes(b'changed')
    with pytest.raises(CacheIntegrityError):c.fetch(URL)
    assert len(requests)==1 and blob.read_bytes()==b'changed'


def test_rate_limit_retry_is_bounded_and_respects_server_wait(tmp_path):
    c,clock,requests=cache(tmp_path,[Response(429,{'retry-after':'2'},b''),good()])
    c.fetch(URL)
    assert len(requests)==2 and clock.waits==[2.]
    assert c.attempts()[0]['outcome']=='retryable_failure'


@pytest.mark.parametrize('retry',['60','nan','inf','not-a-date'])
def test_retry_after_never_causes_early_or_unbounded_retry(tmp_path,retry):
    c,clock,requests=cache(tmp_path,[Response(429,{'retry-after':retry},b'')])
    with pytest.raises(AcquisitionError):c.fetch(URL)
    assert len(requests)==1 and not clock.waits


def test_transport_failure_closes_handles_and_can_recover_after_reopen(tmp_path):
    c,_,requests=cache(tmp_path,[TimeoutError(),TimeoutError(),TimeoutError()])
    with pytest.raises(AcquisitionError,match='three'):c.fetch(URL)
    assert len(requests)==3
    recovered,_,_=cache(tmp_path,[good()]);body,_=recovered.fetch(URL)
    assert body==b'{"filings":{}}'
    assert len(recovered.attempts())==4
    renamed=tmp_path/'moved.sqlite';recovered.dbpath.rename(renamed)
    assert renamed.exists()  # Real Windows open-handle regression check.


@pytest.mark.parametrize('response',[
    Response(304,{},b''),Response(200,{'content-type':'application/json'},b'broken'),
    Response(200,{'content-type':'application/pdf'},b'%PDF'),
    Response(200,{'content-type':'text/html'},b'<title>Access Denied</title>'),
    Response(200,{'content-type':'text/plain'},b'')])
def test_invalid_payload_does_not_create_a_successful_source(tmp_path,response):
    c,_,_=cache(tmp_path,[response])
    with pytest.raises(AcquisitionError):c.fetch(URL)
    with pytest.raises(AcquisitionError,match='No successfully'):c.read_cached(URL,60)
    assert not list((tmp_path/'blobs').iterdir())


@pytest.mark.parametrize('url',['http://data.sec.gov/x','https://evil.example/x','https://data.sec.gov@evil.example/x','https://data.sec.gov:bad/x','https://data.sec.gov/x#fragment'])
def test_source_origin_contract(url):
    with pytest.raises(AcquisitionError):canonical_url(url,{'data.sec.gov'})


def submission():
    return {'cik':'320193','filings':{'recent':{
        'form':['10-K','10-K','10-K/A','10-K'],
        'filingDate':['2026-10-20','2025-10-31','2025-11-01','2024-11-01'],
        'accessionNumber':['0000320193-26-000001','0000320193-25-000001','0000320193-25-000002','0000320193-24-000001'],
        'primaryDocument':['future.htm','current.htm','amended.htm','prior.htm'],
        'reportDate':['2026-09-30','2025-09-30','2025-09-30','2024-09-30']}}}


def test_pair_selection_excludes_future_and_amended_filings():
    pair=select_annual_pair(submission(),'2026-10-14')
    assert pair['current']['filing_date']=='2025-10-31'
    assert pair['prior']['filing_date']=='2024-11-01'
    assert pair['current']['url']=='https://www.sec.gov/Archives/edgar/data/320193/000032019325000001/current.htm'


def test_pair_selection_rejects_misaligned_and_unsafe_metadata():
    data=submission();data['filings']['recent']['form'].pop()
    with pytest.raises(ValueError,match='Misaligned'):select_annual_pair(data,'2026-10-14')
    data=submission();data['filings']['recent']['primaryDocument'][1]='../outside.htm'
    with pytest.raises(ValueError,match='document'):select_annual_pair(data,'2026-10-14')
    data=submission();data['filings']['recent']['reportDate'][1]='2026-01-01'
    with pytest.raises(ValueError,match='Report date'):select_annual_pair(data,'2026-10-14')
