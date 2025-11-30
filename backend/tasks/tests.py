# backend/tasks/tests.py
from django.test import TestCase
from datetime import date, timedelta
from .scoring import score_task, detect_cycle, DEFAULT_WEIGHTS

class ScoringUnitTests(TestCase):

    def test_past_due_increases_urgency(self):
        t = {
            'id': 1,
            'title': 'Past due',
            'due_date': date.today() - timedelta(days=2),
            'estimated_hours': 2,
            'importance': 5,
            'dependencies': []
        }
        s = score_task(t, weights=DEFAULT_WEIGHTS['smart'], all_tasks_map={1:t})
        self.assertGreaterEqual(s['components']['urgency'], 0.9)

    def test_quick_win_has_higher_effort_component(self):
        t_small = {'id':2,'title':'Quick','due_date':None,'estimated_hours':0.25,'importance':4,'dependencies':[]}
        t_big = {'id':3,'title':'Long','due_date':None,'estimated_hours':10,'importance':4,'dependencies':[]}
        s_small = score_task(t_small, weights=DEFAULT_WEIGHTS['smart'], all_tasks_map={2:t_small})
        s_big = score_task(t_big, weights=DEFAULT_WEIGHTS['smart'], all_tasks_map={3:t_big})
        self.assertGreater(s_small['components']['effort'], s_big['components']['effort'])

    def test_dependency_count_affects_dependency_component(self):
        # task 1 is depended on by 3 tasks => higher dependency score
        all_tasks = {
            1: {'id':1,'dependencies':[]},
            2: {'id':2,'dependencies':[1]},
            3: {'id':3,'dependencies':[1]},
            4: {'id':4,'dependencies':[1]},
        }
        t1 = {'id':1,'title':'A','due_date':None,'estimated_hours':1,'importance':5,'dependencies':[]}
        s = score_task(t1, weights=DEFAULT_WEIGHTS['smart'], all_tasks_map=all_tasks)
        self.assertGreaterEqual(s['components']['dependency'], 0.5)

    def test_detect_cycle_true_and_false(self):
        deps_true = {1:[2],2:[3],3:[1]}
        deps_false = {1:[2],2:[3],3:[]}
        self.assertTrue(detect_cycle(deps_true))
        self.assertFalse(detect_cycle(deps_false))
