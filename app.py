from flask import Flask, render_template, send_file
import requests
import sqlite3
from wordcloud import WordCloud
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import os

app = Flask(__name__)

# Tạo database và table nếu chưa có
def init_db():
    conn = sqlite3.connect('data_sqlite.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provinces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province_code TEXT,
            province_name TEXT,
            average_population REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gradRate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province_name TEXT,
            year INTEGER,
            percentage REAL 
        )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medicalUnits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province_name TEXT,
            year INTEGER,
            hospitals REAL, 
            clinics REAL,
            nursings REAL,
            local REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province_name TEXT,
            year INTEGER,
            cases REAL, 
            people REAL
        )
    ''')
    conn.commit()
    conn.close()

# Read from file and save data into sqlite
def read_from_file_and_store():
    # Print the current working directory
    # print("Current Working Directory:", os.getcwd()) # Use for debugging

    # Set the relative path to the dataset folder
    dataset_path = os.getcwd() + "/raw data"

    # Display the contents of the dataset folder
    # print(os.listdir(dataset_path)) # Use for debugging

    fn = "pci.xlsx"

    fp = os.path.join(dataset_path, fn)

    df = pd.read_excel(fp, sheet_name='Tổng hợp', usecols=["Vùng", "Tỉnh/Thành phố", "CSTP 6: Cạnh tranh bình đẳng", "CSTP 2: Tiếp cận đất đai", "CSTP 10: Thiết chế pháp lý & An ninh trật tự"])

    # print(df.head())

    conn = sqlite3.connect('data_sqlite.db')
    cursor = conn.cursor()

    for index, row in df.iterrows():
        cursor.execute('''
        INSERT INTO newTuanTable (Tỉnh_Thành_phố, Cạnh_tranh_bình_đẳng, Tiếp_cận_đất_đai, Thiết_chế_pháp_lý_An_ninh_trật_tự, Vùng)
        VALUES (?, ?, ?, ?, ?)
        ''', (row['Tỉnh/Thành phố'], row['CSTP 2: Tiếp cận đất đai'], row['CSTP 6: Cạnh tranh bình đẳng'], row['CSTP 10: Thiết chế pháp lý & An ninh trật tự'], row['Vùng']))

    conn.commit()
    conn.close()

# Gọi API và lưu vào SQLite
def fetch_and_store_data():
    url = "https://apigis.gso.gov.vn/api/web/exportdetail"
    payload = {
        "province_code": "00",
        "years": ["2022"],
        "import_type": 1
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=payload, headers=headers, verify=False)
    if response.status_code == 200:
        json_data = response.json()
        data_export = json_data['data']['dataExport']  # Lấy list từ dataExport
        
        conn = sqlite3.connect('data_sqlite.db')
        cursor = conn.cursor()

        # Xóa dữ liệu cũ trước khi lưu dữ liệu mới
        cursor.execute('DELETE FROM provinces')

        # Lưu dữ liệu vào bảng
        for item in data_export:
            # skip 'TOAN QUOC'
            if item[1] == "":
                continue
            province_code = item[0]
            province_name = item[1]
            average_population = item[2] if item[2] != "" else 0 
            cursor.execute('INSERT INTO provinces (province_code, province_name, average_population) VALUES (?, ?, ?)', 
                           (province_code, province_name, average_population))

        data = [
            ["Da Nang", 2022, 100, 80000],  # 2022 data for Da Nang
            ["Da Nang", 2023, 125, 100000],  # 2023 data for Da Nang
            ["Ho Chi Minh City", 2022, 650, 8000000],  # 2022 data for HCMC
            ["Ho Chi Minh City", 2023, 789, 9000000],  # 2023 data for HCMC
            ["Ha Noi", 2022, 123, 1491],
            ["Ha Noi", 2023, 1515, 123123]
        ]

        # Insert data into the table
        for row in data:
            cursor.execute("INSERT INTO crime_data VALUES (?, ?, ?, ?)", row)

        conn.commit()
        conn.close()
def get_data():
    conn = sqlite3.connect('data_sqlite.db')
    df_from_db = pd.read_sql_query("SELECT * FROM newTuanTable", conn)
    conn.close()
    return df_from_db

def visualize_crime_data():
    conn = sqlite3.connect('data_sqlite.db')
    df = pd.read_sql_query("SELECT * FROM crimes", conn)
    conn.close()
    provinces = [row[0] for row in df]
    cases_2022 = [row[1] for row in df if row[1] == 2022]
    cases_2023 = [row[2] for row in df if row[2] == 2023]

    plt.figure(figsize=(12, 6))  # Adjust figure size for better readability
    bar_width = 0.35  # Adjust bar width for clearer separation
    index = range(len(provinces))  # Create x-axis positions for bars

    # Plot bars for 2022 cases
    plt.bar(index, cases_2022, bar_width, label='2022 Cases')

    # Plot bars for 2023 cases with a slight offset on the x-axis
    plt.bar([p + bar_width for p in index], cases_2023, bar_width, label='2023 Cases')

    plt.xlabel("Province Name")
    plt.ylabel("Number of Cases")
    plt.title("Number of Crimes Cases in Each Province (2022 vs 2023)")
    plt.xticks([p + bar_width / 2 for p in index], provinces, rotation=45, ha="right")  # Adjust x-axis labels
    plt.legend()
    plt.tight_layout()
    plt.show()

def graph_test(df):
    # Create a plotly figure object
    fig = Figure(data=[
        Pie(labels=df_grouped.index, values=df_grouped['Cạnh_tranh_bình_đẳng'], hole=0.4,
            title='Tỷ lệ cạnh tranh bình đẳng giữa các vùng')
    ])

    # Update layout for better interactivity and aesthetics
    fig.update_layout(
        title_x=0.5,  # Center title
        annotations=[dict(text=percent, x=i, y=0.5, font_size=14, showarrow=False)
                     for i, percent in
                     enumerate(df_grouped['Cạnh_tranh_bình_đẳng'] / df_grouped['Cạnh_tranh_bình_đẳng'].sum() * 100)],
        # Add percentage annotations
        legend_title_text="Vùng"  # Update legend title
    )

    # Show the interactive chart
    fig.show() 


# Lấy dữ liệu từ SQLite
def get_data_from_db():
    conn = sqlite3.connect('data_sqlite.db')
    cursor = conn.cursor()
    cursor.execute('SELECT province_name, average_population FROM provinces')
    data = cursor.fetchall()
    conn.close()
    return data

# Tạo word cloud từ dữ liệu
def create_word_cloud(data):
    word_freq = {item[0]: item[1] for item in data}
    
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate_from_frequencies(word_freq)
    
    # Đảm bảo thư mục tồn tại
    if not os.path.exists('static/images'):
        os.makedirs('static/images')
    
    # Lưu word cloud thành file hình ảnh
    wordcloud.to_file('static/images/wordcloud.png')

# Route để hiển thị biểu đồ cột
@app.route('/')
def chart_bar():
    fetch_and_store_data()  # Lấy và lưu dữ liệu từ API
    data = get_data_from_db()  # Lấy dữ liệu từ SQLite
    read_from_file_and_store()
    df = get_data()
    graph_test(df)
    # Chuẩn bị dữ liệu cho biểu đồ
    province_names = [item[0] for item in data]
    average_populations = [item[1] for item in data]

    return render_template('chart.html', province_names=province_names, average_populations=average_populations)

# Route để hiển thị word cloud
@app.route('/word_cloud')
def chart_word_cloud():
    data = get_data_from_db()  # Lấy dữ liệu từ SQLite
    
    # Tạo word cloud từ dữ liệu
    create_word_cloud(data)
    
    # Hiển thị word cloud trên trang
    return render_template('wordcloud.html')

if __name__ == '__main__':
    init_db()  # Tạo bảng nếu chưa có
    # app.run(debug=True)

    port = int(os.environ.get('PORT', 8080))  # Dùng 8080 là port mặc định khi không có biến môi trường
    app.run(host='0.0.0.0', port=port)
