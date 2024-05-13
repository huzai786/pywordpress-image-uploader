import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from wordpressapi.media_api import MediaData
from wpdata_types import ScraperBotInput, LogoLocation, ImageVariance
from jinja2 import Environment, FileSystemLoader, Template
from bs4 import BeautifulSoup, ResultSet


# Specify the template directory
template_dir = "templates"

# Create a Jinja2 environment
env = Environment(loader=FileSystemLoader(template_dir))

def split_text_into_lines(text: str, max_width: int, draw, font):
    lines = []
    words = text.split()
    current_line = ''
    
    for word in words:
        # Check if adding the next word exceeds the max width
        if textsize(current_line + ' ' + word, font=font)[0] <= max_width:
            # Add word to the current line
            if current_line:
                current_line += ' '
            current_line += word
        else:
            # Add current line to the lines list and start a new line with the current word
            lines.append(current_line)
            current_line = word
    
    # Add the last line
    if current_line:
        lines.append(current_line)
    
    return lines

def get_file(directory: str, filter: list) -> list[str]:
    files = []
    for (dirpath, dirnames, filenames) in os.walk(directory):
        files.extend(filenames)
    files = [os.path.join(directory, f) for f in files if os.path.splitext(f)[1] in filter]
    return files


def run_image_uploader(bot_input: ScraperBotInput):
    """
    bot_input.wp_page_id (required): wordpress page id
    bot_input.image_folder_path (required): path of image folder from which to get images
    bot_input.output_folder_path (required): output folder path to which the images will be stored
    bot_input.logo_file_path (required): logo file path
    bot_input.watermark_file_path (required): path of watermark file
    bot_input.quotes (required): list of quotes to use
    bot_input.keywords (required): list of keywords to use
    bot_input.image_size (required): image size
    bot_input.image_name (required): name of the image to use as a placeholder
    bot_input.element_id (required): id of the element to which to insert the content
    bot_input.wpapi (required): WpApi class instance
    bot_input.logo_location (required): LogoLocation enum
    bot_input.image_variance (required): ImageVariance enum
    bot_input.img_count_attribute_name (required): self explainatory
    bot_input.font_file: font file in otf or ttf to use, defaults to dearpygui default font
    bot_input.font_size: size of font to use defaults to 60
    bot_input.logo_size: size of the logo, defaults to 200, 100 if not given
    """
    #region Filtering input
    if not bot_input.logo_size:
        logo_size = (200, 100)
    else:
        logo_size = bot_input.logo_size
    if not bot_input.font_size:
        font_size = 60
    else:
        font_size = bot_input.font_size

    if bot_input.font_file:
        font = ImageFont.truetype(bot_input.font_file, font_size)
    else:
        font = ImageFont.load_default(font_size)
    if bot_input.image_size[0] == 0 or bot_input.image_size[1] == 0:
        image_size = None
    else:
        image_size = bot_input.image_size 
    # endregion

    images = get_file(bot_input.image_folder_path, [".png", ".jpg", ".jpeg"])
    
    print(f"Total images Found in folder {bot_input.image_folder_path}: {len(images)}")
    print(f"Total Quotes Found in file: {len(bot_input.quotes)}")
    
    total_images = len(images) * len(bot_input.quotes)
    total_posted = 0
    
    print(f"total images to post {total_images}")
    # Put logo on the bottom left corner of the image
    PROCESSED_IMAGES: list[Image.Image] = []

    logo = Image.open(bot_input.logo_file_path).resize(logo_size)
    watermark = Image.open(bot_input.watermark_file_path)

    images_data: list[tuple[str, str]] = []  # list of tuples containing image name and wp link
    random_names_occupied = []

    for image_path in images:
        # reduce the brightness of image and resize it
        image_file = Image.open(image_path)
        enhancer = ImageEnhance.Brightness(image_file)
        image_file = enhancer.enhance(0.8)
        if image_size:
            image_file = image_file.resize(image_size)    
        image_file = process_image(image_file, watermark)
        PROCESSED_IMAGES.append(image_file)

    for quote in bot_input.quotes:
        for img_processed in PROCESSED_IMAGES:                
            img_copy = img_processed.copy()
            img_copy = paste_logo(img_copy, logo, bot_input.logo_location)
            img_copy = draw_text(img_copy, quote, font)
            random_name = f"{bot_input.image_name}_{random.choice(bot_input.keywords)}"
            while True:
                if random_name not in random_names_occupied:
                    break
                else:
                    random_name += f"_{random.choice(bot_input.keywords)}"
            image_file_name = random_name + ".png"
            random_names_occupied.append(random_name) 

            # also upload this image to wordpress and get the source url, and save it in the list
            output_image_path = os.path.join(bot_input.output_folder_path, image_file_name) 
            img_copy.save(output_image_path)

            media_input = MediaData(output_image_path, image_file_name, image_file_name)
            created, output = bot_input.wpapi.media.create_media(media_input)
            if created and output:
                print(f"{image_file_name} successfully uploaded!")
                total_posted += 1

            print(f"Images left {total_images - total_posted}")
            siteurl, imglinkpart = output.link.split("wp-content")
            imglink = f"/wp-content{imglinkpart}"
            images_data.append((image_file_name, imglink ))

    if bot_input.image_variance == ImageVariance.DifferentQuote:
        images_data = change_order(images_data, len(PROCESSED_IMAGES))
    # create the page content with those image links and update the 
    # content to the page id 
    print("Creating html from images data.")
    
    # Load the template
    template = env.get_template("content_template.html")
    post_content = bot_input.wpapi.page.get_content(bot_input.wp_page_id)
    content = update_content(template, post_content, bot_input.element_id, images_data, bot_input.img_count_attribute_name)
    if content:
        updated = bot_input.wpapi.page.update_content(bot_input.wp_page_id, content)
        if updated:
            print("content uploaded!")
            return True
        else:
            print("Content failed to upload")
            return False
    else:
        print(f"element with id {bot_input.element_id} not found!")
        return False    

def textsize(text, font):
    im = Image.new(mode="P", size=(0, 0))
    draw = ImageDraw.Draw(im)
    _, _, width, height = draw.textbbox((0, 0), text=text, font=font)
    return width, height

def update_content(template: Template, post_content: str, element_id: str, images_data: list[tuple[str, str]], count_attribute: str) -> str:
    bs = BeautifulSoup(post_content, 'lxml')
    target_elements: ResultSet = bs.find_all(id=element_id)
    # distribute evenly among the elements
    # if it finds a image_count attribute, it renderers that about of images
    # there and distribute the left over evenly, if image_count is greater than
    # total images, then it will just render all images there.

    # create a hashmap out of the elements with required id, with fields
    # has_count: bool, which says if it has a count attribute, 
    target_element_data = []
    for element in target_elements:
        edata = {"element": element}
        if count_attribute in element.attrs:
            edata["has_count"] = True
            try:
                image_count = int(element.attrs[count_attribute])
                edata["count"] = image_count
            except ValueError:
                edata["has_count"] = False
        else:
            edata["has_count"] = False
        target_element_data.append(edata)
    # loop over the key and values, and check if it has count attribute
    # if it has render that amount of images and put it in that tag
    # if it doesnt have it get the amount of image by deviding the left over 
    # images with number of elements left to put in the content
    total_elements = len(target_element_data)
    image_start_index = 0
    for i, element_data in enumerate(target_element_data):
        if image_start_index < len(images_data):
            if element_data["has_count"]:
                img_count = element_data["count"] 
                available_images = len(images_data) - image_start_index 
                img_count = min([img_count, available_images])
                if img_count == 0:
                    img_count = available_images
                images_till_index = image_start_index + (img_count % len(images_data)) 
            else:
                images_till_index = int(image_start_index + (len(images_data) / total_elements))
            ctx = {"images": images_data[image_start_index: images_till_index]}
            if image_start_index == 0:
                ctx["render_style"] = True
            image_start_index = images_till_index
            image_content = template.render(ctx)
            element_data["element"].append(BeautifulSoup(image_content, "lxml"))
    
    return str(bs)

def process_image(image: Image.Image, watermark: Image.Image):
    image.paste(watermark, (image.width // 2 - watermark.width // 2, 
                           (image.height // 2) - watermark.height // 2), 
                           watermark)

    return image

def draw_text(image: Image.Image, quote: str, font):
    # Render quote on the image
    draw = ImageDraw.Draw(image)
    # Split text into multiple lines if necessary
    
    text_area_width = int(image.width * 0.80)  # 80% of the original width
    # text_area_left_offset = (image.width - text_area_width) // 2  # Calculate the left offset

    lines = split_text_into_lines(quote, text_area_width, draw, font)

    # Calculate total height of all lines
    total_height = sum(textsize(line, font=font)[1] for line in lines)
    y_offset = (image.height - total_height) // 2

    # Draw each line
    for line in lines:
        text_width, text_height = textsize(line, font=font)
        text_position = ((image.width - text_width) // 2) - 10, y_offset
        draw.text(text_position, line, font=font, fill="white")
        y_offset += text_height

    return image

def change_order(data_list: list[tuple[str, str]], total_quotes: int):
    new_list = []
    i = 0
    while i < total_quotes:
        for x in range(0, len(data_list), total_quotes):
            new_list.append(data_list[x + i])
        i += 1
    return new_list

def paste_logo(image: Image.Image, logo: Image.Image, logo_location: LogoLocation):
    if logo_location == LogoLocation.BottomLeft:
        logo_position = (10, image.height - logo.height - 10)
    elif logo_location == LogoLocation.BottomRight:
        logo_position = (image.width - logo.width - 10, image.height - logo.height - 10)
    elif logo_location == LogoLocation.TopLeft:
        logo_position = (10, 10)
    elif logo_location == LogoLocation.TopRight:
        logo_position = (image.width - logo.width - 10, 10)
    elif logo_location == LogoLocation.Shuffle:
        logo_position = random.choice([(10, image.height - logo.height - 10), 
                                       (image.width - logo.width - 10, image.height - logo.height - 10), 
                                       (10, 10), 
                                       (image.width - logo.width - 10, 10)
                                    ])

    image.paste(logo, logo_position, logo)
    return image
