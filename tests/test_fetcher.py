import json, os, unittest
import fetcher

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "raw_repos.json")
USER = "sanjaygupta-professional"


class TestNormalize(unittest.TestCase):
    def setUp(self):
        with open(FIX) as f:
            self.raw = json.load(f)

    def test_pages_repo_live_url_constructed(self):
        rec = fetcher.normalize(self.raw[0], USER)
        self.assertEqual(rec["live_url"], "https://sanjaygupta-professional.github.io/alpha-site")
        self.assertTrue(rec["is_owner"])

    def test_homepage_overrides_pages(self):
        rec = fetcher.normalize(self.raw[1], USER)
        self.assertEqual(rec["live_url"], "https://beta.example.com")

    def test_bare_repo_no_live_url(self):
        rec = fetcher.normalize(self.raw[2], USER)
        self.assertIsNone(rec["live_url"])
        self.assertFalse(rec["is_owner"])
        self.assertEqual(rec["owner"], "rai-learning-map")
        self.assertEqual(rec["description"], "")
        self.assertEqual(rec["language"], "")

    def test_sort_key_newest_first(self):
        recs = [fetcher.normalize(r, USER) for r in self.raw]
        recs.sort(key=fetcher.record_sort_key, reverse=True)
        self.assertEqual(recs[0]["name"], "secret-x")


class TestCollect(unittest.TestCase):
    def setUp(self):
        with open(FIX) as f:
            self.raw = json.load(f)

    def _fake_run(self, args):
        joined = " ".join(args)
        if args[-1] == "user" or args[-1].endswith("/user"):
            return json.dumps({"login": USER})
        if "user/orgs" in joined:
            return json.dumps([{"login": "rai-learning-map"}])
        if "user/repos" in joined:
            return json.dumps([r for r in self.raw if r["owner"]["login"] == USER])
        if "orgs/rai-learning-map/repos" in joined:
            return json.dumps([r for r in self.raw if r["owner"]["login"] == "rai-learning-map"])
        return "[]"

    def test_collect_excludes_private(self):
        out = fetcher.collect(run=self._fake_run)
        names = [r["name"] for r in out["records"]]
        self.assertNotIn("secret-x", names)
        self.assertIn("alpha-site", names)
        self.assertIn("gamma-lib", names)

    def test_collect_counts(self):
        out = fetcher.collect(run=self._fake_run)
        self.assertEqual(out["counts"]["repos"], 3)
        self.assertEqual(out["counts"]["live"], 2)
        self.assertEqual(out["user"], USER)

    def test_collect_sorted_newest_first(self):
        out = fetcher.collect(run=self._fake_run)
        self.assertEqual(out["records"][0]["name"], "alpha-site")


if __name__ == "__main__":
    unittest.main()
