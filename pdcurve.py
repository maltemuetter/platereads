from matplotlib import pyplot as plt
import pandas as pd
import math
import numpy as np
from scipy.optimize import curve_fit

class PharmacoDynamicCurves:
    def __init__(self, plates:list):
        self.collect_wells(plates)
        self.antibiotics = self.df.antibiotic.unique()

    def collect_wells(self, plates):
        self.wells = []
        for i, plate in enumerate(plates):
            for name, well in plate.well.items():
                if well.well_type in ["assay", "positive"]:
                    entry = {"plate":i, "well":name, "antibiotic":well.antibiotic, "concentration":well.concentration, "obj":well, "well_type":well.well_type}
                    self.wells.append(entry)
        self.df = pd.DataFrame().from_records(self.wells)

    def create_pd_curves(self, window_size = 1, signal_noise_ratio = 2):
         self.curves = {}
         for antibiotic in self.antibiotics:
              if antibiotic != "None":
                print(antibiotic)
                curve = PharmacoDynamicCurve(self.df, antibiotic)
                curve.fit_rates(window_size=window_size, signal_noise_ratio=signal_noise_ratio)
                self.curves.update({antibiotic:curve})

    def fit_hill_curves(self, maxfev = 1000):
        print("\n fit hill curves")
        for curve in self.curves.values():
            print(curve.antibiotic)
            curve.fit_hill_curve(maxfev = maxfev)

    def plot_pdcurves(self, figsize = (12, 20)):
        l = math.ceil((len(self.antibiotics)-1)/2)
        fig, axs = plt.subplots(l, 2, figsize = figsize)
        r, c = 0, 0
        for antibiotic in self.antibiotics:
            if antibiotic != "None":
                curve = self.curves[antibiotic]
                curve.plot(axs[r, c])
                if c == 1:
                    c = 0
                    r += 1
                else:
                    c = 1
        fig.tight_layout()
              

class PharmacoDynamicCurve:
    def __init__(self, df:pd.DataFrame, antibiotic):
        self.antibiotic = antibiotic
        self.df = df[(df.antibiotic == antibiotic) | (df.well_type == "positive")].copy()
        self.wells = dict(zip(self.df.well, self.df.obj))
        self.fit_successful = False

    def fit_rates(self, window_size=1, signal_noise_ratio=5):
        self.df.obj.apply(lambda well: well.fit_curve(data_type="lum", window_size=window_size, signal_noise_ratio=signal_noise_ratio))
        self.df["rate"] = self.df.obj.apply(lambda well: well.rate)
        self.df['rate'] = pd.to_numeric(self.df['rate'], errors='coerce')
        self.df = self.df.dropna(subset=['rate'])

    def fit_hill_curve(self, maxfev = 1000):
        initial_guesses = [max(self.df.rate), min(self.df.rate), np.mean(self.df.concentration), 1.0]
        try: 
            params, cov = curve_fit(pharmacodynamic_function, self.df.concentration, self.df.rate, p0=initial_guesses, maxfev = maxfev)
            self.psiMax, self.psiMin, self.zMic, self.kappa = params
            self.fit_successful = True
        except:
            print(self.antibiotic, "- not able to fit hill curve")
            self.fit_successful = False

    def predict(self, concentrations):
        return pharmacodynamic_function(concentrations, self.psiMax, self.psiMin, self.zMic, self.kappa )

    def plot(self, ax=None, plot_fit = True, n = 100, fitcolor = "red", dotcolor = "blue"):
            if ax is None:
                _, ax = plt.subplots()

            ax.scatter(self.df.concentration, self.df.rate, label="PD Curve", color = dotcolor)
            ax.set_xscale("log")
            ax.set_xlabel("Concentration")
            ax.set_ylabel("Max Rate")
            ax.legend()
            ax.set_title(self.antibiotic + " PD-Curve")

            if plot_fit and self.fit_successful:
                assays = self.df[self.df.concentration > 0].concentration
                concentrations = np.logspace(np.log10(assays.min()/10), np.log10(self.df.concentration.max()), n)
                y = self.predict(concentrations)
                ax.plot(concentrations, y, color = fitcolor)

# Define the pharmacodynamic function
def pharmacodynamic_function(a, psi_max, psi_min, z_MIC, kappa):
    return psi_max - ((psi_max - psi_min) * (a / z_MIC) ** kappa) / (1 + (a / z_MIC) ** kappa)

