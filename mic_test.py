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

    def plot(self, figsize=(6, 3)):
        h, w = math.ceil(len(self.antibiotics) / 2), 2
        figsize = (figsize[0] * w, figsize[1] * h)
        fig, axs = plt.subplots(h, w, figsize=figsize)

        i, j = 0, 0
        for antibiotic in self.antibiotics:
            self.mic_tests[antibiotic].plot(ax=axs[j, i], xscale="log")
            if i == 1:
                i = 0
                j += 1
            else:
                i = 1
        fig.tight_layout()


class MicTest:
    def __init__(self, wells: list, antibiotic_name):
        self.wells = wells
        self.name = antibiotic_name
        self.positive = self.eval_pos_wells()
        self.positive_median = self.positive["od_end"].median()
        self.indicator_df = self.eval_assay_wells()
        self.get_mic()

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
                    }
                )

        return pd.DataFrame().from_records(indicator_df)

    def get_mic(self, n=1000):
        self.concentrations = self.indicator_df["concentration"].values
        self.observed_growth = self.indicator_df["growth"].values.astype(int)
        self.concentration_range = np.logspace(
            np.log(self.concentrations.min() + 10**-6) + 10**-6,
            np.log(self.concentrations.max()),
            n,
        )
        if not self.observed_growth.any():
            self.ci_lower = self.ci_upper = self.mic_estimate = "< " + str(
                np.min(self.concentrations)
            )
        elif self.observed_growth.all():
            self.ci_lower = self.ci_upper = self.mic_estimate = "> " + str(
                np.max(self.concentrations)
            )
        else:
            self.estimate_mic_and_ci()

    # Define the step function
    @staticmethod
    def step_function(m, concentration):
        return concentration < m

    # Objective function to minimize
    @staticmethod
    def objective_function(m, concentrations, observed_growth):
        predictions = MicTest.step_function(m, concentrations)
        sse = np.sum((observed_growth - predictions) ** 2)
        return sse

    def estimate_mic_and_ci(self):
        self.sses = np.array(
            [
                self.objective_function(m, self.concentrations, self.observed_growth)
                for m in self.concentration_range
            ]
        )
        ci_indices = np.where(self.sses == np.min(self.sses))[0]
        self.ci_lower = self.concentration_range[ci_indices[0]]
        self.ci_upper = self.concentration_range[ci_indices[-1]]
        self.mic_estimate = (self.ci_lower + self.ci_upper) / 2

    def plot(self, xscale="log", ax=None):
        if ax is None:
            _, ax = plt.subplots()
        ax.scatter(
            self.indicator_df["concentration"],
            self.indicator_df["growth"],
            color="blue",
            label="Observations",
        )
        if not type(self.mic_estimate) == str:
            step_min = self.step_function(self.ci_lower, self.concentration_range)
            step_mean = self.step_function(self.mic_estimate, self.concentration_range)
            step_max = self.step_function(self.ci_upper, self.concentration_range)
            ax.fill_between(
                self.concentration_range,
                step_min,
                step_max,
                color="red",
                alpha=0.2,
                label="best guess range",
            )
            ax.plot(
                self.concentration_range,
                step_mean,
                "r--",
                label=f"Estimated MIC: {self.mic_estimate:.2f} ug/ml",
            )
        ax.set_xlabel("Concentration (ug/ml)")
        ax.set_ylabel("Growth")
        ax.set_title(f"Growth vs Concentration for {self.name}")
        ax.legend()
        ax.set_xscale(xscale)

        return ax

    def results(self):
        return {
            "antibiotic": self.name,
            "mic_best_middle": self.mic_estimate,
            "mic_best_lower": self.ci_lower,
            "mic_best_upper": self.ci_upper,
        }
