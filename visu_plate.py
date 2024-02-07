import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Sample DataFrame
data = {
    'wells': ['A1', 'A2', 'B1', 'B2', 'D5', 'H15'],
    'growth': [True, False, True, True, False, True]
}
df = pd.DataFrame(data)

# Convert the well notation to row, col


def well_to_rc(well):
    return ord(well[0])-65, int(well[1:])-1


# Prepare the data for the 16x24 grid
matrix = np.zeros((16, 24), dtype=bool)

for _, row in df.iterrows():
    r, c = well_to_rc(row['wells'])
    matrix[r, c] = row['growth']

# Visualization
fig, ax = plt.subplots(figsize=(10, 6))
cmap = plt.get_cmap('coolwarm')
ax.imshow(matrix, cmap=cmap, aspect='auto')
ax.set_title('384-well Plate Visualization')
ax.set_xticks(np.arange(0, 24, 1))
ax.set_yticks(np.arange(0, 16, 1))
ax.set_xticklabels(np.arange(1, 25, 1))
ax.set_yticklabels([chr(i) for i in range(65, 81)])
ax.grid(which='both', axis='both', linestyle='-', color='k', linewidth=2)
plt.show()
