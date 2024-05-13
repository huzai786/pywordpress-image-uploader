import csv
import os
import sys
import threading
import time
import dearpygui.dearpygui as dpg

from wordpressapi.wp_api import WpApi
from image_uploader import run_image_uploader
from wpdata_types import GuiTags, ScraperBotInput, LogoLocation, WindowsIds, ImageVariance


SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 700
csv_cred_file_path = "credentials.csv"

IMAGE, FONT, TEXT = "image", "font", "text"


class GUI:
    def __init__(self) -> None:
        self.websites_apis: dict[str, WpApi] = self.load_credentials()
        if not self.websites_apis:
            print("no credentials found!")
            sys.exit()
        self.start_time = None
        self.end_time = None
        self.current_site = list(self.websites_apis.keys())[0]  # its the first value in the keys
        self.file_paths = {
            GuiTags.Image_Folder_Path: "Not Given",
            GuiTags.Output_Folder_Path: "Not Given",
            GuiTags.Logo_File_Path: "Not Given",
            GuiTags.Watermark_File_Path: "Not Given",
            GuiTags.Quote_File_Path: "Not Given",
            GuiTags.Keyword_File_Path: "Not Given",
            GuiTags.Font_File_Path: "Default",
        }
        # Wordpress pages is a dict of page titles and their ids in wordpress
        self.wordpress_pages: dict[str, int] = {"Please Refresh to Load Pages": -1}
        self.refresh_in_progress = False
        self.current_window = WindowsIds.Main_Window
        self.scrapingthread = None

    def load_credentials(self):
        if not os.path.exists(csv_cred_file_path):
            print("credentials.csv doesnt exists")
            with open(csv_cred_file_path, 'w') as f:
                f.write("username,app_password,site_url")

            print("Please add username, password and site url")
            sys.exit()

        websites_apis = {}

        with open(csv_cred_file_path, newline='') as csvfile:
            creds_reader = csv.reader(csvfile, delimiter=",")
            for row in list(creds_reader)[1:]:
                username, password, url = row
                wp_api = WpApi(username=username, app_password=password, site_url=url)
                websites_apis[str(wp_api)] = wp_api

        return websites_apis

    def popup_message(self, text, add_okay=True):
        with dpg.window(label="Popup", width=200, height=150, pos=[SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 - 100],  no_close=True, no_collapse=True, tag=GuiTags.Popup_Msg_TagId.value, modal=True, ):
            dpg.add_text(text)
            if add_okay:
                dpg.add_button(label="OK", pos=[50, 100], width=100, height=40, callback=lambda: dpg.delete_item(GuiTags.Popup_Msg_TagId.value))

    def submit_file_callback(self, sender, app_data, user_data: GuiTags):
        file_path = app_data["file_path_name"]
        self.file_paths[user_data] = file_path
        dpg.set_value(user_data.value, file_path)

    def add_file_dialog(self, label_data_id: GuiTags, tag_id: GuiTags, directory_selector=True, file_type: str | None = None):
        """user data will be the tag id of the label text and class data key"""
        if directory_selector:
            dpg.add_file_dialog(directory_selector=True, show=False, tag=tag_id.value,
                            callback=self.submit_file_callback, user_data=label_data_id,
                            width=700, height=400, modal=True)
        else:
            with dpg.file_dialog(directory_selector=False, show=False, tag=tag_id.value,
                            callback=self.submit_file_callback, user_data=label_data_id,
                            width=700, height=400, modal=True):
                if file_type == IMAGE:
                    dpg.add_file_extension("Source files (*.png *.jpeg *.jpg){.png,.jpeg,.jpg}", color=(0, 255, 255, 255))
                elif file_type == FONT:
                    dpg.add_file_extension("Source files (*.otf *.ttf){.otf, .ttf}", color=(0, 255, 255, 255))
                elif file_type == TEXT:
                    dpg.add_file_extension("Source files (*.txt){.txt}", color=(0, 255, 255, 255))

    def update_page_combo(self, sender, app_data):
        self.refresh_in_progress = True
        self.popup_message("Refreshing please wait!", add_okay=False)
        self.wordpress_pages = self.websites_apis[self.current_site].page.list_pages()
        self.pages_titles = list(self.wordpress_pages.keys())
        if not self.pages_titles:
            dpg.delete_item(GuiTags.Popup_Msg_TagId.value)
            self.wordpress_pages: dict[str, int] = {"Please Refresh to Load Pages": -1}
            self.pages_titles = list(self.wordpress_pages.keys())
            dpg.configure_item(GuiTags.Page_Select_Tag.value, items=self.pages_titles)
            dpg.configure_item(GuiTags.Page_Select_Tag.value, default_value=self.pages_titles[0])    
        else:
            dpg.configure_item(GuiTags.Page_Select_Tag.value, items=self.pages_titles)
            dpg.configure_item(GuiTags.Page_Select_Tag.value, default_value=self.pages_titles[0])
            dpg.delete_item(GuiTags.Popup_Msg_TagId.value)
        
    def page_create_window(self):
        with dpg.window(tag=WindowsIds.Create_Page_Window.value, no_close=True, no_move=True, show=False, width=SCREEN_WIDTH, height=SCREEN_HEIGHT, no_collapse=True, no_title_bar=True):
            dpg.add_text("Create New Page", indent=SCREEN_WIDTH//2-70)
            dpg.add_button(label="Back", callback=lambda : self.change_window(WindowsIds.Main_Window))
            dpg.add_button(label="Save Changes")

    def credentials_window(self):
        with dpg.window(tag=WindowsIds.Credentials_Window.value, no_collapse=True, no_title_bar=True, no_close=True, no_move=True, show=False, width=SCREEN_WIDTH, height=SCREEN_HEIGHT, no_resize=True):
            dpg.add_text("Credentials", indent=SCREEN_WIDTH//2-70)
            dpg.add_button(label="Back", callback=lambda : self.change_window(WindowsIds.Main_Window))
            dpg.add_text(f"Current Site Selected: {self.current_site}")
            dpg.add_combo(list(self.websites_apis.keys()), default_value=list(self.websites_apis.keys())[0], tag=GuiTags.Select_Credentials_Tag_Id.value, width=300)
            dpg.add_button(label="Save Changes", callback=lambda: self.change_current_site(GuiTags.Select_Credentials_Tag_Id))

    def change_current_site(self, tagid: GuiTags):
        value = dpg.get_value(tagid.value)
        self.current_site = value
        self.wordpress_pages: dict[str, int] = {"Please Refresh to Load Pages": -1}
        dpg.configure_item(GuiTags.Page_Select_Tag.value, items=list(self.wordpress_pages.keys()))
        dpg.configure_item(GuiTags.Page_Select_Tag.value, default_value=list(self.wordpress_pages.keys())[0] )
        self.change_window(WindowsIds.Main_Window)

    def change_window(self, window_id: WindowsIds):
        dpg.configure_item(window_id.value, show=True)
        dpg.configure_item(self.current_window.value, show=False)
        self.current_window = window_id
        
    def initiate_gui(self):
        dpg.create_context()
        dpg.create_viewport(title='Wordpress Image Uploader Bot', width=SCREEN_WIDTH, height=SCREEN_HEIGHT, vsync=True, resizable=False)
        dpg.setup_dearpygui()

        self.add_file_dialog(GuiTags.Image_Folder_Path, GuiTags.Image_Folder_Dialog_Id)
        self.add_file_dialog(GuiTags.Output_Folder_Path, GuiTags.Output_Folder_Dialog_Id)
        self.add_file_dialog(GuiTags.Logo_File_Path, GuiTags.Logo_File_Dialog_Id, directory_selector=False, file_type=IMAGE)
        self.add_file_dialog(GuiTags.Watermark_File_Path, GuiTags.Watermark_File_Dialog_Id, directory_selector=False, file_type=IMAGE)
        self.add_file_dialog(GuiTags.Quote_File_Path, GuiTags.Quote_File_Dialog_Id, directory_selector=False, file_type=TEXT)
        self.add_file_dialog(GuiTags.Keyword_File_Path, GuiTags.Keyword_File_Dialog_Id, directory_selector=False, file_type=TEXT)
        self.add_file_dialog(GuiTags.Font_File_Path, GuiTags.Font_File_Dialog_Id, directory_selector=False, file_type=FONT)
        
        self.set_font_and_theme()
        self.credentials_window()
        self.page_create_window()

        with dpg.window(tag=WindowsIds.Main_Window.value, no_move=True, no_title_bar=True, no_resize=True, min_size=(SCREEN_WIDTH, SCREEN_HEIGHT), max_size=(SCREEN_WIDTH, SCREEN_HEIGHT)):
            dpg.add_text("Wordpress Image Uploader Bot", indent=SCREEN_WIDTH//3 + 20)
            # refresh button
            dpg.add_button(label="Refresh Pages Data", pos=[SCREEN_WIDTH-170, 40], width=150, callback=self.update_page_combo, tag=GuiTags.Refresh_Wp_Pages.value)
            dpg.add_button(label="Change Site",pos=[SCREEN_WIDTH-170, 70] ,  width=150, callback=lambda : self.change_window(WindowsIds.Credentials_Window), tag=GuiTags.Change_Credentials_Button.value)
            dpg.add_separator()
            dpg.add_spacer(width=SCREEN_WIDTH, height=30)
            with dpg.group(horizontal=True):
                dpg.add_text("Current Site Selected: ")
                dpg.add_text(self.current_site)
            dpg.add_spacer(width=SCREEN_WIDTH, height=10)
            
            with dpg.child_window(height=SCREEN_HEIGHT - 200, pos=[0, 100], width=SCREEN_WIDTH-300):
                with dpg.group():
                    # select page
                    with dpg.group(horizontal=True):
                        dpg.add_text("Select Page")
                        wp_pages = list(self.wordpress_pages.keys())
                        dpg.add_combo(wp_pages, default_value=wp_pages[0], indent=110, tag=GuiTags.Page_Select_Tag.value, width=300)
                        dpg.add_spacer(height=5)

                    # Image folder
                    with dpg.group(horizontal=True, width=205):
                        dpg.add_text("Image Folder: ")
                        dpg.add_button(label="Image Folder", indent=110, width=50, callback=lambda: dpg.show_item(GuiTags.Image_Folder_Dialog_Id.value))
                        dpg.add_text(self.file_paths[GuiTags.Image_Folder_Path], tag=GuiTags.Image_Folder_Path.value)
                        dpg.add_spacer(height=5)

                    # Output folder
                    with dpg.group(horizontal=True, width=205):
                        dpg.add_text("Output Folder: ")
                        dpg.add_button(label="Output Folder", indent=110, callback=lambda: dpg.show_item(GuiTags.Output_Folder_Dialog_Id.value))
                        dpg.add_text(self.file_paths[GuiTags.Output_Folder_Path], tag=GuiTags.Output_Folder_Path.value)
                        dpg.add_spacer(height=5)

                    # Logo File
                    with dpg.group(horizontal=True, width=205):
                        dpg.add_text("Logo File: ")
                        dpg.add_button(label="Logo File", indent=110, callback=lambda: dpg.show_item(GuiTags.Logo_File_Dialog_Id.value))
                        dpg.add_text(self.file_paths[GuiTags.Logo_File_Path], tag=GuiTags.Logo_File_Path.value)
                        dpg.add_spacer(height=5)

                    # Watermark File
                    with dpg.group(horizontal=True, width=205):
                        dpg.add_text("Watermark File: ")
                        dpg.add_button(label="Watermark File", indent=110, callback=lambda: dpg.show_item(GuiTags.Watermark_File_Dialog_Id.value))
                        dpg.add_text(self.file_paths[GuiTags.Watermark_File_Path], tag=GuiTags.Watermark_File_Path.value)
                        dpg.add_spacer(height=5)

                    # Quote Txt File
                    with dpg.group(horizontal=True, width=205):
                        dpg.add_text("Quote Text File: ")
                        dpg.add_button(label="Quote File", indent=110, callback=lambda: dpg.show_item(GuiTags.Quote_File_Dialog_Id.value))
                        dpg.add_text(self.file_paths[GuiTags.Quote_File_Path], tag=GuiTags.Quote_File_Path.value)
                        dpg.add_spacer(height=5)

                    # select Keywords file
                    with dpg.group(horizontal=True, width=205):
                        dpg.add_text("Keywords File: ")
                        dpg.add_button(label="keywords File", indent=110, callback=lambda: dpg.show_item(GuiTags.Keyword_File_Dialog_Id.value))
                        dpg.add_text(self.file_paths[GuiTags.Keyword_File_Path], tag=GuiTags.Keyword_File_Path.value)
                        dpg.add_spacer(height=5)

                    # select font file
                    with dpg.group(horizontal=True, width=205):
                        dpg.add_text("Font File: ")
                        dpg.add_button(label="Font File", indent=110, callback=lambda: dpg.show_item(GuiTags.Font_File_Dialog_Id.value))
                        dpg.add_text(self.file_paths[GuiTags.Font_File_Path], tag=GuiTags.Font_File_Path.value)
                        dpg.add_spacer(height=5)

                    # image width
                    with dpg.group(horizontal=True):
                        dpg.add_text("Image Width: ")
                        dpg.add_input_int(tag=GuiTags.Image_Width_Id.value, indent=110, default_value=0, min_value=0, width=130)
                        dpg.add_text("leave for original image width")

                    # image height
                    with dpg.group(horizontal=True):
                        dpg.add_text("Image Height: ")
                        dpg.add_input_int(tag=GuiTags.Image_Height_Id.value, indent=110, default_value=0, min_value=0, width=130)
                        dpg.add_text("leave for original image height")
                    
                    # logo width
                    with dpg.group(horizontal=True):
                        dpg.add_text("Logo Width: ")
                        dpg.add_input_int(tag=GuiTags.Logo_Width_Id.value, indent=110, default_value=0, min_value=0, width=130)
                        dpg.add_text("leave for default: 200")

                    # logo height
                    with dpg.group(horizontal=True):
                        dpg.add_text("Logo Height: ")
                        dpg.add_input_int(tag=GuiTags.Logo_Height_Id.value, indent=110, default_value=0, min_value=0, width=130)
                        dpg.add_text("leave for default: 100")

                    # font size
                    with dpg.group(horizontal=True):
                        dpg.add_text("Font Size: ")
                        dpg.add_input_int(tag=GuiTags.Font_Size_Id.value, indent=110, default_value=0, min_value=0, width=130)
                        dpg.add_text("leave for default: 60")

                    # # image name
                    with dpg.group(horizontal=True):
                        dpg.add_text("Image name: ")
                        dpg.add_input_text(tag=GuiTags.Image_Name.value, width=150, indent=110)
                    
                    # content id
                    with dpg.group(horizontal=True):
                        dpg.add_text("element id: ")
                        dpg.add_input_text(tag=GuiTags.ElementId.value, width=150, indent=110)
            
            with dpg.child_window(height=SCREEN_HEIGHT - 200, pos=[670, 100], width=SCREEN_WIDTH-700):
                with dpg.group(horizontal=True):
                    dpg.add_text("logo location: ")
                    dpg.add_combo([LogoLocation.BottomLeft.value, 
                               LogoLocation.BottomRight.value, 
                               LogoLocation.TopLeft.value, 
                               LogoLocation.TopRight.value, 
                               LogoLocation.Shuffle.value
                              ], 
                              default_value=LogoLocation.BottomLeft.value, 
                              indent=110, 
                              tag=GuiTags.Logo_Select_Tag.value, width=300,
                              )
                with dpg.group(horizontal=True):
                    dpg.add_text("Variation: ")
                    dpg.add_combo([ImageVariance.DifferentImage.value, ImageVariance.DifferentQuote.value], 
                              default_value=ImageVariance.DifferentImage.value, 
                              indent=110, 
                              tag=GuiTags.Image_Variance_Tag.value, width=300,
                              )
                with dpg.group(horizontal=True):
                    dpg.add_text("Image Count Attribute Name: ")
                    dpg.add_input_text(tag=GuiTags.Image_Count_Name.value, width=150, indent=200)

            dpg.add_spacer(width=SCREEN_WIDTH, height=50)
            dpg.add_button(label="Start Bot", callback=self.start_bot, width=300, pos=[SCREEN_WIDTH//2 - 160, SCREEN_HEIGHT - 80], tag=GuiTags.Start_Bot.value)
            dpg.bind_font(self.default_font)

        dpg.show_viewport()
        dpg.set_viewport_pos([100, 30])
        dpg.set_primary_window("main_window", True)

    def start_bot(self):
        #####----------- FILTERING INPUT ---------------######
        #region 
        if -1 in self.wordpress_pages.values():
            self.popup_message("Refresh to load pages!")
            return
        
        # image folder
        if self.file_paths[GuiTags.Image_Folder_Path] == "Not Given":
            self.popup_message("Image Folder Missing!")
            return 
        
        # output folder
        if self.file_paths[GuiTags.Output_Folder_Path] == "Not Given":
            self.popup_message("Output Folder Missing!")
            return
        
        # logo file
        if self.file_paths[GuiTags.Logo_File_Path] == "Not Given":
            self.popup_message("Logo File missing!")
            return
        
        # watermark file
        if self.file_paths[GuiTags.Watermark_File_Path] == "Not Given":
            self.popup_message("Watermrk File missing!")
            return
        
        # quote file
        if self.file_paths[GuiTags.Quote_File_Path] == "Not Given":
            self.popup_message("Quote File missing!")
            return
        with open(self.file_paths[GuiTags.Quote_File_Path], 'r') as f:
            quotes = [q.strip("\n") for q in f.readlines()] 
        if len(quotes) == 0:
            self.popup_message(f"No quotes found in file '{self.file_paths[GuiTags.Quote_File_Path]}'")
            return
        
        # keyword file
        if self.file_paths[GuiTags.Keyword_File_Path] == "Not Given":
            self.popup_message("Keyword file Missing")
            return
        with open(self.file_paths[GuiTags.Keyword_File_Path], 'r') as f:
            keywords = [q.strip("\n") for q in f.readlines()] 
        if len(keywords) == 0:
            self.popup_message(f"No keywords found in file '{self.file_paths[GuiTags.Keyword_File_Path]}'")
            return

        # fontfile file
        if self.file_paths[GuiTags.Font_File_Path] == "Default":
            fontfile = None
        else:
            fontfile = self.file_paths[GuiTags.Font_File_Path]
        logo_location = dpg.get_value(GuiTags.Logo_Select_Tag.value)
        image_variance = dpg.get_value(GuiTags.Image_Variance_Tag.value)
        logo_location_enum = next(i for i in LogoLocation if i.value == logo_location)
        image_variance_enum = next(i for i in ImageVariance if i.value == image_variance)
        img_width = dpg.get_value(GuiTags.Image_Width_Id.value)
        img_height = dpg.get_value(GuiTags.Image_Height_Id.value)
        
        logo_width = dpg.get_value(GuiTags.Logo_Width_Id.value)
        logo_height = dpg.get_value(GuiTags.Logo_Height_Id.value)
        font_size = dpg.get_value(GuiTags.Font_Size_Id.value)
        element_id = dpg.get_value(GuiTags.ElementId.value)
        img_count_attribute_name = dpg.get_value(GuiTags.Image_Count_Name.value)
        if not img_count_attribute_name:
            self.popup_message("please add image count \nattribute name!")
            return
        
        if img_width < 0 or img_height < 0 or font_size < 0 or logo_width < 0 or logo_height < 0:     
            self.popup_message("Value cant be negative!")
            return

        if not logo_width or not logo_height:
            logo_size = None
        else:
            logo_size = (logo_width, logo_height)
        if not font_size:
            font_size = None

        if not element_id:
            self.popup_message("Element Id Missing")
            return
        # image name
        image_name = dpg.get_value(GuiTags.Image_Name.value)
        if not image_name:
            self.popup_message("Image Name Missing")
            return
        #endregion
        #####----------- FILTERING INPUT ENDS ---------------######
        selected_page = dpg.get_value(GuiTags.Page_Select_Tag.value)

        page_id = self.wordpress_pages[selected_page]
        image_folder_path = self.file_paths[GuiTags.Image_Folder_Path]
        output_folder_path = self.file_paths[GuiTags.Output_Folder_Path]
        logo_file_path = self.file_paths[GuiTags.Logo_File_Path]
        watermark_file_path = self.file_paths[GuiTags.Watermark_File_Path]
        image_size = (img_width, img_height)

        dpg.configure_item(GuiTags.Start_Bot.value, enabled=False)
        dpg.configure_item(GuiTags.Refresh_Wp_Pages.value, enabled=False)
        dpg.configure_item(GuiTags.Change_Credentials_Button.value, enabled=False)

        scraper_bot_input = ScraperBotInput(wp_page_id=str(page_id), image_folder_path=image_folder_path, output_folder_path=output_folder_path,
                            logo_file_path=logo_file_path, watermark_file_path=watermark_file_path, quotes=quotes,
                            keywords=keywords, image_size=image_size, image_name=image_name, element_id=element_id,
                            wpapi=self.websites_apis[self.current_site], logo_location=logo_location_enum, image_variance=image_variance_enum, 
                            img_count_attribute_name=img_count_attribute_name, font_file=fontfile,
                            font_size=font_size, logo_size=logo_size)
        self.start_bot_thread(scraper_bot_input)
        
    def start_bot_thread(self, scraper_bot_input: ScraperBotInput):
        self.scrapingthread = threading.Thread(target= lambda : run_image_uploader(scraper_bot_input))
        self.start_time = time.perf_counter()
        self.scrapingthread.start()

    def main_loop(self):
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            self.check_bot_status()

        dpg.destroy_context()

    def check_bot_status(self):
        if self.scrapingthread and not self.scrapingthread.is_alive():
            self.scrapingthread = None
            dpg.configure_item(GuiTags.Start_Bot.value, enabled=True)
            dpg.configure_item(GuiTags.Refresh_Wp_Pages.value, enabled=True)
            dpg.configure_item(GuiTags.Change_Credentials_Button.value, enabled=True)
            self.end_time = time.perf_counter()
            dpg.set_value(GuiTags.Start_Bot.value, "Start Bot")
            self.popup_message(f"Completed\n In {self.end_time - self.start_time:.2f} seconds")
            self.start_time = None
            self.end_time = None

    def set_font_and_theme(self):
        with dpg.font_registry():
            self.default_font = dpg.add_font("font.ttf", 20)

        with dpg.theme() as global_theme:

            with dpg.theme_component(dpg.mvInputText, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 68), category=dpg.mvThemeCat_Core)
            with dpg.theme_component(dpg.mvInputInt, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 68), category=dpg.mvThemeCat_Core)
            with dpg.theme_component(dpg.mvButton, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (30, 30, 30, 68), category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 68), category=dpg.mvThemeCat_Core)

        dpg.bind_theme(global_theme)

if __name__ == "__main__":
    gui = GUI()
    gui.initiate_gui()
    gui.main_loop()
