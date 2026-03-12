import requests

# TO'G'RI TOKEN (image.png dagi bilan bir xil)
BOT_TOKEN = "8665590507:AAEXHhP6_Blv8Ocikc9YCapV4w6nJk51Ni8"
WEBHOOK_URL = "https://repititor-uz.onrender.com/webhook"

# Webhook o'rnatish
response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
print("Bot ma'lumoti:", response.json())  # Bot mavjudligini tekshirish

if response.json().get('ok'):
    # Delete old webhook
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
    
    # Set new webhook
    result = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": WEBHOOK_URL}
    )
    print("Webhook o'rnatildi:", result.json())
else:
    print("Token xato! Tekshiring:", response.json())