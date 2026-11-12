"""Interfaces shared by future data source implementations."""

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class DataSource(ABC):
    """Read one named dataset into a validated dataframe."""

    @abstractmethod
    def read(self, path: Path) -> pd.DataFrame:
        raise NotImplementedError

