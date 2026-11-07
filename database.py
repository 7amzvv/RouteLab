import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROUTERS = [(1, "R1", 80, 220), (2, "R2", 260, 90),
           (3, "R3", 260, 340), (4, "R4", 440, 90),
           (5, "R5", 440, 340), (6, "R6", 620, 90),
           (7, "R7", 620, 340), (8, "R8", 800, 220)]
LINKS = [(1, 1, 2, 35), (2, 2, 8, 40), (3, 1, 3, 5),
         (4, 3, 5, 5), (5, 5, 7, 5), (6, 7, 8, 5),
         (7, 2, 4, 8), (8, 4, 6, 8), (9, 6, 8, 8),
         (10, 4, 5, 12), (11, 6, 7, 10)]


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection):
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    connection.executescript(schema)
    with connection:
        connection.executemany("INSERT OR IGNORE INTO routers VALUES (?, ?, ?, ?)", ROUTERS)
        connection.executemany(
            "INSERT OR IGNORE INTO links (id, source, target, latency) VALUES (?, ?, ?, ?)", LINKS)


def network(connection):
    routers = [dict(row) for row in connection.execute("SELECT * FROM routers ORDER BY id")]
    links = [dict(row) for row in connection.execute("SELECT * FROM links ORDER BY id")]
    return routers, links


def save_simulation(connection, source, destination, algorithm, result, links):
    cursor = connection.execute(
        "INSERT INTO simulations (created_at, source, destination, algorithm, path, "
        "hops, latency, cost, network) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), source, destination,
         algorithm, json.dumps(result["path"]), result["hops"], result["latency"],
         result["cost"], json.dumps(links)))
    return cursor.lastrowid


def history(connection):
    rows = connection.execute("SELECT * FROM simulations ORDER BY id DESC LIMIT 10")
    results = []
    for row in rows:
        result = dict(row)
        result["path"] = json.loads(result["path"])
        result["created_at"] = datetime.fromisoformat(result["created_at"]).astimezone().strftime("%d/%m/%Y %H:%M:%S")
        results.append(result)
    return results
