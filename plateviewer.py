import matplotlib.pyplot as plt
import os
import matplotlib.patches as patches


class PlateViewer:
    def __init__(self, wells: dict):
        self.wells = wells
        self.matrix = self.create_matrix()

    def create_matrix(self):
        well_names = sorted(self.wells.keys())
        rows = sorted(set(well_name[0] for well_name in well_names))
        max_column = max(int(well_name[1:]) for well_name in well_names)
        row_indices = {letter: index for index, letter in enumerate(rows, start=1)}

        matrix = [[None for _ in range(max_column)] for _ in range(len(rows))]

        for well_name, well_object in self.wells.items():
            row = row_indices[well_name[0]] - 1
            column = int(well_name[1:]) - 1
            matrix[row][column] = well_object
        return matrix

    def show(
        self, growth_color="darkblue", no_growth_color="lightgrey", figsize=(16, 6)
    ):
        _, ax = plt.subplots(figsize=figsize)  # Adjust figure size
        ax.set_xlim(0, len(self.matrix[0]))
        ax.set_ylim(0, len(self.matrix))
        plt.xticks(
            range(len(self.matrix[0])), [str(i + 1) for i in range(len(self.matrix[0]))]
        )
        plt.yticks(
            range(len(self.matrix)),
            [
                row
                for row in reversed(
                    sorted(set(well_name[0] for well_name in self.wells.keys()))
                )
            ],
        )
        ax.set_aspect(
            "equal"
        )  # Ensure the aspect ratio is equal to make squares look like squares

        for i, row in enumerate(self.matrix):
            for j, well in enumerate(row):
                if well is not None:
                    color = growth_color if well.od_growth else no_growth_color
                    edgecolor = "none"
                    linewidth = 0

                    if well.well_type == "assay":
                        edgecolor = "white"
                        linewidth = 1
                    elif well.well_type == "positive":
                        edgecolor = "green"
                        linewidth = 4
                    elif well.well_type == "negative":
                        edgecolor = "red"
                        linewidth = 4

                    rect = patches.Rectangle(
                        (j, len(self.matrix) - i - 1),
                        1,
                        1,
                        linewidth=linewidth,
                        edgecolor=edgecolor,
                        facecolor=color,
                    )
                    ax.add_patch(rect)

        plt.grid(True, color="white")

    def save(self, path="./", name="plate_representation.png"):
        plt.savefig(os.path.join(path, name), dpi=300)


import pandas as pd


class PlateViewerDf:
    def __init__(self, df: pd.DataFrame):
        """
        Initializes the PlateViewer with a DataFrame.

        Parameters:
        df (pd.DataFrame): DataFrame containing 'well', 'growth', 'control', and 'antibiotic' columns.
        """
        self.df = df
        self.matrix, self.row_labels, self.max_column, self.antibiotics = (
            self.create_matrix()
        )

    def create_matrix(self):
        """
        Converts the DataFrame into a structured matrix for visualization.

        Returns:
        tuple: (matrix, row_labels, max_column, antibiotics)
        """
        wells = self.df.set_index("well").to_dict(orient="index")
        well_names = sorted(wells.keys())

        rows = sorted(set(well[0] for well in well_names))
        max_column = max(int(well[1:]) for well in well_names)
        row_indices = {letter: index for index, letter in enumerate(rows, start=1)}

        matrix = [[None for _ in range(max_column)] for _ in range(len(rows))]
        antibiotics = {row: None for row in rows}

        for well_name, well_data in wells.items():
            row = row_indices[well_name[0]] - 1
            column = int(well_name[1:]) - 1
            matrix[row][column] = well_data

            # Store antibiotic names for row labeling
            if "antibiotic" in well_data:
                antibiotics[well_name[0]] = well_data["antibiotic"]

        return matrix, rows, max_column, antibiotics

    def show(
        self, growth_color="darkblue", no_growth_color="lightgrey", figsize=(16, 6)
    ):
        """
        Displays the plate layout with growth, well types, and antibiotic row labels.

        Parameters:
        growth_color (str): Color for wells with growth.
        no_growth_color (str): Color for wells without growth.
        figsize (tuple): Size of the figure.
        """
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_xlim(0, self.max_column)
        ax.set_ylim(0, len(self.row_labels))

        # Set axis labels
        plt.xticks(range(self.max_column), [str(i + 1) for i in range(self.max_column)])
        plt.yticks(
            range(len(self.row_labels)),
            list(reversed(self.row_labels)),
        )
        ax.set_aspect("equal")

        # Draw wells
        for i, row in enumerate(self.matrix):
            for j, well in enumerate(row):
                if well is not None:
                    color = growth_color if well["growth"] else no_growth_color
                    edgecolor = "none"
                    linewidth = 0

                    if well["control"] == "positive":
                        edgecolor = "green"
                        linewidth = 3
                    elif well["control"] == "negative":
                        edgecolor = "red"
                        linewidth = 3

                    rect = patches.Rectangle(
                        (j, len(self.matrix) - i - 1),
                        1,
                        1,
                        linewidth=linewidth,
                        edgecolor=edgecolor,
                        facecolor=color,
                    )
                    ax.add_patch(rect)

        # Add row labels for antibiotics
        for i, row in enumerate(reversed(self.row_labels)):
            antibiotic = self.antibiotics.get(row)
            if antibiotic:
                ax.text(
                    -1.5,  # Offset to the left of the first column
                    i,
                    antibiotic,
                    ha="right",
                    va="center",
                    fontsize=10,
                    fontweight="bold",
                    color="black",
                )

        plt.grid(True, color="white")

    def save(self, path="./", name="plate_representation.png"):
        """
        Saves the plate visualization as an image.

        Parameters:
        path (str): Directory to save the image.
        name (str): Name of the image file.
        """
        plt.savefig(os.path.join(path, name), dpi=300)
