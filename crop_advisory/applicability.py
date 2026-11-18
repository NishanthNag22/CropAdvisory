"""Source scope and age screening. Unknown metadata stays explicitly unknown."""
import re
from datetime import date, datetime, timezone


def normalized(text):
    return re.sub(r'[^a-z0-9]+',' ',str(text).lower()).strip()


def assess_source(entry, context, today=None):
    today=today or datetime.now(timezone.utc).date()
    checks={};warnings=[];exclude=False
    source_regions=entry.get('regions') or (['tamil nadu'] if 'tamil nadu' in normalized(entry.get('region','')) else [])
    region=normalized(context.get('region','')).replace('tamilnadu','tamil nadu')
    if not region or not source_regions:
        checks['region']='unknown';warnings.append('Region applicability is unconfirmed.')
    elif any(normalized(r) in region for r in source_regions):
        checks['region']='match'
    else:
        checks['region']='mismatch';warnings.append('Reference region does not match the supplied region.');exclude=True
    user_season=normalized(context.get('season',''))
    seasons=[normalized(s) for s in entry.get('seasons',[])]
    checks['season']='unknown' if not user_season or not seasons else ('match' if user_season in seasons else 'mismatch')
    if checks['season']=='unknown':warnings.append('Season applicability is unconfirmed.')
    if checks['season']=='mismatch':exclude=True;warnings.append('Reference season does not match.')
    systems=[normalized(s) for s in entry.get('production_systems',[])]
    supplied_system=normalized(context.get('production_system',''))
    checks['production_system']='unknown' if not supplied_system or not systems else ('match' if supplied_system in systems else 'mismatch')
    if checks['production_system']=='mismatch':exclude=True;warnings.append('Reference production system does not match.')
    for key in ('published_on','reviewed_on','valid_until'):
        value=entry.get(key)
        if value:
            try:
                parsed=date.fromisoformat(value)
            except (ValueError,TypeError):
                checks[key]='invalid';warnings.append(f'{key} metadata is invalid.');exclude=True;continue
            if key=='valid_until':
                checks[key]='expired' if parsed<today else 'current'
                if parsed<today:exclude=True;warnings.append('Reference validity period has expired.')
            else:
                age=(today-parsed).days
                limit=int(context.get('max_source_age_days',3650))
                checks[key]='future' if age<0 else ('stale' if age>limit else 'current')
                if checks[key]=='future':exclude=True;warnings.append(f'{key} is in the future.')
                if checks[key]=='stale':warnings.append(f'{key} exceeds the configured source-age policy; confirm currency.')
        else:
            checks[key]='unknown'
            if key!='valid_until':warnings.append(f'{key} is unknown; currency cannot be established.')
    if entry.get('crop')!=context['crop']:exclude=True;checks['crop']='mismatch'
    else:checks['crop']='match'
    return {'eligible':not exclude,'checks':checks,'warnings':warnings,
        'note':'Metadata screening is not expert confirmation of local agronomic applicability.'}


def screen_sources(entries, context, today=None):
    accepted=[];excluded=[]
    for entry in entries:
        assessment=assess_source(entry,context,today)
        item=dict(entry,applicability=assessment)
        (accepted if assessment['eligible'] else excluded).append(item)
    return accepted,excluded
