import xml.etree.ElementTree as ET
from dateutil import parser
import pandas as pd


def parse_duration(duration_str):
    duration_str = duration_str.replace("PT", "")
    t = [0, 0, 0]
    if "H" in duration_str:
        h_part = duration_str.split("H")
        t[0] = float(h_part[0])
        duration_str = h_part[1]
    if "M" in duration_str:
        m_part = duration_str.split("M")
        t[1] = float(m_part[0])
        duration_str = m_part[1]
    if "S" in duration_str:
        s_part = duration_str.split("S")
        t[2] = float(s_part[0])
    return 3600 * t[0] + 60 * t[1] + t[2]


class XmlFile:
    def __init__(self, filepath, polymeasure):
        self.filepath = filepath
        self.name = filepath.split("/")[-1].split(".")[0]
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()
        (
            self.section_names,
            self.start_datetimes,
            self.end_datetimes,
            self.parameters,
        ) = self.get_sections()
        modes = [p["Mode"] for p in self.parameters]
        self.method_dict = dict(zip(self.section_names, modes))
        self.df = self.extract_measurement_data()
        self.df["file_time_start"] = pd.to_datetime(
            self.df["file_time_str_start"], utc=True
        )
        if polymeasure:
            self.df["relative time [s]"] = self.df.data_elem_time_str_start.apply(
                parse_duration
            )
            self.df["absolute time"] = self.df["file_time_start"] + pd.to_timedelta(
                self.df["relative time [s]"], unit="s"
            )

    def get_sections(self):
        names = []
        starts = []
        ends = []
        pars = []
        for s in self.root.findall(".//Section"):
            name = s.get("Name")
            start = parser.parse(s.get("Time_Start"))
            end = parser.parse(s.get("Time_End"))
            names.append(name)
            starts.append(start)
            ends.append(end)
            pars.append(self.get_parameters(s))
        return names, starts, ends, pars

    def get_parameters(self, section):
        p = {}
        for param in section.findall("Parameters")[0]:
            p.update({param.get("Name"): param.get("Value")})
        return p

    def extract_measurement_data(self):
        frames = []
        for section in self.root.findall(".//Section"):
            section_name = section.get("Name")
            section_start_str = section.get("Time_Start")
            section_end_str = section.get("Time_End")
            start_dt = parser.parse(section_start_str)
            end_dt = parser.parse(section_end_str)
            for data_elem in section.findall("Data"):
                if data_elem is not None:
                    df = pd.DataFrame.from_records(
                        self.eval_data_element(
                            data_elem, section_name, section_start_str
                        )
                    )
                    if len(df) > 1:
                        total_s = (end_dt - start_dt).total_seconds()
                        df["time_interpolated"] = [
                            start_dt
                            + pd.Timedelta(seconds=(total_s * i / (len(df) - 1)))
                            for i in range(len(df))
                        ]
                    else:
                        df["time_interpolated"] = start_dt
                    frames.append(df)
        return pd.concat(frames)

    def eval_data_element(self, data_elem, section_name, section_start_str):
        rows = []
        data_elem_start_str = data_elem.get("Time_Start")
        cycle = data_elem.get("Cycle")
        for w in data_elem.findall("Well"):
            pos = w.get("Pos")
            row = "".join(x for x in pos if not x.isdigit())
            col = "".join(x for x in pos if x.isdigit())
            s = float(w.find("Single").text)
            rows.append(
                {
                    "well": pos,
                    "row": row,
                    "column": int(col),
                    "method_label": section_name,
                    "method": self.method_dict[section_name],
                    "signal": s,
                    "file_name": self.name,
                    "data_elem_time_str_start": data_elem_start_str,
                    "data_elem_time_start": (
                        parse_duration(data_elem_start_str)
                        if data_elem_start_str
                        else None
                    ),
                    "file_time_str_start": section_start_str,
                    "cycle": cycle,
                }
            )
        return rows
