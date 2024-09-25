import time

from selenium import webdriver
from selenium.webdriver.common.by import By


class ResetRouter:
    option = webdriver.ChromeOptions()
    option.add_argument('--headless')
    driver = webdriver.Chrome(options=option)

    def reset_router(self):
        url = 'http://192.168.0.1/'
        self.driver.get(url)
        time.sleep(1)
        self.driver.find_element(By.XPATH, '//*[@id="local-pwd-tb"]/div[2]/div[1]/span[2]/input[1]').send_keys('1997712345ABCD')
        time.sleep(1)
        self.driver.find_element(By.XPATH, '//*[@id="local-login-button"]').click()
        time.sleep(1)
        self.driver.get('http://192.168.0.1/#reboot')
        time.sleep(1)
        self.driver.find_element(By.XPATH, '//*[@id="reboot-button"]').click()
        time.sleep(1)
        self.driver.find_element(By.XPATH, '//*[@id="reboot-confirm-msg-btn-ok"]').click()
        time.sleep(5)
        self.driver.close()
        self.driver.quit()
        print('Ожидание...')
        for i in range(55):
            time.sleep(1)
            print(i)


if __name__ == '__main__':
    reset = ResetRouter()
    reset.reset_router()
