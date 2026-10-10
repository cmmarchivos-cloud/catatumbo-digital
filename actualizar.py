import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'catatumbo.db')
DB_ADJUNTOS_ANTIGUA = os.path.join(BASE_DIR, 'adjuntos_digitales.db')

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

    # 2. Asegurar la tabla unificada de adjuntos y escáner en catatumbo.db
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adjuntos_escanner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_solicitante TEXT NOT NULL,
            apellido_solicitante TEXT NOT NULL,
            nacionalidad TEXT NOT NULL,
            cedula_solicitante TEXT NOT NULL,
            nombre_funcionario TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,
            numero_acta TEXT,
            anio INTEGER,
            tomo TEXT,
            folio TEXT,
            url_adjunto_copia TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Migrar registros de la base de datos antigua si existiera
    if os.path.exists(DB_ADJUNTOS_ANTIGUA):
        try:
            print("🔄 Encontrada base de datos antigua 'adjuntos_digitales.db'. Migrando registros...")
            conn_antigua = sqlite3.connect(DB_ADJUNTOS_ANTIGUA)
            conn_antigua.row_factory = sqlite3.Row
            registros_viejos = conn_antigua.execute("SELECT * FROM registros_adjuntos").fetchall()
            conn_antigua.close()

            for row in registros_viejos:
                cursor.execute("""
                    INSERT OR IGNORE INTO adjuntos_escanner (
                        id, nombre_solicitante, apellido_solicitante, nacionalidad,
                        cedula_solicitante, nombre_funcionario, tipo_documento,
                        numero_acta, anio, tomo, folio, url_adjunto_copia, fecha_registro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['id'],
                    row['nombre_solicitante'] or '',
                    row['apellido_solicitante'] or '',
                    row['nacionalidad'] or 'V',
                    row['cedula_solicitante'] or '',
                    row['responsable'] or 'Administrador',
                    row['tipo_documento'] or 'Documento',
                    row['num_acta'] or '',
                    row['anio'] or 2026,
                    row['tomo'] or '',
                    row['folio'] or '',
                    row['url_adjunto_copia'] or '',
                    row['fecha_registro']
                ))
            print("✅ Migración de adjuntos completada con éxito.")
        except Exception as e:
            print(f"⚠️ Aviso durante la migración de datos antiguos: {e}")

    conn.commit()
    conn.close()
    print("\n🚀 ¡Base de datos principal 'catatumbo.db' actualizada y unificada con éxito!")

if __name__ == '__main__':
    actualizar_base_datos()
