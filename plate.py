import os
import numpy as np
import pandas as pd
from icecream import ic
from .xlsxfile import XlsxFile
from .xmlfile import XmlFile
from .plate_setup import Setup
from .well import Well


class Plate:
    """
    This class facilitates the reading and processing of data from microtiter plate reader files.

    Attributes:
        path (str): The directory path where files are located.
        block_labels (list of str): Labels used to identify blocks of data within the files.
        gdc_file (bool): Flag indicating the use of GDC file format.
        datetime_format (str): The format for parsing dates and times in the files.
        xml_files (list): Accumulator for discovered XML files matching criteria.
        xlsx_files (list): Accumulator for discovered XLSX files matching criteria.
        setup (Setup): An instance of the Setup class containing experimental setup information.
        file_summary (pd.DataFrame): A summary of the data extracted from the files.
        data (pd.DataFrame): The merged and processed data ready for analysis.
        identifier (str): An identifier used to match files relevant to the experiment.
        filetype (str): The file extension (.xml or .xlsx) to filter relevant files.

    Methods:
        load_xml: Loads and processes XML files based on the class attributes.
        load_xlsx(polymeasure): Loads and processes XLSX files, with an option for polymetric measurements.
        add_setup(filepath): Adds experimental setup information from a specified file.
        merge_setup_and_data: Merges setup information with the data extracted from plate reader files.
        summarize_files(files): Summarizes the data from multiple files into a single DataFrame.
        assign_wells: Assigns wells for analysis based on control and experimental data.
        get_reference_wells: Identifies reference wells for normalization purposes.
        assign_reference_wells: Assigns reference wells to experimental wells for normalization.
    """

    def __init__(
        self,
        identifier: str,
        filetype: str,
        path="./",
        datetime_format="%d.%m.%Y %H:%M:%S",
        block_labels=["Cycle Nr."],
        gdc_file=False,
        polymeasure=False,
        plate_name=None,
    ):
        self.path = path
        self.block_labels = block_labels
        self.gdc_file = gdc_file
        self.datetime_format = datetime_format
        self.xml_files = []
        self.xlsx_files = []
        self.setup = None
        self.file_summary = pd.DataFrame()
        self.data = pd.DataFrame()
        self.identifier = identifier
        self.filetype = filetype
        if not plate_name:
            self.name = os.path.basename(os.getcwd())
        else:
            self.name = plate_name
        if filetype == ".xml":
            self.load_xml(polymeasure)
        else:
            self.load_xlsx(polymeasure)

    def load_xml(self, polymeasure):
        self.xml_files = []
        for root, _, files in os.walk(self.path):
            for file in files:
                if (
                    file.endswith(".xml")
                    and ("$" not in file)
                    and ("setup" not in file)
                    and (self.identifier in file)
                ):
                    filepath = os.path.join(root, file)
                    self.xml_files.append(XmlFile(filepath, polymeasure))

        self.summarize_files(self.xml_files)

    def load_xlsx(self, polymeasure):
        self.xlsx_files = []
        for root, _, files in os.walk(self.path):
            for file in files:
                if (
                    file.endswith(".xlsx")
                    and ("$" not in file)
                    and ("setup" not in file)
                    and (self.identifier in file)
                ):
                    filepath = os.path.join(root, file)
                    ic(polymeasure)
                    self.xlsx_files.append(
                        XlsxFile(
                            filepath,
                            datetime_format=self.datetime_format,
                            block_labels=self.block_labels,
                            gdc_file=self.gdc_file,
                            polymeasure=polymeasure,
                        )
                    )
        self.summarize_files(self.xlsx_files)

    def add_setup(self, filepath="setup.xlsx"):
        self.setup = Setup(filepath)
        self.merge_setup_and_data()

    def merge_setup_and_data(self):
        if not self.setup:
            raise Exception("load setup first")
        if self.file_summary.empty:
            raise Exception("load files first")

        self.data = self.setup.map_to_input_df(self.file_summary)

    def summarize_files(self, files):
        summary = []
        for file in files:
            print(file.name)
            df = file.df.copy()
            df["file_name"] = file.name
            summary.append(df)
        summary = pd.concat(summary)
        summary["identifier"] = self.identifier
        summary.signal = np.maximum(summary.signal, 0)
        self.file_summary = summary

    def assign_wells(
        self,
        od_label=None,
        lum_label=None,
        src="data",
        features=["concentration", "antibiotic"],
        label_col="method",
        od_cut_off=0.1,
    ):
        df = self.__dict__[src]
        self.well = {}
        for well in df.well.unique():
            print(well)
            w = Well(
                df,
                well,
                od_label=od_label,
                lum_label=lum_label,
                label_col=label_col,
                od_cut_off=od_cut_off,
            )
            for feature in features:
                w.fetch_feature(feature)
            self.well.update({well: w})
        if lum_label:
            self.get_reference_wells()
            if not self.reference_wells.empty:
                self.assign_reference_wells()

    def get_reference_wells(self, type_col="control", data_name="data"):
        df = self.__dict__[data_name]
        self.type_col = type_col
        self.neg_controls = df[df[type_col] == "negative"].well.unique()
        self.reference_wells = [
            {"well": w, "contamination": self.well[w].od_contamination}
            for w in self.neg_controls
        ]
        self.reference_wells = pd.DataFrame().from_records(self.reference_wells)
        self.reference_wells["obj"] = self.reference_wells.well.apply(
            lambda x: self.well[x]
        )

    def assign_reference_wells(self, norm_method="closest"):
        assays = self.data[self.data[self.type_col] == "assay"].well.unique()
        self.assay_wells = [self.well[i] for i in assays]
        for well in self.assay_wells:
            well.assign_reference_wells(self.reference_wells)
            well.norm_lum_wells(method=norm_method)

        positives = self.data[self.data[self.type_col] == "positive"].well.unique()
        self.positives = [self.well[i] for i in positives]
        for well in self.positives:
            well.assign_reference_wells(self.reference_wells)
            well.norm_lum_wells(method=norm_method)
