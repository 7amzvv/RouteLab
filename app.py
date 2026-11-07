import json
import secrets
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, session, url_for

import database
from algorithms import simulate


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=secrets.token_hex(32),
                      DATABASE=str(Path(app.instance_path) / "routelab.db"))
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    connection = database.connect(app.config["DATABASE"])
    database.initialize(connection)
    connection.close()

    def get_db():
        if "db" not in g:
            g.db = database.connect(app.config["DATABASE"])
        return g.db

    @app.teardown_appcontext
    def close_db(error):
        connection = g.pop("db", None)
        if connection is not None:
            connection.close()

    @app.before_request
    def protect_forms():
        if "token" not in session:
            session["token"] = secrets.token_hex(24)
        if request.method == "POST":
            token = request.form.get("token", "")
            if not secrets.compare_digest(token, session["token"]):
                abort(400, "Formulaire expiré. Rechargez la page avant de réessayer.")

    @app.route("/", methods=["GET", "POST"])
    def index():
        connection = get_db()
        routers, links = database.network(connection)
        source, destination, algorithm = 1, 8, "bfs"
        error, result = None, None
        status = 200
        if request.method == "POST":
            try:
                source = int(request.form.get("source", ""))
                destination = int(request.form.get("destination", ""))
                algorithm = request.form.get("algorithm", "")
                enabled = {int(value) for value in request.form.getlist("links")}
                if not enabled.issubset({link["id"] for link in links}):
                    raise ValueError("Connexion inconnue.")
                for link in links:
                    link["active"] = int(link["id"] in enabled)
                result = simulate(routers, links, source, destination, algorithm)
                with connection:
                    connection.executemany("UPDATE links SET active = ? WHERE id = ?",
                                           [(link["active"], link["id"]) for link in links])
                    simulation_id = database.save_simulation(
                        connection, source, destination, algorithm, result, links)
                return redirect(url_for("index", simulation=simulation_id), code=303)
            except ValueError as exc:
                error = str(exc) if str(exc) in (
                    "Connexion inconnue.", "Choisissez des routeurs existants.",
                    "Choisissez BFS ou Dijkstra.") else "Vérifiez les routeurs et les connexions sélectionnés."
                status = 400
        elif request.args.get("simulation"):
            row = connection.execute("SELECT * FROM simulations WHERE id = ?",
                                     (request.args["simulation"],)).fetchone()
            if row is None:
                abort(404)
            source, destination, algorithm = row["source"], row["destination"], row["algorithm"]
            result = dict(row)
            result["path"] = json.loads(row["path"])
            links = json.loads(row["network"])
        path = result["path"] if result else []
        route_edges = {tuple(sorted((a, b))) for a, b in zip(path, path[1:])}
        positions = {router["id"]: router for router in routers}
        return render_template("index.html", routers=routers, links=links,
                               positions=positions, source=source, destination=destination,
                               algorithm=algorithm, result=result, error=error,
                               route_edges=route_edges, history=database.history(connection)), status

    @app.post("/reset")
    def reset():
        connection = get_db()
        with connection:
            connection.execute("UPDATE links SET active = 1")
        return redirect(url_for("index"), code=303)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
