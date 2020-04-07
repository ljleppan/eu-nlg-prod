import itertools

import numpy as np
import pandas as pd
from pandas import DataFrame

from generic_eurostat_preprocessor import GenericEuroStatPreprocessor


class IncomePreprocessor(GenericEuroStatPreprocessor):
    def _flatten(self, df: DataFrame) -> DataFrame:
        """
        Flatten a data frame so that each field contains a single value.
        """
        # Replace every underscore in DataFrame
        for column in df.columns:
            df[column] = df[column].str.replace("_", "-")
        new_df = pd.DataFrame()
        names = list(df.columns)
        new_columns = names.pop(0)

        initial_content = []
        values = df.values.tolist()
        values = [value[1:] for value in values]
        values = list(itertools.chain.from_iterable(values))
        values_n_flags = pd.DataFrame(values)[0].str.split(" ", expand=True)
        values_n_flags = values_n_flags.rename(columns={0: "value", 1: "flag"})
        values_n_flags["value"] = values_n_flags["value"].str.replace(",", "")

        for line in df[new_columns]:
            for when in names:
                initial_content.append((",").join([line, when]))
        new_columns = (",").join([new_columns, "when"])
        new_df[new_columns] = initial_content

        columns = new_columns.split(",")
        new_df = new_df[new_columns].str.split(",", expand=True)
        new_df = new_df.rename(columns=dict(zip(list(new_df.columns), columns)))
        new_df = new_df.rename(columns={"GEO": "where"})
        new_df[["value", "flag"]] = values_n_flags

        new_df = pd.pivot_table(
            new_df,
            index=["where", "when"],
            columns=["AGE", "SEX", "INDIC_IL", "UNIT\\TIME"],
            values="value",
            aggfunc="first",
        )
        new_df.reset_index(level=["where", "when"], inplace=True)
        new_df.columns = new_df.columns.to_flat_index()
        new_df.columns = [
            ("income_" + column[0] + "_" + column[1] + "_" + column[2] + "_" + column[3]).lower()
            for column in new_df.columns
        ]
        new_df.rename(columns={"income_where___": "where", "income_when___": "when"}, inplace=True)
        new_df = new_df.replace(to_replace=":", value=np.nan)

        data = [pd.to_numeric(new_df[s], errors="ignore") for s in new_df.columns]
        new_df = pd.concat(data, axis=1, keys=[s.name for s in data])

        # Add when_type and where_type TODO: for example the euro area is now labeled as a country
        where_type = ["country"] * new_df.shape[0]
        when_type = ["year"] * new_df.shape[0]

        new_df["where_type"] = where_type
        new_df["when_type"] = when_type

        return new_df
