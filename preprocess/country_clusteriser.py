import itertools

import pandas as pd
from pandas import DataFrame


class CountryClusteriser:
    def run(self) -> DataFrame:

        gdp_df = pd.read_csv("../database/sdg_08_10+ESTAT.tsv", sep="\t")
        # Flatten DataFrame
        gdp_df = self.flatten_gdp(gdp_df)
        # Clusters for countries
        country_clusters_df = self.cluster_countries(gdp_df)

        return country_clusters_df

    def flatten_gdp(self, df: DataFrame) -> DataFrame:
        """
        Flatten a data frame so that each field contains a single value.
        """

        new_df = pd.DataFrame()
        names = list(df.columns)

        new_columns = names.pop(0)

        initial_content = []
        values = df.values.tolist()
        values = [value[1:] for value in values]
        values = list(itertools.chain.from_iterable(values))
        values_n_flags = pd.DataFrame(values)[0].str.split(" ", expand=True)
        values_n_flags = values_n_flags.rename(columns={0: "value", 1: "flag"})

        for line in df[new_columns]:
            for when in names:
                initial_content.append((",").join([line, when]))
        new_columns = (",").join([new_columns, "when"])
        new_df[new_columns] = initial_content

        columns = new_columns.split(",")
        new_df = new_df[new_columns].str.split(",", expand=True)
        new_df = new_df.rename(columns=dict(zip(list(new_df.columns), columns)))
        new_df = new_df.rename(columns={"geo\\TIME_PERIOD": "where"})

        new_df[["value", "flag"]] = values_n_flags

        new_df = pd.pivot_table(
            new_df, index=["where"], columns=["na_item", "unit", "when"], values="value", aggfunc="first",
        )
        new_df.reset_index(level=["where"], inplace=True)
        new_df.columns = new_df.columns.to_flat_index()
        new_df.columns = [(column[0] + column[1] + column[2]).replace("-", "_").lower() for column in new_df.columns]
        new_df = new_df.replace(to_replace=":", value=0)

        data = [pd.to_numeric(new_df[s], errors="ignore") for s in new_df.columns]
        new_df = pd.concat(data, axis=1, keys=[s.name for s in data])

        return new_df

    def cluster_countries(self, df: DataFrame) -> DataFrame:
        from sklearn.cluster import KMeans
        import numpy as np

        X = df.values
        X = [np.delete(x, 0) for x in X]
        # TODO: I decided to go with 4 clusters since then there is at least 3 countries in each when using GDP.
        # Must be thought through.
        kmeans = KMeans(n_clusters=4, random_state=0).fit(X)
        df["cluster"] = kmeans.labels_
        df = df[["where", "cluster"]]

        return df
