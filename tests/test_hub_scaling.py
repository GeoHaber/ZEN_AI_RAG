# test_hub_scaling.py
import requests
import json
import unittest


class TestHubScaling(unittest.TestCase):
    """TestHubScaling class."""

    def test_hub_scale_endpoint(self):
        """Verify that /swarm/scale exists and accepts a count."""
        url = "http://127.0.0.1:8002/swarm/scale"
        payload = {"count": 2}  # Attempt to scale to 2

        try:
            resp = requests.post(url, json=payload, timeout=5.0)
            # This should FAIL initially with 404 or connection error as it's not implemented
            self.assertEqual(resp.status_code, 200, f"Expected 200, got {resp.status_code}")
            data = resp.json()
            self.assertIn("status", data)
            self.assertIn(data["status"], ("scaling", "scaled"))
        except requests.exceptions.RequestException as e:
            self.fail(f"Request failed: {e}")


if __name__ == "__main__":
    unittest.main()
