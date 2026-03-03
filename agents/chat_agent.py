from qdrant_client import models
from config import MODEL
from database.qdrant_store import search_log

def chat_agent(query, tutor_name=None):
    # Retrieve relevant past logs from Qdrant
    logs = search_log(query, tutor_name=tutor_name, limit=20)
    
    # Construct context
    context = "\n".join(logs) if logs else "Không có thông tin lịch sử nào liên quan."
    
    prompt = f"""
    Bạn là một trợ lý AI phân tích dữ liệu giờ giấc. Hãy dùng ĐÚNG các thông tin lịch sử dưới đây để trả lời câu hỏi của người dùng.
    Nếu không có thông tin, hãy báo không tìm thấy. Không tự bịa thông tin.

    QUY TẮC TÍNH ĐIỂM CHUYÊN CẦN QUAN TRỌNG:
    - Mặc định mỗi ngày/ca làm việc gia sư có tối đa 10 điểm.
    - Số phút đi muộn = (Thời gian quẹt thẻ vào THỰC TẾ) - (Thời gian bắt đầu CA LÀM VIỆC DỰ KIẾN). Đi muộn 1 phút trừ 1 điểm.
    - Số phút về sớm = (Thời gian kết thúc CA LÀM VIỆC DỰ KIẾN) - (Thời gian quẹt thẻ ra THỰC TẾ). Về sớm 1 phút trừ 1 điểm.
    - Điểm tối thiểu là 0.
    Nếu người dùng hỏi về điểm số, hãy dựa vào số phút đi muộn/về sớm trong Log để tự làm phép tính trừ và báo cáo Điểm chính xác.

    Thông tin lịch sử (context):
    {context}

    Câu hỏi của gia sư:
    {query}
    """
    
    response = MODEL.generate_content(prompt)
    return response.text

def run_chat_agent(query, tutor_name):
    # This is simple right now, but could be extended
    answer = chat_agent(query, tutor_name)
    return answer
