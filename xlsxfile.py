import xml.etree.ElementTree as ET
from dateutil import parser
import pandas as pd
import os
from datetime import datetime, timedelta
import pandas as pd
from icecream import ic


class XlsxFile:
    def __init__(
        self,
        filepath,
        datetime_format="%d.%m.%Y %H:%M:%S",
        block_labels=["Cycle Nr."],
        gdc_file=False,
        polymeasure=False,
    ):
        filename = filepath.split("/")[-1]
        name = filename.split(".")[0]
        self.i = name[1:]
        self.block_labels = block_labels
        self.gdc_file = gdc_file
        self.name = name
        self.filepath = filepath
        self.datetime_format = datetime_format
        self.block_dict, self.block_names, self.blocks = self._load_blocks()
        self.start_time = self.get_time()
        self.kinetic = self._is_kinetic_measurement()
        self.polymeasure = polymeasure

        if self.kinetic:
            self._collect_kinetic_data()
            self.eval_kinetic_data()
        else:
            self.data_block_dict = self.get_data_blocks()
            self._make_non_kinetic_df()

    def get_time(self):
        matches = ["Start Time" in str(element) for element in self.raw_file.index]
        block = self.raw_file.loc[matches].dropna(axis=1)
        combined_str = block.iloc[0, 0]
        return datetime.strptime(combined_str, self.datetime_format)

    def _load_blocks(self):
        df = pd.read_excel(self.filepath, header=None)
        self.raw_file = df.copy().set_index(0)
        cut_points = df[df.iloc[:, 0].isna()].index.tolist()
        start_indices = [-1] + cut_points
        end_indices = cut_points + [len(df)]
        blocks = []
        block_names = []
        for start, end in zip(start_indices, end_indices):
            block = df.iloc[start + 1 : end]
            if not block.empty:
                block.columns = block.iloc[0]
                block = block.iloc[1:].set_index(block.columns[0])
                blocks.append(block)
                block_names.append(block.index.name)
        return dict(zip(block_names, blocks)), block_names, blocks

    def _is_kinetic_measurement(self):
        return "List of actions in this measurement script:" in self.block_dict.keys()

    def _collect_kinetic_data(self):
        self.kinetic_data = []
        for label in self.block_labels:
            block = self.block_dict[label]
            if block.index[0] == "Cycle Nr.":
                block = pd.DataFrame(block)
                block.columns = block.iloc[0]
                if self.polymeasure:
                    new_header = block.iloc[0]
                    block = block[1:]
                    block.columns = new_header
                else:
                    block = block[1:].reset_index(drop=True)
            self.kinetic_data.append(block)

    def eval_kinetic_data(self):
        summary = []
        for label, data in zip(self.block_labels, self.kinetic_data):
            if self.gdc_file:
                df = self._eval_gdc_data_block(data)
            else:
                df = self._eval_data_block(data)
            df["label"] = label
            summary.append(df)
        self.df = pd.concat(summary).dropna()

    def _eval_data_block(self, df):
        cycles = df.columns[df.columns.isnull() == False]
        data = []
        for cycle in cycles:
            for index, value in df[cycle].items():
                if index == "Time [s]":
                    time = self.start_time + pd.to_timedelta(value, unit="s")
                elif index == "Temp. [°C]":
                    temperature = value
                elif value != "nan":
                    well = index
                    row = "".join(filter(lambda x: not x.isdigit(), well))
                    column = "".join(filter(lambda x: x.isdigit(), well))
                    df_row = {
                        "row": row,
                        "column": int(column),
                        "well": well,
                        "datetime": time,
                        "temperature": temperature,
                        "signal": value,
                        "file_name": self.name,
                    }
                    data.append(df_row)

        block_df = pd.DataFrame(
            data, columns=["row", "column", "well", "datetime", "temperature", "signal"]
        )
        block_df.columns = block_df.columns.str.lower()
        return block_df

    def _eval_gdc_data_block(self, df):
        cycles = df.index
        data = []
        for cycle in cycles:
            for col, value in df.loc[cycle].items():
                if col == "Time [s]":
                    time = self.start_time + pd.to_timedelta(value, unit="s")
                elif col == "Temp. [°C]":
                    temperature = value
                else:
                    well = col
                    row = "".join(filter(lambda x: not x.isdigit(), well))
                    column = "".join(filter(lambda x: x.isdigit(), well))
                    df_row = {
                        "row": row,
                        "column": int(column),
                        "well": well,
                        "datetime": time,
                        "temperature": temperature,
                        "signal": value,
                        "file_name": self.name,
                    }
                    data.append(df_row)

        block_df = pd.DataFrame(
            data, columns=["row", "column", "well", "datetime", "temperature", "signal"]
        )
        block_df.columns = block_df.columns.str.lower()
        return block_df

    def get_data_blocks(self):
        indices = [i for i, name in enumerate(self.block_names) if name == "<>"]
        blocks = [self.blocks[i] for i in indices]
        names = [self.block_names[i - 1].split(": ")[1] for i in indices]
        return dict(zip(names, blocks))

    def _make_non_kinetic_df(self):
        self.data = self.block_dict["<>"]
        data = []
        for label, data_block in self.data_block_dict.items():
            non_nan_cols = data_block.columns[~data_block.isna().any()]
            for row in data_block.index:
                for col in non_nan_cols:
                    well = row + str(int(col))
                    df_row = {
                        "row": row,
                        "column": col,
                        "well": well,
                        "datetime": self.start_time,
                        "signal": data_block.loc[row, col],
                        "label": label,
                        "file_name": self.name,
                    }
                    data.append(df_row)
        self.df = pd.DataFrame(
            data,
            columns=[
                "row",
                "column",
                "well",
                "datetime",
                "signal",
                "label",
                "file_name",
            ],
        )
        self.df.columns = self.df.columns.str.lower()
