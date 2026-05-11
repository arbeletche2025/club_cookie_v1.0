import uuid
from datetime import datetime
import gspread

gc = gspread.service_account(filename="credenciales.json")

sh = gc.open_by_key("12CR8Ez5yrxrYmwEz9tizQpqSMB8ZR4PBbwjgXoi56z4")
ws = sh.worksheet("Respuestas de formulario 1")

token_baja = str(uuid.uuid4())

nueva_fila = [
    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "Prueba",
    "Python",
    "pruebapython@email.com",
    "2210000000",
    "Guemes",
    "Test 123",
    "Pendiente de pago",
    "",
    "",
    "",
    "",
    token_baja,
    "",
]

ws.append_row(nueva_fila)

print("Fila agregada correctamente.")
print("Token de baja:", token_baja)