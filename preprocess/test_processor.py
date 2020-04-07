from pandas import DataFrame

from generic_eurostat_preprocessor import GenericEuroStatPreprocessor


class TestPreprocessor(GenericEuroStatPreprocessor):
    def _flatten(self, df: DataFrame) -> DataFrame:
        return df
