import argparse
import datetime
from pathlib import Path
from typing import List, Optional

from service import EUNlgService


def generate(outdir: str, datasets: Optional[List[str]] = None, languages: Optional[List[str]] = None,) -> None:
    service = EUNlgService(random_seed=4551546)
    out_dir = Path(outdir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)

    for language in service.get_languages():
        if languages and language not in languages:
            continue
        print(language)
        for dataset in service.get_datasets():
            if datasets and dataset not in datasets:
                continue
            print(" ", dataset)
            for location in service.get_locations(dataset):
                print("   ", location)
                if len(location) != 2:
                    print("      Location not 2 letters, skipping")
                try:
                    start = datetime.datetime.now().timestamp()
                    head, body = service.run_pipeline(language, dataset, location, "country")
                    end = datetime.datetime.now().timestamp()
                    out_path = out_dir / "{}-{}-{}.txt".format(language, dataset, location)
                    with out_path.open("w") as file_handle:
                        file_handle.write(body)
                        file_handle.write("\n")
                        print("      Done (t={})".format(end - start))
                except Exception as ex:
                    print(
                        "      Error with inputs: language={}, dataset={}, location={}".format(
                            language, dataset, location
                        )
                    )
                    print("     ", ex)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk generate news stories")
    parser.add_argument("-d", "--datasets", nargs="*", help="Identifiers of datasets to generate", required=False)
    parser.add_argument("-l", "--languages", nargs="*", help="Identifiers of languages to generate", required=False)
    parser.add_argument("-o", "--out", help="Directory in which the generated files are stored", required=True)
    args = parser.parse_args()
    generate(args.out, args.datasets, args.languages)
