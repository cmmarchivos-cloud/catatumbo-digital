import os
import sqlite3
import requests
import json

# Configuración de rutas y credenciales corregida
URL_SERVIDOR = "https://cmmarchivos.pythonanywhere.com/api/sincronizar"
TOKEN_SECRETO = "Archivoscmm"
DB_PATH = "catatumbo.db"
UPLOAD_FOLDER = "storage_pdf"

def ejecutar_sincronizacion():
    headers = {"Authorization": f"Bearer {TOKEN_SECRETO}"}
    
    print("[*] Conectando con el servidor en la nube para buscar registros pendientes...")
    try:
        response = requests.get(URL_SERVIDOR, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[!] Error del servidor: {response.status_code} - {response.text}")
            return
        
        data = response.json()
        registros = data.get("registros", [])
        
        if not registros:
            print("[✓] La base de datos local ya se encuentra actualizada. No hay registros pendientes.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        ids_procesados = []
        
        for reg in registros:
            # Inserción transaccional respetando la tabla real 'documentos' y sus campos
            cursor.execute("""
                INSERT OR IGNORE INTO documentos (
                    id, tipo_documento, fecha_ingreso, archivos, nombre_masculino,
                    nombre_femenino, nombre_titular, numero_acta, anio_documento,
                    sub_tipo_cementerio, fecha_acta, fecha_gaceta, numero_gaceta,
                    fecha_documento, numero_registro, fecha_ingreso_lab, fecha_egreso_lab
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reg.get("id"),
                reg.get("tipo_documento"),
                reg.get("fecha_ingreso"),
                reg.get("archivos"),
                reg.get("nombre_masculino", ""),
                reg.get("nombre_femenino", ""),
                reg.get("nombre_titular", ""),
                reg.get("numero_acta", ""),
                reg.get("anio_documento", ""),
                reg.get("sub_tipo_cementerio", ""),
                reg.get("fecha_acta", ""),
                reg.get("fecha_gaceta", ""),
                reg.get("numero_gaceta", ""),
                reg.get("fecha_documento", ""),
                reg.get("numero_registro", ""),
                reg.get("fecha_ingreso_lab", ""),
                reg.get("fecha_egreso_lab", "")
            ))
            
            # Descarga de archivos PDF asociados hacia storage_pdf
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            for pdf_url in reg.get("lista_pdfs", []):
                pdf_res = requests.get(pdf_url, headers=headers)
                if pdf_res.status_code == 200:
                    nombre_archivo = pdf_url.split("/")[-1]
                    ruta_destino = os.path.join(UPLOAD_FOLDER, nombre_archivo)
                    with open(ruta_destino, "wb") as f:
                        f.write(pdf_res.content)
            
            ids_procesados.append(reg.get("id"))
            
        conn.commit()
        conn.close()
        
        # Notificar al servidor remoto para limpiar la cola temporal
        confirm_res = requests.post(URL_SERVIDOR, json={"ids": ids_procesados}, headers=headers, timeout=10)
        if confirm_res.status_code == 200:
            print(f"[✓] Sincronización completada con éxito. Se procesaron {len(ids_procesados)} registros.")
        else:
            print("[!] Advertencia: Los registros se guardaron localmente, pero no se pudo confirmar la limpieza en la nube.")

    except requests.exceptions.RequestException as e:
        print(f"[!] Error de conexión con el servidor: {e}")
    except Exception as e:
        print(f"[!] Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    ejecutar_sincronizacion()
