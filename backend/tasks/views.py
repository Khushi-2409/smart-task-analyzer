# backend/tasks/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .scoring import detect_cycle, score_task, DEFAULT_WEIGHTS
from datetime import datetime

@api_view(['POST'])
def analyze_tasks(request):
    """
    POST /api/tasks/analyze/ 
    Body: either an array of tasks OR {"tasks": [...], "mode":"smart"}
    Supports optional "mode" to change weighting: smart|fast|impact|deadline
    """
    payload = request.data
    # accept list or {"tasks": [...], "mode": ...}
    if isinstance(payload, list):
        raw_tasks = payload
        mode = 'smart'
    elif isinstance(payload, dict):
        if 'tasks' in payload and isinstance(payload['tasks'], list):
            raw_tasks = payload['tasks']
            mode = payload.get('mode', payload.get('strategy', 'smart')) or 'smart'
        else:
            return Response({'error':'Send a JSON array or {"tasks":[...]}.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'error':'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

    mode = (mode or 'smart').lower()
    weights = DEFAULT_WEIGHTS.get(mode, DEFAULT_WEIGHTS['smart'])

    # Normalize
    tasks = {}
    for t in raw_tasks:
        tid = t.get('id')
        if tid is None:
            return Response({'error':'Each task must include an "id" field.'}, status=status.HTTP_400_BAD_REQUEST)
        due = None
        if t.get('due_date'):
            try:
                due = datetime.fromisoformat(t['due_date']).date()
            except Exception:
                due = None
        tasks[tid] = {
            'id': tid,
            'title': t.get('title','Untitled'),
            'due_date': due,
            'estimated_hours': float(t.get('estimated_hours') or 1.0),
            'importance': int(t.get('importance') or 5),
            'dependencies': list(t.get('dependencies') or [])
        }

    dep_map = {tid: t['dependencies'] for tid,t in tasks.items()}
    cycle = detect_cycle(dep_map)

    scored = []
    for t in tasks.values():
        sc = score_task(t, weights=weights, all_tasks_map=tasks)
        item = t.copy()
        item.update({
            'score': sc['score'],
            'score_components': sc['components']
        })
        scored.append(item)

    scored_sorted = sorted(scored, key=lambda x: x['score'], reverse=True)
    return Response({'cycle_detected': cycle, 'tasks': scored_sorted})


@api_view(['POST'])
def suggest_tasks(request):
    """
    POST /api/tasks/suggest/
    Accepts same body as analyze. Returns top 3 suggestions + explanations.
    """
    # Reuse analyze logic but inline to avoid fake requests
    payload = request.data
    # accept list or {"tasks": [...], "mode": ...}
    if isinstance(payload, list):
        raw_tasks = payload
        mode = 'smart'
    elif isinstance(payload, dict) and 'tasks' in payload:
        raw_tasks = payload['tasks']
        mode = payload.get('mode', payload.get('strategy', 'smart')) or 'smart'
    else:
        # If the client sent the array directly (common from frontend), handle it
        if isinstance(payload, list):
            raw_tasks = payload
            mode = 'smart'
        else:
            return Response({'error':'Send a JSON array or {"tasks":[...]}.'}, status=status.HTTP_400_BAD_REQUEST)

    # normalize same as analyze
    mode = (mode or 'smart').lower()
    weights = DEFAULT_WEIGHTS.get(mode, DEFAULT_WEIGHTS['smart'])

    tasks = {}
    for t in raw_tasks:
        tid = t.get('id')
        if tid is None:
            return Response({'error':'Each task must include an "id" field.'}, status=status.HTTP_400_BAD_REQUEST)
        due = None
        if t.get('due_date'):
            try:
                due = datetime.fromisoformat(t['due_date']).date()
            except Exception:
                due = None
        tasks[tid] = {
            'id': tid,
            'title': t.get('title','Untitled'),
            'due_date': due,
            'estimated_hours': float(t.get('estimated_hours') or 1.0),
            'importance': int(t.get('importance') or 5),
            'dependencies': list(t.get('dependencies') or [])
        }

    dep_map = {tid: t['dependencies'] for tid,t in tasks.items()}
    cycle = detect_cycle(dep_map)

    scored = []
    for t in tasks.values():
        sc = score_task(t, weights=weights, all_tasks_map=tasks)
        item = t.copy()
        item.update({
            'score': sc['score'],
            'score_components': sc['components']
        })
        scored.append(item)

    scored_sorted = sorted(scored, key=lambda x: x['score'], reverse=True)
    top3 = scored_sorted[:3]

    for t in top3:
        comps = t.get('score_components', {})
        sorted_comps = sorted(comps.items(), key=lambda kv: kv[1], reverse=True)
        reasons = [f"{name}={val}" for name,val in sorted_comps[:2]]
        t['explanation'] = " & ".join(reasons)

    return Response({'cycle_detected': cycle, 'suggestions': top3})
