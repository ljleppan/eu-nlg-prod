from abc import ABC, abstractmethod
from math import sqrt
from typing import List

import pandas as pd
from pandas import DataFrame, Series


class GenericEuroStatPreprocessor(ABC):
    def process(self, df: DataFrame) -> DataFrame:
        df = self._flatten(df)

        id_columns = ["timestamp", "timestamp_type", "location", "location_type", "agent", "agent_type"]
        base_columns: List[str] = [str(column) for column in df.columns if column not in id_columns]

        # Compare columns to EU average
        df = self._compare_to_eu(df, base_columns)

        # Compare columns to USA average
        df = self._compare_to_us(df, base_columns)

        # Rank value columns
        df = self._rank_df(df, base_columns)

        # Remove EU and EEA as their own "countries"
        normal_countries = [code for code in df["location"].unique() if len(code) == 2 and code not in ["EU", "EA"]]
        df = df[df["location"].isin(normal_countries)]
        df.reset_index(drop=True, inplace=True)

        # Add outlierness to data
        outlierness_columns = [column for column in df.columns if column not in id_columns]
        df = self._add_outlierness_to_data(df, outlierness_columns, [])

        return df

    @abstractmethod
    def _flatten(self, df: DataFrame) -> DataFrame:
        pass

    def _comp_to_loc(
        self, df: DataFrame, compare_columns: List[str], compare_location: str, col_format: str
    ) -> DataFrame:
        """
        Add comparison columns that compare each location to a denoted comparison location in the same year.

        This gets complicated to explain so buckle up, chief.

        Basically, let's assume we are given a DataFrame like this as the param `df`:
        ```
          location  timestamp    a    b
        0       EU       2020  NaN  NaN
        1       FI       2020  0.0  1.0
        2       FI       2019  1.0  2.0
        3       SV       2020 -1.0  0.0
        4       SV       2019  0.0  1.0
        5       EU       2019  1.0  1.0
        ```

        Then, assuming further that `compare_columns = ["a", "b"]` and `compare_location = "EU"` and
        `col_format = "{}_comp_eu"`, what we end up getting out looks like this:
        ```
          location  timestamp    a    b  a_comp_eu  b_comp_eu
        0       EU       2020  NaN  NaN        NaN        NaN
        1       FI       2020  0.0  1.0        NaN        NaN
        2       FI       2019  1.0  2.0        0.0        1.0
        3       SV       2020 -1.0  0.0        NaN        NaN
        4       SV       2019  0.0  1.0       -1.0        0.0
        5       EU       2019  1.0  1.0        NaN        NaN
        ```

        The actual processing is done timestamp-by-timestamp, with each step producing certain rows of the X_comp_eu
        columns. These are finally concat'd together and then joined to initial table.
        """
        if compare_location not in df["location"].unique():
            return df

        comp_fragments = []
        for timestamp in df["timestamp"].unique():
            diff = (
                df[(df["timestamp"] == timestamp) & (df["location"] != compare_location)][compare_columns]
                - df[(df["timestamp"] == timestamp) & (df["location"] == compare_location)][
                    compare_columns
                ].values.squeeze()
            )
            diff.columns = [col_format.format(col) for col in diff]
            comp_fragments.append(diff)
        return df.join(pd.concat([*comp_fragments]))

    def _compare_to_us(self, df: DataFrame, compare_columns: List[str]) -> DataFrame:
        return self._comp_to_loc(df, compare_columns, "US", "{}:comp_us")

    def _compare_to_eu(self, df: DataFrame, compare_columns: List[str]) -> DataFrame:
        return self._comp_to_loc(df, compare_columns, "EU28", "{}:comp_eu")

    def _compare_to_similar(self, df: DataFrame, cluster_df: DataFrame, compare_columns: List[str]) -> DataFrame:

        df = df.merge(cluster_df, on="location")
        grouped_by_time_and_cluster = df.groupby(["timestamp", "cluster"])

        for col_name in compare_columns:
            compared_col_name = "{}:comp_similar".format(col_name)
            grouped = grouped_by_time_and_cluster[col_name]
            df[compared_col_name] = df[col_name] - grouped.transform("mean")

        df = df.drop("cluster", axis=1)

        return df

    def _rank_df(self, df: DataFrame, rank_columns: List[str]) -> DataFrame:
        grouped_time = df.groupby(["timestamp", "timestamp_type"])

        for col_name in rank_columns:
            ranked_col_name = "{}:rank".format(col_name)
            reverse_ranked_col_name = "{}_reverse".format(ranked_col_name)
            grouped = grouped_time[col_name]
            df[ranked_col_name] = grouped.rank(ascending=False, method="dense", na_option="keep")
            df[reverse_ranked_col_name] = grouped.rank(ascending=True, method="dense", na_option="keep")
        return df

    def _add_outlierness_to_data(
        self, df: DataFrame, outlierness_columns: List[str], id_columns: List[str]
    ) -> DataFrame:

        const_max_out = 2

        def outlierness(
            val: float, count: int, min_val: float, q1: float, q2: float, q3: float, max_val: float
        ) -> float:
            size_weight = sqrt(1 / sqrt(count))
            if q1 == q3:
                if val == q2:
                    return 0.5 * size_weight
                if val > q3:
                    return 0.5 + (const_max_out - 0.5) * (val - q2) / (max_val - q2) * size_weight
                if val < q1:
                    return 0.5 + (const_max_out - 0.5) * (q2 - val) / (q2 - min_val) * size_weight
            else:
                if (q1 < val) and (val < q3):
                    return (
                        min(
                            outlierness(q1, count, min_val, q1, q2, q3, max_val),
                            outlierness(q3, count, min_val, q1, q2, q3, max_val),
                        )
                        * size_weight
                    )
                return abs(val - q2) / (q3 - q1) * size_weight

        def group_outlierness(grp: Series) -> DataFrame:
            quantiles = grp.quantile([0.25, 0.5, 0.75])
            min_val = grp.min()
            max_val = grp.max()
            q1 = quantiles[0.25]
            q2 = quantiles[0.5]
            q3 = quantiles[0.75]
            return grp.apply(outlierness, args=(grp.size, min_val, q1, q2, q3, max_val))

        rank_columns = [col for col in df.columns.values if "_rank" in col]
        numeric_columns = outlierness_columns

        for column_name in numeric_columns:
            outlierness_ct_column_name = "{}:grouped_by_time:outlierness".format(column_name)
            df[outlierness_ct_column_name] = df.groupby(["timestamp", "timestamp_type"])[column_name].apply(
                group_outlierness
            )

        # Last outlierness:
        #   fixed place and time (which crime was committed most, second most, ... in specific place at specific time)
        raw_numbers_columns = [x for x in numeric_columns if "normalized" not in x]
        normalized_columns = [x for x in numeric_columns if "normalized" in x]

        raw_outlierness = df[raw_numbers_columns]
        norm_outlierness = df[normalized_columns]

        raw_outlierness.reset_index(drop=True, inplace=True)
        norm_outlierness.reset_index(drop=True, inplace=True)

        for i in range(len(raw_outlierness)):
            raw_outlierness.iloc[i] = group_outlierness(raw_outlierness.iloc[i])
            norm_outlierness.iloc[i] = group_outlierness(norm_outlierness.iloc[i])

        raw_outlierness = raw_outlierness.add_suffix(":grouped_by_time_place:outlierness")
        norm_outlierness = norm_outlierness.add_suffix(":grouped_by_time_place:outlierness")

        df = pd.concat([df, raw_outlierness], axis=1)
        df = pd.concat([df, norm_outlierness], axis=1)

        for rank_column_name in rank_columns:
            normal_column_name = rank_column_name.replace("_reverse", "").replace("_rank", "")
            outlierness_rank_column_name = "{}:outlierness".format(rank_column_name)
            outlierness_normal_column_name = "{}:outlierness".format(normal_column_name)
            df[outlierness_rank_column_name] = df[outlierness_normal_column_name]

        non_numeric_columns = id_columns
        for column_name in non_numeric_columns:
            # log.debug("Generating outlyingness values for column {}".format(column_name))
            outlierness_column_name = "{}:outlierness".format(column_name)
            df[outlierness_column_name] = 0.5

        return df
