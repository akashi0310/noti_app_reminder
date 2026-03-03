import schedule
import time

def start_scheduler(main_agent):

    schedule.every().day.at("09:00").do(
        lambda: main_agent.run_task("report")
    )

    schedule.every().day.at("17:00").do(
        lambda: main_agent.run_task("reminder")
    )

    while True:
        schedule.run_pending()
        time.sleep(60)