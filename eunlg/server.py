import argparse
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Union

import bottle
import yaml
from bottle import Bottle, HTTPResponse, request, response, run
from bottle_swagger import SwaggerPlugin

from service import EUNlgService

#
# START INIT
#

# CLI parameters
parser = argparse.ArgumentParser(description="Run the EU-NLG server.")
parser.add_argument("port", type=int, nargs="?", default=8080, help="port number to attach to")
parser.add_argument("--planner", nargs="?", default="full", help="use a specific document planner")
parser.add_argument("--force-cache-refresh", action="store_true", default=False, help="re-compute all local caches")
args = parser.parse_args()
sys.argv = sys.argv[0:1]

log = logging.getLogger("root")
log.setLevel(logging.INFO)

formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(module)s - %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

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
service = EUNlgService(random_seed=4551546, force_cache_refresh=args.force_cache_refresh, planner=args.planner)

# Swagger
with open(Path(__file__).parent / ".." / "swagger.yaml", "r") as file_handle:
    swagger_def = yaml.load(file_handle, Loader=yaml.FullLoader)
app.install(
    SwaggerPlugin(swagger_def, serve_swagger_ui=True, swagger_ui_suburl="/documentation/", validate_requests=False)
)

# Allow for trailing slash in request URLS
@app.hook("before_request")
def strip_path():
    # Needs to be special-cased for /documentation/ 'cause bottle-swagger is weird about it.
    if "/documentation" not in request.environ["PATH_INFO"]:
        request.environ["PATH_INFO"] = request.environ["PATH_INFO"].rstrip("/")


#
# END INIT
#
def allow_cors(opts):
    def decorator(func):
        """ this is a decorator which enables CORS for specified endpoint """

        def wrapper(*args, **kwargs):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(opts)
            response.headers["Access-Control-Allow-Headers"] = (
                "Origin, Accept, Content-Type, X-Requested-With, " "X-CSRF-Token"
            )

            # Only respond with body for non-OPTIONS
            if bottle.request.method != "OPTIONS":
                return func(*args, **kwargs)

        return wrapper

    return decorator


@app.route("/eunlg", method=["POST", "OPTIONS"])
@allow_cors(["POST", "OPTIONS"])
def news() -> Union[Dict[str, Any], HTTPResponse]:
    json = request.json

    if not json:
        response.status = 400
        return {"error": "Missing or empty message body"}

    language = json.get("language", "en")
    if language not in service.get_languages():
        response.status = 400
        return {"error": "Invalid value for 'language', query /languages for valid options."}

    if "dataset" not in json:
        response.status = 400
        return {"error": "Missing 'dataset' field"}
    dataset = json.get("dataset")
    if dataset not in service.get_datasets():
        response.status = 400
        return {"error": "Invalid value for 'dataset', query /datasets for valid options."}
    if dataset not in service.get_datasets(language):
        response.status = 400
        return {"error": "Dataset not supported for language, query /datasets for supported datasets."}

    if "location" not in json:
        response.status = 400
        return {"error": "Missing 'location' field"}
    location = json.get("location")
    if location not in service.get_locations(dataset):
        response.status = 400
        return {"error": "Invalid value for 'location', query /locations for valid options."}

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


@app.route("/datasets", method=["POST", "OPTIONS"])
@allow_cors(["POST", "OPTIONS"])
def datasets() -> Union[HTTPResponse, Dict[str, Any]]:
    json = request.json
    if not json:
        response.status = 400
        return {"error": "Missing request body"}

    if "language" not in json:
        response.status = 400
        return {"error": "Missing 'language' field"}
    language = json.get("language")
    if language not in service.get_languages():
        response.status = 400
        return {"error": "Invalid value for 'language', query /languages for valid options."}

    return {"datasets": service.get_datasets(language)}


@app.route("/locations", method=["POST", "OPTIONS"])
@allow_cors(["POST", "OPTIONS"])
def locations() -> Union[HTTPResponse, Dict[str, Any]]:
    json = request.json
    if not json:
        response.status = 400
        return {"error": "Missing request body"}

    if "dataset" not in json:
        response.status = 400
        return {"error": "Missing 'dataset' field"}
    dataset = json.get("dataset")
    if dataset not in service.get_datasets():
        response.status = 400
        return {"error": "Invalid value for 'dataset', query /datasets for valid options."}

    return {"locations": service.get_locations(dataset)}


@app.route("/health", method=["GET", "OPTIONS"])
@allow_cors(["GET", "OPTIONS"])
def health() -> Dict[str, Any]:
    return {"version": "1.1.0"}


def main() -> None:
    log.info("Starting with options port={}".format(args.port))
    run(app, server="meinheld", host="0.0.0.0", port=args.port)
    log.info("Stopping")


if __name__ == "__main__":
    main()
