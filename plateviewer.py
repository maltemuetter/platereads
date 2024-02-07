import matplotlib.pyplot as plt
import os
import matplotlib.patches as patches


class PlateViewer:
    def __init__(self, plate):
        self.plate = plate
        self.matrix = self.create_matrix()

    def create_matrix(self):
        well_names = sorted(self.plate.well.keys())
        rows = sorted(set(well_name[0] for well_name in well_names))
        max_column = max(int(well_name[1:]) for well_name in well_names)
        row_indices = {letter: index for index, letter in enumerate(rows, start=1)}
        
        matrix = [[None for _ in range(max_column)] for _ in range(len(rows))]

        for well_name, well_object in self.plate.well.items():
            row = row_indices[well_name[0]] - 1
            column = int(well_name[1:]) - 1
            matrix[row][column] = well_object
        return matrix

    def show(self, growth_color='darkblue', no_growth_color='lightgrey', figsize=(16,6)):
        _, ax = plt.subplots(figsize=figsize)  # Adjust figure size
        ax.set_xlim(0, len(self.matrix[0]))
        ax.set_ylim(0, len(self.matrix))
        plt.xticks(range(len(self.matrix[0])), [str(i+1) for i in range(len(self.matrix[0]))])
        plt.yticks(range(len(self.matrix)), [row for row in reversed(sorted(set(well_name[0] for well_name in self.plate.well.keys())))])
        ax.set_aspect('equal')  # Ensure the aspect ratio is equal to make squares look like squares
        
        for i, row in enumerate(self.matrix):
            for j, well in enumerate(row):
                if well is not None:
                    color = growth_color if well.od_growth else no_growth_color
                    edgecolor = 'none'
                    linewidth = 0
                    
                    if well.well_type == "assay":
                        edgecolor = 'white'
                        linewidth = 1
                    elif well.well_type == "positive":
                        edgecolor = 'green'
                        linewidth = 4
                    elif well.well_type == "negative":
                        edgecolor = 'red'
                        linewidth = 4
                        
                    rect = patches.Rectangle((j, len(self.matrix) - i - 1), 1, 1, linewidth=linewidth, edgecolor=edgecolor, facecolor=color)
                    ax.add_patch(rect)
        
        plt.grid(True, color='white')
        
    def save(self, path = "./"):
        plt.savefig(os.path.join(path, "plate_representation.png"), dpi = 300)
    