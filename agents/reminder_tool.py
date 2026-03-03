import pandas as pd
from datetime import datetime
from database.qdrant_store import save_log


def reminder_tool(tutor_name, date_str, shifts):
    shifts_text = ", ".join([f"{s['start']} tới {s['end']}" for s in shifts])
    return f"Gia sư {tutor_name} chú ý: Hôm nay {date_str} bạn có các ca dạy lúc {shifts_text}. Vui lòng vào lớp đúng giờ nhé!"

def run_reminder_tool(df, notification_service):
    target_date = datetime.today().date()
    # Gom nhóm theo gia sư cho ngày hôm nay
    grouped_tutors = {}

    for _, tutor in df.iterrows():
        raw_date = tutor['ngày làm việc']
        if pd.isna(raw_date):
            continue
            
        if hasattr(raw_date, 'date'):
            tutor_date = raw_date.date()
        else:
            try:
                tutor_date = pd.to_datetime(raw_date, format="%d/%m/%Y").date()
            except Exception:
                try:
                    tutor_date = pd.to_datetime(raw_date).date()
                except Exception:
                    continue

        if tutor_date == target_date:
            tutor_name = str(tutor['tên gs']).strip()
            date_str = tutor_date.strftime("%d/%m/%Y")
            shift_info = {
                "start": str(tutor['giờ vào ca']).strip(),
                "end": str(tutor['giờ tan ca']).strip()
            }
            
            if tutor_name not in grouped_tutors:
                grouped_tutors[tutor_name] = {
                    "date_str": date_str,
                    "shifts": []
                }
            grouped_tutors[tutor_name]["shifts"].append(shift_info)

    # Gửi thông báo cho từng gia sư (mỗi gia sư 1 thông báo duy nhất chứa nhiều ca)
    for tutor_name, info in grouped_tutors.items():
        if not info["shifts"]:
            continue
            
        message = reminder_tool(tutor_name, info["date_str"], info["shifts"])
        if message:
            notification_service(
                "Nhắc lịch ca dạy hôm nay",
                message,
                tutor_name=tutor_name
            )
            save_log(
                message,
                {
                    "type": "reminder",
                    "tutor": tutor_name,
                    "date": info["date_str"],
                },
            )