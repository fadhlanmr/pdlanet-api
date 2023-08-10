from selenium import webdriver
from bs4 import BeautifulSoup
import platform

class web_crawl :
    def __init__(self, url, class_list, action) -> None:
        self.url = url
        self.action = action
        self.class_list = class_list
        pass

    def browser(self):
        print("Web Crawl Started, Opening Drive")

        os = platform.system()
        try:
            if os == 'Linux' :
                self.browse = webdriver.Chrome("./chromedriver")
            elif os == 'Windows' :
                self.browse = webdriver.Chrome()
        except:
            raise ValueError('OS / Driver Not Supported')

        self.browse.get(self.url)
        html_source = self.browse.page_source
        self.browse.quit()

        return html_source
    
    def list_soup(self):
        soup = BeautifulSoup(self.browser(), 'html.parser')

        if self.class_list is not None:
            target_class = soup.find_all(class_=self.class_list)

            element = target_class
            # needs to encode utf-8. jp site
            if self.action == 'encode':
                element = [y.encode('utf-8') for y in target_class]
            return element

        elif self.class_list is None:
            all_elements_with_class = soup.find_all(class_=True)

            # IDK WHAT THE BEST PRACTICE ON HOW TO INIT LIST VAR
            elements = []
            classes = []
            for element in all_elements_with_class:
                elements += element
                classes += element.get('class')
                # needs to encode utf-8. jp site
            if self.action == 'encode':
                classes = [x.encode('utf-8') for x in classes]
                elements = [y.encode('utf-8') for y in elements]
            return elements, classes