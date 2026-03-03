from agents.report_agent import run_report_agent
from agents.reminder_tool import run_reminder_tool
from agents.chat_agent import run_chat_agent
from config import MODEL
import json

class Orchestrator:

    def __init__(self, df, notification_service):
        self.df = df
        self.notify = notification_service

    def handle_request(self, user_query):
        prompt = f"""
        Bạn là một hệ thống Orchestrator (Điều phối viên) thông minh.
        Bạn có 3 công cụ/tác vụ có thể thực thi:
        1. "report": Chạy trình tạo báo cáo chấm công của ngày hôm qua cho tất cả gia sư.
        2. "reminder": Chạy trình nhắc nhở lịch dạy hôm nay cho tất cả gia sư.
        3. "chat": Trả lời câu hỏi tra cứu thông tin của gia sư.

        Dựa vào câu lệnh của người dùng dưới đây, hãy xác định họ muốn gọi công cụ nào và NẾU họ đang hỏi về một gia sư cụ thể (thường để chat/tra cứu), hãy trích xuất tên người đó.
        Trả về kết quả DƯỚI DẠNG JSON với định dạng:
        {{
            "task": "report" | "reminder" | "chat" | "unknown",
            "tutor_name": "Tên gia sư (nếu có, nếu không thì để null)"
        }}

        Câu lệnh của người dùng: "{user_query}"
        """

        try:
            # Generate response from Gemini
            response = MODEL.generate_content(prompt)
            # Find JSON block in the response text, in case it includes markdown formatting
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            
            result = json.loads(text)
            task_type = result.get("task", "unknown")
            extracted_tutor = result.get("tutor_name")
            
            if task_type == "report":
                return self.run_task("report")
            elif task_type == "reminder":
                return self.run_task("reminder")
            elif task_type == "chat":
                # For chat, we forward the actual user query and the LLM-extracted tutor name
                return self.run_task("chat", query=user_query, tutor_name=extracted_tutor)
            else:
                return "Xin lỗi, tôi không hiểu yêu cầu của bạn. Bạn có thể nói rõ hơn bạn muốn xem báo cáo, gửi nhắc lịch hay tra cứu lịch sử không?"
        except Exception as e:
            return f"Lỗi hệ thống khi phân tích yêu cầu: {str(e)}"

    def run_task(self, task_type, **kwargs):
        if task_type == "report":
            run_report_agent(self.df, self.notify)
            return "Đã hoàn tất gửi báo cáo chấm công."

        elif task_type == "reminder":
            run_reminder_tool(self.df, self.notify)
            return "Đã hoàn tất gửi nhắc nhở lịch dạy."
            
        elif task_type == "chat":
            query = kwargs.get("query")
            tutor_name = kwargs.get("tutor_name")
            return run_chat_agent(query, tutor_name)
