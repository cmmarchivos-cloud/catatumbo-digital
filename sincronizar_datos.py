import os
import sqlite3
import csv
import io
import urllib.request

# Configuración local de rutas y el ID único del documento de Google Sheets
DB_PATH = "catatumbo.db"
SPREADSHEET_ID = "1cVtzyJ2Y7X9N1fZ9rGZgLxPazXjnuaGg7eIZFVwgX7k"

# Enlaces directos configurados con sus respectivos gids y nombres de pestañas
SHEET_CSV_URLS = [
    (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=1341303465", "Título de Cementerio"),
    (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=872085590", "Solicitud de OMPU"),
    (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=2014289934", "Actas de Matrimonio, Nacimiento y Divorcio"),
    (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=937866469", "Terrenos Ejidos")
]

def asegurar_estructura_bd(cursor):
    """Asegura la estructura correcta de la tabla solicitudes_tramites en SQLite."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitudes_tramites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca_temporal TEXT,
            correo_google TEXT,
            nombre_solicitante TEXT,
            apellido_solicitante TEXT,
            cedula_solicitante TEXT,
            nacionalidad TEXT,
            correo_solicitante TEXT,
            parentesco TEXT,
            tipo_documento TEXT,
            numero_copias TEXT,
            anio_expediente_titulo TEXT,
            fecha_acta TEXT,
            nombre_titular TEXT,
            contrayente_masculino TEXT,
            contrayente_femenino TEXT,
            datos_expediente TEXT,
            url_adjunto_copia TEXT,
            estado TEXT DEFAULT 'PENDIENTE',
            observaciones TEXT,
            sincronizado INTEGER DEFAULT 0,
            tomo TEXT,
            folio TEXT,
            num_acta TEXT,
            monto TEXT,
            codigo_seguridad TEXT
        )
    """)

def mostrar_detalle_registros():
    """Muestra por consola el desglose detallado de todos los campos almacenados en la BD."""
    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, marca_temporal, nombre_solicitante, apellido_solicitante, cedula_solicitante, 
               tipo_documento, parentesco, numero_copias, anio_expediente_titulo, 
               fecha_acta, nombre_titular, contrayente_masculino, contrayente_femenino, 
               datos_expediente, url_adjunto_copia, estado
        FROM solicitudes_tramites
    """)
    registros = cursor.fetchall()
    conn.close()

    print("\n" + "="*90)
    print(" 🔍 INSPECCIÓN DETALLADA DE CAMPOS EN LA BASE DE DATOS")
    print("="*90)
    
    if not registros:
        print("[!] No hay registros almacenados actualmente.")
        return

    for reg in registros:
        print(f"[{reg[0]}] Tipo / Módulo: {reg[5]}")
        print(f"    • Marca Temporal   : {reg[1]}")
        print(f"    • Solicitante      : {reg[2]} {reg[3]} (Cédula: {reg[4]})")
        print(f"    • Parentesco       : {reg[6] or 'N/A'}")
        print(f"    • Número de Copias : {reg[7] or 'N/A'}")
        print(f"    • Año Exp / Título : {reg[8] or 'N/A'}")
        print(f"    • Fecha de Acta    : {reg[9] or 'N/A'}")
        print(f"    • Nombre Titular   : {reg[10] or 'N/A'}")
        print(f"    • Contrayentes     : Masc: [{reg[11] or 'N/A'}] / Fem: [{reg[12] or 'N/A'}]")
        print(f"    • Datos Expediente : {reg[13] or 'N/A'}")
        print(f"    • Archivo Adjunto  : {reg[14] or 'N/A'}")
        print(f"    • Estado Actual    : {reg[15]}")
        print("-" * 90)

def ejecutar_sincronizacion():
    print("[*] Sincronizando datos hacia la tabla 'solicitudes_tramites' (Modo Depuración Activo)...")
    
    if not os.path.exists(DB_PATH):
        print(f"[!] No se encontró la base de datos local en '{DB_PATH}'.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    asegurar_estructura_bd(cursor)
    conn.commit()

    nuevos_registros = 0
    duplicados_omitidos = 0

    try:
        for url, nombre_pestana in SHEET_CSV_URLS:
            print(f"\n--- Procesando pestaña: {nombre_pestana} ---")
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    csv_data = response.read().decode('utf-8')
                
                io_string = io.StringIO(csv_data)
                reader = csv.reader(io_string)
                
                header = next(reader, None)
                if not header:
                    print(f"[!] La pestaña está vacía.")
                    continue

                filas_pestana = 0
                for row in reader:
                    if not row or len(row) < 5:
                        continue
                    
                    total_cols = len(row)
                    
                    marca_temporal = row[0] if total_cols > 0 else ""
                    correo_google = row[1] if total_cols > 1 else ""
                    nombre_solicitante = row[2] if total_cols > 2 else ""
                    apellido_solicitante = row[3] if total_cols > 3 else ""
                    cedula_solicitante = row[4] if total_cols > 4 else ""
                    nacionalidad = row[5] if total_cols > 5 else "V"
                    correo_solicitante = row[6] if total_cols > 6 else correo_google

                    parentesco = ""
                    tipo_documento = nombre_pestana
                    numero_copias = ""
                    anio_expediente = ""
                    fecha_acta = ""
                    nombre_titular = ""
                    contrayente_masculino = ""
                    contrayente_femenino = ""
                    datos_expediente = ""
                    url_adjunto_copia = ""

                    if "Matrimonio" in nombre_pestana:
                        parentesco = row[7] if total_cols > 7 else ""
                        tipo_documento = row[8] if total_cols > 8 else nombre_pestana
                        fecha_acta = row[9] if total_cols > 9 else ""
                        numero_copias = row[10] if total_cols > 10 else ""
                        contrayente_masculino = row[11] if total_cols > 11 else ""
                        contrayente_femenino = row[12] if total_cols > 12 else ""
                        nombre_titular = f"Contrayentes: {contrayente_masculino} / {contrayente_femenino}".strip(" /")
                        if total_cols > 13:
                            url_adjunto_copia = row[13]

                    elif "Cementerio" in nombre_pestana:
                        tipo_documento = row[7] if total_cols > 7 else nombre_pestana
                        parentesco = row[8] if total_cols > 8 else ""
                        anio_expediente = row[9] if total_cols > 9 else ""
                        numero_copias = row[10] if total_cols > 10 else ""
                        nombre_titular = row[11] if total_cols > 11 else ""
                        if total_cols > 12:
                            url_adjunto_copia = row[12]

                    elif "OMPU" in nombre_pestana:
                        tipo_documento = row[7] if total_cols > 7 else nombre_pestana
                        parentesco = row[8] if total_cols > 8 else ""
                        anio_expediente = row[9] if total_cols > 9 else ""
                        numero_copias = row[10] if total_cols > 10 else ""
                        datos_expediente = row[11] if total_cols > 11 else ""
                        if total_cols > 12:
                            url_adjunto_copia = row[12]

                    elif "Ejidos" in nombre_pestana:
                        parentesco = row[7] if total_cols > 7 else ""
                        tipo_documento = row[8] if total_cols > 8 else nombre_pestana
                        anio_expediente = row[9] if total_cols > 9 else ""
                        nombre_titular = row[10] if total_cols > 10 else ""
                        numero_copias = row[11] if total_cols > 11 else ""
                        if total_cols > 12:
                            url_adjunto_copia = row[12]

                    # Validación anti-duplicados
                    if marca_temporal and cedula_solicitante:
                        cursor.execute("""
                            SELECT 1 FROM solicitudes_tramites 
                            WHERE marca_temporal = ? AND cedula_solicitante = ? AND tipo_documento = ?
                        """, (marca_temporal, cedula_solicitante, tipo_documento))
                        
                        if cursor.fetchone():
                            duplicados_omitidos += 1
                            continue

                    cursor.execute("""
                        INSERT INTO solicitudes_tramites (
                            marca_temporal, correo_google, correo_solicitante, nombre_solicitante, apellido_solicitante,
                            nacionalidad, cedula_solicitante, tipo_documento, parentesco,
                            numero_copias, anio_expediente_titulo, fecha_acta, 
                            nombre_titular, contrayente_masculino, contrayente_femenino, 
                            datos_expediente, url_adjunto_copia, estado, sincronizado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 1)
                    """, (
                        marca_temporal, correo_google, correo_solicitante, nombre_solicitante, apellido_solicitante,
                        nacionalidad, cedula_solicitante, tipo_documento, parentesco,
                        numero_copias, anio_expediente, fecha_acta,
                        nombre_titular, contrayente_masculino, contrayente_femenino,
                        datos_expediente, url_adjunto_copia
                    ))
                    
                    nuevos_registros += 1
                    filas_pestana += 1

                print(f"[✓] Nuevos importados desde '{nombre_pestana}': {filas_pestana}")

            except Exception as sheet_err:
                print(f"[!] Error leyendo la pestaña '{nombre_pestana}': {sheet_err}")

        conn.commit()
        conn.close()
        
        print(f"\n[✓] Sincronización completada con éxito.")
        print(f"    - Registros nuevos agregados: {nuevos_registros}")
        print(f"    - Duplicados omitidos: {duplicados_omitidos}")

        # Llamar a la función de detalle para mostrar la data en consola
        mostrar_detalle_registros()

    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
        print(f"[!] Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    ejecutar_sincronizacion()
