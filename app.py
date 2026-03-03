import streamlit as st
st.set_page_config(page_title="Tutor Multi-Agent System", layout="wide")

from data.excel_loader import load_excel
from agents.orchestrator import Orchestrator
from agents.chat_agent import run_chat_agent
from agents.report_agent import get_yesterday_scores
from database.qdrant_store import init_qdrant, ingest_excel_data
import threading
from scheduler import start_scheduler

st.title("🎓 Tutor Multi-Agent System")

init_qdrant()

import json
import os

MAILBOX_FILE = "mailbox.json"

def load_mailbox():
    if not os.path.exists(MAILBOX_FILE):
        return []
    try:
        with open(MAILBOX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_mailbox(data):
    with open(MAILBOX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

uploaded_file = r"C:\Users\lapla\.vscode\code_space\edupia\deadline5-3\noti_app_reminder\Data.xlsx"

if uploaded_file:
    df = load_excel(uploaded_file)
    df_display = df.astype(str)

    def ui_notification(subject, content, tutor_name=None):
        mailbox = load_mailbox()
        mailbox.append({
            "tutor_name": tutor_name,
            "subject": subject,
            "content": content,
            "read": False
        })
        save_mailbox(mailbox)

    orchestrator = Orchestrator(df, ui_notification)

    tab_manager, tab_tutor = st.tabs(["💼 Dành cho Quản lý", "👩‍🏫 Dành cho Gia sư"])

    with tab_manager:
        col_main, col_chat = st.columns([1, 1])

        with col_main:
            st.markdown("### 🏆 Rank điểm")
            scores_df = get_yesterday_scores(df)
            if scores_df:
                st.dataframe(scores_df, width='stretch', hide_index=True)
            else:
                st.info("Không có dữ liệu chấm điểm cho ngày hôm qua.")
                
            st.markdown("---")
            st.markdown("### 🛠️ Manual Testing")
            if st.button("Chạy thử báo cáo 9h"):
                result = orchestrator.run_task("report")
                st.success(result)

            if st.button("Chạy thử nhắc lịch 17h"):
                result = orchestrator.run_task("reminder")
                st.success(result)

            if st.button("Bật Auto Scheduler"):
                threading.Thread(
                    target=start_scheduler,
                    args=(orchestrator,),
                    daemon=True
                ).start()
                st.success("Scheduler đang chạy nền (tạo thông báo nội bộ)")
                
            st.markdown("---")
            st.markdown("### 🗄️ Database Management")
            if st.button("📥 Đồng bộ toàn bộ dữ liệu Excel"):
                with st.spinner("Đang xử lý và đồng bộ dữ liệu vào Qdrant (có thể mất vài phút)..."):
                    count = ingest_excel_data(df)
                    st.success(f"Đã đồng bộ thành công {count} bản ghi mới vào Database!")

        with col_chat:
            st.markdown("### 🤖 Chatbot support TM")
            
            user_query = st.text_input("Yêu cầu của bạn (VD: Nhập câu hỏi vào đây):", key="manager_chat")
            
            if st.button("Gửi cho Chatbot", key="btn_manager"):
                if not user_query:
                    st.warning("Vui lòng nhập yêu cầu.")
                else:
                    with st.spinner("Chatbot đang xử lý..."):
                        response = orchestrator.handle_request(user_query=user_query)
                        st.success("Kết quả:")
                        st.write(response)

    with tab_tutor:
        tutor_list = df["tên gs"].dropna().astype(str).str.strip().unique().tolist()
        
        selected_tutor = st.selectbox("Đăng nhập với tư cách Gia sư:", [""] + tutor_list)
        
        if selected_tutor:
            st.markdown(f"### 📬 Hộp thư của {selected_tutor}")
            
            mailbox = load_mailbox()
            unread_count = 0
            
            for notif in mailbox:
                if notif.get("tutor_name") == selected_tutor and not notif.get("read"):
                    st.toast(f"**{notif['subject']}**\n\n{notif['content']}", icon="🔔")
                    notif["read"] = True
                    unread_count += 1
            
            # Lưu lại trạng thái đã đọc
            if unread_count > 0:
                save_mailbox(mailbox)
                    
            if unread_count == 0:
                st.info("Không có thông báo mới.")
                
            with st.expander("Lịch sử thông báo"):
                has_old = False
                
                if st.button("🗑️ Xoá toàn bộ lịch sử", key=f"clear_history_{selected_tutor}"):
                    new_mailbox = [n for n in mailbox if n.get("tutor_name") != selected_tutor]
                    save_mailbox(new_mailbox)
                    mailbox = new_mailbox
                    st.success("Đã xoá lịch sử thông báo!")
                    st.rerun()
                
                for notif in reversed(mailbox):
                    if notif.get("tutor_name") == selected_tutor:
                        has_old = True
                        st.markdown(f"**{notif['subject']}**: {notif['content']}")
                if not has_old:
                    st.write("Chưa có thông báo nào.")
                
            st.markdown("---")
            st.markdown("### 💬 Trợ lý AI Cá nhân")
            
            tutor_query = st.text_input(f"Hỏi AI về lịch sử làm việc của bạn:", key="tutor_chat")
            
            if st.button("Hỏi AI", key="btn_tutor"):
                if not tutor_query:
                    st.warning("Vui lòng nhập câu hỏi.")
                else:
                    with st.spinner("AI đang tìm thông tin..."):
                        response = run_chat_agent(tutor_query, tutor_name=selected_tutor)
                        st.info(response)
