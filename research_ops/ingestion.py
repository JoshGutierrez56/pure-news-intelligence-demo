"""Content-addressed public-document acquisition with explicit freshness/failure.

Uses Python's maintained HTTP/SQLite libraries; no inference or packet generation.
"""
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import time
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit,quote
from urllib.request import Request,build_opener,HTTPRedirectHandler


class AcquisitionError(RuntimeError):
    pass


class CacheIntegrityError(AcquisitionError):
    pass


@dataclass
class Response:
    status:int
    headers:dict
    body:bytes


def canonical_url(url,allowed_hosts):
    try:
        parts=urlsplit(url)
        valid=parts.scheme=='https' and parts.hostname in allowed_hosts and not parts.username and not parts.password and not parts.fragment and parts.port in (None,443)
    except ValueError:
        valid=False
    if not valid:
        raise AcquisitionError('Only approved HTTPS public-source hosts are allowed')
    return parts._replace(netloc=parts.hostname).geturl()


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self,allowed_hosts):self.allowed_hosts=allowed_hosts
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        canonical_url(newurl,self.allowed_hosts)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class PublicDocumentCache:
    def __init__(self,root,user_agent,allowed_hosts=('www.sec.gov','data.sec.gov'),transport=None,
                 now=None,sleep=time.sleep,monotonic=time.monotonic,max_bytes=25_000_000,max_retry_wait=10.):
        if not isinstance(user_agent,str) or len(user_agent.strip())<12 or '\n' in user_agent or '\r' in user_agent:
            raise ValueError('Supply a descriptive research User-Agent with a contact route')
        if not isinstance(max_bytes,int) or isinstance(max_bytes,bool) or max_bytes<1 or not math.isfinite(max_retry_wait) or max_retry_wait<0:
            raise ValueError('Invalid acquisition bounds')
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);(self.root/'blobs').mkdir(exist_ok=True)
        self.dbpath=self.root/'index.sqlite';self.user_agent=user_agent;self.allowed_hosts=set(allowed_hosts)
        self.now=now or (lambda:datetime.now(timezone.utc));self.sleep=sleep;self.monotonic=monotonic
        self.max_bytes=max_bytes;self.max_retry_wait=max_retry_wait;self.last_request=None
        self.transport=transport or self._http
        with closing(sqlite3.connect(self.dbpath)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS sources (url TEXT PRIMARY KEY, sha256 TEXT NOT NULL, etag TEXT, last_modified TEXT, retrieved_at TEXT NOT NULL, checked_at TEXT NOT NULL, content_type TEXT NOT NULL, byte_count INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, url TEXT NOT NULL, at TEXT NOT NULL, outcome TEXT NOT NULL, status INTEGER, detail TEXT NOT NULL)')
            db.commit()

    def _stamp(self):
        now=self.now()
        if now.tzinfo is None:raise ValueError('Acquisition clock must be timezone aware')
        return now.astimezone(timezone.utc).isoformat()

    def _http(self,url,headers):
        request=Request(url,headers=headers)
        opener=build_opener(SafeRedirect(self.allowed_hosts))
        try:
            with opener.open(request,timeout=25) as response:
                body=response.read(self.max_bytes+1)
                return Response(response.status,{k.lower():v for k,v in response.headers.items()},body)
        except HTTPError as exc:
            with exc:
                return Response(exc.code,{k.lower():v for k,v in exc.headers.items()},exc.read(min(self.max_bytes+1,4096)))

    def _attempt(self,url,outcome,status,detail):
        with closing(sqlite3.connect(self.dbpath)) as db:
            db.execute('INSERT INTO attempts(url,at,outcome,status,detail) VALUES(?,?,?,?,?)',(url,self._stamp(),outcome,status,detail))
            db.commit()

    def _source(self,url):
        with closing(sqlite3.connect(self.dbpath)) as db:
            db.row_factory=sqlite3.Row
            row=db.execute('SELECT * FROM sources WHERE url=?',(url,)).fetchone()
        return dict(row) if row else None

    def _body(self,source):
        if not isinstance(source['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',source['sha256']):
            raise CacheIntegrityError('Invalid source checksum identity')
        path=self.root/'blobs'/source['sha256']
        if not path.exists():raise CacheIntegrityError('Missing cached source blob')
        body=path.read_bytes()
        if len(body)!=source['byte_count'] or hashlib.sha256(body).hexdigest()!=source['sha256']:
            raise CacheIntegrityError('Cached source checksum mismatch; preserved for investigation')
        return body

    def read_cached(self,url,max_age_seconds):
        if not math.isfinite(max_age_seconds) or max_age_seconds<0:raise ValueError('Cache age must be finite and nonnegative')
        url=canonical_url(url,self.allowed_hosts);source=self._source(url)
        if source is None:raise AcquisitionError('No successfully acquired source is cached')
        body=self._body(source)
        age=(self.now()-datetime.fromisoformat(source['checked_at'])).total_seconds()
        if age<0 or age>max_age_seconds:raise AcquisitionError('Cached source is stale or clock is inconsistent')
        with closing(sqlite3.connect(self.dbpath)) as db:
            last=db.execute('SELECT outcome,status FROM attempts WHERE url=? ORDER BY id DESC LIMIT 1',(url,)).fetchone()
        return body,{**source,'age_seconds':age,'freshness':'Within caller-specified age of the last successful check; not a new live validation',
                     'last_attempt_outcome':last[0] if last else None,'last_attempt_status':last[1] if last else None,
                     'scope':'Current-vintage observed availability, not historical point-in-time certification'}

    def _backoff(self,headers,attempt):
        raw=headers.get('retry-after')
        if raw:
            try:delay=float(raw)
            except ValueError:
                try:
                    requested=parsedate_to_datetime(raw)
                    if requested.tzinfo is None:raise ValueError('Ambiguous retry date')
                    delay=(requested-self.now()).total_seconds()
                except (TypeError,ValueError,OverflowError) as exc:
                    raise AcquisitionError('Invalid Retry-After; no early retry performed') from exc
            if not math.isfinite(delay):raise AcquisitionError('Invalid Retry-After; no early retry performed')
            delay=max(0.,delay)
        else:delay=float(2**attempt)
        if delay>self.max_retry_wait:raise AcquisitionError(f'Retry deferred: server requires {delay:.0f} seconds; no early retry performed')
        return delay

    def fetch(self,url):
        url=canonical_url(url,self.allowed_hosts);source=self._source(url)
        if source:self._body(source)
        headers={'User-Agent':self.user_agent,'Accept-Encoding':'identity','Accept':'application/json,text/html,text/plain'}
        if source and source['etag']:headers['If-None-Match']=source['etag']
        if source and source['last_modified']:headers['If-Modified-Since']=source['last_modified']
        for attempt in range(3):
            if self.last_request is not None:
                remaining=.5-(self.monotonic()-self.last_request)
                if remaining>0:self.sleep(remaining)
            self.last_request=self.monotonic()
            try:response=self.transport(url,headers)
            except (URLError,TimeoutError,OSError) as exc:
                self._attempt(url,'transport_error',None,type(exc).__name__)
                if attempt==2:raise AcquisitionError('Transport failed after three bounded attempts') from exc
                self.sleep(2**attempt);continue
            status=response.status;response.headers={k.lower():v for k,v in response.headers.items()}
            if status in (429,500,502,503,504):
                self._attempt(url,'retryable_failure',status,'No source freshness updated')
                if attempt==2:raise AcquisitionError(f'HTTP {status}: retry limit reached')
                self.sleep(self._backoff(response.headers,attempt));continue
            if status==304:
                if source is None:
                    self._attempt(url,'invalid_not_modified',304,'No prior cached representation')
                    raise AcquisitionError('304 without a cached representation')
                body=self._body(source);stamp=self._stamp()
                with closing(sqlite3.connect(self.dbpath)) as db:
                    db.execute('UPDATE sources SET checked_at=? WHERE url=?',(stamp,url));db.commit()
                self._attempt(url,'not_modified',304,source['sha256'])
                return body,{**self._source(url),'http_status':304,'outcome':'not_modified'}
            if status!=200:
                self._attempt(url,'blocked_or_missing',status,'No retry or synthetic/provider fallback')
                raise AcquisitionError(f'HTTP {status}: acquisition stopped; cached data are not relabeled fresh')
            body=response.body;ctype=response.headers.get('content-type','').split(';')[0].strip().lower()
            if not body or len(body)>self.max_bytes or ctype not in ('application/json','text/html','text/plain','application/xhtml+xml'):
                self._attempt(url,'invalid_content',200,'Empty/oversized body or unsupported media type')
                raise AcquisitionError('Source content failed size/media checks')
            prefix=body[:4096].lower()
            if any(marker in prefix for marker in (b'your request originates from an undeclared automated tool',b'request rate threshold exceeded',b'<title>access denied')):
                self._attempt(url,'access_error_body',200,'Access-error page is not a source document')
                raise AcquisitionError('Access-error HTML returned with HTTP 200')
            if ctype=='application/json':
                try:json.loads(body)
                except (ValueError,UnicodeDecodeError) as exc:
                    self._attempt(url,'invalid_json',200,'Body is not valid JSON')
                    raise AcquisitionError('Invalid source JSON') from exc
            digest=hashlib.sha256(body).hexdigest();blob=self.root/'blobs'/digest
            if blob.exists():
                if blob.read_bytes()!=body:raise CacheIntegrityError('Content-addressed blob collision/corruption')
            else:
                temporary=blob.with_suffix('.tmp');temporary.write_bytes(body);temporary.replace(blob)
            stamp=self._stamp()
            with closing(sqlite3.connect(self.dbpath)) as db:
                db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?,?,?)',
                    (url,digest,response.headers.get('etag'),response.headers.get('last-modified'),stamp,stamp,ctype,len(body)))
                db.commit()
            self._attempt(url,'acquired',200,digest)
            return body,{**self._source(url),'http_status':200,'outcome':'acquired'}
        raise AssertionError('Unreachable retry state')

    def attempts(self):
        with closing(sqlite3.connect(self.dbpath)) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute('SELECT * FROM attempts ORDER BY id')]


def select_annual_pair(submissions,as_of):
    """Validate recent SEC arrays; select distinct 10-Ks known by filing date.

    Current-vintage metadata filtered by reported filing date is not a PIT archive.
    """
    cutoff=datetime.fromisoformat(as_of).date()
    if isinstance(submissions['cik'],bool) or not re.fullmatch(r'\d{1,10}',str(submissions['cik'])):raise ValueError('Invalid CIK')
    cik=int(submissions['cik'])
    if not 0<cik<10**10:raise ValueError('Invalid CIK')
    recent=submissions['filings']['recent'];fields=('form','filingDate','accessionNumber','primaryDocument','reportDate')
    if len({len(recent[f]) for f in fields})!=1:raise ValueError('Misaligned SEC metadata arrays')
    rows=[];seen=set()
    for i,form in enumerate(recent['form']):
        if form!='10-K':continue
        filing=datetime.fromisoformat(recent['filingDate'][i]).date()
        if filing>cutoff:continue
        report=datetime.fromisoformat(recent['reportDate'][i]).date()
        if report>filing:raise ValueError('Report date cannot follow filing date')
        accession=recent['accessionNumber'][i];document=recent['primaryDocument'][i]
        if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession) or accession in seen:raise ValueError('Invalid or duplicate accession')
        if not isinstance(document,str) or not document or '/' in document or '\\' in document or '..' in document:raise ValueError('Invalid primary document name')
        seen.add(accession)
        rows.append({'cik':cik,'accession':accession,'filing_date':str(filing),'report_date':str(report),
                     'url':f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace("-","")}/{quote(document,safe="")}'})
    rows.sort(key=lambda r:(r['filing_date'],r['accession']),reverse=True)
    if len(rows)<2:raise AcquisitionError('Fewer than two eligible 10-Ks; no substitute filing is invented')
    if rows[0]['report_date']==rows[1]['report_date']:raise AcquisitionError('Pair does not span distinct reporting periods')
    return {'current':rows[0],'prior':rows[1],'selection_as_of':str(cutoff),
            'scope':'Two most recent eligible distinct-report 10-Ks in current metadata; no guarantee of historical membership or unmodified source availability.'}
