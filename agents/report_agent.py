import pandas as pd
from config import MODEL
from database.qdrant_store import save_log
from datetime import datetime, time as dtime, timedelta


def _to_datetime(value):
    """
    Chuẩn hóa giá trị thời gian từ Excel / pandas:
    - Nếu là datetime -> dùng luôn
    - Nếu là time -> ghép với ngày hôm nay
    - Nếu là str -> parse với các format phổ biến
    """
    if value in ("", None):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, dtime):
        return datetime.combine(datetime.today().date(), value)
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def check_late(actual_start_time, scheduled_start_time):
    actual = _to_datetime(actual_start_time)
    scheduled = _to_datetime(scheduled_start_time)
    if actual is None or scheduled is None:
        return 0
    diff = (actual - scheduled).total_seconds() / 60
    return max(0, int(diff))


def check_early_leave(actual_end_time, scheduled_end_time):
    actual = _to_datetime(actual_end_time)
    scheduled = _to_datetime(scheduled_end_time)
    if actual is None or scheduled is None:
        return 0
    diff = (scheduled - actual).total_seconds() / 60
    return max(0, int(diff))

def calculate_score(late_minutes, early_leave_minutes):
    total_minutes = late_minutes + early_leave_minutes

    if total_minutes >= 10:
        return 0

    score = 10 - total_minutes
    return max(0, round(score, 1))

def generate_report(tutor_name, date_str, shifts):
    total_late = 0
    total_early = 0
    shifts_detail = ""
    
    for i, shift in enumerate(shifts):
        late_minutes = check_late(shift["actual_start"], shift["start"])
        early_leave_minutes = check_early_leave(shift["actual_end"], shift["end"])
        total_late += late_minutes
        total_early += early_leave_minutes
        
        shifts_detail += f"- Ca {i+1}: {shift['start']} - {shift['end']} (Thực tế: {shift['actual_start']} - {shift['actual_end']})\n"

    score = calculate_score(total_late, total_early)

    prompt = f"""
    Viết thông báo chấm công ngày hôm qua ({date_str}) cho gia sư {tutor_name}.
    Các ca làm việc trong ngày:
    {shifts_detail}
    Tổng kết: Đi muộn tổng cộng {total_late} phút, Về sớm tổng cộng {total_early} phút.
    Điểm chấm công của ngày: {score}/10.

    Yêu cầu: Hãy viết một thông báo NGẮN GỌN DƯỚI DẠNG 1 ĐOẠN VĂN DUY NHẤT (không dùng gạch chân, không dùng dấu gạch đầu dòng, không xuống dòng). 
    """

    response = MODEL.generate_content(prompt)
    
    import re
    clean_text = response.text.replace('\n', ' ').replace('- ', '').replace('*', '').strip()
    clean_text = re.sub(' +', ' ', clean_text)

    return clean_text

def run_report_agent(df, notification_service):
    target_date = (datetime.today() - timedelta(days=1)).date()
    grouped_tutors = {}
        
    for _, tutor in df.iterrows():
        raw_date = tutor['ngày làm việc']
        if pd.isna(raw_date):
            continue
            
        if hasattr(raw_date, 'date'):
            tutor_date = raw_date.date()
        else:
            # Fallback for string dates
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
                "end": str(tutor['giờ tan ca']).strip(),
                "actual_start": str(tutor['giờ chấm công']).strip(),
                "actual_end": str(tutor['giờ nghỉ']).strip()
            }
            
            if tutor_name not in grouped_tutors:
                grouped_tutors[tutor_name] = {
                    "date_str": date_str,
                    "shifts": []
                }
            grouped_tutors[tutor_name]["shifts"].append(shift_info)

    for tutor_name, info in grouped_tutors.items():
        if not info["shifts"]:
            continue
            
        message = generate_report(tutor_name, info["date_str"], info["shifts"])
        notification_service(
            "Báo cáo giờ giấc hôm qua",
            message,
            tutor_name=tutor_name
        )
        save_log(message, {"type": "report", "tutor": tutor_name})

def get_yesterday_scores(df):
    target_date = (datetime.today() - timedelta(days=1)).date()
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
            shift_info = {
                "start": str(tutor['giờ vào ca']).strip(),
                "end": str(tutor['giờ tan ca']).strip(),
                "actual_start": str(tutor['giờ chấm công']).strip(),
                "actual_end": str(tutor['giờ nghỉ']).strip()
            }
            if tutor_name not in grouped_tutors:
                grouped_tutors[tutor_name] = {"shifts": []}
            grouped_tutors[tutor_name]["shifts"].append(shift_info)

    results = []
    for tutor_name, info in grouped_tutors.items():
        total_late = 0
        total_early = 0
        for shift in info["shifts"]:
            total_late += check_late(shift["actual_start"], shift["start"])
            total_early += check_early_leave(shift["actual_end"], shift["end"])
        
        score = calculate_score(total_late, total_early)
        results.append({
            "Tên gia sư": tutor_name, 
            "Điểm": score, 
            "Đi muộn (phút)": total_late, 
            "Về sớm (phút)": total_early
        })
    
    results.sort(key=lambda x: (-x["Điểm"], x["Đi muộn (phút)"] + x["Về sớm (phút)"], x["Tên gia sư"]))
    return results
