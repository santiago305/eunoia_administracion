"""
text_utils.py
--------------
Funciones de utilidad para trabajar con texto:
- normalizar: poner en minúsculas y quitar tildes para facilitar comparaciones.
"""

def normalizar(texto: str) -> str:
    """
    Normaliza un texto para facilitar las búsquedas:
    - Convierte a minúsculas.
    - Reemplaza tildes y la ñ.

    Esto ayuda a comparar "Operación", "operacion", "operación", etc.
    """
    texto = texto.lower()
    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    return texto
