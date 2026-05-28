#!/usr/bin/env python3
"""MacAPK Smart Diagnoser — Trend analysis and health recommendations."""

from datetime import datetime


def analyze_trends(history):
    """Analyze historical data for trends.
    
    Args:
        history: list of check dicts from HistoryDB.get_last()
    
    Returns:
        dict with trend info per module: direction, change, advice
    """
    if len(history) < 2:
        return {'status': 'insufficient_data', 'message': 'Minimaal 2 meetsessies nodig voor trendanalyse'}
    
    trends = {}
    modules = ['cpu', 'gpu', 'ram', 'disk', 'battery', 'network', 'sensors', 'security']
    
    for mod in modules:
        scores = []
        for h in history:
            if mod in h.get('modules', {}):
                scores.append(h['modules'][mod]['score'])
        
        if len(scores) < 2:
            trends[mod] = {'direction': 'stable', 'change': 0, 'advice': 'Onvoldoende data'}
            continue
        
        recent = scores[-3:] if len(scores) >= 3 else scores[-2:]
        older = scores[:-3] if len(scores) >= 3 else [scores[0]]
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        change = recent_avg - older_avg
        
        if change > 5:
            direction = 'improving'
            advice = _get_improvement_advice(mod, recent_avg)
        elif change < -5:
            direction = 'declining'
            advice = _get_decline_advice(mod, recent_avg, change)
        else:
            direction = 'stable'
            advice = _get_stable_advice(mod, recent_avg)
        
        trends[mod] = {
            'direction': direction,
            'change': round(change, 1),
            'current': round(recent_avg, 1),
            'advice': advice,
        }
    
    # Overall trend
    overall_scores = [h['overall_score'] for h in history]
    if len(overall_scores) >= 2:
        change = overall_scores[-1] - overall_scores[0]
        trends['overall'] = {
            'direction': 'improving' if change > 2 else 'declining' if change < -2 else 'stable',
            'change': round(change, 1),
            'current': round(overall_scores[-1], 1),
        }
    
    return trends


def _get_improvement_advice(module, score):
    advice = {
        'cpu': f'CPU gebruik daalt — systeem wordt rustiger ({score:.0f}/100)',
        'gpu': f'GPU belasting neemt af ({score:.0f}/100)',
        'ram': f'Geheugengebruik verbetert — meer vrije RAM ({score:.0f}/100)',
        'disk': f'Schijfruimte situatie verbetert ({score:.0f}/100)',
        'battery': f'Accutoestand stabiel/goed ({score:.0f}/100)',
        'network': f'Netwerkprestaties verbeteren ({score:.0f}/100)',
        'sensors': f'Temperaturen dalen — koeler systeem ({score:.0f}/100)',
        'security': f'Veiligheidsscore verbetert ({score:.0f}/100)',
    }
    return advice.get(module, f'Score {score:.0f}/100 — verbeterend')


def _get_decline_advice(module, score, change):
    advice = {
        'cpu': f'⚠️ CPU belasting stijgt — sluit zware apps of herstart ({score:.0f}/100, {change:+.1f})',
        'gpu': f'⚠️ GPU belasting toegenomen — check GPU-intensieve apps ({score:.0f}/100)',
        'ram': f'⚠️ Geheugenonderdrukking toegenomen — mogelijk geheugenlek ({score:.0f}/100)',
        'disk': f'⚠️ Schijfruimte neemt af — ruim grote bestanden op ({score:.0f}/100)',
        'battery': f'⚠️ Accugezondheid daalt — controleer laadgedrag ({score:.0f}/100)',
        'network': f'⚠️ Netwerkprestaties verminderen — check verbinding ({score:.0f}/100)',
        'sensors': f'⚠️ Temperatuur stijgt — check ventilatie en belasting ({score:.0f}/100)',
        'security': f'⚠️ Veiligheidsscore gedaald — voer updates uit ({score:.0f}/100)',
    }
    return advice.get(module, f'Score {score:.0f}/100 — dalend ({change:+.1f})')


def _get_stable_advice(module, score):
    advice = {
        'cpu': f'CPU stabiel op {score:.0f}/100',
        'gpu': f'GPU stabiel op {score:.0f}/100',
        'ram': f'Geheugen stabiel op {score:.0f}/100',
        'disk': f'Schijf stabiel op {score:.0f}/100',
        'battery': f'Accu stabiel op {score:.0f}/100',
        'network': f'Netwerk stabiel op {score:.0f}/100',
        'sensors': f'Temperatuur stabiel op {score:.0f}/100',
        'security': f'Veiligheid stabiel op {score:.0f}/100',
    }
    return advice.get(module, f'Stabiel op {score:.0f}/100')


def generate_report(check_result, trends=None):
    """Generate a human-readable Markdown report."""
    scores = check_result.get('scores', {})
    overall = scores.get('overall', 0)
    status = scores.get('overall_status', 'onbekend')
    status_icon = {'groen': '✅', 'geel': '⚠️', 'rood': '❌'}.get(status, 'ℹ️')
    
    lines = [
        f'# MacAPK Keuringsrapport',
        f'',
        f'**Datum:** {datetime.now().strftime("%d-%m-%Y %H:%M")}',
        f'',
        f'## {status_icon} Totaalscore: {overall}/100 — {status.upper()}',
        f'',
    ]
    
    module_icons = {'groen': '✅', 'geel': '⚠️', 'rood': '❌'}
    module_names = {
        'cpu': 'Motor (CPU)', 'gpu': 'Uitlaat (GPU)', 'ram': 'Brandstof (RAM)',
        'disk': 'Chassis (Schijf)', 'battery': 'Elektrisch (Accu)', 'network': 'Verklikkers (Netwerk)',
        'sensors': 'Temperatuur', 'security': 'Veiligheid',
    }
    
    for mod, info in scores.get('modules', {}).items():
        icon = module_icons.get(info['status'], 'ℹ️')
        name = module_names.get(mod, mod.upper())
        lines.append(f'### {icon} {name}: {info["score"]}/100')
        for d in info.get('diagnoses', []):
            lines.append(f'- {d}')
        if trends and mod in trends:
            t = trends[mod]
            arrow = {'improving': '↗️', 'declining': '↘️', 'stable': '→'}.get(t['direction'], '→')
            lines.append(f'- {arrow} Trend: {t["advice"]}')
        lines.append('')
    
    lines.append('---')
    lines.append('*MacAPK — De APK Keuring voor je Mac*')
    
    return '\n'.join(lines)