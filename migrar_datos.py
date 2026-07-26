import os
import json
import sqlite3

# Definir rutas en el directorio actual
DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_DB_LOCAL = os.path.join(DIRECTORIO_BASE, "catatumbo.db")
RUTA_JSON = os.path.join(DIRECTORIO_BASE, "documentos.json")

def migrar_registros_seguros():
    """Copia los datos de documentos.json hacia catatumbo.db sin eliminar el archivo original."""
    if not os.path.exists(RUTA_JSON):
        print("⚠ No se encontró el archivo documentos.json. No hay registros que migrar.")
        return

    if not os.path.exists(RUTA_DB_LOCAL):
        print("⚠ La base de datos local catatumbo.db no existe. Ejecuta primero base_datos.py.")
        return

    # Leer los datos antiguos del JSON
    with open(RUTA_JSON, 'r', encoding='utf-8') as f:
        documentos = json.load(f)

    conexion = sqlite3.connect(RUTA_DB_LOCAL)
    cursor = conexion.cursor()

    contador = 0
    for doc in documentos:
        # Extraer los datos adaptándolos de forma segura
        codigo = doc.get('numero_acta') or doc.get('numero_gaceta') or doc.get('numero_registro') or "S/C"
        titulo = doc.get('nombre_titular') or doc.get('nombre_masculino') or doc.get('nombre_femenino') or doc.get('tipo_documento', 'Documento')
        categoria = doc.get('tipo_documento', '')
        descripcion = f"Año: {doc.get('anio_documento', '')} | Ingreso: {doc.get('fecha_ingreso', '')}"
        
        archivos = doc.get('archivos', [])
        ruta_archivo = archivos[0] if archivos else ""

        # Insertar en la nueva base de datos local
        cursor.execute("""
            INSERT INTO registros_catatumbo 
            (codigo_documento, titulo, categoria, descripcion, ruta_archivo_local, sincronizado_nube)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (str(codigo), str(titulo), str(categoria), str(descripcion), str(ruta_archivo)))
        contador += 1

    conexion.commit()
    conexion.close()
    
    print(f"✔ ¡Migración completada con éxito! Se pasaron {contador} registros a la base de datos local.")
    print("✔ Tu archivo original 'documentos.json' está intacto y seguro.")

if __name__ == "__main__":
    migrar_registros_seguros()
