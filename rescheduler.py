import time
import atexit
from datetime import datetime
import argparse
import requests
from utils import get_config, UrlConstructor, SchedulerUtil, COOLDOWN_TIME, FACILITIES

from logger import logger
class VisaScheduler:
    def __init__(self, config):
        self.urls = UrlConstructor(config)
        self.util = SchedulerUtil(config)
        self.token_expired = True

    @staticmethod
    def MY_CONDITION_DATE(year, month, day):
        return True  # No custom condition wanted for the new scheduled date

    # def MY_CONDITION_TIME(hour, minute): return int(hour) >= 8 and int(hour) <= 12 and int(minute) == 0
    @staticmethod
    def MY_CONDITION_TIME(hour, minute):
        return True  # No custom condition wanted for the new scheduled date
    
    def login(self):

        if self.util.is_logged_in() and not self.token_expired:
            self.util.go_to_page(self.urls.get_appointment_url())
        else:
            login_url = self.urls.get_login_url()
            self.util.prepare_login_form(login_url)
            self.util.fill_login_form(self.urls.get_appointment_url())
            self.token_expired = False

    def get_earlier_date(self, facility_id):
        if self.token_expired:
            return None

        url = self.urls.get_date_api_path(facility_id)
        referer = self.urls.get_appointment_url()
        headers = self.util.get_headers(referer, True, True)

        r = requests.get(url, headers=headers)

        if r.status_code == 401:
            logger.red("Token expired. Login again...")
            self.token_expired = True
            return None

        if r.status_code != 200:
            logger.red(f"Failed to get available dates, status code: {r.status_code}")
            return None

        data = r.json()
        dates = data[:5]

        for d in dates:
            date = d.get('date')
            if self.util.is_earlier(date):
                logger.green(f"Found earlier date: {date}", 1)
                year, month, day = date.split('-')
                if VisaScheduler.MY_CONDITION_DATE(year, month, day):
                        return date
            else:
                logger.red(f"[{date}] later than [{self.util.date_before.strftime('%Y-%m-%d')}]", 1)
        return None
    
    def get_available_time(self, date, facility_id):
        if self.token_expired:
            return None
        
        url = self.urls.get_time_api_path(date, facility_id)
        referer = self.urls.get_appointment_url()
        headers = self.util.get_headers(referer, True, True)
        r = requests.get(url, headers=headers)

        if r.status_code == 401:
            logger.red("Token expired. Login again...")
            self.token_expired = True
            return None

        if r.status_code != 200:
            logger.red(f"Failed to get available dates, status code: {r.status_code}")
            return None

        data = r.json()
        available_times = data.get("available_times")[::-1]

        for t in available_times:
            hour, minute = t.split(":")
            if self.MY_CONDITION_TIME(hour, minute):
                logger.green(f"Available appointment time: {date} {t}")
                return t
            
        logger.red(f"No available time found for {date}")

        return None

    
    def reschedule(self, date, facility_id):
        logger.green(f"Found date slot: {date}. Trying to reschedule...", 1)
        time = self.get_available_time(date,facility_id)

        if not time:
            return False
        
        url = self.urls.get_appointment_url()
        payload = self.util.build_reschedule_payload(facility_id, date, time)
        headers = self.util.get_headers(url)

        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

        logger.blue(f"Rescheduling for {date} {time}", 1)

        r = requests.post(url, headers=headers, data=payload)

        if r.status_code == 200 and (r.text.find('successfully scheduled') != -1):
            logger.green(f"Rescheduled successfully for {date} {time}!")
            return True
        else:
            now = datetime.now().strftime("%Y%m%d%H%M%S")
            with open(f"./{facility_id}_failed_{now}.html", "w+") as f:
                f.write(r.text)
            logger.red(f"Failed to reschedule for {date} {time}. Check {facility_id}_failed_{now}.html")
            return False
        
def ensure_working_hours():
    start_time = datetime.now()
    if start_time.hour >= 19 or start_time.hour <= 4:
        return True
    return False

def save_log():
    logger.dump(None)
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Reschedule visa appointment with the provided configuration')
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('--interval', type=int, default=60, help='seconds between two retries')
    parser.add_argument('--max_times', type=int, default=70, help='maximum times to retry if not scheduled')

    args = parser.parse_args()

    scheduler = VisaScheduler(get_config(args.config))

    count = 0
    max_times = args.max_times

    atexit.register(save_log)

    while ensure_working_hours and  count < max_times:

        try:

            logger.blue(f"-----[Retry {count+1}/{max_times}]-----")
            scheduler.login()
            time.sleep(2)

            rescheduled = False

            for facility, facility_id in FACILITIES.items():

                if rescheduled:
                    break
                
                logger.blue(f"[{facility}] :Checking for date slots ...", 1)
                date = scheduler.get_earlier_date(facility_id)
                if date:
                    rescheduled = scheduler.reschedule(date, facility_id)
                    if rescheduled:
                        print(f"Rescheduled successfully for {facility} at {date}!")
                        break
                else:
                    logger.yellow(f"No earlier date slot found for {facility}.", 1)
            
            if not rescheduled and not scheduler.token_expired:
                print(f"💩 No earlier date slots found. Retry after {args.interval} seconds...")
                time.sleep(args.interval)

        except Exception as e:
            print(f"Exception: {e}")
            time.sleep(COOLDOWN_TIME)
        finally:
            count += 1
    save_log()

    

