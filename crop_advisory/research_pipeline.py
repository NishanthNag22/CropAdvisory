"""Direct multilingual generation arm for research, separate from production UI."""
import time
from .engine import validate_input, select_evidence, build_messages, sensor_summary, LANGUAGES
from .applicability import screen_sources
from .verification import assess, screened_answer


def direct_advice(payload,client,model):
    started=time.perf_counter();data=validate_input(payload)
    evidence,excluded=screen_sources(select_evidence(data),data)
    draft=None;metrics={};checks=[];error=None
    if evidence:
        messages=build_messages(data,evidence)
        messages[0]['content']=messages[0]['content'].replace('Answer in English.',f"Answer directly in {LANGUAGES[data['language']]}.")
        draft,metrics=client.chat(model,messages)
        checks,error=assess(draft,evidence,client,model)
    supported=[r for r in checks if r['status']=='supported']
    localized=screened_answer(supported,evidence) if supported else None
    return {'input':data,'summary':sensor_summary(data),'answer':'','translation':localized,'draft':draft,
        'evidence':evidence,'excluded_sources':excluded,'verification':checks,'verification_error':error,
        'withheld_claims':len(checks)-len(supported),'generation_performed':draft is not None,
        'advisory_withheld':not bool(supported),'metrics':metrics,'translation_checks':None,
        'translation_status':'direct_generation_research_arm','human_review_required':True,
        'elapsed_seconds':time.perf_counter()-started,'mode':'research_direct',
        'note':'Direct target-language generation is not a translation of an English answer. Evaluate against the same expert rubric; no translation-fidelity score is inferred automatically.'}
