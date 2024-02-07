from matplotlib import pyplot as plt
import pandas as pd
import math

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

    def fit_rates(self, window_size=1, signal_noise_ratio=5):
        self.df.obj.apply(lambda well: well.fit_curve(data_type="lum", window_size=window_size, signal_noise_ratio=signal_noise_ratio))
        self.df["rate"] = self.df.obj.apply(lambda well: well.rate)
        self.df['rate'] = pd.to_numeric(self.df['rate'], errors='coerce')
        self.df = self.df.dropna(subset=['rate'])

    def _create_curves(self):
        for well in self.df.well.unique():
            well_df = self.df[self.df.well == well]
            concentration = well_df[self.concentration_column].iloc[0]
            curve = CurveFit(well_df, f"Curve for Well {well}", t_col=self.t_col, y_col=self.y_col)
            curve.fit_rates()
            curve.get_max_rate()
            self.concentrations.append(concentration)
            self.curves.append(curve)
            self.rates.append(curve.max_rate)

    def plot(self, ax=None):
        if ax is None:
            _, ax = plt.subplots()

        ax.scatter(self.df.concentration, self.df.rate, label="PD Curve")
        ax.set_xscale("log")
        ax.set_xlabel("Concentration")
        ax.set_ylabel("Max Rate")
        ax.legend()
        ax.set_title("Pharmacodynamic Curve")
