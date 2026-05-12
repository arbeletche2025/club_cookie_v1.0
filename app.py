import os
import uuid
from datetime import datetime

import gspread
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles



load_dotenv()

app = FastAPI()


# Carpeta para archivos estáticos: logo, imágenes, css, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Datos de Google Sheets
SPREADSHEET_ID = "12CR8Ez5yrxrYmwEz9tizQpqSMB8ZR4PBbwjgXoi56z4"
WORKSHEET_NAME = "Respuestas de formulario 1"

# Datos de Mercado Pago / entorno
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
COOKIE_BOX_PRICE = float(os.getenv("COOKIE_BOX_PRICE", "35000"))


import json
from google.oauth2.service_account import Credentials

def get_worksheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(credentials)
    else:
        gc = gspread.service_account(filename="credenciales.json")
    sh = gc.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(WORKSHEET_NAME)


def create_mp_subscription(mail: str, external_reference: str):
    """
    Crea una suscripción única en Mercado Pago.
    Mercado Pago exige payer_email para /preapproval.
    """
    if not MP_ACCESS_TOKEN:
        raise ValueError("Falta MP_ACCESS_TOKEN en el archivo .env")

    url = "https://api.mercadopago.com/preapproval"

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "reason": "Club de la Cookie - Box mensual",
        "external_reference": external_reference,
        "payer_email": mail,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": COOKIE_BOX_PRICE,
            "currency_id": "ARS",
        },
        "back_url": f"{BASE_URL}/gracias",
    }
    print("Payload enviado a MP:", payload)
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code >= 400:
        print("Error Mercado Pago:", response.status_code)
        print(response.text)
        response.raise_for_status()

    return response.json()

@app.get("/")
def root():
    return RedirectResponse("/club")

@app.get("/club", response_class=HTMLResponse)
def club_form():
    return """
    <html>
      <head>
        <title>Club de la Cookie</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
      </head>

      <body style="margin:0;background:#fff0f6;font-family:Arial,Helvetica,sans-serif;padding:32px 16px;">
        <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.08);">

          <div style="background:linear-gradient(135deg,#ff5cad 0%,#ff9f1c 100%);padding:28px 24px;text-align:center;">

            <div style="margin-bottom:18px;">
              <img
                src="/static/logo-cookie-world.png"
                alt="The Cookie World"
                style="max-width:300px;width:100%;height:auto;display:block;margin:0 auto;"
              >
            </div>

            <div style="font-size:34px;line-height:1.15;font-weight:900;color:#ffffff;font-family:Georgia,'Times New Roman',serif;margin-bottom:12px;">
              Club de la Cookie 🍪
            </div>

            <div style="display:inline-block;background:#ffffff;color:#ff5cad;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:7px 18px;border-radius:999px;">
              Suscripción mensual
            </div>
          </div>

          <div style="padding:30px 26px;">
            <p style="text-align:center;color:#444;font-size:16px;line-height:1.6;margin-top:0;margin-bottom:24px;">
              Completá tus datos para ser parte del club TCW
            </p>

            <form method="post" action="/club">

              <label style="font-size:13px;font-weight:bold;color:#555;">Nombre</label>
              <input name="nombre" required style="width:100%;box-sizing:border-box;padding:12px;margin:6px 0 14px;border:1px solid #ddd;border-radius:10px;font-size:15px;">

              <label style="font-size:13px;font-weight:bold;color:#555;">Apellido</label>
              <input name="apellido" required style="width:100%;box-sizing:border-box;padding:12px;margin:6px 0 14px;border:1px solid #ddd;border-radius:10px;font-size:15px;">

              <label style="font-size:13px;font-weight:bold;color:#555;">Mail</label>
              <input name="mail" type="mail" required style="width:100%;box-sizing:border-box;padding:12px;margin:6px 0 14px;border:1px solid #ddd;border-radius:10px;font-size:15px;">

              <label style="font-size:13px;font-weight:bold;color:#555;">Número de teléfono</label>
              <input name="telefono" required style="width:100%;box-sizing:border-box;padding:12px;margin:6px 0 14px;border:1px solid #ddd;border-radius:10px;font-size:15px;">

              <label style="font-size:13px;font-weight:bold;color:#555;">Barrio</label>
              <input name="barrio" required style="width:100%;box-sizing:border-box;padding:12px;margin:6px 0 14px;border:1px solid #ddd;border-radius:10px;font-size:15px;">

              <label style="font-size:13px;font-weight:bold;color:#555;">Dirección de entrega</label>
              <input name="direccion" required style="width:100%;box-sizing:border-box;padding:12px;margin:6px 0 22px;border:1px solid #ddd;border-radius:10px;font-size:15px;">

              <button type="submit" style="width:100%;background:#ff5cad;color:white;border:none;padding:15px;border-radius:999px;font-weight:bold;font-size:16px;cursor:pointer;">
                Ir al pago 🍪
              </button>

            </form>
          </div>

        </div>
      </body>
    </html>
    """


@app.post("/club")
def submit_club_form(
    nombre: str = Form(...),
    apellido: str = Form(...),
    mail: str = Form(...),
    telefono: str = Form(...),
    barrio: str = Form(...),
    direccion: str = Form(...),
):
    ws = get_worksheet()

    token_baja = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    nueva_fila = [
        timestamp,
        nombre,
        apellido,
        mail,
        telefono,
        barrio,
        direccion,
        "Pendiente de pago",
        "",
        "",
        "",
        "",
        token_baja,
        "",
    ]

    ws.append_row(nueva_fila)

    all_values = ws.get_all_values()
    row_number = len(all_values)

    external_reference = f"club_cookie_fila_{row_number}"

    try:
        subscription = create_mp_subscription(
            mail=mail,
            external_reference=external_reference,
        )

        preapproval_id = subscription.get("id")
        link_pago = (
            subscription.get("init_point")
            or subscription.get("sandbox_init_point")
            or subscription.get("link")
        )

        ws.update_acell(f"I{row_number}", preapproval_id or "")
        ws.update_acell(f"J{row_number}", link_pago or "")

        if not link_pago:
            ws.update_acell(f"H{row_number}", "Error")
            return HTMLResponse(
                """
                <html>
                  <body style="font-family:Arial;padding:40px;text-align:center;background:#fff0f6;">
                    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;padding:32px;">
                      <h1 style="color:#ff5cad;">No pudimos generar el link de pago</h1>
                      <p>Revisá la respuesta de Mercado Pago en la terminal.</p>
                    </div>
                  </body>
                </html>
                """,
                status_code=500,
            )

        return RedirectResponse(link_pago, status_code=303)

    except Exception as e:
        print("Error creando suscripción:", str(e))
        ws.update_acell(f"H{row_number}", "Error")

        return HTMLResponse(
            f"""
            <html>
              <body style="font-family:Arial;padding:40px;text-align:center;background:#fff0f6;">
                <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;padding:32px;">
                  <h1 style="color:#ff5cad;">Error al crear la suscripción</h1>
                  <p>No pudimos generar el link de Mercado Pago.</p>
                  <p style="color:#777;font-size:13px;">Detalle técnico: {str(e)}</p>
                </div>
              </body>
            </html>
            """,
            status_code=500,
        )


@app.get("/gracias", response_class=HTMLResponse)
def gracias():
    return """
    <html>
      <head>
        <title>Gracias - Club de la Cookie</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
      </head>

      <body style="margin:0;background:#fff0f6;font-family:Arial,Helvetica,sans-serif;padding:32px 16px;">
        <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.08);">

          <div style="background:linear-gradient(135deg,#ff5cad 0%,#ff9f1c 100%);padding:28px 24px;text-align:center;">

            <div style="margin-bottom:18px;">
              <img
                src="/static/logo-cookie-world.png"
                alt="The Cookie World"
                style="max-width:300px;width:100%;height:auto;display:block;margin:0 auto;"
              >
            </div>

            <div style="font-size:32px;line-height:1.15;font-weight:900;color:#ffffff;font-family:Georgia,'Times New Roman',serif;margin-bottom:12px;">
              Gracias por sumarte 🍪
            </div>

            <div style="display:inline-block;background:#ffffff;color:#ff5cad;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:7px 18px;border-radius:999px;">
              Club de la Cookie
            </div>
          </div>

          <div style="padding:32px 26px;text-align:center;">
            <h1 style="color:#ff5cad;margin-top:0;font-size:28px;">
              Ya casi sos parte
            </h1>

            <p style="font-size:16px;color:#444;line-height:1.7;">
              Estamos validando tu pago con Mercado Pago.
            </p>

            <p style="font-size:16px;color:#444;line-height:1.7;">
              Cuando se confirme, te va a llegar el mail de bienvenida.
            </p>

            <div style="margin-top:24px;background:#fff8f1;border:2px dashed #ff9f1c;border-radius:14px;padding:16px;color:#333;font-size:15px;">
              Estado actual: <strong>Pendiente de confirmación</strong>
            </div>
          </div>

        </div>
      </body>
    </html>
    """
if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)