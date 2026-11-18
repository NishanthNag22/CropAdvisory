"""Crop-filtered retrieval with a download-free baseline and optional local embeddings."""
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CROPS = ('tomato', 'rice', 'wheat', 'cotton')
# Input vocabulary is expanded before searching English evidence.
ALIASES = {
    'soil_moisture': ('water','moisture','irrigation','drainage','dry','wet','flood','watering'),
    'soil_pH': ('ph','acid','acidic','alkaline','alkalinity'),
    'nitrogen_deficiency': ('nitrogen','yellow','leaves','deficiency','nutrient'),
    'soil_nutrition': ('fertilizer','fertiliser','nutrient','npk','soil test'),
    'growth_stage': ('stage','flower','flowering','square','boll','panicle','booting','heading','germination','root','tillering'),
}

def load_entries(crop):
    if crop not in CROPS:
        raise ValueError('Unsupported crop: ' + str(crop))
    if crop == 'tomato':
        entries = json.loads((ROOT/'data/tomato_knowledge.json').read_text(encoding='utf-8'))
        return [dict(e, crop='tomato', region='Tamil Nadu, India', reviewed_on='2026-11-18') for e in entries]
    entries = json.loads((ROOT/'data/crop_knowledge.json').read_text(encoding='utf-8'))
    return [e for e in entries if e['crop'] == crop]


def query_text(data):
    parts = [data.get('question',''), data.get('symptoms',''), data.get('growth_stage','')]
    if data.get('ph') is not None:
        parts.append('soil pH')
    if data.get('moisture') is not None:
        parts.append('soil moisture irrigation')
    return ' '.join(parts).lower()


@lru_cache(maxsize=2)
def semantic_index(crop, model_path):
    """Never download weights during inference. Provision model_path before use."""
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    model = SentenceTransformer(model_path, local_files_only=True)
    entries = load_entries(crop)
    vectors = model.encode([e['topic']+' '+e['guidance'] for e in entries], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    index = faiss.IndexFlatIP(vectors.shape[1]); index.add(vectors)
    return model, index, entries


def retrieve(data, backend='lexical', model_path=None, top_k=3):
    query = query_text(data)
    if backend == 'semantic':
        if not model_path:
            raise ValueError('Set EMBEDDING_MODEL_PATH to a preinstalled local model directory.')
        model, index, entries = semantic_index(data['crop'], model_path)
        vector = model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype('float32')
        scores, indices = index.search(vector, min(top_k,len(entries)))
        return [dict(entries[int(i)],score=float(s),retrieval='semantic') for s,i in zip(scores[0],indices[0]) if i >= 0 and s >= .25]
    if backend != 'lexical':
        raise ValueError('Retrieval backend must be lexical or semantic.')
    topics = {topic for topic, words in ALIASES.items() if any(re.search(r'\b'+re.escape(word)+r'\b',query) for word in words)}
    query_terms = set(re.findall(r'[a-z]+',query))
    ranked=[]
    for entry in load_entries(data['crop']):
        if entry['topic'] not in topics:
            continue
        overlap = query_terms & set(re.findall(r'[a-z]+',entry['guidance'].lower()))
        ranked.append(dict(entry,score=1+len(overlap),retrieval='lexical'))
    return sorted(ranked,key=lambda e:-e['score'])[:top_k]
