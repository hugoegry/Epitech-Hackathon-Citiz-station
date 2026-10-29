import os
from pathlib import Path
import pandas as pd

_TABLES = Path(os.environ.get("SHIM_TABLES", Path(__file__).resolve().parents[1] / "data/lakehouse/Tables"))


class _Writer:
    def __init__(self, df):
        self.df = df

    def mode(self, *_):
        return self

    def option(self, *_):
        return self

    def saveAsTable(self, name):
        _TABLES.mkdir(parents=True, exist_ok=True)
        self.df.to_parquet(_TABLES / f"{name}.parquet", index=False)


class _Frame:
    def __init__(self, df):
        self.df = df
        self.write = _Writer(df)

    def toPandas(self):
        return self.df.copy()


class _Reader:
    def table(self, name):
        return _Frame(pd.read_parquet(_TABLES / f"{name}.parquet"))


class _Spark:
    read = _Reader()

    def createDataFrame(self, df):
        return _Frame(df.reset_index(drop=True))


spark = _Spark()
