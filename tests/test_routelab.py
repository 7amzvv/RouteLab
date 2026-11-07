import json
import tempfile
import unittest
from pathlib import Path

import database
from algorithms import simulate
from app import create_app


def small_network(edges, count=4):
    routers = [{"id": index} for index in range(1, count + 1)]
    links = [{"id": index, "source": a, "target": b, "latency": latency, "active": 1}
             for index, (a, b, latency) in enumerate(edges, 1)]
    return routers, links


class AlgorithmTests(unittest.TestCase):
    def test_direct_connection(self):
        routers, links = small_network([(1, 2, 4), (2, 3, 6)], 3)
        for algorithm in ("bfs", "dijkstra"):
            result = simulate(routers, links, 1, 2, algorithm)
            self.assertEqual(result["path"], [1, 2])
            self.assertEqual(result["latency"], 4)

    def test_different_optima(self):
        routers, links = small_network([(1, 4, 30), (1, 2, 2), (2, 3, 2), (3, 4, 2)])
        self.assertEqual(simulate(routers, links, 1, 4, "bfs")["path"], [1, 4])
        result = simulate(routers, links, 1, 4, "dijkstra")
        self.assertEqual(result["path"], [1, 2, 3, 4])
        self.assertEqual(result["cost"], 6)

    def test_disconnected_components(self):
        routers, links = small_network([(1, 2, 3), (3, 4, 2)])
        for algorithm in ("bfs", "dijkstra"):
            result = simulate(routers, links, 1, 4, algorithm)
            self.assertEqual(result["path"], [])
            self.assertIsNone(result["cost"])

    def test_disabled_link_and_latency_change(self):
        routers, links = small_network([(1, 4, 30), (1, 2, 2), (2, 3, 2), (3, 4, 2)])
        links[2]["active"] = 0
        self.assertEqual(simulate(routers, links, 1, 4, "dijkstra")["path"], [1, 4])
        links[2]["active"] = 1
        links[0]["latency"] = 1
        self.assertEqual(simulate(routers, links, 1, 4, "dijkstra")["cost"], 1)

    def test_same_router(self):
        routers, links = small_network([])
        for algorithm in ("bfs", "dijkstra"):
            self.assertEqual(simulate(routers, links, 2, 2, algorithm),
                             {"path": [2], "hops": 0, "latency": 0, "cost": 0})

    def test_cycle_zero_latency_and_reverse_direction(self):
        routers, links = small_network([(1, 2, 0), (2, 3, 0), (1, 3, 1), (3, 4, 2)])
        result = simulate(routers, links, 4, 1, "dijkstra")
        self.assertEqual(result["path"], [4, 3, 2, 1])
        self.assertEqual(result["latency"], 2)

    def test_invalid_choices(self):
        routers, links = small_network([])
        for source, algorithm in [(9, "bfs"), (1, "unknown")]:
            with self.assertRaises(ValueError):
                simulate(routers, links, source, 4, algorithm)


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = str(Path(self.folder.name) / "test.db")
        self.app = create_app({"TESTING": True, "DATABASE": self.path, "SECRET_KEY": "test-key"})
        self.client = self.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as session:
            self.token = session["token"]

    def post(self, **changes):
        data = {"source": "1", "destination": "8", "algorithm": "bfs",
                "links": [str(index) for index in range(1, 12)], "token": self.token}
        data.update(changes)
        return self.client.post("/", data=data, follow_redirects=True)

    def test_demo_and_saved_results(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post(algorithm="dijkstra").status_code, 200)
        connection = database.connect(self.path)
        self.addCleanup(connection.close)
        rows = connection.execute("SELECT * FROM simulations ORDER BY id").fetchall()
        self.assertEqual(json.loads(rows[0]["path"]), [1, 2, 8])
        self.assertEqual((rows[0]["hops"], rows[0]["latency"], rows[0]["cost"]), (2, 75, 2))
        self.assertEqual(json.loads(rows[1]["path"]), [1, 3, 5, 7, 8])
        self.assertEqual((rows[1]["hops"], rows[1]["latency"], rows[1]["cost"]), (4, 20, 20))

    def test_failure_and_alternate_route(self):
        response = self.post(algorithm="dijkstra", links=[str(i) for i in range(1, 12) if i != 6])
        self.assertEqual(response.status_code, 200)
        connection = database.connect(self.path)
        self.addCleanup(connection.close)
        row = connection.execute("SELECT * FROM simulations").fetchone()
        self.assertEqual(json.loads(row["path"]), [1, 3, 5, 7, 6, 8])
        self.assertEqual(row["latency"], 33)

    def test_no_path_and_same_source_messages(self):
        self.assertIn("Aucun chemin disponible", self.post(links=[]).get_data(as_text=True))
        self.assertIn("Aucun déplacement nécessaire", self.post(destination="1", links=[]).get_data(as_text=True))

    def test_persistence_reset_and_snapshot(self):
        self.post(links=[])
        second_app = create_app({"TESTING": True, "DATABASE": self.path})
        self.assertIn("Aucun chemin disponible", second_app.test_client().get("/?simulation=1").get_data(as_text=True))
        response = self.client.post("/reset", data={"token": self.token}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        connection = database.connect(self.path)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute("SELECT SUM(active) FROM links").fetchone()[0], 11)
        self.assertIn("Aucun chemin disponible", self.client.get("/?simulation=1").get_data(as_text=True))

    def test_invalid_request_does_not_change_database(self):
        for data in ({"source": "abc"}, {"source": "99"}, {"algorithm": "bad"}, {"links": ["99"]}):
            self.assertEqual(self.post(**data).status_code, 400)
        self.assertEqual(self.client.post("/", data={}).status_code, 400)
        self.assertEqual(self.client.get("/?simulation=999").status_code, 404)
        connection = database.connect(self.path)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM simulations").fetchone()[0], 0)
        self.assertEqual(connection.execute("SELECT SUM(active) FROM links").fetchone()[0], 11)

    def test_changed_latency_is_used(self):
        connection = database.connect(self.path)
        with connection:
            connection.execute("UPDATE links SET latency = 1 WHERE id IN (1, 2)")
        connection.close()
        self.post(algorithm="dijkstra")
        connection = database.connect(self.path)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute("SELECT latency FROM simulations").fetchone()[0], 2)

    def test_refresh_does_not_duplicate_and_history_is_limited(self):
        response = self.client.post("/", data={"source": "1", "destination": "8", "algorithm": "bfs", "token": self.token})
        self.assertEqual(response.status_code, 303)
        self.client.get(response.location)
        self.client.get(response.location)
        for _ in range(11):
            self.post()
        connection = database.connect(self.path)
        self.addCleanup(connection.close)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM simulations").fetchone()[0], 12)
        self.assertEqual(len(database.history(connection)), 10)


if __name__ == "__main__":
    unittest.main()
