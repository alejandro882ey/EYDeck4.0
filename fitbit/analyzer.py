import csv
import os
from collections import defaultdict
from typing import Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

def normalize_name(name: str) -> str:
    """Normaliza nombres para comparación: quita espacios, pasa a minúsculas, elimina caracteres especiales."""
    if not name:
        return ''
    return ''.join(e for e in name.lower().strip() if e.isalnum())

def load_metas():
    metas = {}
    path = os.path.join(PROJECT_ROOT, 'metas_MANAGERS.csv')
    if not os.path.exists(path):
        return metas
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = r.get('manager') or r.get('Manager')
            norm_key = normalize_name(key)
            metas[norm_key] = r
    return metas

def collect_metrics_from_db_or_files(upload_source=None):
    # Stub: In the real implementation this will query DB models or parse uploaded files
    # Return structure: { 'partner_name': {'ansr': value, 'hours': value, 'monthly': {...}, 'annual': {...}} }
    sample = {
        'Partner A': {'ansr': 0.85, 'hours': 120},
        'Partner B': {'ansr': 0.60, 'hours': 80},
    }
    return sample

def compare_against_metas(metrics: Dict[str, Dict[str, Any]], metas: Dict[str, Any]):
    results = {}
    for partner, vals in metrics.items():
        norm_partner = normalize_name(partner)
        meta = metas.get(norm_partner, {})
        target_ansr = float(meta.get('target_ansr', 0)) if meta else 0
        target_hours = float(meta.get('target_hours', 0)) if meta else 0
        results[partner] = {
            'ansr': vals.get('ansr'),
            'hours': vals.get('hours'),
            'target_ansr': target_ansr,
            'target_hours': target_hours,
            'ansr_diff': (vals.get('ansr') - target_ansr) if vals.get('ansr') is not None else None,
            'hours_diff': (vals.get('hours') - target_hours) if vals.get('hours') is not None else None,
        }
    return results

def run_fitbit_analysis(upload_source=None):
    from .ai_helper import generate_analysis
    from .teams_notifier import send_message
    metas = load_metas()
    metrics = collect_metrics_from_db_or_files(upload_source)
    comparison = compare_against_metas(metrics, metas)

    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL')
    results = {}
    for partner, comp in comparison.items():
        analysis = generate_analysis(partner, comp)
        title = f"Fitbit Análisis para {partner}"
        text = f"{analysis['summary']}\n\nSugerencia IA: {analysis['suggestion']}"
        notify_result = send_message(webhook_url, title, text)
        results[partner] = {
            'comparison': comp,
            'analysis': analysis,
            'notification': notify_result
        }
    return results
