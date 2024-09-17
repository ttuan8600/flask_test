from flask import Flask, render_template, send_file
import requests
import sqlite3
from wordcloud import WordCloud
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
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
    CREATE TABLE IF NOT EXISTS tuanTable (
        Tỉnh_Thành_phố TEXT,
        Cạnh_tranh_bình_đẳng REAL,
        Vùng TEXT
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

    df = pd.read_excel(fp, sheet_name='Tổng hợp', usecols=["Vùng", "Tỉnh/Thành phố", "CSTP 6: Cạnh tranh bình đẳng"])

    # print(df.head())

    conn = sqlite3.connect('data_sqlite.db')
    cursor = conn.cursor()

    for index, row in df.iterrows():
        cursor.execute('''
        INSERT INTO tuanTable (Tỉnh_Thành_phố, Cạnh_tranh_bình_đẳng, Vùng)
        VALUES (?, ?, ?)
        ''', (row['Tỉnh/Thành phố'], row['CSTP 6: Cạnh tranh bình đẳng'], row['Vùng']))

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
        
        conn.commit()
        conn.close()
def get_data():
    conn = sqlite3.connect('data_sqlite.db')
    df_from_db = pd.read_sql_query("SELECT * FROM tuanTable", conn)
    conn.close()
    return df_from_db

def graph_test(df):
    df_grouped = df.groupby('Vùng')
    fig = go.Figure()

    for name, group in df_grouped:
        bottom = 0
        for index, row in group.iterrows():
            fig.add_trace(go.Bar(
                x=[name],
                y=[row['Cạnh_tranh_bình_đẳng']],
                base=bottom,
                name=row['Tỉnh_Thành_phố']
            ))
            bottom += row['Cạnh_tranh_bình_đẳng']

    fig.update_layout(
        barmode='stack',
        yaxis_title='Cạnh tranh bình đẳng',
        title='Sự cạnh tranh bình đẳng giữa các vùng'
    )
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
