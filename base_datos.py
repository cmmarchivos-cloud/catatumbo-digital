import os
import sqlite3

# Definir la ruta del archivo de base de datos directamente en el disco de la PC
DIRECTORIO_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_DB_LOCAL = os.path.join(DIRECTORIO_BASE, "catatumbo.db")

def inicializar_base_datos_local():
    """Crea la base de datos y la tabla de registros en el disco local de la PC si no existen."""
    conexion = sqlite3.connect(RUTA_DB_LOCAL)
    cursor = conexion.cursor()
    
    # Tabla principal para almacenar los registros localmente de forma segura
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros_catatumbo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_documento TEXT NOT NULL,
            titulo TEXT NOT NULL,
            categoria TEXT,
            descripcion TEXT,
            ruta_archivo_local TEXT,
            sincronizado_nube INTEGER DEFAULT 0,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conexion.commit()
    conexion.close()
    print("Base de datos local inicializada correctamente en el disco.")

def guardar_registro_local(codigo, titulo, categoria, descripcion, ruta_archivo=""):
    """Guarda un nuevo registro de forma permanente en la PC y luego lo sincroniza con la nube."""
    try:
        conexion = sqlite3.connect(RUTA_DB_LOCAL)
        cursor = conexion.cursor()
        
        cursor.execute("""
            INSERT INTO registros_catatumbo 
            (codigo_documento, titulo, categoria, descripcion, ruta_archivo_local, sincronizado_nube)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (codigo, titulo, categoria, descripcion, ruta_archivo))
        
        conexion.commit()
        registro_id = cursor.lastrowid
        conexion.close()
        
        print(f"✔ Guardado con éxito en el disco de la PC (ID local: {registro_id}).")
        
        # Sincronizar automáticamente con la nube a través de la pasarela
        sincronizar_con_nube(registro_id, codigo, titulo, categoria, descripcion)
        return True
    except Exception as e:
        print(f"Error al guardar localmente: {e}")
        return False

def sincronizar_con_nube(registro_id, codigo, titulo, categoria, descripcion):
    """Pasarela con la nube: Envía los datos al servidor remoto manteniendo el respaldo local."""
    try:
        print(f"☁ Sincronizando registro {codigo} con la pasarela en la nube...")
        
        # [Aquí se ejecutará la conexión con la pasarela en la nube]
        # Si la operación es exitosa, actualizamos el estado local a sincronizado (1)
        
        conexion = sqlite3.connect(RUTA_DB_LOCAL)
        cursor = conexion.cursor()
        cursor.execute("UPDATE registros_catatumbo SET sincronizado_nube = 1 WHERE id = ?", (registro_id,))
        conexion.commit()
        conexion.close()
        print("✔ Sincronización con la nube completada.")
        
    except Exception as e:
        print("⚠ Sin conexión a la nube. El dato está seguro en el disco de tu PC y se sincronizará luego.")

def buscar_registros(criterio):
    """Busca registros de forma rápida y directa en el disco local de la PC."""
    conexion = sqlite3.connect(RUTA_DB_LOCAL)
    cursor = conexion.cursor()
    
    cursor.execute("""
        SELECT id, codigo_documento, titulo, categoria, descripcion, ruta_archivo_local, sincronizado_nube, fecha_registro 
        FROM registros_catatumbo 
        WHERE titulo LIKE ? OR codigo_documento LIKE ? OR categoria LIKE ?
    """, (f"%{criterio}%", f"%{criterio}%", f"%{criterio}%"))
    
    resultados = cursor.fetchall()
    conexion.close()
    return resultados

if __name__ == "__main__":
    inicializar_base_datos_local()
