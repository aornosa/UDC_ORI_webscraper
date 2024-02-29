import sys
import threading
import time
from math import floor

from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options

import csv

url = "https://udc.adv-pub.moveonfr.com/report-page-1575/"
fname = "erasmus"
from_uni = "Universidade da Coruña"
fac = "Facultad de Informática"
from_name = f'{from_uni}\n{fac}'

filter_by_fac = True

options = Options()
options.add_argument('--headless')
options.add_argument('start-maximized')
options.add_argument("window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

stage = 'start'
print('Starting...\n')


class site:
    # city: str
    # country: str
    # uni_name: str
    # course_lnk: str
    # lang_req: str
    # course_lang: str
    # av_spots: int

    def __init__(self):
        self.city = "city"
        self.country = "country"
        self.uni_name = "uni_name"
        self.course_lnk = "course_lnk"
        self.lang_req = "lang_req"
        self.course_lang = "course_lang"
        self.av_spots = 1
        self.mov_type = "mov_type"
        self.course_lvl = "course_lvl"
        self.rating = 0

    def __str__(self):
        return f"UniversityCourse(city={self.city}, country={self.country}, uni_name={self.uni_name}, " \
               f"course_lnk={self.course_lnk}, lang_req={self.lang_req}, course_lang={self.course_lang}, " \
               f"av_spots={self.av_spots})"

    def __to_row__(self):
        return [self.city, self.country, self.uni_name, self.course_lnk, self.lang_req, self.course_lang,
                self.av_spots, self.mov_type, self.course_lvl, self.rating]


def color_code_spots(n: int):
    if n == 1:
        return f'\033[1;31m{n}'
    elif 1 < n <= 3:
        return f'\033[1;33m{n}'
    elif 3 < n <= 5:
        return f'\033[1;32m{n}'
    elif n > 5:
        return f'\033[1;34m{n}'


def color_code_percentile(n: int):
    if 0 <= n < 25:
        return f'\033[1;31m{n}'
    elif 25 <= n < 50:
        return f'\033[1;33m{n}'
    elif 50 <= n < 80:
        return f'\033[1;92m{n}'
    elif n > 80:
        return f'\033[1;36m{n}'
    else:
        f"{n}"


def scroll_down(web_driver):
    print(f'\rGathering data...\n')

    # Get scroll height.
    last_height = web_driver.execute_script("return document.body.scrollHeight")

    while True:

        for button in driver.find_elements(By.CLASS_NAME, 'showloadmorecss'):
            ActionChains(driver).move_to_element(button).click(button).perform()

        # Scroll down to the bottom.
        web_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load the page.
        time.sleep(1)

        # Calculate new scroll height and compare with last scroll height.
        new_height = web_driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            break

        last_height = new_height


def calculate_rating(uni: site):
    lang_req_score = (1 if 'B1' in uni.lang_req else 0.825 if 'B2' in uni.lang_req else 0.5) * \
                     (1 if ('English' or 'Spanish' or 'Español') in uni.lang_req else 0.5)
    course_lang_score = (1 if ('English' or 'Inglés' or 'Spanish' or 'Español') in uni.lang_req else 0.5)
    lang_score = lang_req_score * course_lang_score
    placement_score = (1 if ('República Checa' or 'Hungría' or 'Polonia'
                             or 'Rumanía' or 'Eslovenia' or 'Austria') in uni.country else 0.75)
    total = ((uni.av_spots / 4) + lang_score * 2 + placement_score * 2) * (100 / 5)
    return total


def get_sites(link: str):
    lst = []

    driver.get(link)
    driver.maximize_window()
    time.sleep(3)
    scroll_down(driver)

    print('\rGathering details...\n')
    for item_div in driver.find_elements(By.CLASS_NAME, '_university_block'):
        new_uni = site()
        origen = item_div.find_element(By.XPATH,
                                       './/*[@class="col-md-4 col-sm-6 col-xs-6"]/following-sibling::*').text

        if filter_by_fac and from_name != origen:
            continue

        new_uni.uni_name = item_div.find_element(By.CLASS_NAME, '_univname').text

        try:
            new_uni.mov_type = item_div.find_element(
                By.XPATH, '//*[contains(text(), "Programa")]'
                          '/../../following-sibling::*').text
        except NoSuchElementException:
            new_uni.mov_type = "Not Specified"

        details = item_div.find_element(By.CSS_SELECTOR, '#moredetailsid > div > div > span')
        ActionChains(driver).move_to_element(details).click(details).perform()
        time.sleep(0.25)
        # Get details page 1
        try:
            spots_str = item_div.find_element(
                By.XPATH, '//*[contains(text(), "Plazas restantes")]/../../following-sibling::*').text
            new_uni.av_spots = next((int(char) for char in spots_str if char.isdigit()), None)
        except NoSuchElementException:
            new_uni.av_spots = None

        try:
            new_uni.lang_req = item_div.find_element(
                By.XPATH, '//*[contains(text(), "Recomendaciones/requisitos lingüísticos")]'
                          '/../../following-sibling::*').text
        except NoSuchElementException:
            new_uni.lang_req = "English B1"

        try:
            new_uni.course_lang = item_div.find_element(
                By.XPATH, '//*[contains(text(), "Idioma de enseñanza")]'
                          '/../../following-sibling::*').text
        except NoSuchElementException:
            new_uni.course_lang = "Not Specified"

        try:
            new_uni.course_lvl = item_div.find_element(
                By.XPATH, '//*[contains(text(), "Nivel")]'
                          '/../../following-sibling::*').text
        except NoSuchElementException:
            new_uni.course_lvl = "Not Specified"

        # Move to page 2
        gotonext = item_div.find_element(By.XPATH, '//*[@id="whichtabinstitutions"]')
        ActionChains(driver).move_to_element(gotonext).click(gotonext).perform()

        # Get details page 2
        try:
            new_uni.country = item_div.find_element(
                By.XPATH, '//*[contains(text(), "País")]'
                          '/../../following-sibling::*').text
        except NoSuchElementException:
            new_uni.country = "Not Specified"

        try:
            new_uni.city = item_div.find_element(
                By.XPATH, '//*[contains(text(), "Ciudad")]'
                          '/../../following-sibling::*').text
        except NoSuchElementException:
            new_uni.city = "Not Specified"

        try:
            new_uni.course_lnk = item_div.find_element(
                By.XPATH, '//*[contains(text(), "Catálogo de cursos en destino")]'
                          '/../../following-sibling::*').text
        except NoSuchElementException:
            new_uni.course_lnk = "Not Specified"

        # Close window by clicking away
        ActionChains(driver).move_to_element(details).click(details).perform()

        new_uni.rating = calculate_rating(new_uni)
        lst.append(new_uni)

    driver.close()
    return lst


def print_sites(lst: list[site]):
    global stage
    stage = 'Done'
    time.sleep(1)

    print(f'\033[1;33m'
          f'---- Found \033[1;36m{len(lst)} \033[1;33moptions for \033[1;31m{fac}, {from_uni}: \033[1;33m----\n')
    for loc in lst:
        # print(loc.__str__())
        print(f"\033[0;32mNombre:\033[1;37m {loc.uni_name}\n"
              f"\033[0;32mCiudad:\033[1;37m {loc.city}\n"
              f"\033[0;32mPaís:\033[1;37m {loc.country}\n"
              f"\033[0;32mPlazas:\033[1;37m {color_code_spots(loc.av_spots)}\n"
              f"\033[0;32mCertificado Requerido:\033[1;37m {loc.lang_req}\n"
              f"\033[0;32mIdioma Clases:\033[1;37m {loc.course_lang}\n"
              f"\033[0;32mCatálogo Clases:\033[1;37m {loc.course_lnk}\n"
              f"\033[0;32mTipo Movilidad:\033[1;37m {loc.mov_type}\n"
              f"\033[0;32mNivel:\033[1;37m {loc.course_lvl}\n"
              f"\033[0;32mPuntuación:\033[1;37m {color_code_percentile(round(loc.rating))}%\n"
              )
    return


def save_to_csv(lst: list[site]):

    with open(f'{fname}.csv', 'w', encoding='utf-16') as f:
        # Create a CSV writer object that will write to the file 'f'
        csv_writer = csv.writer(f)

        # Write the field names (column headers) to the first row of the CSV file
        csv_writer.writerow(['city', 'country', 'uni_name', 'course_lnk',
                             'lang_req', 'course_lang', 'av_spots', 'mov_type',
                             'course_lvl', 'rating'])

        # Write all the rows of data to the CSV file
        for row in lst:
            csv_writer.writerow(site.__to_row__(row))


if __name__ == '__main__':
    start_time = time.time()

    def timer():
        while stage != 'Done':
            sys.stdout.write(f'\rTime elapsed: {floor((time.time() + 0.5 - start_time) / 60)}:'
                             f'{format(round(time.time() - start_time) % 60, "02d")}')
            sys.stdout.flush()
            time.sleep(0.1)
        print('\rDone!     ')


    t2 = threading.Thread(target=timer)
    t2.start()

    site_list = get_sites(url)
    print_sites(site_list)
    save_to_csv(site_list)
