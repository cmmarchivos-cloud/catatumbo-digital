import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'catatumbo.db')

def actualizar_base_datos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Asegurar la tabla de solicitudes y trámites de Google Forms
    cursor.execute('''
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
            tomo TEXT,
            folio TEXT,
            num_acta TEXT,
            monto TEXT,
            fecha_acta TEXT,
            nombre_titular TEXT,
            contrayente_masculino TEXT,
            contrayente_femenino TEXT,
            datos_expediente TEXT,
            url_adjunto_copia TEXT,
            estado TEXT DEFAULT 'PENDIENTE',
            observaciones TEXT,
            sincronizado INTEGER DEFAULT 0
        )
    ''')

    # 2. Detectar la tabla principal de registros de documentos existente
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tablas = [row[0] for row in cursor.fetchall()]
    
    tabla_principal = None
    for t in ["registros_catatumbo", "registros", "documentos"]:
        if t in tablas:
            tabla_principal = t
            break
    
    if not tabla_principal:
        tabla_principal = "registros_catatumbo"

    # Crear tabla principal si no existe
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {tabla_principal} (
            index_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_documento TEXT,
            fecha_ingreso TEXT
        )
    ''')

    # 3. Lista de columnas nuevas o requeridas que se añadirán de forma segura
    columnas_nuevas = [
        ("tomo", "TEXT"),
        ("folio", "TEXT"),
        ("anio_documento", "TEXT"),
        ("numero_acta", "TEXT"),
        ("numero_gaceta", "TEXT"),
        ("numero_registro", "TEXT"),
        ("nombre_titular", "TEXT"),
        ("nombre_masculino", "TEXT"),
        ("nombre_femenino", "TEXT"),
        ("sub_tipo_cementerio", "TEXT"),
        ("fecha_acta", "TEXT"),
        ("fecha_gaceta", "TEXT"),
        ("fecha_documento", "TEXT"),
        ("fecha_ingreso_lab", "TEXT"),
        ("fecha_egreso_lab", "TEXT"),
        ("archivos", "TEXT")
    ]

    # Añadir columnas a la tabla principal si no existen (sin borrar datos previos)
    for col_nombre, col_tipo in columnas_nuevas:
        try:
            cursor.execute(f"ALTER TABLE {tabla_principal} ADD COLUMN {col_nombre} {col_tipo};")
            print(f"✅ Columna '{col_nombre}' agregada a '{tabla_principal}'.")
        except sqlite3.OperationalError:
            print(f"ℹ️ La columna '{col_nombre}' ya existe en '{tabla_principal}'.")

    # Añadir campos también a solicitudes_tramites por seguridad
    columnas_solicitudes = [
        ("tomo", "TEXT"),
        ("folio", "TEXT"),
        ("num_acta", "TEXT"),
        ("monto", "TEXT")
    ]
    for col_nombre, col_tipo in columnas_solicitudes:
        try:
            cursor.execute(f"ALTER TABLE solicitudes_tramites ADD COLUMN {col_nombre} {col_tipo};")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()
    print("\n🚀 ¡Base de datos actualizada con éxito! Todos los campos nuevos están listos.")

if __name__ == '__main__':
    actualizar_base_datos()
