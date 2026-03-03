import pandas as pd

def load_excel(file):
    df = pd.read_excel(file)

    # Chuẩn hóa tên cột: bỏ khoảng trắng thừa và đưa về chữ thường
    # để khớp với các key đang dùng trong agents (ví dụ: "giờ chấm công").
    df.columns = df.columns.str.strip().str.lower()

    df.fillna("", inplace=True)
    return df