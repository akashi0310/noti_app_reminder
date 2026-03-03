from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

client = QdrantClient(url="http://localhost:6333")  # Connect to Docker instance

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

COLLECTION_NAME = "tutor_logs"

def init_qdrant():
    if not client.collection_exists(collection_name=COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

def save_log(text, metadata):
    vector = embedding_model.encode(text).tolist()

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": text,
                    **metadata
                }
            )
        ]
    )

def search_log(query_text, tutor_name=None, limit=3):
    query_vector = embedding_model.encode(query_text).tolist()

    filter_conditions = None
    if tutor_name:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="tutor",  # Dựa trên metadata lúc lưu
                    match=MatchValue(value=tutor_name)
                )
            ]
        )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=filter_conditions,
        limit=limit
    )

    return [hit.payload["text"] for hit in results.points if hit.payload]

def ingest_excel_data(df):
    """
    Đọc tất cả các dòng từ DataFrame Excel và đưa vào Qdrant như lịch sử.
    """
    count = 0
    for idx, row in df.iterrows():
        # Xây dựng nội dung log cho dòng dữ liệu này
        tutor_name = str(row.get("tên gs", "")).strip()
        date_str = str(row.get("ngày làm việc", "")).strip()
        start_expected = str(row.get("giờ vào ca", "")).strip()
        end_expected = str(row.get("giờ tan ca", "")).strip()
        start_actual = str(row.get("giờ chấm công", "")).strip()
        end_actual = str(row.get("giờ nghỉ", "")).strip()

        if not tutor_name or not date_str:
            continue
            
        text = (f"Lịch sử ngày {date_str}: Gia sư {tutor_name} có ca làm việc "
                f"từ {start_expected} đến {end_expected}. "
                f"Thực tế quẹt thẻ vào lúc {start_actual} và ra lúc {end_actual}.")

        try:
            # Kiểm tra xem log cho ca này đã lưu chưa để tránh duplicate
            # Tìm kiếm exact match date & tutor, đây là bản giả lập bằng semantic
            # Thực tế save_log ghi đè theo ID nếu UUID cố định, 
            # nhưng ta dùng UUID ngẫu nhiên, nên ta tìm kiếm nhanh xem vector có trùng logic ko
            logs_found = search_log(f"Lịch sử ngày {date_str} ca làm việc từ {start_expected}", tutor_name=tutor_name, limit=1)
            
            # Nếu tìm thấy một câu tương tự cho ngày hôm đó, skip (hoặc có thể so sánh chuỗi)
            is_duplicate = False
            for existing_text in logs_found:
                if date_str in existing_text and start_expected in existing_text:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                save_log(text, {
                    "type": "history_excel",
                    "tutor": tutor_name,
                    "date": date_str
                })
                count += 1
        except Exception as e:
            pass
            
    return count