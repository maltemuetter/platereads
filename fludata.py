import pandas as pd


class FluorescenceData:
    def __init__(self, data, control_col="control"):
        self.input_data = data
        self.control = self.input_data[control_col]
        if self.control.any() == False:
            raise Exception("No control data")
        self.signal_data = self.input_data[self.control == False]
        self.control_data = self.input_data[self.control == True]
        self.average_noise()

    def average_noise(self):
        avg_control_signal = (
            self.control_data.groupby("time")["signal"].mean().reset_index()
        )
        avg_control_signal.rename(columns={"signal": "noise"}, inplace=True)
        self.signal_data = pd.merge(
            self.signal_data, avg_control_signal, on="time", how="left"
        )
        self.norm_signal()

    def norm_signal(self):
        self.signal_data["flu"] = self.signal_data.signal - self.signal_data.noise
        self.signal_data["signal_to_noise"] = round(
            self.signal_data.signal / self.signal_data.noise, 2
        )
