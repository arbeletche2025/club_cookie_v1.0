import gspread

gc = gspread.service_account(filename="credenciales.json")

sh = gc.open_by_key("12CR8Ez5yrxrYmwEz9tizQpqSMB8ZR4PBbwjgXoi56z4")
ws = sh.worksheet("Respuestas de formulario 1")

rows = ws.get_all_records()

print("Conexión exitosa.")
print(f"Cantidad de filas encontradas: {len(rows)}")

print("Encabezados:")
print(ws.row_values(1))