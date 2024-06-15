from __future__ import with_statement
from AnalyticsClient import AnalyticsClient
import pandas as pd
from streamlit.components.v1 import html
from reportlab.lib.pagesizes import landscape, letter, portrait
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib import colors
import requests
from PIL import Image
from io import BytesIO
import pikepdf
import os
import re

def generate_catalogue_pdf():
    def compress_pdf(input_pdf_path, output_pdf_path):
        if not os.path.exists(input_pdf_path):
            raise FileNotFoundError(f"Input PDF file '{input_pdf_path}' does not exist.")
        with pikepdf.open(input_pdf_path) as pdf:
            pdf.save(output_pdf_path, compress_streams=True)
    def resize_image(image, max_width, max_height):
        img = Image.open(image)
        img.thumbnail((max_width, max_height))
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    
    def sort_dataframe_by_variant_count(df):
        print('sorting')
        print(df['SubCategory'])
        subcategory_counts = df.groupby('SubCategory')['variantid'].count().reset_index()
        print(subcategory_counts)
        subcategory_counts.columns = ['SubCategory', 'Count']
        sorted_subcategories = subcategory_counts.sort_values(by='Count', ascending=False)['SubCategory']
        df['SubCategory'] = pd.Categorical(df['SubCategory'], categories=sorted_subcategories, ordered=True)
        df = df.sort_values('SubCategory')
        print('Sorted')
        return df
    
    def parse_colors(color_text):
        color_mapping = {
            'red': '#ff0000',
            'blue': '#0000ff',
            'green': '#008000',
            'yellow': '#ffff00',
            'black': '#000000',
            'white': '#ffffff',
            'brown': '#a52a2a',
            'orange': '#ffa500',
            'pink': '#ffc0cb',
            'purple': '#800080',
            'gray': '#808080',
            'grey': '#808080',
            'multicolor': None,
            'military': '#2e3b4e'
        }
        colors_list = re.findall(r'[a-zA-Z]+', color_text.lower())
        color_codes = [color_mapping.get(color) for color in colors_list if color in color_mapping and color_mapping.get(color) is not None]
        # Use a default color if no valid color is found
        if not color_codes:
            color_codes = ['#0000FF']  # Default color
        return color_codes
    def create_pdf(df, output_file, max_image_width, max_image_height, orientation='portrait'):
        print('Creating Pdf')
        if orientation == 'portrait':
            page_width, page_height = portrait(letter)
        elif orientation == 'landscape':
            page_width, page_height = landscape(letter)
        else:
            raise ValueError("Invalid orientation. Please specify 'portrait' or 'landscape'.")
        margin_rows = 100
        margin_columns = 30
        increased_page_width = 685 + 420
        increased_page_height = (1040 + 400) * 1.5
        df['Platform'] = pd.Categorical(df['Platform'], categories=['Production', 'Distribution'], ordered=True)
        print('Platform ')
        df = df.sort_values(by='Platform')
        subcategories = df['SubCategory'].unique()
        num_columns = 2
        num_rows = 3
        total_width = (max_image_width + margin_columns) * num_columns + margin_columns * (num_columns - 1) + margin_rows * 2
        total_height = (max_image_height + margin_rows) * num_rows + margin_rows * 2
        x_offset = (increased_page_width - total_width) / 2 + 25
        y_offset = (increased_page_height - total_height) / 2
        c = canvas.Canvas(output_file, pagesize=(increased_page_width, increased_page_height))
        styles = getSampleStyleSheet()
        small_image_path = "BijnisLogo.png"
        small_image_width = 140
        small_image_height = 70
        click_icon_path = "Click.png"
        click_icon_width = 50
        click_icon_height = 5
        for subcategory in subcategories:
            subcategory_df = df[df['SubCategory'] == subcategory]
            print(subcategory)
            production_df = subcategory_df[subcategory_df['Platform'] == 'Production'].head(6)
            distribution_df = subcategory_df[subcategory_df['Platform'] == 'Distribution'].head(6)
            for platform_df, platform_name in zip([production_df, distribution_df], ['Production', 'Distribution']):
                if platform_df.empty:
                    continue
                pages = (len(platform_df) + num_columns * num_rows - 1) // (num_columns * num_rows)
                for page in range(pages):
                    c.drawImage(small_image_path, (increased_page_width + margin_rows) - small_image_width - 100, increased_page_height - small_image_height, width=small_image_width, height=small_image_height)
                    subcategory_upper = f"{subcategory.upper()}"
                    c.setFont("Helvetica-Bold", 40)
                    text_width = c.stringWidth(subcategory_upper, 'Helvetica-Bold', 40)
                    c.drawString((increased_page_width / 2 - text_width / 2), increased_page_height - 40, subcategory_upper)
                    sub_df = platform_df.iloc[page * num_columns * num_rows:(page + 1) * num_columns * num_rows]
                    # sub_df = sub_df.fillna('')  # Replace NaN values with empty string
                    image_urls = sub_df['App_Image'].astype(str).tolist()
                    product_names = sub_df['ProductName'].astype(str).tolist()
                    price_ranges = sub_df['Price_Range'].astype(str).tolist()
                    deeplink_urls = sub_df['App_Deeplink'].astype(str).tolist()
                    sizes = sub_df['VariantSize'].astype(str).tolist()
                    colors_list = sub_df['Color'].astype(str).tolist()
                    page_has_content = False
                    for i, (image_url, product_name, price_range, deeplink_url, size, color_text) in enumerate(zip(image_urls, product_names, price_ranges, deeplink_urls, sizes, colors_list)):
                        row_index = i // num_columns
                        col_index = i % num_columns
                        x = x_offset + margin_columns + col_index * (max_image_width + margin_columns) + 50
                        y = y_offset + margin_rows + (num_rows - row_index - 1) * (max_image_height + margin_rows)
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            img_bytes = BytesIO(response.content)
                            img = Image.open(img_bytes)
                            img.thumbnail((max_image_width, max_image_height - 30))
                            c.drawImage(ImageReader(img_bytes), x, y + 60, width=max_image_width, height=max_image_height - 80, preserveAspectRatio=True)
                            c.linkURL(deeplink_url, (x, y + 60, x + max_image_width, y + max_image_height - 80))
                            if platform_name == 'Production':
                                rect_color = colors.HexColor("#F26522")
                            else:
                                rect_color = colors.HexColor("#FFCA18")
                            c.setStrokeColor(rect_color)
                            c.setLineWidth(4)
                            c.roundRect(x, y - 30, max_image_width + 20, max_image_height + 90, radius=10)
                            hyperlink_style = ParagraphStyle('hyperlink', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=24, textColor=colors.black, underline=True)
                            product_info = f'{product_name}<br/><br/><font size="18" color="red" style="text-decoration: underline; text-decoration-thickness: 2px;">CLICK </font><font size="18" color="black" style="text-decoration: underline; text-decoration-thickness: 2px;"> For More Info</font>'
                            hyperlink = f'<a href="{deeplink_url}" color="black">{product_info}</a>'
                            p = Paragraph(hyperlink, hyperlink_style)
                            if len(product_name) <= 20:
                                hyperlink_style.fontSize = 30
                                p = Paragraph(hyperlink, hyperlink_style)
                                pwidth = c.stringWidth(product_name, 'Helvetica-Bold', 30)
                            else:
                                hyperlink_style.fontSize = 600 / len(product_name)
                                p = Paragraph(hyperlink, hyperlink_style)
                                pwidth = c.stringWidth(product_name, 'Helvetica-Bold', 600 / len(product_name))
                            p.wrapOn(c, max_image_width, max_image_height)
                            p.drawOn(c, x + (((max_image_width) / 2) - (pwidth / 2)), y + 590)
                            c.setStrokeColor('black')
                            c.setLineWidth(2)
                            c.setFillColor('black')
                            print(pwidth)
                            c.roundRect(x + (((max_image_width) / 2) - (pwidth / 2)) - 5, y + 565, pwidth + 40, 60, radius=10)
                            p.wrapOn(c, max_image_width, max_image_height)
                            p.drawOn(c, x + (((max_image_width) / 2) - (pwidth / 2)), y + 590)
                            color_codes = parse_colors(color_text)
                            rect_y = y + 30
                            rect_width = 25
                            rect_height = 25
                            rect_spacing = 5
                            c.setFont("Helvetica", 18)
                            for j, color_code in enumerate(color_codes):
                                rect_x = x + j * (rect_width + rect_spacing) + 120
                                c.setFillColor(color_code)
                                c.setLineWidth(0)
                                c.rect(rect_x, rect_y - 40, rect_width, rect_height, fill=1)
                                break
                            if len(size) <= 20:
                                c.setFont("Helvetica", 28)
                                c.setFillColor('black')
                                c.drawString(rect_x + 50, rect_y - 40, f"Size: {size}")
                            else: 
                                c.setFont("Helvetica", 12)
                                c.setFillColor('black')
                                c.drawString(rect_x + 50, rect_y - 40, f"Size: {size}")
                            c.setFillColor('yellow')
                            c.circle(x + 500, rect_y + 80, 70, fill=1, stroke=1)
                            c.setFont("Helvetica-Bold", 20)
                            c.setFillColor('black')
                            c.drawString(x + 450, rect_y + 80, 'Price (Rs):')
                            print(product_name)
                            if len(price_range) >= 11:
                                c.setFont("Helvetica-Bold", 22)
                                c.drawString(x + 450, rect_y + 60, f'{price_range}')
                            else:
                                c.setFont("Helvetica-Bold", 24)
                                c.drawString(x + 450, rect_y + 60, f'{price_range}')
                            page_has_content = True
                        else:
                            print(f"Failed to download image from {image_url}")
                    if page_has_content:
                        c.showPage()
        c.save()

    output_file = 'sample_catalogue.pdf'
    compressed_output_file = 'sample_catalogue_compressed.pdf'
    max_image_width = 146 + 400
    max_image_height = 175 + 400
    df = pd.read_csv('PDFReport_174857000100873355.csv')
    # df = df[df['ProductName'] == 'Epochlite 432']
    df = df[df['SuperCategory'] == 'Apparels']
    df = sort_dataframe_by_variant_count(df)
    # df = df.head(20)
    create_pdf(df, output_file, max_image_width, max_image_height)
    compress_pdf(output_file, compressed_output_file)
    return compressed_output_file

generate_catalogue_pdf()