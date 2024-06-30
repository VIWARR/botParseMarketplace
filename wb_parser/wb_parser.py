import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import numpy as np
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from wb_parser.utils import *


# Инициализация драйвера Selenium
def init_driver():
    # Настройка Selenium
    options = Options()
    options.add_argument('--headless')  # Запуск в фоновом режиме (без графического интерфейса)
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920x1080')

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver


# Функция прокрутки страницы вниз
def scroll_down(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)


# Функция для парсинга страницы товара
def parse_product_page(driver, product_url):
    driver.get(product_url)
    time.sleep(2)

    # Получение HTML-кода страницы товара
    product_soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Бренд товара
    brand_elem = product_soup.find('a', class_='is-link full-details-item__value-logo')
    brand = brand_elem.text.strip() if brand_elem else 'Бренд отсутствует'

    # Поставщик товара
    supplier_elem = product_soup.find('span', class_='seller-name')
    supplier = supplier_elem.text.strip() if supplier_elem else "Поставщик отсутствует"

    # Цена товара
    price_elem = product_soup.find('span', class_='product-price-current__value')
    price = remove_chars_and_convert_to_int(price_elem.text.strip(), 3) if price_elem else np.nan

    # Объем товара (если есть)
    volume = np.nan
    details_items = product_soup.find_all('tr', class_='full-details-item')
    for item in details_items:
        th = item.find('th', class_='full-details-item__name')
        if th and th.text.strip() == 'Объем товара':
            td = item.find('td', class_='full-details-item__value')
            if td:
                volume = remove_chars_and_convert_to_int(td.text.strip(), 3)
                break

    # Рейтинг товара
    rating_item = product_soup.find('div', class_='product-header__rating-value')
    rating = rating_item.text.strip() if rating_item else np.nan

    # Количество отзывов
    reviews_count_item = product_soup.find('span', {'data-tag': 'visualFeedbackCount', 'itemprop': 'reviewCount'})
    reviews_count = reviews_count_item.text.strip() if reviews_count_item else np.nan

    print([brand, supplier, price, volume, rating, reviews_count, product_url])


    return [brand, supplier, price, volume, rating, reviews_count, product_url]


# Функция для парсинга ссылок на товары с текущей страницы
def parse_current_page(driver, page_url):
    # Получение HTML-кода страницы
    driver.get(page_url)
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Парсинг ссылок на страницы товаров
    links = soup.find_all("a", class_="product-card__link")
    product_urls = ["https://www.wildberries.by" + link["href"] for link in links]

    return product_urls


# Функция поиска по сайту
def navigate_to_search_page(driver, search_term):
    driver.get("https://www.wildberries.by/")

    # Явное ожидание элемента поиска
    wait = WebDriverWait(driver, 10)
    search_box = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'search-component-input')))

    # Поиск товаров
    search_box.send_keys(search_term)
    search_box.send_keys(Keys.RETURN)

    time.sleep(3)  # Ожидание загрузки страницы

    return driver.current_url


# Функция поиска ссылок пагинации
def navigate_to_next_page(driver):
    try:
        # Поиск элемента пагинации
        pagination = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'pagination--bottom'))
        )

        # Прокрутка страницы вниз
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        # Поиск кнопки "Дальше" внутри элемента пагинации
        next_button = pagination.find_element(By.XPATH, ".//button[contains(@class, 'pagination__next')]")

        if not next_button.is_enabled():
            return None

        next_button.click()
        time.sleep(5)
        return driver.current_url

    except Exception as e:
        print(f"Error navigating to next page: {e}")
        return None


# Функция парсинга товаров
async def parse_products(search_term, num_pages, driver=None):
    print("- - - parse_products - - - ")

    print(f"search_term {type(search_term)}")
    print(f"num_pages {type(num_pages)}")

    if driver is None:
        driver = init_driver()

    columns = ['brand', 'supplier', 'price(BYN)', 'volume(ml)', 'rating', 'reviews_count', 'product_url']
    df = pd.DataFrame(columns=columns)

    try:
        # Поиск по товару
        start_url = navigate_to_search_page(driver, search_term)
        if not start_url:
            print(f"Не удалось найти страницу поиска для запроса '{search_term}'")
            return

        search_page_urls = [start_url]
        print(f"1. - - start_url - - - ")
        print(f"{start_url}")

        # Парсинг страниц поиска и товаров в отдельных потоках
        with ThreadPoolExecutor() as executor:
            futures = []
            for page in range(1, num_pages):
                next_page_url = navigate_to_next_page(driver)
                print(f"2. - - next_page_url- - - ")
                print(f"{next_page_url}")
                if next_page_url:
                    search_page_urls.append(next_page_url)
                else:
                    break

            for page_url in search_page_urls:
                futures.append(executor.submit(parse_current_page, driver, page_url))

            for future in as_completed(futures):
                try:
                    product_urls = future.result()
                    if product_urls:
                        for product_url in product_urls:
                            new_row = pd.DataFrame([parse_product_page(driver, product_url)], columns=columns)
                            print(new_row)
                            df = pd.concat([df, new_row], ignore_index=True)
                except Exception as e:
                    print(f"Error parsing search page: {e}")

        return df

    except Exception as e:
        print(f"Произошла ошибка: {e}")

    finally:
        driver.quit()