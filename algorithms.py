from collections import deque


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
