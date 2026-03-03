notifications = []

def send_email(subject, content):
    """
    Demo notification sender.
    Thay vì gửi email thật, chỉ lưu thông báo vào bộ nhớ
    để web hiển thị ở góc màn hình.
    """
    notifications.append(
        {
            "subject": subject,
            "content": content,
        }
    )

def get_notifications():
    return notifications