import xml.etree.ElementTree as ET
from dateutil import parser
import pandas as pd


class XmlFile:
    def __init__(self, filepath):
        self.filepath = filepath
        self.name = filepath.split("/")[-1].split(".")[0]
        self.tree = ET.parse(self.filepath)
        self.root = self.tree.getroot()

        (
            self.section_names,
            self.start_datetimes,
            self.end_datetimes,
        ) = self.get_sections()
        self.df = self.extract_measurement_data()

    def get_sections(self):
        section_names = []
        start_datetimes = []
        end_datetimes = []

        for section in self.root.findall(".//Section"):
            name = section.get("Name")
            start_time_str = section.get("Time_Start")
            end_time_str = section.get("Time_End")
            start_datetime = parser.parse(start_time_str)
            end_datetime = parser.parse(end_time_str)

            section_names.append(name)
            start_datetimes.append(start_datetime)
            end_datetimes.append(end_datetime)

        return section_names, start_datetimes, end_datetimes

    def extract_measurement_data(self):
        data = []
        for i, section_name in enumerate(self.section_names):
            section_start = self.start_datetimes[i]
            section_end = self.end_datetimes[i]
            section = self.root.find(f".//Section[@Name='{section_name}']")
            if section is not None:
                data_elem = section.find("Data")
                if data_elem is not None:
                    for well in data_elem.findall("Well"):
                        well_pos = well.get("Pos")
                        row = "".join(filter(lambda x: not x.isdigit(), well_pos))
                        col = "".join(filter(lambda x: x.isdigit(), well_pos))
                        df_row = {
                            "well": well_pos,
                            "row": row,
                            "column": int(col),
                            "method": section_name,
                            "signal": float(well.findtext("Single")),
                            "file_name": self.name,
                            "time_start": section_start,
                            "time_end": section_end,
                        }
                        data.append(df_row)
            else:
                raise Exception(f"Could not find section: {section_name}")

        return pd.DataFrame(
            data,
            columns=[
                "well",
                "row",
                "column",
                "method",
                "signal",
                "file_name",
                "time_start",
                "time_end",
            ],
        )
