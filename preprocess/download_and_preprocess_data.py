import gzip
import pickle
from pathlib import Path

import pandas as pd
import requests

from cphi_preprocessor import CPHIPreprocessor
from env_preprocessor import EnvPreprocessor
from health_cost_preprocessor import HealthCostPreprocessor
from health_funding_preprocessor import HealthFundingPreprocessor

DATA_ROOT = Path(__file__).parent.absolute() / ".." / "data"

DOWNLOAD_URL = "https://ec.europa.eu/eurostat/estat-navtree-portlet-prod/BulkDownloadListing?file=data%2F{}.tsv.gz"

DATA = {
    "cphi": {"table_id": "ei_cphi_m", "preprocessor": CPHIPreprocessor()},
    "env": {"table_id": "env_ac_epneec", "preprocessor": EnvPreprocessor()},
    "health_funding": {"table_id": "hlth_sha11_hf", "preprocessor": HealthFundingPreprocessor()},
    "health_cost": {"table_id": "hlth_sha11_hc", "preprocessor": HealthCostPreprocessor()},
}


def run():
    for dataset, details in DATA.items():
        print("Processing", dataset)
        print("\tDownloading...")
        cache_path = DATA_ROOT / (dataset + ".cache")
        gz_path = DATA_ROOT / (dataset + ".gz")
        tsv_path = DATA_ROOT / (dataset + ".tsv")

        url = DOWNLOAD_URL.format(details["table_id"])
        with requests.get(url, stream=True) as response, open(gz_path, "wb") as gz_handle:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    gz_handle.write(chunk)

        print("\tDownload complete")
        print("\tPreprocessing...")

        with gzip.open(gz_path, "rb") as gz_handle, open(tsv_path, "wb") as tsv_handle:
            tsv_handle.write(gz_handle.read())

        with gzip.open(cache_path, "wb") as cache_handle:
            df = pd.read_csv(tsv_path, sep="\t")
            df = details["preprocessor"].process(df)
            pickle.dump(df, cache_handle)
        print("\tPreprocessing complete")


if __name__ == "__main__":
    run()
