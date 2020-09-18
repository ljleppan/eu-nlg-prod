import argparse
import datetime
from pathlib import Path
from typing import List, Optional

from service import EUNlgService


def generate(outdir: str, datasets: Optional[List[str]] = None, languages: Optional[List[str]] = None,) -> None:
    out_dir = Path(outdir)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)

    variants = [
        "random",
        "score",
        # "earlystop",
        # "topicsim",
        # "contextsim",
        "full",
    ]

    for variant_idx, variant in enumerate(variants):
        service = EUNlgService(random_seed=4551546, planner=variant)
        print("{} ({}/{})".format(variant, variant_idx + 1, len(variants)))

        filtered_languages = [lang for lang in service.get_languages() if ((not languages) or (lang in languages))]
        for language_idx, language in enumerate(filtered_languages):
            print("  {} ({}/{})".format(language, language_idx + 1, len(filtered_languages)))

            filtered_datasets = [ds for ds in service.get_datasets(language) if ((not datasets) or (ds in datasets))]
            for dataset_index, dataset in enumerate(filtered_datasets):
                print("    {} ({}/{})".format(dataset, dataset_index + 1, len(filtered_datasets)))
                locations = service.get_locations(dataset)
                for location_idx, location in enumerate(locations):
                    print("      {} ({}/{})".format(location, location_idx + 1, len(locations)))
                    try:
                        start = datetime.datetime.now().timestamp()
                        head, body = service.run_pipeline(language, dataset, location, "country")
                        end = datetime.datetime.now().timestamp()
                        out_path = out_dir / "{}-{}-{}-{}.txt".format(variant, language, dataset, location)
                        with out_path.open("w") as file_handle:
                            file_handle.write(body)
                            file_handle.write("\n")
                            print("      Done (t={})".format(end - start))
                    except Exception as ex:
                        print(
                            "      Error with inputs: variant={}, language={}, dataset={}, location={}".format(
                                variant, language, dataset, location
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
