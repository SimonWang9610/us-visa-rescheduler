import time
from datetime import datetime
import argparse
import requests
from utils import get_config, UrlConstructor, SchedulerUtil, COOLDOWN_TIME, FACILITIES

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
            print("Login start...")
            self.util.fill_login_form(self.urls.get_appointment_url())
            self.token_expired = False

    def get_earlier_date(self, facility_id):
        if self.token_expired:
            return None

        url = self.urls.get_date_api_path(facility_id)
        print("Querying available dates: ", url)
        referer = self.urls.get_appointment_url()
        headers = self.util.get_headers(referer, True, True)

        r = requests.get(url, headers=headers)

        if r.status_code == 401:
            print("❌ Token expired. Login again...")
            self.token_expired = True
            return None

        if r.status_code != 200:
            print(f"❌ Failed to get available dates, status code: {r.status_code}")
            return None

        data = r.json()
        dates = data[:5]

        for d in dates:
            date = d.get('date')
            if self.util.is_earlier(date):
                year, month, day = date.split('-')
                if VisaScheduler.MY_CONDITION_DATE(year, month, day):
                        return date
            else:
                print(f"    ❌ Date {date} not desired")
        return None
    
    def get_available_time(self, date, facility_id):
        if self.token_expired:
            return None
        
        url = self.urls.get_time_api_path(date, facility_id)
        referer = self.urls.get_appointment_url()
        print("Querying available time slots: ", url)
        headers = self.util.get_headers(referer, True, True)
        r = requests.get(url, headers=headers)

        if r.status_code == 401:
            print("❌ Token expired. Login again...")
            self.token_expired = True
            return None

        if r.status_code != 200:
            print(f"❌ Failed to get available dates, status code: {r.status_code}")
            return None

        data = r.json()
        available_times = data.get("available_times")[::-1]

        for t in available_times:
            hour, minute = t.split(":")
            if self.MY_CONDITION_TIME(hour, minute):
                print(f"Available appointment time: {date} {t}")
                return t

        return None

    
    def reschedule(self, date):
        print(f"    ✅ Found earlier date: {date}. Trying to reschedule...")
        time = self.get_available_time(date)

        if not time:
            print(f"    ❌ No available time found for {date}")
            return False
        
        url = self.urls.get_appointment_url()
        payload = self.util.build_reschedule_payload(date, time)
        headers = self.util.get_headers(url)

        r = requests.post(url, headers=headers, data=payload)

        if r.status_code == 200 and (r.text.find('Successfully Scheduled') != -1):
            print(f"✅ Rescheduled Successfully! {date} {time}")
            return True
        else:
            print(f"❌ Reschedule Failed. {date} {time}. [{r.text}]")
            return False

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Reschedule visa appointment with the provided configuration')
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('--interval', type=int, default=60, help='seconds between two retries')
    parser.add_argument('--max_times', type=int, default=60, help='maximum times to retry if not scheduled')

    args = parser.parse_args()

    scheduler = VisaScheduler(get_config(args.config))

    count = 0
    max_times = args.max_times

    while count < max_times:
        try:
            start_time = datetime.now()

            print(f">>>>>>>>>>>>>> [START] {count+1} times {start_time} <<<<<<<<<<<")
            scheduler.login()
            time.sleep(2)

            rescheduled = False

            for facility, facility_id in FACILITIES.items():

                if rescheduled:
                    break

                print(f"🧐 [{facility}] :Checking for earlier date ...")
                date = scheduler.get_earlier_date(facility_id)
                if date:
                    rescheduled = scheduler.reschedule(date)
                    if rescheduled:
                        print(f"Rescheduled successfully for {facility} at {date}!")
                        break
                else:
                    print(f"    ❌ No earlier date found for {facility}.")

            end_time = datetime.now()
            diff = end_time - start_time
            print(f">>>>>>>>>>>>>> [END] [spent {diff.seconds} seconds] <<<<<<<<<<<")
            
            if not rescheduled and not scheduler.token_expired:
                print(f"💩 No earlier date found. Retry after {args.interval} seconds...")
                time.sleep(args.interval)

        except Exception as e:
            print(f"Exception: {e}")
            time.sleep(COOLDOWN_TIME)
        finally:
            count += 1


