from collections import deque
from heapq import heappop, heappush


def build_graph(routers, links):
    graph = {router["id"]: [] for router in routers}
    for link in links:
        if link["active"]:
            source, target = link["source"], link["target"]
            graph[source].append((target, link["latency"]))
            graph[target].append((source, link["latency"]))
    return graph


def reconstruct(previous, destination):
    path = []
    while destination is not None:
        path.append(destination)
        destination = previous[destination]
    return path[::-1]


def bfs(graph, source, destination):
    previous = {source: None}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        if current == destination:
            return reconstruct(previous, destination)
        for neighbor, latency in graph[current]:
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)
    return []


def dijkstra(graph, source, destination):
    distances = {source: 0}
    previous = {source: None}
    queue = [(0, source)]
    while queue:
        cost, current = heappop(queue)
        if cost != distances[current]:
            continue
        if current == destination:
            return reconstruct(previous, destination)
        for neighbor, latency in graph[current]:
            candidate = cost + latency
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = current
                heappush(queue, (candidate, neighbor))
    return []


def simulate(routers, links, source, destination, algorithm):
    graph = build_graph(routers, links)
    if source not in graph or destination not in graph:
        raise ValueError("Choisissez des routeurs existants.")
    if algorithm not in ("bfs", "dijkstra"):
        raise ValueError("Choisissez BFS ou Dijkstra.")
    search = bfs if algorithm == "bfs" else dijkstra
    path = search(graph, source, destination)
    latency = sum(dict(graph[a])[b] for a, b in zip(path, path[1:])) if path else None
    hops = len(path) - 1 if path else None
    return {"path": path, "hops": hops, "latency": latency,
            "cost": hops if algorithm == "bfs" else latency}
