'use strict';
// Human-authored interface/reference translations; no additional model calls.
const HindiUI = (() => {
  let catalog = {};
  const originals = new WeakMap();
  const ready = fetch('/hi.json').then(r => {
    if (!r.ok) throw new Error('Hindi interface catalog unavailable.');
    return r.json();
  }).then(data => { catalog = data; });
  const active = () => document.querySelector('[name="language"]').value === 'hi';
  function text(value) {
    const s = String(value ?? '');
    if (!active()) return s;
    if (Object.hasOwn(catalog, s)) return catalog[s];
    return s.replace(/\[Evidence\s+(\d+)\]/g, '[साक्ष्य $1]');
  }
  function note(value) {
    const s=String(value || '');
    if (!active()) return s;
    if (Object.hasOwn(catalog,s)) return catalog[s];
    let m=s.match(/^(moisture|temperature|ph): ([a-z_, ]+); (interpret cautiously|excluded from advice)\.$/);
    if(m) return `${text(m[1])}: ${m[2].split(', ').map(text).join(', ')}; ${m[3]==='interpret cautiously'?'सावधानी से समझें।':'सलाह में शामिल नहीं किया गया।'}`;
    m=s.match(/^(published_on|reviewed_on|valid_until) (.+)$/);
    if(m) {
      const endings={'is unknown; currency cannot be established.':'अज्ञात है; संदर्भ के अद्यतन होने की पुष्टि नहीं की जा सकती।','metadata is invalid.':'की जानकारी अमान्य है।','is in the future.':'भविष्य की है।','exceeds the configured source-age policy; confirm currency.':'निर्धारित अधिकतम आयु से पुरानी है; अद्यतन होने की पुष्टि करें।'};
      if(endings[m[2]]) return `${text(m[1])} ${endings[m[2]]}`;
    }
    if(s.startsWith('Translation review could not confirm:')) return 'अनुवाद की अर्थ संबंधी जाँच पूरी तरह सफल नहीं हुई। मूल अंग्रेज़ी सलाह नीचे उपलब्ध है।';
    if(s.startsWith('Translation failed checks:')) return 'अनुवाद में संख्याओं, इकाइयों, लिपि या संदर्भों की जाँच असफल रही। मूल अंग्रेज़ी सलाह नीचे उपलब्ध है।';
    if(s.includes('translation segment') || s.includes('Translation assessment unavailable')) return 'अनुवाद पूरा नहीं हुआ या उसकी जाँच सफल नहीं हुई। मूल अंग्रेज़ी सलाह नीचे उपलब्ध है।';
    return 'इस जानकारी की स्वचालित जाँच पूरी नहीं हुई। मूल तकनीकी विवरण नीचे देखें।';
  }
  function apply() {
    document.documentElement.lang=active()?'hi':'en';
    document.title=active()?'CropAdvisory · खेत की सलाह':'CropAdvisory · Field assistant';
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()) {
      const node=walker.currentNode;
      if(node.parentElement.closest('#result, #model-status, #error, #submit, script')) continue;
      if(!originals.has(node)) originals.set(node,node.nodeValue);
      const original=originals.get(node), trimmed=original.trim();
      node.nodeValue=original.replace(trimmed,text(trimmed));
    }
    for(const el of document.querySelectorAll('[placeholder]')) {
      if(!originals.has(el)) originals.set(el,el.placeholder);
      el.placeholder=text(originals.get(el));
    }
    // Result labels also switch without altering the original English advice.
    for(const el of document.querySelectorAll('#result h3, #result summary, #result .hint, #download')) {
      if(el.closest('#sources, #quality, #verification') || el.id==='language-title') continue;
      if(!originals.has(el)) originals.set(el,el.textContent);
      el.textContent=text(originals.get(el));
    }
  }
  return {ready,active,text,note,apply};
})();
