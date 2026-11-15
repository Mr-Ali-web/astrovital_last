"""Stage 3.2: performance guardrails for a view-at-a-time interface."""
import re
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from astro_medical.api import create_app
from tempfile import TemporaryDirectory

class SectionedUiTests(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory()
        self.client=TestClient(create_app(Path(self.folder.name)/'ui.sqlite3',background=False))
        self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.folder.cleanup()
    def test_only_five_primary_navigation_items(self):
        html=self.client.get('/').text
        self.assertEqual(len(re.findall(r'<a href="#[^"]+" data-primary=',html)),5)
        self.assertIn('aria-label="Ichki bo‘limlar"',html)
        self.assertIn('id="globalRisk"',html)
    def test_sections_hidden_when_not_chosen(self):
        html=self.client.get('/').text
        for route in ['crew-section','individual','shared','zones','emergency','alerts','events']:
            self.assertRegex(html,fr'<section[^>]+id="{route}"[^>]*data-view="{route}" hidden')
        self.assertIn('data-view="overview"',html)
        self.assertIn('[hidden]{display:none!important}',self.client.get('/static/style.css').text)
    def test_lazy_history_and_incidents_and_no_eager_interval(self):
        script=self.client.get('/static/app.js').text
        self.assertIn("case 'events':",script)
        self.assertIn("case 'individual':",script)
        self.assertIn("case 'emergency':",script)
        self.assertIn('await ensureStage3();',script)
        self.assertNotIn('setInterval(refresh,2000)',script)
        self.assertIn('document.hidden ? 20000 : 4000',script)
    def test_server_monitoring_background_is_separate_from_ui(self):
        from astro_medical.api import create_app as factory
        import inspect
        self.assertIn('await asyncio.sleep(2)',inspect.getsource(factory))
    def test_ai_still_disabled(self):
        health=self.client.get('/api/health').json()
        self.assertEqual(health['mode'],'SIMULATION_ONLY')
        self.assertFalse(health['ai_model_enabled'])
