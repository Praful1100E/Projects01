from flask import Flask, request, render_template_string
import pandas as pd

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Company Sector Counter</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            animation: fadeIn 1s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        h1 {
            color: #00d4ff;
            text-align: center;
            text-shadow: 0 0 10px #00d4ff;
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 10px #00d4ff; }
            to { text-shadow: 0 0 20px #00d4ff, 0 0 30px #00d4ff; }
        }
        p { text-align: center; color: #b0b0b0; }
        form {
            max-width: 600px;
            margin: 20px auto;
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);
            backdrop-filter: blur(10px);
            transition: transform 0.3s ease;
        }
        form:hover { transform: translateY(-5px); }
        label {
            display: block;
            margin-top: 15px;
            color: #00d4ff;
            font-weight: bold;
        }
        input[type="file"], input[type="text"] {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid #00d4ff;
            border-radius: 5px;
            color: #e0e0e0;
            transition: border-color 0.3s ease;
        }
        input:focus { border-color: #00ffff; outline: none; box-shadow: 0 0 10px #00d4ff; }
        button {
            width: 100%;
            padding: 12px;
            margin-top: 20px;
            background: linear-gradient(45deg, #00d4ff, #0099cc);
            color: #0f0f23;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.3s ease, transform 0.2s ease;
        }
        button:hover {
            background: linear-gradient(45deg, #00ffff, #00aaff);
            transform: scale(1.05);
        }
        .result {
            max-width: 800px;
            margin: 30px auto;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid #00d4ff;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);
            backdrop-filter: blur(10px);
            animation: slideIn 0.5s ease-out;
        }
        @keyframes slideIn {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
            overflow: hidden;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(0, 212, 255, 0.3);
        }
        th {
            background: linear-gradient(45deg, #00d4ff, #0099cc);
            color: #0f0f23;
            font-weight: bold;
        }
        tr:hover { background: rgba(0, 212, 255, 0.1); }
    </style>
</head>
<body>
    <h1>Company Sector Counter</h1>
    <p>Upload the Excel file and enter a company name to get details about the sectors they work in and counts.</p>
    <form method="post" enctype="multipart/form-data">
        <label for="file">Upload Excel file (.xlsx):</label>
        <input type="file" name="file" accept=".xlsx" required />
        <label for="company_name">Enter company name:</label>
        <input type="text" name="company_name" required />
        <button type="submit">Search</button>
    </form>
    {{ content|safe }}
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    content = ''
    if request.method == 'POST':
        file = request.files.get('file')
        company_name = request.form.get('company_name', '').strip()
        if not file or not company_name:
            content = '<div class="result"><p style="color:red;">Please upload a file and enter a company name.</p></div>'
        else:
            try:
                xls = pd.ExcelFile(file)
                total_count = 0
                sector_counts = {}
                sectors_found = set()
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
                    df.fillna('', inplace=True)
                    # Iterate rows
                    for idx, row in df.iterrows():
                        sector = row.get('Sector', '')
                        # Check all columns except District and Sector for company name
                        company_columns = [col for col in df.columns if col not in ['District', 'Sector']]
                        found_in_row = any(company_name.lower() == str(row[col]).strip().lower() for col in company_columns)
                        if found_in_row:
                            total_count += 1
                            sector_counts[sector] = sector_counts.get(sector, 0) + 1
                            sectors_found.add(sector)
                if total_count > 0:
                    content = f'<div class="result"><h2>Results for "{company_name}"</h2>'
                    content += f'<p><strong>Total occurrences:</strong> {total_count}</p>'
                    content += f'<p><strong>Sectors found:</strong> {", ".join(sorted(sectors_found))}</p>'
                    content += '<h3>Occurrences per Sector:</h3>'
                    content += '<table><tr><th>Sector</th><th>Count</th></tr>'
                    for sector, count in sorted(sector_counts.items()):
                        content += f'<tr><td>{sector}</td><td>{count}</td></tr>'
                    content += '</table></div>'
                else:
                    content = f'<div class="result"><p>No occurrences of "{company_name}" found in the uploaded file.</p></div>'
            except Exception as e:
                content = f'<div class="result"><p style="color:red;">Error processing file: {str(e)}</p></div>'
    return render_template_string(HTML_TEMPLATE, content=content)

if __name__ == '__main__':
    app.run(debug=True, port=5002)  # Run on different port to avoid conflicts
