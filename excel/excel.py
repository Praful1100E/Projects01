import pandas as pd

# Load Excel file
file = "your_excel_file.xlsx"
xls = pd.ExcelFile(file)

# Show available sheet names (titles of sheets)
print("Sheets in this Excel file:")
for i, sheet in enumerate(xls.sheet_names, start=1):
    print(f"{i}. {sheet}")

# Select a sheet
sheet_name = input("Enter sheet name to check: ")
df = pd.read_excel(file, sheet_name=sheet_name)

# Show column titles
print("\nAvailable Columns:")
print(df.columns.tolist())

# Search for a specific name in the whole sheet
search_name = input("\nEnter name to count: ")
count = df.apply(lambda row: row.astype(str).str.contains(search_name, case=False)).sum().sum()

print(f"\n'{search_name}' is repeated {count} times in sheet '{sheet_name}'.")