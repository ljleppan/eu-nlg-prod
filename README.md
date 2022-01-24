# News generation from EU data

## Setup and Docker

Build with
```
docker build -t eunlg:latest .
```

Server runs in port 8080. Run docker as
```
docker run -p 8080:8080 -v <data_path>:/app/data eunlg:latest
```

where `<data_path>` is a suitable path for datasets to be stored on the local
system. The dockerfile includes and entrypoint bash script that automatically
downloads the relevant dataframes the system needs.

You can also run `preprocess/download_and_preprocess.py` to populate said
folder from the EuroStat source data.

## API

With the server running, browse to /documentation/ to view the Swagger API
description.

## Selecting a non-default document planner

You can select a non-default document planner by supplying the `--planner <name>` 
argument during startup. The most interesting of these is probably the `neuralsim` 
variant, which uses the FinEst BERT model to determine information similarity. Note that
using this planner
1) significantly increases the generation times
2) requires *much* more memory, with ~16 gigs recommended

## Development 

###Formatting, linting, etc.

The project is set up for use of `isort`, `black` and `flake8`.

It's notable that `isort` is only used to order the imports (something black
can't do), but black's formatting is to be preferred over isort. What this
means is that black must be ran after isort.

Manually run the formatters and linting with
```
 $ isort -rc . && black . && flake8 .
```
You can run
```
 $ pre-commit install
```
to force git to run both black and flake8 for you before it allows you to commit.

## License

For licensing/copyright information on the Eurostat datasets, and limitations on the commercial use of specific subsets of that data, see https://ec.europa.eu/eurostat/about/policies/copyright

The code contained in this repository is licensed as described in the LICENSE file.
