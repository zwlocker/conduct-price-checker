import requests
from bs4 import BeautifulSoup
import json
import smtplib
from email.message import EmailMessage
import boto3
from decimal import Decimal
from dotenv import load_dotenv
import os

load_dotenv()

email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")

database = boto3.resource('dynamodb', region_name='us-east-1')
table = database.Table('conductPriceTable')

def lambda_handler(event, context):
    url = "https://www.nintendo.com/us/store/products/conduct-together-switch/"
    response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')

    price_data = json.loads(soup.find("script", id="__NEXT_DATA__").string) \
        .get('props', {}) \
        .get('pageProps', {}) \
        .get('initialApolloState', {}) \
        .get('StoreProduct:{"sku":"7100015189","locale":"en_US"}', {}) \
        .get('prices({"personalized":false})', {}) \
        .get('minimum', {}) \
    
    current_price = Decimal(str(price_data.get('finalPrice')))
    
    if price_data.get('discounted', False) and not (stored_price() == current_price):
        send_email(current_price)        
        save_price(current_price)
        return {"statusCode": 200, "body": "New discount detected"}

    save_price(current_price)
    return {"statusCode": 200, "body": "New discount not detected"}

def send_email(final_price):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(email_user, email_password)
    message = EmailMessage()
    message['Subject'] = "Price change!"
    message['From'] = email_user
    message['To'] = "zacharywlocker@gmail.com"

    message.set_content(f"Conduct Together is on sale for ${final_price}!")
    message.add_alternative(f"""\
    <html>
        <body>
            <p><span style="color: black;">Conduct Together is <b>on sale</b> for ${final_price}</span>!</p>
            <p><span style="color: black;">Check out </span><a href="https://www.nintendo.com/us/store/products/conduct-together-switch/">https://www.nintendo.com/us/store/products/conduct-together-switch/</a> <span style="color: black;">for more details.</span></p>

            <p><span style="color: black;">You can't miss this once in a lifetime offer to lose all of your friends. Happy conducting!</span></p>
            <p><img src="https://www.nintendo.com/eu/media/images/11_square_images/games_18/nintendo_switch_download_software/SQ_NSwitchDS_ConductTogether_image500w.jpg" alt="Nintendo Logo" style="width:200px; height:auto;" /></p>

        </body>
    </html>
    """, subtype = 'html')

    s.send_message(message)
    s.quit()

def save_price(price):
    price_decimal = Decimal(str(price))
    table.put_item(
        Item={
            'price_id': '1',
            'price': price_decimal
        }
    )
    
def stored_price():
    response = table.get_item(
        Key={
            'price_id': '1'
        }
    )
    return response['Item']['price']

