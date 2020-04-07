import argparse
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any, Dict, Union

import bottle
import yaml
from bottle import TEMPLATE_PATH, Bottle, HTTPResponse, request, response, run
from bottle_swagger import SwaggerPlugin

from service import EUNlgService

#
# START INIT
#

# CLI parameters
parser = argparse.ArgumentParser(description="Run the EU-NLG server.")
parser.add_argument("port", type=int, default=8080, help="port number to attach to")
parser.add_argument("--force-cache-refresh", action="store_true", default=False, help="re-compute all local caches")
args = parser.parse_args()
sys.argv = sys.argv[0:1]

log = logging.getLogger("root")
log.setLevel(logging.DEBUG)

formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(module)s - %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.DEBUG)

rotating_file_handler = logging.handlers.RotatingFileHandler(
    Path(__file__).parent / ".." / "reporter.log",
    mode="a",
    maxBytes=5 * 1024 * 1024,
    backupCount=2,
    encoding=None,
    delay=0,
)
rotating_file_handler.setFormatter(formatter)
rotating_file_handler.setLevel(logging.INFO)

log.addHandler(stream_handler)
log.addHandler(rotating_file_handler)

# Bottle
app = Bottle()
service = EUNlgService(random_seed=4551546, force_cache_refresh=args.force_cache_refresh)

TEMPLATE_PATH.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../views/")
static_root = os.path.dirname(os.path.realpath(__file__)) + "/../static/"

# Swagger
with open(Path(__file__).parent / ".." / "swagger.yaml", "r") as file_handle:
    swagger_def = yaml.load(file_handle, Loader=yaml.FullLoader)
app.install(SwaggerPlugin(swagger_def, serve_swagger_ui=True, swagger_ui_suburl="/documentation/"))

#
# END INIT
#


def allow_cors(opts):
    def decorator(func):
        """ this is a decorator which enables CORS for specified endpoint """

        def wrapper(*args, **kwargs):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(opts)

            # Only respond with body for non-OPTIONS
            if bottle.request.method != "OPTIONS":
                return func(*args, **kwargs)

        return wrapper

    return decorator


@app.route("/documentation")
@allow_cors(["POST", "OPTIONS"])
def documentation() -> None:
    bottle.redirect("/documentation/")


@app.route("/eunlg", method=["POST", "OPTIONS"])
@allow_cors(["POST", "OPTIONS"])
def news() -> Union[Dict[str, Any], HTTPResponse]:
    json = request.json

    language = json.get("language", "en")
    if language not in service.get_languages():
        return HTTPResponse({"error": "Invalid value for 'language', query /languages for valid options."}, 400)

    if "dataset" not in json:
        return HTTPResponse({"error": "Missing 'dataset' field"}, 400)
    dataset = json.get("dataset")
    if dataset not in service.get_datasets():
        return HTTPResponse({"error": "Invalid value for 'dataset', query /datasets for valid options."}, 400)

    if "location" not in json:
        return HTTPResponse({"error": "Missing 'location' field"}, 400)
    location = json.get("location")
    if location not in service.get_locations(dataset):
        return HTTPResponse({"error": "Invalid value for 'location', query /locations for valid options."}, 400)

    # TODO: Read from params after support for more locations
    location_type = "C"

    header, body = service.run_pipeline(language, dataset, location, location_type)
    return dict(
        {"location": location, "location_type": location_type, "language": language, "header": header, "body": body}
    )


@app.route("/languages", method=["GET", "OPTIONS"])
@allow_cors(["GET", "OPTIONS"])
def languages() -> Dict[str, Any]:
    return {"languages": service.get_languages()}


@app.route("/datasets", method=["GET", "OPTIONS"])
@allow_cors(["GET", "OPTIONS"])
def datasets() -> Dict[str, Any]:
    return {"datasets": service.get_datasets()}


@app.route("/locations", method=["POST", "OPTIONS"])
@allow_cors(["POST", "OPTIONS"])
def locations() -> Union[HTTPResponse, Dict[str, Any]]:
    json = request.json

    if "dataset" not in json:
        return HTTPResponse("Missing 'dataset' field", 400)
    dataset = json.get("dataset")
    if dataset not in service.get_datasets():
        return HTTPResponse({"error": "Invalid value for 'dataset', query /datasets for valid options."}, 400)

    return {"locations": service.get_locations(dataset)}


@app.route("/health", method=["GET", "OPTIONS"])
@allow_cors(["GET", "OPTIONS"])
def health() -> Dict[str, Any]:
    return {"version": "v0.1.0"}


def main() -> None:
    log.info("Starting with options port={}".format(args.port))
    run(app, server="meinheld", host="0.0.0.0", port=args.port)
    log.info("Stopping")


if __name__ == "__main__":
    main()
