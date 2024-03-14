import seaborn as sns
import math
import pandas as pd
from .fitting import CurveFit
import numpy as np


class Well:
    def __init__(
        self,
        data,
        w,
        type_col="control",
        t_col="time",
        od_label=None,
        lum_label=None,
        label_col="label",
        signal_col="signal",
        od_blank="min",
        od_cut_off=0.1,
    ):
        (
            self.raw_data,
            self.t_col,
            self.od_label,
            self.lum_label,
            self.label_col,
            self.signal_col,
            self.name,
        ) = (data, t_col, od_label, lum_label, label_col, signal_col, w)
        self.df = data[data.well == w].copy()
        self.df = self.df.sort_values(by=t_col)
        self.tend = self.df[t_col].max()
        self.iend = self.df[self.df.time == self.tend].index[0]
        self.t0 = self.df[t_col].min()
        self.i0 = self.df[self.df.time == self.tend].index[0]

        if len(self.df[type_col]) != 1:
            Exception("well type ambigous")
        self.well_type = self.df[type_col].values[0]
        self.od_contamination, self.od_growth, self.lum_growth = False, False, False

        if od_label:
            self.od_df = self.df[self.df[label_col] == od_label].copy()
            self.od_values = self.od_df[signal_col].values
            self.get_od_norm(blank=od_blank)
            self.get_od_growth(cut_off=od_cut_off)
            if (self.well_type == "negative") & self.od_growth:
                Exception("(od) contamination of well", self.name)
                self.od_contamination = True
            self.od_end = self.od_df[(self.df[t_col] == self.tend)]["od_norm"].values[0]

        if lum_label:
            self.lum_df = self.df[self.df[label_col] == lum_label].copy()
            self.lum_values = self.lum_df[self.signal_col].values
            self.lum_growth = self.lum_values[-1] > self.lum_values[0]

        self.features = []

    def assign_reference_wells(self, reference_wells):
        def dist(well1, well2):
            i1, j1 = ord(well1[0]) - ord("A"), int(well1[1:])
            i2, j2 = ord(well2[0]) - ord("A"), int(well2[1:])
            return math.sqrt((i2 - i1) ** 2 + (j2 - j1) ** 2)

        distance = []
        uncontaminated = reference_wells[reference_wells.contamination == False].copy()
        for _, control_well in uncontaminated.iterrows():
            distance.append(
                {
                    "well": control_well.well,
                    "distance": dist(self.name, control_well.well),
                    "obj": control_well.obj,
                }
            )
        self.reference_wells = pd.DataFrame().from_records(distance)

    def plot_od_growthcurve(self, y_col="od_norm"):
        sns.pointplot(data=self.od_df, x=self.t_col, y=y_col)

    def plot_lum_growthcurve(self):
        sns.pointplot(data=self.lum_df, x=self.t_col, y=self.signal_col)

    def get_od_norm(self, blank="min"):
        if blank == "min":
            self.od_df["od_norm"] = self.od_df[self.signal_col] - min(self.od_values)
        else:
            Exception("no alternative method available yet.")

    def get_od_growth(self, cut_off=0.1):
        self.od_growth = self.od_df.od_norm.values[-1] > cut_off

    def fetch_feature(self, label):
        if label not in self.df.columns:
            Exception("requested feature not in self.df")
        else:
            self.features.append(label)

        sub = self.df[label].unique()
        if len(sub) == 1:
            self.__dict__.update({label: sub[0]})
        else:
            Exception("feature ambigous")

    def norm_lum_wells(self, method="closest"):
        if method == "closest":
            self.norm_lum_closest()
        else:
            Exception("Right now the only norming method is closest")

    def norm_lum_closest(self):
        dmin = self.reference_wells.distance.min()
        idx = self.reference_wells[self.reference_wells.distance == dmin]
        self.norm_ref_wells = idx.well
        self.norm_df = self.raw_data[self.raw_data.well.isin(self.norm_ref_wells)]
        self.norm_df = self.norm_df[self.norm_df[self.label_col] == self.lum_label][
            [self.t_col, self.signal_col]
        ]
        self.norm_df = (
            self.norm_df.groupby(["time"])
            .mean()
            .rename(columns={self.signal_col: "lum_ref"})
        )
        self.lum_df = self.lum_df.merge(
            self.norm_df[["lum_ref"]],
            left_on="time",
            right_index=True,
            suffixes=("", "_norm"),
        )
        self.lum_df["rlu"] = self.lum_df[self.signal_col] - self.lum_df.lum_ref
        self.lum_df["rlu"] = np.maximum(self.lum_df["rlu"], 0)
        self.lum_df["signal_noise_ratio"] = self.lum_df[self.signal_col] / (
            self.lum_df.lum_ref + 1
        )

    def fit_curve(
        self, data_type, normed=True, t_max=5, signal_noise_ratio=5, window_size=1
    ):
        if data_type == "od":
            df = self.od_df
            y_col = data_type + "_norm" if normed else "signal"
        elif data_type == "lum":
            df = self.lum_df
            y_col = "rlu" if normed else "signal"
        else:
            Exception('data_type has to be "od" or "lum"')
        df = df[(df.time < t_max) & (df.signal_noise_ratio > signal_noise_ratio)]
        if len(df) <= 1:
            self.rate = "not enough data"
        else:
            self.curve = CurveFit(df, name=self.name, t_col="time", y_col=y_col)
            self.curve.fit_rates(window=window_size)
            self.rate = self.curve.m

    def __repr__(self):
        base_info = f"Well('{self.name}', Type='{self.well_type}'"
        od_info = f", OD Growth={'Yes' if hasattr(self, 'od_growth') and self.od_growth else 'No'}"
        lum_info = f", Lum Growth={'Yes' if hasattr(self, 'lum_growth') and self.lum_growth else 'No'}"
        contamination_info = f", Type={self.well_type}"

        # Dynamically add fetched features
        features_info = ""
        for feature in self.features:
            value = getattr(self, feature, "N/A")
            features_info += f", {feature.capitalize()}='{value}'"

        return base_info + od_info + lum_info + contamination_info + features_info + ")"
