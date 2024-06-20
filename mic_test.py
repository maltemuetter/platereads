from matplotlib import pyplot as plt
import math
import pandas as pd
import numpy as np
import os


class MicTestMulti:
    def __init__(self, plates: list, control_col="control"):
        self.plates = plates
        self.control_col = control_col
        self.data = []
        self.wells = []
        self.summarize_plates()

        self.antibiotics = self.data["antibiotic"].unique()
        self.get_mics()

    def summarize_plates(self):
        for plate in self.plates:
            sub = plate.data[
                (plate.data[self.control_col] == "assay")
                | (plate.data[self.control_col] == "pos")
            ]
            self.wells += [plate.well[name] for name in sub.well.unique()]
            self.data.append(plate.data[(plate.data[self.control_col] == "assay")])
        self.data = pd.concat(self.data)

    def get_mics(self):
        self.mic_tests = {}
        mic = []
        for antibiotic in self.antibiotics:
            test = MicTest(self.wells, antibiotic)
            self.mic_tests.update({antibiotic: test})
            mic.append(test.results())
        self.mic = pd.DataFrame().from_records(mic)

    def save(self, suffix="", path="", prefix=""):
        self.mic.to_excel(os.path.join(path, prefix + "mic_results" + suffix + ".xlsx"))

    def plot_inhibition(self, figsize=(6, 3), save_path=None, name="inhibition.png"):
        h, w = math.ceil(len(self.antibiotics) / 2), 2
        figsize = (figsize[0] * w, figsize[1] * h)
        fig, axs = plt.subplots(h, w, figsize=figsize)

        i, j = 0, 0
        for antibiotic in self.antibiotics:
            self.mic_tests[antibiotic].plot_inhibition(ax=axs[j, i])
            if i == 1:
                i = 0
                j += 1
            else:
                i = 1
        fig.tight_layout()
        if save_path:
            plt.savefig(os.path.join(save_path, name), dpi=300)


class MicTest:
    def __init__(self, wells: list, antibiotic_name):
        self.wells = wells
        self.name = antibiotic_name
        self.positive = self.eval_pos_wells()
        self.positive_median = self.positive["od_end"].median()
        self.indicator_df = self.eval_assay_wells()
        self.inhibition_df, self.mic = self.calc_mic()

    def eval_pos_wells(self):
        positive = []
        for well in self.wells:
            if well.well_type == "pos":
                positive.append(
                    {
                        "well": well.name,
                        "od_end": well.od_end,
                        "type": well.well_type,
                    }
                )
        return pd.DataFrame().from_records(positive)

    def eval_assay_wells(self):
        indicator_df = []
        for well in self.wells:
            if well.antibiotic == self.name:
                well.get_od_growth(cut_off=0.1 * self.positive_median)
                indicator_df.append(
                    {
                        "well": well.name,
                        "growth": well.od_growth,
                        "concentration": float(well.concentration),
                        "type": well.well_type,
                        "od_end": well.od_end,
                    }
                )

        return pd.DataFrame().from_records(indicator_df)

    def calc_mic(self):
        inhibition = (
            self.indicator_df[["concentration", "growth"]]
            .groupby(["concentration"])
            .mean()
            .reset_index()
        )
        mic = inhibition[inhibition.growth <= 0.5].concentration.min()
        return inhibition, mic

    def plot_inhibition(self, xscale="log", ax=None):
        if ax is None:
            _, ax = plt.subplots()
        ax.scatter(
            self.inhibition_df["concentration"],
            self.inhibition_df["growth"],
            color="blue",
            label="Observations",
        )
        ax.axvline(x=self.mic, color="green", linestyle="--", label="MIC")
        ax.axhline(y=0.5, color="gray", linestyle="--", label="50% Threshold")
        ax.set_xlabel("Concentration (ug/ml)")
        ax.set_ylabel("Fraction of Wells that Grew")
        ax.set_title(
            f"f(growth) vs concentration for {self.name} (mic = {self.mic} [$\mu g/ml$])"
        )
        ax.legend()
        ax.set_xscale(xscale)
        return ax

    def results(self):
        return {"antibiotic": self.name, "mic": self.mic}
