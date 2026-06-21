import unittest
from datetime import datetime, timezone
import render


def sample_data():
    return {
        "user": "sanjaygupta-professional",
        "orgs": ["rai-learning-map"],
        "counts": {"repos": 3, "live": 2, "orgs": 1},
        "records": [
            {"name": "alpha-site", "owner": "sanjaygupta-professional", "description": "A deployed site", "language": "HTML", "stars": 3, "pushed_at": "2026-06-18T10:00:00Z", "repo_url": "https://github.com/sanjaygupta-professional/alpha-site", "live_url": "https://sanjaygupta-professional.github.io/alpha-site", "is_owner": True},
            {"name": "beta-tool", "owner": "sanjaygupta-professional", "description": "CLI", "language": "Go", "stars": 0, "pushed_at": "2026-06-10T08:00:00Z", "repo_url": "https://github.com/sanjaygupta-professional/beta-tool", "live_url": "https://beta.example.com", "is_owner": True},
            {"name": "gamma-lib", "owner": "rai-learning-map", "description": "", "language": "", "stars": 1, "pushed_at": "2026-05-01T08:00:00Z", "repo_url": "https://github.com/rai-learning-map/gamma-lib", "live_url": None, "is_owner": False},
        ],
    }


class TestRender(unittest.TestCase):
    def setUp(self):
        self.html = render.render(sample_data(), "2026-06-20")

    def test_is_html_document(self):
        self.assertTrue(self.html.lstrip().startswith("<!DOCTYPE html>"))

    def test_hero_has_live_repos_only(self):
        hero = self.html.split("<!-- GROUPS -->")[0]
        self.assertIn("alpha-site", hero)
        self.assertIn("beta-tool", hero)
        self.assertNotIn("gamma-lib", hero)

    def test_all_repos_in_groups(self):
        self.assertIn("gamma-lib", self.html)
        self.assertIn("rai-learning-map", self.html)

    def test_counts_rendered(self):
        self.assertIn("live sites", self.html.lower())

    def test_no_purple_or_white_bg(self):
        low = self.html.lower()
        self.assertNotIn("a78bfa", low)
        self.assertNotIn("6c8fff", low)
        self.assertIn("#f5f4ed", low)

    def test_html_escaping(self):
        data = sample_data()
        data["records"][0]["description"] = "x <script>alert(1)</script>"
        html = render.render(data, "2026-06-20")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_embedded_no_runtime_fetch(self):
        self.assertNotIn("api.github.com", self.html)
        self.assertNotIn("fetch(", self.html)


class TestTimeAgo(unittest.TestCase):
    def test_today(self):
        now = datetime(2026, 6, 20, tzinfo=timezone.utc)
        self.assertEqual(render.time_ago("2026-06-20T01:00:00Z", now), "today")

    def test_days(self):
        now = datetime(2026, 6, 20, 1, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(render.time_ago("2026-06-17T01:00:00Z", now), "3d ago")


if __name__ == "__main__":
    unittest.main()
