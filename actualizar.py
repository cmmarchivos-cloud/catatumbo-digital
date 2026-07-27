import os
import sqlite3

def actualizar_base_datos():
    db_path = 'catatumbo.db'
    print("[*] Verificando esquema de la base de datos...")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Verificar si la tabla documentos existe
            cursor.execute("PRAGMA table_info(documentos);")
            columnas = [col[1] for col in cursor.fetchall()]
            
            if columnas:
                if 'sincronizado' not in columnas:
                    cursor.execute("ALTER TABLE documentos ADD COLUMN sincronizado INTEGER DEFAULT 0;")
                    conn.commit()
                    print("[✓] Columna 'sincronizado' agregada exitosamente a la tabla 'documentos'.")
                else:
                    print("[✓] La tabla 'documentos' ya cuenta con la columna 'sincronizado'.")
            else:
                print("[!] Advertencia: La tabla 'documentos' no existe en la base de datos.")
            conn.close()
        except Exception as e:
            print(f"[!] Error al actualizar la base de datos: {e}")
    else:
        print("[!] No se encontró el archivo 'catatumbo.db'.")

def actualizar_app_py():
    app_path = 'app.py'
    print("[*] Verificando rutas en 'app.py'...")
    
    if not os.path.exists(app_path):
        print("[!] Error: No se encontró el archivo 'app.py' en la raíz.")
        return

    with open(app_path, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Verificar si el endpoint ya existe para evitar duplicarlo
    if '/api/sincronizar' in contenido:
        print("[✓] El endpoint de sincronización ya está integrado en 'app.py'.")
        return

    # Bloque de código seguro adaptado estrictamente a la tabla 'documentos' y 'storage_pdf'
    codigo_api = '''

# --- INICIO DE ENDPOINT DE SINCRONIZACION AUTOMATICA ---
from flask import request, jsonify

TOKEN_SECRETO = "TU_TOKEN_SECRETO_AQUI"

@app.route('/api/sincronizar', methods=['GET', 'POST'])
def api_sincronizar():
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {TOKEN_SECRETO}":
        return jsonify({"error": "No autorizado"}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM documentos WHERE sincronizado = 0")
        registros = []
        for row in cursor.fetchall():
            reg = dict(row)
            try:
                archivos_lista = json.loads(reg.get('archivos') or '[]')
            except:
                archivos_lista = []
            reg['lista_pdfs'] = [f"https://{request.host}/storage_pdf/{nombre}" for nombre in archivos_lista]
            registros.append(reg)
        conn.close()
        return jsonify({"registros": registros}), 200
        
    elif request.method == 'POST':
        data = request.json
        ids = data.get("ids", [])
        if ids:
            placeholders = ','.join(['?'] * len(ids))
            cursor.execute(f"UPDATE documentos SET sincronizado = 1 WHERE id IN ({placeholders})", ids)
            conn.commit()
        conn.close()
        return jsonify({"status": "ok"}), 200
# --- FIN DE ENDPOINT DE SINCRONIZACION AUTOMATICA ---
'''

    try:
        with open(app_path, 'a', encoding='utf-8') as f:
            f.write(codigo_api)
        print("[✓] Endpoint '/api/sincronizar' agregado correctamente a 'app.py'.")
    except Exception as e:
        print(f"[!] Error al modificar 'app.py': {e}")

if __name__ == "__main__":
    print("=== INICIANDO ACTUALIZACIÓN AUTOMATIZADA DE CATATUMBO DIGITAL ===")
    actualizar_base_datos()
    actualizar_app_py()
    print("=== PROCESO DE ACTUALIZACIÓN FINALIZADO ===")
