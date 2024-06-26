import requests
import os
from datetime import datetime, timedelta
import xlwings as xw
import pandas as pd


class hydro_npp_daily_data:

    def __init__(self):
        self.main_directory = r'C:\GNA\Data\Hydro Level'
        self.final_directory = r'C:\GNA\Data Upload'
        self.file_directory = r'C:\GNA\Data\Hydro Level\Downloaded Files1'
        self.clear_or_create_directory(self.file_directory)
        self.output_directory = r'C:\GNA\Data\Hydro Level\Edited xlsx Files'
        self.clear_or_create_directory(self.output_directory)
        self.error_log_file = r'C:\GNA\Data\Hydro Level\error_files.xlsx'
        pass

    def clear_or_create_directory(selfself, directory):
        if os.path.exists(directory):
            for file in os.listdir(directory):
                file_path_full = os.path.join(directory, file)
                if os.path.isfile(file_path_full):
                    os.remove(file_path_full)
        else:
            os.makedirs(directory)

    def convert_xls_to_xlsx(self, file_path):
        xls_files = []
        for file in os.listdir(file_path):
            if file.endswith('.xls'):
                xls_files.append(os.path.join(file_path, file))

        for file in xls_files:
            output_path = os.path.join(file_path, os.path.splitext(os.path.basename(file))[0] + '.xlsx')
            try:
                app = xw.App(visible=False)  # Open Excel in the background
                workbook = app.books.open(file)
                workbook.save(output_path)
                workbook.close()
                app.quit()
                print(f"Conversion completed. File saved at: {output_path}")
            except Exception as e:
                print(f"Error: {e}")

    def hydro_level_data(self):
        base_date = datetime.now()
        end_date = datetime.now() - timedelta(10)
        # end_date = datetime(2019,1,1)

        while base_date > end_date:
            start_date = base_date.strftime('%d-%m-%Y')
            start_date_2 = base_date.strftime('%Y-%m-%d')

            url = f"https://npp.gov.in/public-reports/cea/daily/dgr/{start_date}/dgr6-{start_date_2}.xls"
            response = requests.get(url)

            if response.status_code == 200:
                with open(f'{self.file_directory}/{start_date}.xls', 'wb') as f:
                    f.write(response.content)

                print(f"Downloaded data for date: {start_date_2}")
            else:
                print(f"No data available for date: {start_date_2}")

            base_date = base_date - timedelta(days=1)

        if base_date == end_date:
            print("Reached end date. Exiting loop.")

        hydro_npp_daily_data.convert_xls_to_xlsx(self, self.file_directory)

    def edit_xlsx_file(self):
        xlsx_files = []
        error_files = []
        for file in os.listdir(self.file_directory):
            if file.endswith('.xlsx'):
                xlsx_files.append(os.path.join(self.file_directory, file))

        for xlsx_file in xlsx_files:
            output_file = os.path.join(self.output_directory,
                                       os.path.splitext(os.path.basename(xlsx_file))[0] + '.xlsx')
            try:

                df = pd.read_excel(xlsx_file)
                region_row_index = None
                # Find the row and column containing 'Region' values
                for index, row in df.iterrows():
                    for column in df.columns:
                        if isinstance(row[column], str) and row[column].startswith('Reservoir'):
                            region_row_index = index
                            break
                    if region_row_index is not None:
                        break
                # Drop all rows above this value
                if region_row_index is not None:
                    df = df.iloc[region_row_index:]
                    print("Reservoir data indexed successfully.")
                else:
                    print("No 'Reservoir' values found.")
                combined_row = []
                for i in range(len(df.iloc[0])):
                    value1 = str(df.iloc[0][i])  # Convert to string
                    value2 = str(df.iloc[1][i])  # Convert to string
                    if value1 == 'nan':
                        combined_row.append(f'{df.iloc[0][i - 1]} ({value2})')
                    elif value2 == 'nan':
                        combined_row.append(value1)
                    else:
                        combined_row.append(f'{value1} ({value2})')
                # print(combined_row)
                df.iloc[0] = combined_row
                table_heading = df.iloc[0]
                df = df.iloc[1:]
                df.columns = table_heading

                # Assuming 'df' is your DataFrame
                df = df[~(df.iloc[:, 0].astype(str).str.contains('1'))]
                # Drop rows where the first column is empty
                df = df.dropna(subset=[df.columns[0]])
                file_date = xlsx_file.split("Files\\")[1].split('.xlsx')[0]
                df.insert(0, 'Date', file_date)
                df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
                df['Date'] = df['Date'].dt.date

                df.to_excel(output_file, index=False)
                print(f'File Edited {output_file}')
            except Exception as e:
                print(e)
                error_files.append(xlsx_file)
        if error_files:
            try:
                pd.DataFrame({'Error Files': error_files}).to_excel(self.error_log_file, index=False)
                print(f"Error log saved to '{self.error_log_file}'")
            except Exception as e:
                print(f"Error saving error log: {e}")

    def merge_xlsx_files(self):
        xlsx_files = []
        for file in os.listdir(self.output_directory):
            if file.endswith('.xlsx'):
                xlsx_files.append(os.path.join(self.output_directory, file))
        merged_df = pd.DataFrame()

        for file in xlsx_files:
            df = pd.read_excel(file)
            df.reset_index(drop=True, inplace=True)  # Reset index before concatenating
            merged_df = pd.concat([merged_df, df], ignore_index=True)

        if 'Energy Content At Present  (MU)' in merged_df.columns:
            merged_df['Energy Content At Present  (MU)'].fillna('', inplace=True)
            merged_df.loc[merged_df['Energy Content At Present  (MU)'] != '', 'Energy Content At Present Level (MU)'] = \
                merged_df['Energy Content At Present  (MU)']
            merged_df.drop('Energy Content At Present  (MU)', axis=1, inplace=True)

        final_file = os.path.join(self.final_directory, 'hydro_npp.xlsx')
        merged_df.to_excel(final_file, index=False)
        print(f"Merged File Saved at '{final_file}'")

    def get_data(self):
        hydro_npp_daily_data.hydro_level_data(self)
        hydro_npp_daily_data.edit_xlsx_file(self)
        hydro_npp_daily_data.merge_xlsx_files(self)
        pass


if __name__ == '__main__':
    hydro_npp = hydro_npp_daily_data()
    hydro_npp.get_data()
    pass
