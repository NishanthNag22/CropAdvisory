'use strict';
const $ = id => document.getElementById(id);
const t = value => HindiUI.text(value);
const form = $('advisory');
let latest = null, installedModels = null;
function modelStatus() {
  $('model-status').textContent = installedModels === null
    ? (HindiUI.active()?'Ollama उपलब्ध नहीं है। ollama serve शुरू करें या अंग्रेज़ी में केवल संदर्भों का पूर्वावलोकन चुनें।':'Ollama unavailable. Start ollama serve, or choose the English evidence-only preview.')
    : (HindiUI.active()?`Ollama जुड़ा है · ${installedModels} मॉडल स्थापित हैं`:`Ollama connected · ${installedModels} installed models`);
}
fetch('/api/models').then(async r => {
  const data=await r.json(); if(!r.ok) throw new Error(data.error);
  for(const model of data.models || []) {const option=document.createElement('option');option.value=model.name;$('models').append(option);}
  installedModels=(data.models || []).length;
}).catch(()=>{}).finally(async()=>{await HindiUI.ready;modelStatus();});
HindiUI.ready.then(()=>{HindiUI.apply();$('submit').textContent=t('Generate advisory ↗');}).catch(e=>{$('error').textContent=e.message;$('error').hidden=false;});
form.elements.language.addEventListener('change',async()=>{
  await HindiUI.ready;HindiUI.apply();modelStatus();$('submit').textContent=t('Generate advisory ↗');
  // A previous result belongs to its submitted language, not the new selection.
  latest=null;$('result').hidden=true;$('empty').hidden=false;$('error').hidden=true;
});
$('example').addEventListener('click',()=>{
  form.reset();form.elements.moisture.max='100';form.elements.temperature.min='-20';form.elements.temperature.max='70';
  Object.entries({moisture:'28',temperature:'30',ph:'6.8',question:'What should I check before changing irrigation?',mode:'evidence',language:'en'}).forEach(([key,value])=>form.elements[key].value=value);
  HindiUI.apply();modelStatus();$('submit').textContent=t('Generate advisory ↗');form.scrollIntoView({behavior:'smooth'});
});
function sensorSummary(data) {
  if(!HindiUI.active()) return data.summary;
  const input=data.input, lines=[`फसल: ${t({tomato:'Tomato',rice:'Rice',wheat:'Wheat',cotton:'Cotton'}[input.crop])}`];
  for(const [key,label] of [['region','क्षेत्र'],['soil_type','मिट्टी का प्रकार'],['growth_stage','विकास अवस्था'],['symptoms','दिखने वाले लक्षण']]) lines.push(`${label}: ${input[key] || 'नहीं दिया गया'}`);
  for(const [key,record] of Object.entries(input.sensor_quality || {})) {
    lines.push(`${t(key)}: ${record.normalized_value ?? 'नहीं दिया गया'} ${record.unit}`);
    lines.push(`माप का समय: ${record.timestamp || 'अज्ञात'}; गुणवत्ता: ${record.states.map(t).join(', ')}`);
  }
  const weather=input.weather || {};
  lines.push(`मौसम की स्थिति: ${(weather.states || []).map(t).join(', ')}`);
  for(const [key,label] of [['rainfall_24h_mm','पिछले 24 घंटे की वर्षा (mm)'],['forecast_rainfall_mm','अनुमानित वर्षा (mm)'],['humidity','आर्द्रता (%)']]) lines.push(`${label}: ${weather[key] ?? 'नहीं दिया गया'}`);
  lines.push(`मौसम की जानकारी का समय: ${weather.timestamp || 'अज्ञात'}`,`मौसम का स्रोत: ${weather.weather_source || 'नहीं दिया गया'}`);
  if(weather.weather_notes) lines.push(`मौसम संबंधी टिप्पणी: ${weather.weather_notes}`);
  lines.push('VWC सेंसर का कच्चा प्रतिशत नहीं है। खेत की जानकारी उपयोगकर्ता ने दी है।');
  return lines.join('\n');
}
function render(data) {
  latest=data;HindiUI.apply();$('empty').hidden=true;$('result').hidden=false;
  $('answer').textContent=data.answer;$('english-original').open=!HindiUI.active() || !data.translation;
  $('summary').textContent=sensorSummary(data);
  const mode=data.mode==='evidence'?(HindiUI.active()?'केवल संदर्भ · मॉडल का उपयोग नहीं':'EVIDENCE PREVIEW · NO LLM'):(data.generation_performed?data.model:(HindiUI.active()?'जानकारी उपलब्ध नहीं · मॉडल का उपयोग नहीं':'NO COVERAGE · NO LLM'));
  $('result-meta').textContent=`${mode} · ${data.elapsed_seconds}${HindiUI.active()?' सेकंड':'s'}`;
  $('translated').hidden=!data.translation;$('translated-text').textContent=t(data.translation || '');$('translated-text').lang=data.input.language;$('language-title').textContent=t(data.language);
  const notes=[...(data.quality_warnings || [])];
  if(data.verification_error) notes.push(data.verification_error);
  if(['withheld','unavailable'].includes(data.translation_status)) notes.push(data.translation_failure_reason || 'Translation assessment unavailable');
  for(const source of data.evidence || []) notes.push(...(source.applicability?.warnings || []));
  $('quality').replaceChildren();
  for(const note of new Set(notes)) {const p=document.createElement('p');p.className='hint';p.textContent=HindiUI.note(note);$('quality').append(p);}
  for(const source of data.excluded_sources || []) {
    const p=document.createElement('p');p.className='hint';p.textContent=HindiUI.active()?`शामिल नहीं किया गया: ${t(source.source)}। ${(source.applicability?.warnings || []).map(HindiUI.note).join(' ')}`:`Excluded ${source.source}: ${(source.applicability?.warnings || []).join(' ')}`;$('quality').append(p);
  }
  $('verification').replaceChildren();
  for(const check of data.verification || []) {const p=document.createElement('p');p.lang='en';p.textContent=`${check.status} · ${check.claim} — ${check.reason}`;$('verification').append(p);}
  $('original-diagnostics').textContent=HindiUI.active()?notes.join('\n'):'';
  $('sources').replaceChildren();
  for(const [i,source] of (data.evidence || []).entries()) {
    const box=document.createElement('div'),title=document.createElement('strong'),guidance=document.createElement('p'),scope=document.createElement('p');
    title.textContent=`${t(`[Evidence ${i+1}]`)} ${t(source.source)}`;
    guidance.textContent=t(source.guidance);scope.className='hint';
    scope.textContent=HindiUI.active()?`क्षेत्र: ${t(source.region || 'unknown')} · प्रकाशन तिथि: ${t(source.published_on || 'unknown')} · समीक्षा तिथि: ${t(source.reviewed_on || 'unknown')}`:`Scope: ${source.region || 'unknown'} · Published: ${source.published_on || 'unknown'} · Reviewed: ${source.reviewed_on || 'unknown'}`;
    box.append(title,guidance,scope);
    if(source.source_url && /^https?:\/\//.test(source.source_url)) {const a=document.createElement('a');a.href=source.source_url;a.textContent=t('View original source ↗');a.target='_blank';a.rel='noopener noreferrer';box.append(a);}
    $('sources').append(box);
  }
  if(!data.evidence.length) $('sources').textContent=t('No source in this knowledge base matches the supplied topic.');
}
form.addEventListener('submit',async event=>{
  event.preventDefault();await HindiUI.ready;
  const payload=Object.fromEntries(new FormData(event.target));
  $('error').hidden=true;$('result').hidden=true;latest=null;$('submit').disabled=true;form.elements.language.disabled=true;$('submit').textContent=t('Preparing your advisory…');
  try {
    const response=await fetch('/api/advice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}),data=await response.json();
    if(!response.ok) throw new Error(data.error || 'Request failed');render(data);
  } catch(e) {$('error').textContent=HindiUI.active()?`सलाह तैयार नहीं हो सकी। ${HindiUI.note(e.message)}`:e.message;$('error').title=e.message;$('error').hidden=false;}
  finally {$('submit').disabled=false;form.elements.language.disabled=false;$('submit').textContent=t('Generate advisory ↗');}
});
$('download').addEventListener('click',()=>{
  if(!latest) return;
  const display=HindiUI.active()?{language:'hi',advisory:$('translated-text').textContent,quality:[...$('quality').children].map(p=>p.textContent),sources:[...$('sources').children].map(p=>p.textContent),sensor_summary:$('summary').textContent}:null;
  const url=URL.createObjectURL(new Blob([JSON.stringify({...latest,localized_display:display},null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='crop-advisory.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
form.elements.temperature_unit.addEventListener('change',()=>{const f=form.elements.temperature,fahrenheit=form.elements.temperature_unit.value==='°F';f.min=fahrenheit?'-4':'-20';f.max=fahrenheit?'158':'70';});
form.elements.moisture_unit.addEventListener('change',()=>{form.elements.moisture.max=form.elements.moisture_unit.value==='fraction'?'1':'100';});
