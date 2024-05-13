from typing import NamedTuple
import requests
import traceback
import json

class PageOutput(NamedTuple):
    id: str | None
    slug: str
    link: str
    
class PageData(NamedTuple):
    slug: str | None = None
    status: str | None = None
    title: str | None = None
    excerpt: str | None = None
    comment_status: str | None = None
    ping_status: str | None = None

class WordpressApiPageCrud:
    headers = {"Content-Type": "application/json; charset=utf-8"}


    def __init__(self, site_url: str, username: str, app_password: str) -> None:
        self.site_url = site_url 
        self.page_url_part = "/wp-json/wp/v2/pages"
        
        self.username = username
        self.app_password = app_password

    def test_credentials(self):
        try:
            res = requests.post(self.site_url + "/wp-json/wp/v2/tags", data=json.dumps({"name": "testing"}), headers=self.headers,
                                auth=(self.username, self.app_password))
            if res.status_code == 201:
                res = requests.delete(self.site_url + f"/wp-json/wp/v2/tags/{res.json()['id']}", data=json.dumps({"force": True}), headers=self.headers,
                                      auth=(self.username, self.app_password))
                return True, ""
            else:
                return False, f"incorrect credentials for site {self.site_url}"
        except requests.exceptions.RequestException as e:
            return False, e


    def list_pages(self) -> dict[str, int]:
        """returns a dictionary with page title as key and its wordpress id """
        pages_data = {}
        try:
            response = requests.get(self.site_url + self.page_url_part, headers=WordpressApiPageCrud.headers, 
                                    auth=(self.username, self.app_password))
            if response.status_code == 200:
                results = response.json()
                if len(results) > 0:
                    for res in results:
                        pages_data[res['title']['rendered']] = res['id'] 
                return pages_data
            else:
                return pages_data
            
        except requests.RequestException:
            print(traceback.format_exc())
            return pages_data
    
    def get_content(self, page_id: str) -> str:
        url = f"{self.site_url + self.page_url_part}/{page_id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                results = response.json()
                content = results["content"]["rendered"]
                return content
            
        except requests.RequestException as e:
            print(e)
            

    def update_content(self, page_id: str, content: str) -> bool:
        try:
            payload = {
                "content": content
            }
            update_url = f"{self.site_url + self.page_url_part}/{page_id}"
            response = requests.post(update_url, headers=self.headers, auth=(self.username, self.app_password), json=payload)
            if response.status_code == 200:
                return True
            else:
                return False
        
        except requests.RequestException:
            print(traceback.format_exc())
            return False
    
    def create_page(self, data: PageData) -> tuple[bool, PageOutput | None]:
        try:    
            response = requests.post(self.site_url, data=json.dumps(data._asdict()), headers=WordpressApiPageCrud.headers, 
                                     auth=(self.username, self.app_password))
            if response.status_code in(200, 201):
                return True, PageOutput(id=response.json()["id"], slug=response.json()["slug"], link=response.json()["link"]) 
            else:
                return False, None
            
        except requests.RequestException:
            print(traceback.format_exc())
            return False, None
        
    def delete_page(self, wp_page_id: str) -> bool:
        try:
            response = requests.delete(f"{self.site_url}/{wp_page_id}", headers=WordpressApiPageCrud.headers, 
                                       auth=(self.username, self.app_password))
            if response.status_code == 200:
                return True
            else:
                return False
            
        except requests.RequestException:
            print(traceback.format_exc())
            return False
        
    def __str__(self):
        return f"{self.site_url}"