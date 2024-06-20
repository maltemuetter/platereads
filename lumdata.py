import math
import pandas as pd


class LumData:
    def __init__(self, data, control_col="control"):
        self.input_data = data
        self.control = self.input_data[control_col]
        if not self.control.any():
            raise Exception("No control data")
        self.signal_data = self.input_data[self.control == False].copy()
        self.control_data = self.input_data[self.control == True].copy()

    def average_noise(self):
        avg_control_signal = (
            self.control_data.groupby("time")["signal"].mean().reset_index()
        )
        avg_control_signal.rename(columns={"signal": "noise"}, inplace=True)
        self.signal_data = pd.merge(
            self.signal_data, avg_control_signal, on="time", how="left"
        ).copy()
        self.norm_signal()

    def closest_control_noise(self):
        T = self.input_data.time.unique()
        wells = self.input_data.well.unique()
        for index, row in self.signal_data.iterrows():
            time = row["time"]
            well = (row["row"], row["column"])
            closest_control_wells = self.find_closest_controls(well, time)
            closest_control_signals = self.control_data.loc[
                (self.control_data["well"].isin(closest_control_wells))
                & (self.control_data["time"] == time),
                "signal",
            ]
            avg_closest_control_signal = closest_control_signals.mean()
            self.signal_data.loc[index, "noise"] = avg_closest_control_signal
        self.norm_signal()

    def find_closest_controls(self, well, time):
        def dist(well1, well2):
            i1, j1 = ord(well1[0]) - ord("A"), well1[1]
            i2, j2 = ord(well2[0]) - ord("A"), well2[1]
            return math.sqrt((i2 - i1) ** 2 + (j2 - j1) ** 2)

        control_wells = [
            (row["row"], row["column"])
            for _, row in self.control_data[
                self.control_data["time"] == time
            ].iterrows()
        ]

        min_dist = float("inf")
        closest_wells = []

        for control_well in control_wells:
            distance = dist(well, control_well)
            if distance < min_dist:
                min_dist = distance
                closest_wells = [control_well[0] + str(int(control_well[1]))]
            elif distance == min_dist:
                closest_wells.append(control_well[0] + str(int(control_well[1])))

        return closest_wells

    def norm_signal(self):
        self.signal_data["rlu"] = self.signal_data["signal"] - self.signal_data["noise"]
        self.signal_data["signal_to_noise"] = round(
            self.signal_data["signal"] / self.signal_data["noise"], 2
        )
