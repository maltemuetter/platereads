from matplotlib import pyplot as plt
import seaborn as sns
import math
import pandas as pd
import numpy as np
import math 



class MicTestMulti:
    def __init__(self, plate, antibiotic_col = "antibiotic", value_col = "od_norm", concentration_col = "concentration", t_col = "time", control_col = "control", cut_off = .1):
        self.plate = plate
        self.data = plate.data[plate.data[control_col] == "assay"].copy()
        self.antibiotics = self.data[antibiotic_col].unique()
        self.value_col = value_col
        self.antibiotic_col = antibiotic_col
        self.concentration_col = concentration_col
        self.t = self.data[t_col].unique()
        self.t_max = self.data[t_col].max()
        self.t_col = t_col
        self.cut_off = cut_off
        self.get_mics()

    def get_mics(self):
        self.mic_tests = {}
        mic = []
        for antibiotic in self.antibiotics:
            test = MicTest(self.plate, antibiotic, antibiotic_col = "antibiotic", value_col = "od_norm", concentration_col = "concentration", t_col = "time", cut_off = .1)
            self.mic_tests.update( {
                antibiotic: test})
            mic.append(test.results())    
        self.mic = pd.DataFrame().from_records(mic)

    def save(self, prefix = "", suffix = ""):
        self.mic.to_csv(prefix + "mic_results" + suffix + ".csv")

    def plot(self, figsize = (6, 3)):
        h, w = math.ceil(len(self.antibiotics)/2), 2
        figsize = (figsize[0] * w, figsize[1] * h)
        fig, axs = plt.subplots(h, w, figsize = figsize)

        i, j = 0, 0
        for antibiotic in self.antibiotics:
            self.mic_tests[antibiotic].plot(ax = axs[j, i], xscale = "log")
            if i == 1:
                i = 0
                j += 1
            else: 
                i = 1
        fig.tight_layout()


class MicTest:
    def __init__(self, plate, antibiotic, value_col="od", antibiotic_col="antibiotic", concentration_col="concentration", cut_off=0.1, t_col="time"):
        self.data = plate.data[plate.data[antibiotic_col] == antibiotic]
        self.antibiotic = antibiotic
        self.cut_off = cut_off
        self.t_col = t_col
        self.value_col = value_col
        self.concentration_col = concentration_col
        self.t = self.data[t_col].unique()
        self.t_max = self.data[t_col].max()

        self.wells = []
        self.indicator_df = []
        for w in self.data.well.unique():
            well = plate.well[w]
            self.wells.append(well)
            self.indicator_df.append({
                "well": well.name,
                "growth": well.od_growth,
                "concentration": float(well.concentration)
            })
        self.indicator_df = pd.DataFrame().from_records(self.indicator_df)
        self.get_mic()

    def get_mic(self, n = 1000):
        self.concentrations = self.indicator_df[self.concentration_col].values
        self.observed_growth = self.indicator_df['growth'].values.astype(int)
        self.concentration_range = np.logspace(np.log(self.concentrations.min()), np.log(self.concentrations.max()), n)
        if not self.observed_growth.any():
            self.ci_lower = self.ci_upper = self.mic_estimate = "< " + str(np.min(self.concentrations))
        elif self.observed_growth.all(): 
            self.ci_lower = self.ci_upper = self.mic_estimate = "> " + str(np.max(self.concentrations))
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
        self.sses = np.array([self.objective_function(m, self.concentrations, self.observed_growth) for m in self.concentration_range])
        ci_indices = np.where(self.sses == np.min(self.sses))[0]
        self.ci_lower = self.concentration_range[ci_indices[0]]
        self.ci_upper = self.concentration_range[ci_indices[-1]]   
        self.mic_estimate = (self.ci_lower + self.ci_upper) / 2
        

    def plot(self, xscale="linear", ax=None):
        if ax is None:
            _, ax = plt.subplots()
        ax.scatter(self.indicator_df[self.concentration_col], self.indicator_df['growth'], color='blue', label='Observations')
        if not type(self.mic_estimate) == str:
            step_min = self.step_function(self.ci_lower, self.concentration_range)
            step_mean = self.step_function(self.mic_estimate, self.concentration_range)
            step_max = self.step_function(self.ci_upper, self.concentration_range)
            ax.fill_between(self.concentration_range, step_min, step_max, color='red', alpha=0.2, label='best guess range')
            ax.plot(self.concentration_range, step_mean, 'r--', label=f'Estimated MIC: {self.mic_estimate:.2f} ug/ml')        
        ax.set_xlabel('Concentration (ug/ml)')
        ax.set_ylabel('Growth')
        ax.set_title(f'Growth vs Concentration for {self.antibiotic}')
        ax.legend()
        ax.set_xscale(xscale)

        return ax
    
    def results(self):
        return {
            "antibiotic":self.antibiotic,
            "mic_best_middle": self.mic_estimate,
            "mic_best_lower" : self.ci_lower,
            "mic_best_upper" : self.ci_upper
        }
