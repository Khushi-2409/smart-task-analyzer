# backend/tasks/scoring.py
from datetime import date
import math

DEFAULT_WEIGHTS = {
    'smart': {'urgency':0.35,'importance':0.35,'effort':0.15,'dependency':0.15},
    'fast': {'urgency':0.15,'importance':0.2,'effort':0.5,'dependency':0.15},
    'impact': {'urgency':0.2,'importance':0.5,'effort':0.1,'dependency':0.2},
    'deadline': {'urgency':0.6,'importance':0.2,'effort':0.1,'dependency':0.1}
}

def days_until(due_date):
    if not due_date:
        return None
    return (due_date - date.today()).days

def detect_cycle(tasks_map):
    visited = {}
    def dfs(node):
        state = visited.get(node, 0)
        if state == 1:
            return True
        if state == 2:
            return False
        visited[node] = 1
        for nbr in tasks_map.get(node, []):
            if dfs(nbr):
                return True
        visited[node] = 2
        return False
    for n in tasks_map.keys():
        if visited.get(n, 0) == 0:
            if dfs(n):
                return True
    return False

def score_task(task, weights=None, all_tasks_map=None):
    if weights is None:
        weights = DEFAULT_WEIGHTS['smart']

    # Urgency
    days = None
    if task.get('due_date'):
        try:
            days = (task['due_date'] - date.today()).days
        except Exception:
            days = None
    if days is None:
        urgency = 0.10
    elif days < 0:
        urgency = 1.0
    else:
        urgency = max(0.0, min(1.0, 1.0 - (days / 30.0)))

    # Importance scale 1..10 -> 0..1
    imp = task.get('importance', 5)
    try:
        imp = int(imp)
    except Exception:
        imp = 5
    imp = max(1, min(10, imp))
    importance = (imp - 1) / 9.0

    # Effort: smaller is better (quick wins)
    try:
        est = float(task.get('estimated_hours') or 1.0)
    except Exception:
        est = 1.0
    est = max(0.01, est)
    effort = 1.0 / (1.0 + math.log1p(est))

    # Dependency: count how many tasks depend on this one
    dep_count = 0
    if all_tasks_map:
        for t in all_tasks_map.values():
            if task['id'] in t.get('dependencies', []):
                dep_count += 1
    dependency = min(1.0, dep_count / 5.0)

    total = (weights.get('urgency',0)*urgency +
             weights.get('importance',0)*importance +
             weights.get('effort',0)*effort +
             weights.get('dependency',0)*dependency)

    return {
        'score': round(float(total)*100, 2),  # return 0-100 scale for better UI
        'components': {
            'urgency': round(float(urgency), 4),
            'importance': round(float(importance), 4),
            'effort': round(float(effort), 4),
            'dependency': round(float(dependency), 4),
        }
    }
