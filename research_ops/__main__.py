"""Bounded source acquisition CLI; no model calls or frozen-packet rewriting."""
import argparse
import json
from pathlib import Path
import sys

from .ingestion import AcquisitionError, PublicDocumentCache, select_annual_pair


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--user-agent',required=True,help='Descriptive project name and contact route')
    parser.add_argument('--allow-host',action='append',default=[],help='Explicit additional public HTTPS host')
    parser.add_argument('--receipt',type=Path,required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    fetch=sub.add_parser('fetch');fetch.add_argument('url')
    cached=sub.add_parser('cached');cached.add_argument('url');cached.add_argument('--max-age',type=float,required=True)
    pair=sub.add_parser('annual-pair');pair.add_argument('--cik',required=True);pair.add_argument('--as-of',required=True)
    args=parser.parse_args()
    receipt=args.receipt.resolve()
    if receipt.exists():parser.error('Use a new receipt path; prior evidence is not overwritten')
    cache=PublicDocumentCache(args.cache,args.user_agent,allowed_hosts={'www.sec.gov','data.sec.gov',*args.allow_host})
    result={'command':args.command,'source_mode':'current-vintage public acquisition, not a PIT archive',
            'model_calls':0,'frozen_packet_changes':0}
    code=0
    try:
        if args.command=='annual-pair':
            if not args.cik.isdigit() or not 0<int(args.cik)<10**10:raise ValueError('Invalid CIK')
            url=f'https://data.sec.gov/submissions/CIK{int(args.cik):010d}.json'
            body,source=cache.fetch(url)
            selected=select_annual_pair(json.loads(body),args.as_of)
            result.update({'selection':selected,'metadata_source':source,'filings':{}})
            for label in ('prior','current'):
                _,filing=cache.fetch(selected[label]['url'])
                result['filings'][label]=filing
        elif args.command=='cached':
            _,source=cache.read_cached(args.url,args.max_age);result['source']=source
        else:
            _,source=cache.fetch(args.url);result['source']=source
        result['status']='completed'
    except (AcquisitionError,ValueError,KeyError) as exc:
        result.update({'status':'blocked','error_type':type(exc).__name__,'reason':str(exc)})
        code=2
    result['attempts']=cache.attempts()
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return code


if __name__=='__main__':sys.exit(main())
