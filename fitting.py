import numpy as np
from matplotlib import pyplot as plt
from sklearn.linear_model import LinearRegression
import seaborn as sns
from scipy.optimize import minimize
import math
import pandas as pd

class CurveFit:
    def __init__(
        self,
        data,
        name = None,
        t_col="t",
        y_col="rlu",
    ):
        self.data = data.copy()
        self.data[data[y_col] < 0] = 0
        self.y = data[y_col].values
        self.name = name
        self.t_col = t_col
        self.y_col = y_col
        self.T = data[t_col].unique()
        self.get_y0()
        self.guess_growth_rate()

    def get_y0(self):
        self.t0 = self.data[self.t_col].min()
        self.t = np.array(self.T - self.t0)
        df0 = self.data[self.data[self.t_col] == self.t0]
        self.y0 = df0[self.y_col].mean()

    def guess_growth_rate(self):
        self.t_end = self.data[self.t_col].max()
        df_end = self.data[self.data[self.t_col] == self.t_end]
        self.y_end = df_end[self.y_col].mean()
        self.growth_rate_pre = np.log(self.y_end / self.y0) / (self.t_end - self.t0)
        if self.growth_rate_pre > 0:
            self.curve_type = "growth curve"
        else:
            self.curve_type = "kill curve"

    def fit_rates(self, window=1, n=100):
        self.window  = window
        T = np.linspace(
            self.data[self.t_col].min() + window / 2,
            self.data[self.t_col].max() - window / 2,
            n,
        )
        self.t_fit = []
        m_values = []
        for i, t in enumerate(T):
            window_data = self.data[
                (self.data[self.t_col] >= t - window / 2)
                & (self.data[self.t_col] <= t + window / 2)
            ]
            X = window_data[self.t_col].values.reshape(-1, 1)
            y = np.log(window_data[self.y_col].values+10**-5)

            if len(y) >= 2:
                model = LinearRegression()
                model.fit(X, y)
                m_values.append(model.coef_[0])
                self.t_fit.append(t)
        
        if len(m_values) >= 1:
            if self.curve_type == "growth curve":
                self.m = max(m_values)
            elif self.curve_type == "kill curve":
                self.m = min(m_values)
            else:
                raise Exception("something weird happened")
            self.m_values = m_values
            self.apply_slope()
        else:
            self.m = "no fit possible"
        
        

    def apply_slope(self):
        idx = np.where(self.m_values == self.m)[0] 
        Y = []
        T = pd.Series(self.t_fit)
        for t in T[idx]:
            Y.append(self.get_corresponding_y(t))
        self.t_center = self.t_fit[idx[math.floor(len(idx)/2)]-1]
        self.t_slope = np.linspace(self.t_center - self.window/2, self.t_center + self.window/2, len(self.t_fit))
        self.y_slope = self.predict(self.t_slope-self.t_center, np.mean(Y))

    def get_corresponding_y(self, t):
        dt = abs(self.t - t)
        idx = np.where(dt == np.min(dt))[0][0]
        return self.y[idx]

    def plot(
        self, color_data="red", plot_data=True, ax=False, figsize=(12, 8), yscale="log", slope = False
    ):
        if not ax:
            _, ax = plt.subplots(figsize=figsize)
        if plot_data:
            ax.plot(self.data[self.t_col], self.y, ".", color=color_data)
        ax.set_yscale(yscale)
        ax.set_title(self.name)

        plt.plot(self.t_slope, self.y_slope)

        return ax

    def predict(self, t, y0):
        return y0 * np.exp(self.m * t)


    def plot_slope(self, ax=None):
        if ax is None:
            _, ax = plt.subplots()

        ax.plot(self.t_fit, self.m_values, "-", label="Slope (m)")

        if hasattr(self, "max_rate"):
            ax.plot(self.max_rate_time, self.max_rate, "ro", label="Max Rate")

        ax.set_title("Slope Over Time")
        ax.set_xlabel("Time")
        ax.set_ylabel("Slope (m)")
        ax.legend()
        return ax



class LinearCloudFit:
    def __init__(self, data, x_col, y_col):
        self.data = data
        self.x_col = x_col
        self.y_col = y_col
        self.x = data[x_col]
        self.y = data[y_col]

    def fit(self, method="sgn_log"):
        if method == "sgn_log":
            result = minimize(residual_sgn_log, 1, args=(self.x, self.y))
        elif method == "lin":
            result = minimize(residual_lin, 1, args=(self.x, self.y))
        else:
            raise Exception("the method has to be either 'lin' or 'sgn_log'")
        self.m_optimized = result.x[0]

    def plot(
        self,
        plot_fit=False,
        n=100,
        annotation_column=None,
        ax=None,
        scale="log",
        palette="pastel",
        fit_color_i: int = 1,
    ):
        colors = sns.color_palette(palette)

        if not ax:
            _, ax = plt.subplots()

        df = self.data
        g = sns.scatterplot(data=df, x=self.x, y=self.y, palette=palette)
        if annotation_column:
            for i in range(df.shape[0]):
                plt.annotate(
                    df.iloc[i]["file_name"], (df.iloc[i][self.x_col], df.iloc[i][self.y_col])
                )
        x_line = np.linspace(min(self.x), max(self.x), n)
        y_line = self.m_optimized * x_line
        if plot_fit:
            try:
                plt.plot(x_line, y_line, color=colors[fit_color_i])
                g.set_xlabel("count")
            except:
                ("Plotting fit didn't work. Did you calculate the fit first?")

        g.set_xscale(scale)
        g.set_yscale(scale)
        self.g = g


def residual_sgn_log(m, x, y):
    sgn_log_x = np.sign(x) * np.log(np.abs(x))
    sgn_log_y = np.sign(y) * np.log(np.abs(y))
    sgn_log_m = np.sign(m) * np.log(np.abs(m))
    return np.sum((sgn_log_m + sgn_log_x - sgn_log_y) ** 2)


def residual_lin(m, x, y):
    return np.sum((m * x - y) ** 2)
