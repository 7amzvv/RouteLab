CREATE TABLE IF NOT EXISTS routers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY,
    source INTEGER NOT NULL REFERENCES routers(id),
    target INTEGER NOT NULL REFERENCES routers(id),
    latency INTEGER NOT NULL CHECK(latency >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    CHECK(source < target),
    UNIQUE(source, target)
);

CREATE TABLE IF NOT EXISTS simulations (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    source INTEGER NOT NULL REFERENCES routers(id),
    destination INTEGER NOT NULL REFERENCES routers(id),
    algorithm TEXT NOT NULL CHECK(algorithm IN ('bfs', 'dijkstra')),
    path TEXT NOT NULL,
    hops INTEGER,
    latency INTEGER,
    cost INTEGER,
    network TEXT NOT NULL
);
