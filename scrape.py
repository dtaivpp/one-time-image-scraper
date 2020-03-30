import requests
import os
from net_tools import generate_headers
from bs4 import BeautifulSoup
import lxml
import json
import pickle
import logging

def get_link_list(id):
    '''Return list of links'''
    _path = os.path.join(os.getcwd(), 'state', f"{id}.txt")
    links = []
    with open(_path, 'r') as f:
        for line in f:
            links.append(line.strip())

    return links


class Scraper:
    def __init__(self, worker_id, last_link_index=None, last_page_index=None, last_metadata=None):
        self.worker_id = worker_id
        self.session= requests.Session()
        self.session.trust_env=False
        self.headers = generate_headers()
        self.cookie_jar = self.get_cookies(self.headers)
        self.link_list = get_link_list(self.worker_id)

        # Restart at page index
        if last_page_index != None:
            self.current_page_index = last_page_index
        else:
            self.current_page_index = 1

        # Restart at link index
        if (last_link_index != None):
            self.current_link_index = last_link_index
        else:
            self.current_link_index = 0

        self.current_base_url = ""

        self.current_request = None
        if last_metadata != None:
            self.metadata = last_metadata
        else:
            self.metadata = {}

        self.logger = logging.getLogger(__name__)

        fileHandle = logging.FileHandler(f'{self.worker_id}.log')
        fileHandle.setLevel(logging.DEBUG)
        self.logger.addHandler(fileHandle)

        consoleHandle = logging.StreamHandler()
        consoleHandle.setLevel(logging.INFO)
        # Setup the formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        consoleHandle.setFormatter(formatter)
        self.logger.addHandler(consoleHandle)

    def get_image_url(self, soup):
        '''return list of image urls'''
        elements = soup.find_all("img", {"class":"page-image"})
        image_url_list = []

        for element in elements:
            image_url_list.append(element['src'])

        return image_url_list

    def re_authenticate(self):
        # self.proxy = self.next_proxy()
        self.session = requests.Session()
        self.session.trust_env = False
        self.headers = generate_headers()
        self.cookie_jar = self.get_cookies(self.headers)
        logging.info("Re-Authenticating")

    def log_failure(self):
        _path = os.path.join(os.getcwd(), 'state')

        with open(os.path.join(_path, f'FailureFor{self.worker_id}.json'), '+w') as f:
            json.dump({
                'worker_id': self.worker_id,
                'current_page_index': self.current_page_index,
                'current_link_index': self.current_link_index,
                'metadata': self.metadata
            }, f)
        
        with open(os.path.join(_path, f'ResultRequest{self.worker_id}-{self.current_link_index}.p'), '+wb') as p:
            pickle.dump(self.current_request, p)

    def get_cookies(self, headers):
        '''returns cookie jar'''
        response = self.session.get("https://tinyurl.com/rcpcnj8", headers=headers, allow_redirects=True)
        return response.cookies
    

    def save_image(self, image_url):
        # get the name behind the last slash and before the ? 
        arr = image_url.split('/')
        image_name = arr[-1:][0].split('?')[0]

        _path = os.path.join(os.getcwd(), 'Issues', self.metadata["issue_name"].replace("/", "-"))

        if not os.path.isdir(_path):
            os.mkdir(_path)
            self.logger.info(f"Creating Dir: {_path}")

        _path = os.path.join(_path, image_name)

        tries = 3
        while tries != 0:
            r = self.session.get(image_url, stream=True, verify=False)
            if r.status_code == 200:
                with open(_path, '+wb') as f:
                    for chunk in r:
                        f.write(chunk)
                    tries = 0
                    return True
            else:
                tries -= 1
                if tries == 0:
                    self.current_request = r
                    self.log_failure()
                else:
                    self.re_authenticate()
        
        return False

    def save_metadata(self):
        _path = os.path.join(os.getcwd(), 'Issues', self.metadata["issue_name"].replace("/", "-"))

        if not os.path.isdir(_path):
            os.mkdir(_path)
            self.logger.info(f"Creating Dir: {_path}")

        _path = os.path.join(_path, "metadata.json")
        with open(_path, '+w') as f:
            json.dump(self.metadata, f)

        self.logger.info(f'Saved Meta for: {self.metadata["issue_name"].replace("/", "-")}')


    def main(self):
        # Iterate over links starting at the last used link
        for index in range(self.current_link_index, len(self.link_list)):
            self.current_link_index = index
            self.current_base_url = "https://website_x.com" + self.link_list[index][:-1]
            

            if self.current_page_index == 1:
                # Get first page 
                tries = 3
                while tries != 0:
                    response = self.session.get(self.current_base_url + '1',   
                                            headers=self.headers, 
                                            verify=False) # Add proxies in here
                    if response.status_code == 200:
                        tries = 0
                    else:
                        tries -= 1
                        if tries == 0:
                            self.current_request = response
                            self.log_failure()
                            self.logger.error("Failed to get base page")
                            raise Exception("F Dis")
                        else:
                            self.re_authenticate()

                # Soup page
                soup = BeautifulSoup(response.text, 'lxml')
                root_element = soup.find("div", {'class':'issues-spread-container'})


                # Create Metadata off page
                self.metadata = {
                        'num_pages': root_element["data-num-pages"],
                        'issue_num': root_element["data-issue-id"],
                        'issue_name': root_element["data-name"],
                        'starting_url': self.link_list[index]
                    }

                self.save_metadata()

                image_urls = self.get_image_url(soup)
                for image_url in image_urls:
                    result = self.save_image(image_url)
                    if not result:
                        self.logger.error("Failed to get and save image")
                        raise Exception("F Dis")

            for i in range(self.current_page_index, int(self.metadata["num_pages"])+1):
                if i%2 == 0 and i != int(self.metadata["num_pages"]):
                    # Skip if not odd page and not last page
                    continue

                self.current_page_index = i
                # Get Page
                tries = 3
                while tries != 0:
                    response = self.session.get(f"{self.current_base_url}{i}",   
                                            headers=self.headers, 
                                            verify=False) # Add proxies in here
                    if response.status_code == 200:
                        tries = 0
                    else:
                        tries -= 1
                        if tries == 0:
                            self.current_request = response
                            self.log_failure()
                            self.logger.error(f"Failed to get internal page {self.current_page_index}")
                            raise Exception("F Dis")
                        else:
                            self.re_authenticate()
                
                # Parse page request
                _soup = BeautifulSoup(response.text, 'lxml')
                image_urls = self.get_image_url(_soup)
                for _image_url in image_urls:
                    result = self.save_image(_image_url)
                    if not result:
                        self.logger.error("Failed to get and save image")
                        raise Exception("F Dis")
                
                if i == int(self.metadata["num_pages"]):
                    self.current_page_index = 1