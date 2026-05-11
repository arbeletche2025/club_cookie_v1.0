import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("MP_ACCESS_TOKEN")
base_url = os.getenv("BASE_URL")
price = os.getenv("COOKIE_BOX_PRICE")

print("BASE_URL:", base_url)
print("COOKIE_BOX_PRICE:", price)

if token:
    print("MP_ACCESS_TOKEN encontrado correctamente.")
    print("El token empieza con:", token[:8])
else:
    print("No se encontró MP_ACCESS_TOKEN.")
    print("Revisá que el archivo .env exista y esté en la carpeta principal del proyecto.")