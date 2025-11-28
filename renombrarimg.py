import os
import json
from pathlib import Path

# Ruta donde están tus comprobantes ACTUALES
RUTA_ORIGEN = Path(r"C:\proyectos-finales\eunoia_administracion\entrenamiento\databaset\raw")

# Archivo donde guardaremos el mapeo
MAPA_SALIDA = RUTA_ORIGEN / "rename_map.json"

def main():
    imagenes = sorted([
        f for f in RUTA_ORIGEN.glob("*.*")
        if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]
    ])

    if not imagenes:
        print("❌ No se encontraron imágenes en la carpeta indicada.")
        return

    mapa = {}
    contador = 1

    for img in imagenes:
        nuevo_nombre = f"img_{contador:04d}{img.suffix.lower()}"
        nuevo_path = RUTA_ORIGEN / nuevo_nombre

        img.rename(nuevo_path)
        mapa[img.name] = nuevo_nombre

        contador += 1

    # Guardar JSON del mapeo
    with open(MAPA_SALIDA, "w", encoding="utf-8") as f:
        json.dump(mapa, f, indent=4, ensure_ascii=False)

    print("✨ Renombrado completado")
    print(f"📝 Mapa guardado en: {MAPA_SALIDA}")
    print(f"📌 Total imágenes renombradas: {len(mapa)}")

if __name__ == "__main__":
    main()
