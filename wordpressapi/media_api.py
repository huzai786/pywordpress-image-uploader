import json
import os
from pathlib import Path
from typing import NamedTuple
import requests


class MediaData(NamedTuple):
    file_path: str | bytes
    file_name: str
    alt_text: str | None = ''
    caption: str | None = ''

class MediaOutput(NamedTuple):
    id: str | None
    slug: str = ''
    link: str = ''
    alt_text: str = ''
    title: str = ''

class WordpressApiMediaCrud:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    
    def __init__(self, site_url: str, username: str, app_password: str) -> None:
        self.site_url = site_url 
        self.media_url_part = "/wp-json/wp/v2/media"
        self.site_media_url = self.site_url + self.media_url_part
        self.username = username
        self.app_password = app_password

    def create_media(self, media_data: MediaData) -> tuple[bool, MediaOutput | None]:
        image_name = media_data.file_name
        if isinstance(media_data.file_path, str):
            img_data = open(media_data.file_path, 'rb').read()
        else:
            img_data = media_data.file_path
            
        img_header = { 
            'Content-Type': 'image/png',
            'Content-Disposition' : 'attachment; filename=%s'% image_name
        }
        
        res = requests.post(self.site_media_url, data=img_data, auth=(self.username, self.app_password), headers=img_header)
        if res.status_code == 201:
            output = MediaOutput(id=res.json()["id"], 
                                 slug=res.json()["slug"],
                                 link=res.json()["guid"]["rendered"],
                                #  link=res.json()['_links']['self'][0]['href'],
                                 alt_text=media_data.alt_text, # type: ignore
                                 title=res.json()["title"]["rendered"]
                                )
            update_image = {'alt_text': media_data.alt_text, "caption": media_data.caption}
            requests.post(self.site_media_url + f"/{res.json()['id']}",
            json=update_image, auth=(self.username, self.app_password))
            return True, output
        
        else:
            print(res.json())
            return False, None
    
    
    def update_media(self, wp_media_id: str, media_data: MediaData) -> tuple[bool, MediaOutput | None]:
        try:
            image_extension = Path(media_data.file_path).suffix # type: ignore
            if image_extension != '.jpg':
                img_path = media_data.file_path.replace(image_extension, '.jpg')  # type: ignore # noqa: F841

            image_name = os.path.basename(media_data.file_path)
            
            img_data = open(media_data.file_path, 'rb').read()
            img_header = {
                'Content-Type': 'image/jpg',
                'Content-Disposition': 'attachment; filename=%s' % image_name,
            }
            data = {
                "file": img_data,
                'alt_text': media_data.alt_text,
                'caption': media_data.caption,
            }
            res = requests.post(f"{self.site_media_url}/{wp_media_id}",
                                json=data, headers=img_header,
                                auth=(self.username, self.app_password))
            
            if res.status_code == 200:
                output = MediaOutput(id=res.json()["id"], 
                                 slug=res.json()["slug"],
                                 link=res.json()['guid']['rendered'],
                                 alt_text=res.json()["alt_text"],
                                 title=res.json()["title"]["rendered"]
                                )
                print("Media updated successfully.")
                return True, output
            else:
                print("Failed to update media.")
                print(res.status_code, res.text)
                return False, None
        
        except Exception as e:
            print(e)
            return False, None

    def delete_media(self, wp_media_id: str) -> bool:
        try:
            res = requests.delete(f"{self.site_media_url}/{wp_media_id}", 
                                  headers=self.headers, auth=(self.username, self.app_password), 
                                  data=json.dumps({"force": True}))
            
            if res.status_code == 200:
                print("Media deleted successfully.")
                return True
            else:
                print("Failed to delete media.")
                print(res.status_code, res.text)
                return False
        except Exception as e:
            print(e)
            return False
    
    def list_media(self) -> list:
        try:
            response = requests.get(self.site_media_url, headers=self.headers, auth=(self.username, self.app_password))
            if response.status_code == 200:
                return response.json()
            else:
                return []
        except Exception as e:
            print(e)
            return []
        