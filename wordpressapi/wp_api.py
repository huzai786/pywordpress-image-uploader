from wordpressapi.media_api import WordpressApiMediaCrud
from wordpressapi.page_api import WordpressApiPageCrud


class WpApi:
    def __init__(self, site_url: str, username: str, app_password: str) -> None:
        self.site_url = site_url 
        self.username = username
        self.app_password = app_password

        self.media = WordpressApiMediaCrud(site_url, username, app_password)
        self.page = WordpressApiPageCrud(site_url, username, app_password)

    def __str__(self) -> str:
        return str(self.page)