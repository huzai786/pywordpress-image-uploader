from enum import Enum
from typing import NamedTuple
from wordpressapi.wp_api import WpApi

class LogoLocation(Enum):
    TopLeft = "Top Left"
    TopRight = "Top Right"
    BottomLeft = "Bottom Left"
    BottomRight = "Bottom Right"
    Shuffle = "Shuffle"

class ImageVariance(Enum):
    DifferentImage = "Different Images Same Quote"
    DifferentQuote = "Different Quotes Same Image"


class ScraperBotInput(NamedTuple):
    wp_page_id: str
    image_folder_path: str
    output_folder_path: str
    logo_file_path: str
    watermark_file_path: str
    quotes: list[str]
    keywords: list[str]
    image_size: tuple[int, int]
    image_name: str
    element_id: str
    wpapi: WpApi
    logo_location: LogoLocation
    image_variance: ImageVariance
    img_count_attribute_name: str
    font_file: str | None = None
    font_size: int | None = None
    logo_size: tuple[int, int] | None = None

class GuiTags(Enum):
    Popup_Msg_TagId = 'info_popup'
    Page_Select_Tag = 'page_combo'
    Logo_Select_Tag = "Logo_Select_Tag"
    Select_Credentials_Tag_Id = "credentials_combo"
    Refresh_Wp_Pages = "refresh_pages_button"
    Change_Credentials_Button = "Change_Credentials_Button"
    Create_Page_Button = "Create_Page_Button"
    Image_Variance_Tag = "Image_Variance_Tag"
    Image_Count_Name = "Image_Count_Name"

    Image_Folder_Dialog_Id = "image_folder_dialog_id"
    Output_Folder_Dialog_Id = "output_folder_dialog_id"
    Logo_File_Dialog_Id = "logo_file_dialog_id"
    Watermark_File_Dialog_Id = "watermark_file_dialog_id"
    Quote_File_Dialog_Id = "quote_file_dialog_id"
    Font_File_Dialog_Id = "font_file_dialog_id"
    Keyword_File_Dialog_Id = "Keyword_File_Dialog_Id"

    Image_Folder_Path = "image_folder_path"
    Output_Folder_Path = "output_folder_path"
    Logo_File_Path = "logo_file_path"
    Watermark_File_Path = "watermark_file_path"
    Quote_File_Path = "quote_file_path"
    Font_File_Path = "font_file_path"
    Keyword_File_Path = "Keyword_File_Path"

    Image_Width_Id = "img_width"
    Image_Height_Id = "img_height"
    Font_Size_Id = "font_size"
    Logo_Width_Id = "logo_width"
    Logo_Height_Id = "logo_height"
    Image_Name = "image_name"
    Start_Bot = "start_bot"
    ElementId = "html_element_id"



class WindowsIds(Enum):
    Main_Window = "main_window"
    Credentials_Window = "credentials_window"
    Create_Page_Window = "page_window"
