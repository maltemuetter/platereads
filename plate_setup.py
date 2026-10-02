import pandas as pd

class Setup:
    def __init__(self, filepath):
        self.path = filepath
        self.sheets = self.get_sheet_names()
        self.df = self.create_dataframe()

    def get_sheet_names(self):
        xls = pd.ExcelFile(self.path)
        sheets = [sheet for sheet in xls.sheet_names if "ignore" not in sheet.lower()]
        xls.close()
        return sheets

    def create_dataframe(self):
        columns = ["row", "column", "well"] + self.sheets
        all_rows = []

        for sheet in self.sheets:
            temp_df = pd.read_excel(self.path, sheet_name=sheet, engine='openpyxl',  index_col=0)
            row_names = temp_df.index.tolist()
            col_names = temp_df.columns.tolist()

            for row in row_names:
                for col in col_names:
                    well = row + str(col)
                    
                    existing_row = next((index for index, content in enumerate(all_rows) 
                                         if content['row'] == row and content['column'] == col), None)
                    
                    if existing_row is None:
                        new_row = {'row': row, 'column': col, 'well': well, sheet: temp_df.loc[row, col]}
                        all_rows.append(new_row)
                    else:
                        all_rows[existing_row][sheet] = temp_df.loc[row, col]

        df = pd.DataFrame(all_rows, columns=columns)
        return df

    def map_to_input_df(self, input_df):
        merge_cols = [col for col in self.df.columns if col not in input_df.columns]
        df_to_merge = self.df[['well'] + merge_cols]
        mapped_df = pd.merge(input_df, df_to_merge, on='well', how='left')
        return mapped_df
