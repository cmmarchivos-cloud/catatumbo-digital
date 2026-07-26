import os
import sqlite3

RUTA_DB_LOCAL = os.path.join(os.path.dirname(__file__), "catatumbo.db")

def verificar():
    conexion = sqlite3.connect(RUTA_DB_LOCAL)
    cursor = conexion.cursor()
    cursor.execute("SELECT id, codigo_documento, titulo, categoria, fecha_registro FROM registros_catatumbo")
    registros = cursor.fetchall()
    conexion.close()
    
    print(f"Registros encontrados en el disco local: {len(registros)}")
    for r in registros:
        print(f"-> ID: {r[0]} | Código: {r[1]} | Título: {r[2]} | Categoría: {r[3]}")

if __name__ == "__main__":
    verificar()
