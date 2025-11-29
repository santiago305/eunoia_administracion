import gspread
from google.oauth2.service_account import Credentials


# -------- CONFIGURACIÓN GLOBAL --------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    "eunoia.json",   # Cambia si está en otra ruta
    scopes=SCOPES
)
client = gspread.authorize(creds)

sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1aWa99epeIy7pZn3MaVxOy-CMsc9RQLVP3MGk1kwQeqA/edit?gid=472731081#gid=472731081"
)

# Puedes cambiar el nombre según donde vayas a registrar
worksheet_noviembre = sheet.worksheet("NOVIEMBRE")


# -------- FUNCIÓN PRINCIPAL --------
RANGO_ENCABEZADOS = "B2:J2"
CAMPOS_NUMERICOS = {"INGRESOS", "EGRESOS"}


def registrar_movimiento(
    worksheet,
    mes: str,
    fecha: str,
    numero_operacion: str,
    descripcion: str,
    detalle: str,
    metodo_pago: str,
    estado: str,
    ingresos: float | int | None = None,
    egresos: float | int | None = None,
):
    """
    Inserta un movimiento en la hoja indicada,
    respetando los encabezados B2:J2 y sin tocar la columna K (SALDO).
    """

    # Leer encabezados
    encabezados = worksheet.get(RANGO_ENCABEZADOS)[0]

    # Calcular siguiente fila libre usando la columna B (MES)
    col_mes = worksheet.col_values(2)
    siguiente_fila = 3 if len(col_mes) <= 1 else len(col_mes) + 1

    # Crear diccionario con datos
    nuevo_registro = {
        "MES": mes,
        "FECHA": fecha,
        "N° DE OPERACIÓN": numero_operacion,
        "DESCRIPCIÓN": descripcion,
        "DETALLE": detalle,
        "MÉTODO DE PAGO": metodo_pago,
        "ESTADO": estado,
        "INGRESOS": ingresos if ingresos is not None else 0,
        "EGRESOS": egresos if egresos is not None else 0,
    }

    # Construir fila respetando orden de encabezados
    fila_nueva = []
    for h in encabezados:
        valor = nuevo_registro.get(h, "")
        if h in CAMPOS_NUMERICOS and valor not in ("", None):
            try:
                valor = float(valor)
            except ValueError:
                pass
        else:
            if valor is None:
                valor = ""
        fila_nueva.append(valor)

    # Escribir en B:J en la fila disponible
    rango = f"B{siguiente_fila}:J{siguiente_fila}"
    worksheet.update(range_name=rango, values=[fila_nueva])
