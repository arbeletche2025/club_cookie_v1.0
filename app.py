import os
import uuid
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage

import gspread
import requests
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI()

# Carpeta para archivos estáticos: logo, imágenes, css, etc.
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Datos de Google Sheets
SPREADSHEET_ID = "12CR8Ez5yrxrYmwEz9tizQpqSMB8ZR4PBbwjgXoi56z4"
WORKSHEET_NAME = "Respuestas de formulario 1"

# Datos de Mercado Pago / entorno
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
COOKIE_BOX_PRICE = float(os.getenv("COOKIE_BOX_PRICE", "35000"))

# Datos de Gmail SMTP
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "The Cookie World")


def get_worksheet():
    """
    Conecta con Google Sheets.
    En Render usa GOOGLE_CREDENTIALS_JSON.
    En local usa credenciales.json.
    """
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


def get_headers(ws):
    return ws.row_values(1)


def get_col_number(ws, header_name):
    headers = get_headers(ws)
    if header_name not in headers:
        raise ValueError(f"No se encontró la columna: {header_name}")
    return headers.index(header_name) + 1


def find_row_by_value(ws, header_name, value):
    """
    Busca una fila por el valor de una columna.
    Devuelve número de fila o None.
    """
    col_number = get_col_number(ws, header_name)
    values = ws.col_values(col_number)

    for index, cell_value in enumerate(values, start=1):
        if str(cell_value).strip() == str(value).strip():
            return index

    return None


def get_cell_by_header(ws, row_number, header_name):
    col_number = get_col_number(ws, header_name)
    return ws.cell(row_number, col_number).value


def update_cell_by_header(ws, row_number, header_name, value):
    col_number = get_col_number(ws, header_name)
    ws.update_cell(row_number, col_number, value)


def enviar_mail(destinatario, asunto, texto_plano, html=None):
    """
    Envía un mail usando Gmail SMTP.
    """
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise ValueError("Faltan SMTP_EMAIL o SMTP_APP_PASSWORD en el archivo .env")

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_EMAIL}>"
    msg["To"] = destinatario

    msg.set_content(texto_plano)

    if html:
        msg.add_alternative(html, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        smtp.send_message(msg)


def enviar_mail_bienvenida(nombre, mail, token_baja):
    """
    Envía el mail de bienvenida al Club de la Cookie.
    """
    asunto = "Ya sos parte del Club TCW 🍪"
    link_baja = f"{BASE_URL}/cancelar?token={token_baja}"

    texto = f"""Hola, {nombre}:

¡Gracias por sumarte al Club de la Cookie! 🍪

Ya recibimos tu suscripción correctamente y desde ahora sos parte del club mensual de The Cookie World.

Cada mes vas a recibir una box especial con cookies exclusivas, sabores de edición limitada y sorpresas pensadas solo para miembros del club.

Cuando se acerque la entrega de tu box, te vamos a enviar un recordatorio con toda la información para que puedas organizar tu merienda como corresponde.

Mientras tanto, andá poniendo la pava, la cafetera o tu plan favorito, porque tu próxima merienda especial ya está en camino. 💖

Gracias por confiar en nosotros.

Atentamente,
The Cookie World 🍪

Si querés darte de baja del Club de la Cookie, podés anular tu suscripción desde acá:
{link_baja}
"""

    html = f"""
    <html>
      <body style="margin:0;background:#fff0f6;font-family:Arial,Helvetica,sans-serif;padding:24px;">
        <div style="max-width:620px;margin:0 auto;background:#ffffff;border:2px solid #ff5cad;border-radius:22px;overflow:hidden;box-shadow:0 8px 24px rgba(0,0,0,0.08);">

          <div style="background:linear-gradient(135deg,#ff5cad 0%,#ff9f1c 100%);padding:28px 24px;text-align:center;color:#ffffff;">
            <h1 style="margin:0;font-size:30px;font-family:Georgia,'Times New Roman',serif;">
              Ya sos parte del Club TCW 🍪
            </h1>
          </div>

          <div style="padding:28px 26px;color:#333;font-size:16px;line-height:1.7;">
            <p>Hola, <strong>{nombre}</strong>:</p>

            <p>¡Gracias por sumarte al <strong>Club de la Cookie</strong>! 🍪</p>

            <p>Ya recibimos tu suscripción correctamente y desde ahora sos parte del club mensual de <strong>The Cookie World</strong>.</p>

            <p>Cada mes vas a recibir una box especial con cookies exclusivas, sabores de edición limitada y sorpresas pensadas solo para miembros del club.</p>

            <p>Cuando se acerque la entrega de tu box, te vamos a enviar un recordatorio con toda la información para que puedas organizar tu merienda como corresponde.</p>

            <p>Mientras tanto, andá poniendo la pava, la cafetera o tu plan favorito, porque tu próxima merienda especial ya está en camino. 💖</p>

            <p>Gracias por confiar en nosotros.</p>

            <p style="margin-top:26px;">
              Atentamente,<br>
              <strong>The Cookie World 🍪</strong>
            </p>

            <hr style="border:none;border-top:1px solid #eee;margin:28px 0;">

            <p style="font-size:13px;color:#777;line-height:1.5;">
              Si querés darte de baja del Club de la Cookie, podés anular tu suscripción desde acá:<br>
              <a href="{link_baja}" style="color:#ff5cad;">Anular suscripción</a>
            </p>
          </div>
        </div>
      </body>
    </html>
    """

    enviar_mail(mail, asunto, texto, html)


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


def get_mp_subscription(preapproval_id):
    """
    Consulta una suscripción en Mercado Pago.
    """
    if not MP_ACCESS_TOKEN:
        raise ValueError("Falta MP_ACCESS_TOKEN en el archivo .env")

    url = f"https://api.mercadopago.com/preapproval/{preapproval_id}"

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)

    print("Consulta suscripción MP:", response.status_code)
    print(response.text)

    if response.status_code >= 400:
        response.raise_for_status()

    return response.json()


def cancel_mp_subscription(preapproval_id):
    """
    Cancela una suscripción en Mercado Pago.
    """
    if not MP_ACCESS_TOKEN:
        raise ValueError("Falta MP_ACCESS_TOKEN en el archivo .env")

    url = f"https://api.mercadopago.com/preapproval/{preapproval_id}"

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "status": "canceled"
    }

    response = requests.put(url, json=payload, headers=headers)

    print("Cancelación MP:", response.status_code)
    print(response.text)

    if response.status_code >= 400:
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
              <input name="mail" type="email" required style="width:100%;box-sizing:border-box;padding:12px;margin:6px 0 14px;border:1px solid #ddd;border-radius:10px;font-size:15px;">

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

        update_cell_by_header(ws, row_number, "preapproval_id", preapproval_id or "")
        update_cell_by_header(ws, row_number, "link_pago", link_pago or "")

        if not link_pago:
            update_cell_by_header(ws, row_number, "Estado", "Error")
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
        update_cell_by_header(ws, row_number, "Estado", "Error")

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


@app.post("/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    """
    Recibe avisos de Mercado Pago.
    Cuando la suscripción queda autorizada, actualiza Google Sheets y manda mail de bienvenida.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    print("Webhook Mercado Pago recibido:")
    print(body)

    query_params = dict(request.query_params)
    print("Query params:", query_params)

    event_type = body.get("type") or body.get("topic") or query_params.get("topic") or query_params.get("type")

    data = body.get("data") or {}
    preapproval_id = (
        data.get("id")
        or body.get("id")
        or query_params.get("id")
        or query_params.get("data.id")
    )

    if not preapproval_id:
        print("Webhook sin preapproval_id. Se responde OK igual.")
        return {"ok": True, "message": "Sin preapproval_id"}

    # Por ahora nos enfocamos en eventos de suscripción.
    # Si llega otro tipo de evento, intentamos consultar igual.
    print("Event type:", event_type)
    print("Preapproval ID:", preapproval_id)

    try:
        subscription = get_mp_subscription(preapproval_id)
        status = subscription.get("status")

        print("Estado suscripción MP:", status)

        if status not in ["authorized", "active"]:
            return {"ok": True, "message": f"Suscripción no activa todavía: {status}"}

        ws = get_worksheet()
        row_number = find_row_by_value(ws, "preapproval_id", preapproval_id)

        if not row_number:
            print("No se encontró fila con preapproval_id:", preapproval_id)
            return {"ok": True, "message": "Fila no encontrada"}

        estado_actual = get_cell_by_header(ws, row_number, "Estado")

        # Evita mandar el mail dos veces si Mercado Pago manda más de un webhook.
        if estado_actual == "Activo":
            return {"ok": True, "message": "La fila ya estaba activa"}

        nombre = get_cell_by_header(ws, row_number, "Nombre")
        mail = get_cell_by_header(ws, row_number, "Mail")
        token_baja = get_cell_by_header(ws, row_number, "token_baja")

        fecha_pago = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        update_cell_by_header(ws, row_number, "Estado", "Activo")
        update_cell_by_header(ws, row_number, "fecha_pago", fecha_pago)

        enviar_mail_bienvenida(nombre, mail, token_baja)

        print("Mail de bienvenida enviado a:", mail)

        return {"ok": True, "message": "Suscripción activada y mail enviado"}

    except Exception as e:
        print("Error procesando webhook:", str(e))
        return {"ok": False, "error": str(e)}


@app.get("/cancelar", response_class=HTMLResponse)
def cancelar_suscripcion(token: str):
    """
    Cancela la suscripción usando el token_baja guardado en Google Sheets.
    """
    try:
        ws = get_worksheet()
        row_number = find_row_by_value(ws, "token_baja", token)

        if not row_number:
            return HTMLResponse(
                """
                <html>
                  <body style="font-family:Arial;background:#fff0f6;padding:40px;text-align:center;">
                    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;padding:32px;">
                      <h1 style="color:#ff5cad;">No encontramos tu suscripción</h1>
                      <p>El link de baja no es válido o ya no está disponible.</p>
                    </div>
                  </body>
                </html>
                """,
                status_code=404,
            )

        estado_actual = get_cell_by_header(ws, row_number, "Estado")
        preapproval_id = get_cell_by_header(ws, row_number, "preapproval_id")

        if estado_actual == "Inactivo":
            return HTMLResponse(
                """
                <html>
                  <body style="font-family:Arial;background:#fff0f6;padding:40px;text-align:center;">
                    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;padding:32px;">
                      <h1 style="color:#ff5cad;">Tu suscripción ya estaba dada de baja</h1>
                      <p>No tenés una suscripción activa en este momento.</p>
                    </div>
                  </body>
                </html>
                """
            )

        if not preapproval_id:
            update_cell_by_header(ws, row_number, "Estado", "Inactivo")
            update_cell_by_header(ws, row_number, "fecha_baja", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

            return HTMLResponse(
                """
                <html>
                  <body style="font-family:Arial;background:#fff0f6;padding:40px;text-align:center;">
                    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;padding:32px;">
                      <h1 style="color:#ff5cad;">Suscripción dada de baja</h1>
                      <p>Tu estado fue actualizado como inactivo.</p>
                    </div>
                  </body>
                </html>
                """
            )

        cancel_mp_subscription(preapproval_id)

        fecha_baja = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        update_cell_by_header(ws, row_number, "Estado", "Inactivo")
        update_cell_by_header(ws, row_number, "fecha_baja", fecha_baja)

        return HTMLResponse(
            """
            <html>
              <body style="font-family:Arial;background:#fff0f6;padding:40px;text-align:center;">
                <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;padding:32px;">
                  <h1 style="color:#ff5cad;">Suscripción anulada</h1>
                  <p>Tu baja del Club de la Cookie fue procesada correctamente.</p>
                  <p>Gracias por haber sido parte de The Cookie World 🍪</p>
                </div>
              </body>
            </html>
            """
        )

    except Exception as e:
        print("Error cancelando suscripción:", str(e))

        return HTMLResponse(
            f"""
            <html>
              <body style="font-family:Arial;background:#fff0f6;padding:40px;text-align:center;">
                <div style="max-width:560px;margin:0 auto;background:#ffffff;border:3px solid #ff5cad;border-radius:24px;padding:32px;">
                  <h1 style="color:#ff5cad;">No pudimos cancelar la suscripción</h1>
                  <p>Intentá nuevamente más tarde o contactanos.</p>
                  <p style="font-size:13px;color:#777;">Detalle técnico: {str(e)}</p>
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