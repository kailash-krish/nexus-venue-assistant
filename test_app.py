import unittest
from nexus-venue-assistant.appt import app

class TestNexusAssistant(unittest.TestCase):
    def setUp(self):
        # Set up the test client
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = app.test_client()

    def tearDown(self):
        self.ctx.pop()

    def test_home_page(self):
        """Test if the home page loads (HTTP 200)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_api_recommend(self):
        """Test if the API returns correct JSON structure"""
        response = self.client.get('/api/recommend')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Verify keys exist in the response
        self.assertIn('gates', data)
        self.assertIn('protip', data)
        self.assertIn('crowd_score', data)
        
    def test_logic_consistency(self):
        """Test if the best gate is actually the one with the best score"""
        response = self.client.get('/api/recommend')
        data = response.get_json()
        gates = data['gates']
        
        # Find the gate marked as 'is_best'
        best_gate = next(g for g in gates if g['is_best'])
        # Find the actual minimum score
        min_score = min(g['score'] for g in gates)
        
        self.assertEqual(best_gate['score'], min_score)

if __name__ == '__main__':
    unittest.main()