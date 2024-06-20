import xml.etree.ElementTree as ET
from dateutil import parser
import pandas as pd
from dateutil.relativedelta import relativedelta


def parse_duration(duration_str):
    duration_parts = duration_str.split("T")[-1].split("H")[-1]
    time = [0, 0, 0]
    for i, t in enumerate(["H", "M", "S"]):
        duration_parts = duration_parts.split(t)
        if len(duration_parts) > 1:
            time[i] = float(duration_parts[0])
        duration_parts = duration_parts[-1]
    return relativedelta(hours=time[0], minutes=time[1], seconds=time[2])


class XmlFile:
    def __init__(self, filepath, polymeasure):
        self.filepath = filepath
        self.name = filepath.split("/")[-1].split(".")[0]
        self.tree = ET.parse(self.filepath)
        self.root = self.tree.getroot()

        (
            self.section_names,
            self.start_datetimes,
            self.end_datetimes,
        ) = self.get_sections()

        if polymeasure:
            self.df = self.extract_measurement_data_poly()
        else:
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

    def extract_measurement_data_poly(self):
        data = []
        for section in self.root.findall(".//Section"):
            section_name = section.get("Name")
            section_start_str = section.get("Time_Start")
            section_start = parser.parse(section_start_str)
            data_elements = section.findall("Data")
            for data_elem in data_elements:
                data_start_duration = parse_duration(data_elem.get("Time_Start"))
                data_start_time = section_start + data_start_duration
                data.extend(
                    self.eval_data_element(data_elem, section_name, data_start_time)
                )
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
                "cycle",
            ],
        )

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

    def eval_data_element(self, data_elem, section_name, data_start_time):
        data = []
        cycle = data_elem.get("Cycle")  # Get the cycle number
        for well in data_elem.findall("Well"):
            well_pos = well.get("Pos")
            row = "".join(filter(lambda x: not x.isdigit(), well_pos))
            col = "".join(filter(lambda x: x.isdigit(), well_pos))
            signal = float(
                well.find("Single").text
            )  # Ensure to retrieve text and convert to float
            df_row = {
                "well": well_pos,
                "row": row,
                "column": int(col),
                "method": section_name,
                "signal": signal,
                "file_name": self.name,
                "time_start": data_start_time,
                "cycle": cycle,
            }
            data.append(df_row)
        return data
