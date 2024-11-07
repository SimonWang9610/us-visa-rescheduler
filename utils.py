import time
import datetime
import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager


STEP_TIME = 0.5  # time between steps (interactions with forms): 0.5 seconds
COOLDOWN_TIME = 60*60  # wait time when temporary banned (empty list): 60 minutes

FACILITIES = {
    "OTTAWA": "92",
    "MONTREAL": "91",
    "TORONTO": "94",
    "QUEBEC": "93",
}

def get_config(filename='config.json'):
    with open(filename) as f:
        config = json.load(f)

        if 'username' not in config:
            raise ValueError('username not found in config.json')
        if 'password' not in config:
            raise ValueError('password not found in config.json')
        if 'schedule_id' not in config:
            raise ValueError('schedule_id not found in config.json')
        if 'date_before' not in config:
            raise ValueError('date_before not found in config.json')
        if 'country_code' not in config:
            raise ValueError('country_code not found in config.json')
        
        return config

class UrlConstructor:
    def __init__(self, config):
        self.config = config

    def get_login_url(self):
        country_code = self.config['country_code']
        return f"https://ais.usvisa-info.com/{country_code}/niv"

    def get_appointment_url(self):
        country_code = self.config['country_code']
        schedule_id = self.config['schedule_id']
        return f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/appointment"
    
    def get_date_api_path(self, facility_id):
        api_path = f"/days/{facility_id}.json?appointments[expedite]=false"

        return self.get_appointment_url() + api_path
    
    def get_time_api_path(self, date, facility_id):
        api_path = f"/times/{facility_id}.json?date={date}&appointments[expedite]=false"

        return self.get_appointment_url() + api_path
    
    
class SchedulerUtil:
    def __init__(self, config):
        self.config = config
        # service = Service(ChromeDriverManager().install())
        # self.driver = webdriver.Chrome(service=service)
        opts = webdriver.FirefoxOptions()
        opts.add_argument("--headless")
        service = Service(GeckoDriverManager().install())
        self.driver = webdriver.Firefox(options=opts, service=service)

    def prepare_login_form(self, url):
        self.driver.get(url)
        time.sleep(STEP_TIME)
        a = self.driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
        a.click()
        time.sleep(STEP_TIME)

        print("Login start...")
        href = self.driver.find_element(By.XPATH, '//*[@id="header"]/nav/div[1]/div[1]/div[2]/div[1]/ul/li[3]/a')
    
        href.click()
        time.sleep(STEP_TIME)
        Wait(self.driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

        print("\tclick bounce")
        a = self.driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
        a.click()
        time.sleep(STEP_TIME)
        
    def is_logged_in(self):
        session = self.driver.get_cookie("_yatri_session")

        if not session:
            return False
        
        cookie = self.driver.get_cookie("_yatri_session")["value"]
        if len(cookie) <= 350:
            return False
        return True
    
    def fill_login_form(self, redirect, waiting_time=60):
            username = self.config["username"]
            password = self.config["password"]

            user = self.driver.find_element(By.ID, 'user_email')
            user.send_keys(self.config["username"])
            time.sleep(1)

            password = self.driver.find_element(By.ID, 'user_password')
            password.send_keys(self.config["password"])
            time.sleep(1)

            box = self.driver.find_element(By.CLASS_NAME, 'icheckbox')
            box.click()
            time.sleep(1)

            btn = self.driver.find_element(By.NAME, 'commit')
            btn.click()
            time.sleep(1)

            # print("\twaiting for continue appointment information")
            # Wait(self.driver, waiting_time).until(EC.presence_of_element_located((By.CLASS_NAME, 'consular-appt')))

            print("Login successful!")

            if redirect:
                time.sleep(5)
                self.go_to_page(redirect)

    def get_headers(self, referer, x_requested_with=False, accept=False):
        agent = self.driver.execute_script("return navigator.userAgent;")
        cookie = self.driver.get_cookie("_yatri_session")["value"]

        headers = {
            "User-Agent": agent,
            "Cookie": "_yatri_session=" + cookie,
            "Referer": referer,
        }

        if x_requested_with:
            headers["X-Requested-With"] = "XMLHttpRequest"

        if accept:
            headers["Accept"] = "application/json, text/javascript, */*; q=0.01"

        return headers
    
    def go_to_page(self, url):

        current_url = self.driver.current_url

        if current_url != url:
            print(f"Going to {url}")
            self.driver.get(url)
    
    def is_earlier(self, date):
        return datetime.datetime.strptime(date, '%Y-%m-%d') < datetime.datetime.strptime(self.config["date_before"], '%Y-%m-%d')
    
    def build_reschedule_payload(self,facility_id, date, time):

        token = self.driver.find_element(By.NAME, 'authenticity_token').get_attribute('value')
        confirmed_limit_message = self.driver.find_element(By.NAME, 'confirmed_limit_message').get_attribute('value')
        use_consulate_appointment_capacity = self.driver.find_element(By.NAME, 'use_consulate_appointment_capacity').get_attribute('value')

        return {
            "authenticity_token": token,
            "confirmed_limit_message": confirmed_limit_message,
            "use_consulate_appointment_capacity": use_consulate_appointment_capacity,
            "appointments[consulate_appointment][facility_id]": facility_id,
            "appointments[consulate_appointment][date]": date,
            "appointments[consulate_appointment][time]": time,
        }

