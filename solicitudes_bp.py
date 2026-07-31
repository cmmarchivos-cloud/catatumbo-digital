import csv
import io
import json
import random
import string
import urllib.request
import urllib.parse
import smtplib
import traceback
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app

from base_datos import get_db

solicitudes_bp = Blueprint('solicitudes_bp', __name__)

def generar_codigo_seguridad():
    letras = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CMBM-{letras}"

def obtener_trimestre(fecha_str):
    if not fecha_str:
        return "Sin Fecha"
    fecha_limpia = fecha_str.strip()
    
    # Intentar formatos estándar de fecha y hora
    formatos = (
        "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", 
        "%m/%d/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"
    )
    for fmt in formatos:
        try:
            dt = datetime.strptime(fecha_limpia, fmt)
            mes = dt.month
            trimestre = (mes - 1) // 3 + 1
            return f"Q{trimestre} - {dt.year}"
        except ValueError:
            continue
            
    # Respaldo inteligente buscando año y mes mediante extracción numérica si el formato es atípico
    try:
        import re
        match_anio = re.search(r'\b(20\d{2})\b', fecha_limpia)
        anio = match_anio.group(1) if match_anio else "2026"
        
        numeros = re.findall(r'\b(0?[1-9]|1[0-2])\b', fecha_limpia)
        if numeros:
            mes = int(numeros[0])
            trimestre = (mes - 1) // 3 + 1
            return f"Q{trimestre} - {anio}"
        return f"Trimestre {anio}"
    except Exception:
        pass
        
    return "Desconocido"

# --- VISTA PRINCIPAL ---
@solicitudes_bp.route('/solicitudes')
def ver_solicitudes():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    solicitudes = conn.execute("SELECT * FROM solicitudes_tramites ORDER BY id DESC").fetchall()
    conn.close()
    
    # Recuperar datos temporales del expediente seleccionado (si existen)
    expediente_activo = session.get('expediente_activo', {})
    
    return render_template('solicitudes.html', solicitudes=solicitudes, expediente_activo=expediente_activo)

# --- CAPTURAR Y ALMACENAR DATOS DEL EXPEDIENTE SELECCIONADO ---
@solicitudes_bp.route('/solicitudes/usar-expediente', methods=['GET', 'POST'])
def usar_datos_expediente():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    session['expediente_activo'] = {
        'anio': request.args.get('anio') or request.form.get('anio', ''),
        'tomo': request.args.get('tomo') or request.form.get('tomo', ''),
        'folio': request.args.get('folio') or request.form.get('folio', ''),
        'acta': request.args.get('acta') or request.form.get('acta', '')
    }
    
    flash('📋 Datos del expediente importados correctamente. Seleccione la solicitud a procesar.', 'success')
    return redirect(url_for('solicitudes_bp.ver_solicitudes'))

# --- PROCESAR, GUARDAR Y ENVIAR COMPROBANTE QR ---
@solicitudes_bp.route('/solicitudes/procesar/<int:id>', methods=['POST'])
def procesar_y_guardar(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    anio_expediente = request.form.get('anio_expediente_titulo')
    tomo = request.form.get('tomo')
    folio = request.form.get('folio')
    num_acta = request.form.get('num_acta')
    monto = request.form.get('monto')
    estado = request.form.get('estado')
    confirmado = request.form.get('confirmado')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM solicitudes_tramites WHERE id = ?", (id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        flash('❌ Solicitud no encontrada.', 'danger')
        return redirect(url_for('solicitudes_bp.ver_solicitudes'))

    codigo_seguridad = row['codigo_seguridad'] if 'codigo_seguridad' in row.keys() else None
    ya_procesada = (row['estado'] == 'PROCESADA' or (codigo_seguridad and str(codigo_seguridad).startswith('CMBM-')))

    if ya_procesada and confirmado != '1':
        conn.close()
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Confirmación</title></head>
        <body>
        <script>
            if (confirm("⚠️ Esta solicitud ya fue procesada y enviada anteriormente.\\n\\n¿Desea reenviar el comprobante?")) {{
                var form = document.createElement('form');
                form.method = 'POST';
                form.action = "{url_for('solicitudes_bp.procesar_y_guardar', id=id)}";
                
                var data = {{
                    'anio_expediente_titulo': {json.dumps(anio_expediente or '')},
                    'tomo': {json.dumps(tomo or '')},
                    'folio': {json.dumps(folio or '')},
                    'num_acta': {json.dumps(num_acta or '')},
                    'monto': {json.dumps(monto or '')},
                    'estado': {json.dumps(estado or '')},
                    'confirmado': '1'
                }};
                
                for (var key in data) {{
                    var input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = key;
                    input.value = data[key];
                    form.appendChild(input);
                }}
                document.body.appendChild(form);
                form.submit();
            }} else {{
                window.location.href = "{url_for('solicitudes_bp.ver_solicitudes')}";
            }}
        </script>
        </body>
        </html>
        """

    if estado == 'PROCESADA':
        if not codigo_seguridad or not str(codigo_seguridad).startswith('CMBM-'):
            codigo_seguridad = generar_codigo_seguridad()

        nombre = row['nombre_solicitante'] or ''
        apellido = row['apellido_solicitante'] or ''
        cedula = row['cedula_solicitante'] or ''
        nacionalidad = row['nacionalidad'] or 'V'
        correo = row['correo_solicitante'] or ''
        tipo_doc = row['tipo_documento'] or 'Documento'
        id_full = f"{nacionalidad}-{cedula}"

        monto_str = f"Bs. {monto}" if monto and "Bs" not in monto else (monto or "Por verificar en taquilla")

        texto_qr = (f"🏛️ CMBM - ARCHIVO MUNICIPAL\n"
                    f"SOLICITANTE: {nombre} {apellido}\n"
                    f"ID: {id_full}\n"
                    f"DOCUMENTO: {tipo_doc}\n"
                    f"MONTO: {monto_str}\n"
                    f"UBICACIÓN: AÑO {anio_expediente}/T:{tomo}/F:{folio}/ACTA:{num_acta}\n"
                    f"SEGURIDAD: {codigo_seguridad}")
        
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(texto_qr)}"

        html_cuerpo = f"""
        <div style="background-color: #f4f7f9; padding: 10px; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 12px;">
          <div style="max-width: 550px; margin: auto; background-color: #ffffff; border-radius: 6px; overflow: hidden; border: 1px solid #e1e8ed;">
            
            <div style="background: linear-gradient(135deg, #03254c 0%, #064b99 100%); color: white; padding: 12px; text-align: center;">
              <div style="font-size: 16px; font-weight: 800; letter-spacing: 1px;">ARCHIVO MUNICIPAL</div>
              <div style="font-size: 9px; text-transform: uppercase; opacity: 0.9; letter-spacing: 1px;">Concejo Municipal Bolivariano de Maracaibo</div>
            </div>

            <div style="padding: 15px; line-height: 1.3;">
              <h3 style="color: #03254c; margin-top: 0; font-size: 14px;">¡Solicitud Procesada con Éxito! Comprobante de Trámite N° {id}!</h3>
              <p style="color: #555; margin: 3px 0 10px 0; font-size: 12px;">Estimado(a) ciudadano(a) <b>{nombre} {apellido}</b>, se ha generado su comprobante digital de validación para el trámite de documentos certificados.</p>
              
              <div style="background-color: #f8fafc; border-radius: 6px; padding: 10px; border: 1px solid #edf2f7; margin-bottom: 10px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                  <tr><td style="padding: 3px 0; color: #718096;">👤 Titular:</td><td style="padding: 3px 0; text-align: right; font-weight: bold; color: #2d3748;">{nombre} {apellido}</td></tr>
                  <tr><td style="padding: 3px 0; color: #718096;">🆔 Cédula / ID:</td><td style="padding: 3px 0; text-align: right; font-weight: bold; color: #2d3748;">{id_full}</td></tr>
                  <tr><td style="padding: 3px 0; color: #718096;">📄 Documento:</td><td style="padding: 3px 0; text-align: right; font-weight: bold; color: #2d3748;">{tipo_doc}</td></tr>
                  <tr><td style="padding: 3px 0; color: #718096;">📂 Ubicación Archivo:</td><td style="padding: 3px 0; text-align: right; font-weight: bold; color: #2d3748;">Año {anio_expediente} | T:{tomo} | F:{folio} | Acta:{num_acta}</td></tr>
                  <tr><td style="padding: 3px 0; color: #718096;">💰 Monto a Pagar:</td><td style="padding: 3px 0; text-align: right; font-weight: bold; color: #e53e3e;">{monto_str}</td></tr>
                  <tr><td style="padding: 5px 0 2px 0; color: #718096;">🔐 Código de Seguridad:</td><td style="padding: 5px 0 2px 0; text-align: right;"><span style="background-color: #03254c; color: white; padding: 2px 6px; border-radius: 3px; font-family: monospace; font-size: 12px;">{codigo_seguridad}</span></td></tr>
                </table>
              </div>

              <div style="border-left: 3px solid #f6ad55; background-color: #fffaf0; padding: 10px; border-radius: 0 6px 6px 0; margin-bottom: 10px; font-size: 11px;">
                <div style="color: #9c4221; font-weight: bold; margin-bottom: 4px;">📍 PASOS OBLIGATORIOS PARA RETIRAR:</div>
                <ul style="margin: 0; padding-left: 15px; color: #744210; line-height: 1.3;">
                  <li style="margin-bottom: 3px;">Asistir a <b>SEDEMAT</b> (Sector Valle Frío, Av. 3F entre calles 81 y 82).</li>
                  <li style="margin-bottom: 3px;">Realizar el pago de aranceles municipales correspondientes.</li>
                  <li>Presentar el pago del SEDEMAT para la certificación del documento y su posterior retiro (3 días hábiles).</li>
                </ul>
              </div>

              <div style="text-align: center; border-top: 1px solid #edf2f7; padding-top: 10px;">
                <div style="font-size: 10px; font-weight: bold; color: #a0aec0; margin-bottom: 6px; text-transform: uppercase;">Validación de Integridad de Datos</div>
                <img src="{qr_url}" width="105" height="105" style="border: 1px solid #e2e8f0; padding: 2px; border-radius: 4px;">
                <p style="font-size: 9px; color: #cbd5e0; margin-top: 6px; font-family: monospace;">ID AUDITORÍA: CMBM-WEB-SYS-2026</p>
              </div>
            </div>

            <div style="background-color: #f8fafc; padding: 8px; text-align: center; font-size: 9px; color: #a0aec0; border-top: 1px solid #edf2f7;">
              Este es un mensaje automático. Por favor no responder a esta dirección.<br>
              <b>Alcaldía Bolivariana de Maracaibo - Gestión Eficiente.</b>
            </div>

          </div>
        </div>
        """

        try:
            email_emisor = current_app.config.get('MAIL_USERNAME')
            email_password = current_app.config.get('MAIL_PASSWORD')
            smtp_server = current_app.config.get('MAIL_SERVER')
            smtp_port = current_app.config.get('MAIL_PORT')

            if not correo or '@' not in str(correo) or '.' not in str(correo) or len(correo.strip()) < 5:
                flash(f'⚠️ ATENCIÓN (Trámite #{id}): El estado se actualizó, pero el correo "{correo}" es inválido y no se pudo enviar el comprobante.', 'warning')
            else:
                msg = MIMEMultipart()
                msg['From'] = email_emisor
                msg['To'] = correo
                msg['Subject'] = Header(f"🏛️ COMPROBANTE DIGITAL: {nombre} {apellido} (Trámite #{id} - {tipo_doc})", 'utf-8')
                msg.attach(MIMEText(html_cuerpo, 'html', 'utf-8'))

                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(email_emisor, email_password)
                server.sendmail(email_emisor, correo, msg.as_bytes())
                server.quit()
                flash(f'✅ Comprobante enviado a: {correo}', 'success')
        except Exception as e:
            print("=== ERROR DETALLADO DE ENVÍO DE CORREO ===")
            traceback.print_exc()
            flash(f'⚠️ Error enviando correo: {str(e)}', 'danger')

    try:
        conn.execute('''
            UPDATE solicitudes_tramites 
            SET anio_expediente_titulo = ?, tomo = ?, folio = ?, num_acta = ?, monto = ?, estado = ?, codigo_seguridad = ?
            WHERE id = ?
        ''', (anio_expediente, tomo, folio, num_acta, monto, estado, codigo_seguridad, id))
        conn.commit()
        
        # Limpiar el expediente activo de la sesión una vez procesado con éxito
        session.pop('expediente_activo', None)
    except Exception as e:
        print(f"[!] Error actualizando base de datos: {e}")
    
    conn.close()
    return redirect(url_for('solicitudes_bp.ver_solicitudes'))

# --- PROCESAR Y ARCHIVAR OP ---
@solicitudes_bp.route('/procesar_solicitud/<string:num_op>', methods=['POST'])
def procesar_solicitud(num_op):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS op_procesados (
            op TEXT PRIMARY KEY
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO op_procesados (op) VALUES (?)", (num_op,))
    cursor.execute("DELETE FROM solicitudes_tramites WHERE id = ?", (num_op,))
    
    conn.commit()
    conn.close()

    flash("Trámite procesado y registrado con éxito.", "success")
    return redirect(url_for('solicitudes_bp.ver_solicitudes'))

# --- ELIMINAR SOLICITUD ( ENVÍO A PAPELERA DE RECICLAJE ) ---
@solicitudes_bp.route('/solicitudes/eliminar/<int:id>')
def eliminar_solicitud(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papelera_solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca_temporal TEXT,
            correo_solicitante TEXT,
            apellido_solicitante TEXT,
            nombre_solicitante TEXT,
            nacionalidad TEXT,
            cedula_solicitante TEXT,
            tipo_documento TEXT,
            parentesco TEXT,
            numero_copias TEXT,
            nombre_titular TEXT,
            estado TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros_excluidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT,
            marca_temporal TEXT,
            tipo_documento TEXT
        )
    ''')

    cursor.execute("SELECT * FROM solicitudes_tramites WHERE id = ?", (id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("""
            INSERT INTO papelera_solicitudes (
                marca_temporal, correo_solicitante, apellido_solicitante, nombre_solicitante,
                nacionalidad, cedula_solicitante, tipo_documento, parentesco,
                numero_copias, nombre_titular, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['marca_temporal'], row['correo_solicitante'], row['apellido_solicitante'], 
            row['nombre_solicitante'], row['nacionalidad'], row['cedula_solicitante'], 
            row['tipo_documento'], row['parentesco'], row['numero_copias'], 
            row['nombre_titular'], row['estado']
        ))

        cursor.execute("""
            INSERT INTO registros_excluidos (cedula, marca_temporal, tipo_documento) 
            VALUES (?, ?, ?)
        """, (row['cedula_solicitante'], row['marca_temporal'], row['tipo_documento']))

        cursor.execute("DELETE FROM solicitudes_tramites WHERE id = ?", (id,))

    conn.commit()
    conn.close()
    
    flash('🗑️ Solicitud enviada a la papelera de reciclaje.', 'info')
    return redirect(url_for('solicitudes_bp.ver_solicitudes'))

# --- VISTA PAPELERA DE RECICLAJE ---
@solicitudes_bp.route('/solicitudes/papelera')
def ver_papelera():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papelera_solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca_temporal TEXT, correo_solicitante TEXT, apellido_solicitante TEXT, 
            nombre_solicitante TEXT, nacionalidad TEXT, cedula_solicitante TEXT, 
            tipo_documento TEXT, parentesco TEXT, numero_copias TEXT, nombre_titular TEXT, estado TEXT
        )
    ''')
    papelera = cursor.execute("SELECT * FROM papelera_solicitudes ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('papelera.html', papelera=papelera)

# --- RESTAURAR DESDE PAPELERA ---
@solicitudes_bp.route('/solicitudes/papelera/restaurar/<int:id>', methods=['GET', 'POST'])
def restaurar_solicitud(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM papelera_solicitudes WHERE id = ?", (id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("""
            INSERT INTO solicitudes_tramites (
                marca_temporal, correo_solicitante, apellido_solicitante, nombre_solicitante,
                nacionalidad, cedula_solicitante, tipo_documento, parentesco,
                numero_copias, nombre_titular, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['marca_temporal'], row['correo_solicitante'], row['apellido_solicitante'], 
            row['nombre_solicitante'], row['nacionalidad'], row['cedula_solicitante'], 
            row['tipo_documento'], row['parentesco'], row['numero_copias'], 
            row['nombre_titular'], row['estado']
        ))

        cursor.execute("""
            DELETE FROM registros_excluidos 
            WHERE cedula = ? AND marca_temporal = ? AND tipo_documento = ?
        """, (row['cedula_solicitante'], row['marca_temporal'], row['tipo_documento']))

        cursor.execute("DELETE FROM papelera_solicitudes WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    flash('♻️ Solicitud restaurada con éxito a la bandeja principal.', 'success')
    return redirect(url_for('solicitudes_bp.ver_papelera'))

# --- ELIMINAR DEFINITIVO DESDE PAPELERA ---
@solicitudes_bp.route('/solicitudes/papelera/eliminar-definitivo/<int:id>', methods=['GET', 'POST'])
def eliminar_definitivo(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM papelera_solicitudes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash('⚡ Registro eliminado permanentemente de la papelera.', 'warning')
    return redirect(url_for('solicitudes_bp.ver_papelera'))

# --- INFORME DE ESTADÍSTICAS TRIMESTRALES (ACTUALIZADO) ---
@solicitudes_bp.route('/solicitudes/estadisticas')
def estadisticas_trimestrales():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papelera_solicitudes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca_temporal TEXT, correo_solicitante TEXT, apellido_solicitante TEXT, 
            nombre_solicitante TEXT, nacionalidad TEXT, cedula_solicitante TEXT, 
            tipo_documento TEXT, parentesco TEXT, numero_copias TEXT, nombre_titular TEXT, estado TEXT
        )
    ''')

    activas = cursor.execute("SELECT estado, marca_temporal FROM solicitudes_tramites").fetchall()
    papelera = cursor.execute("SELECT marca_temporal FROM papelera_solicitudes").fetchall()
    conn.close()

    estadisticas = {}

    def asegurar_trimestre(trim):
        if trim not in estadisticas:
            estadisticas[trim] = {'procesadas': 0, 'pendientes': 0, 'borradas': 0, 'total': 0}

    for row in activas:
        trim = obtener_trimestre(row['marca_temporal'])
        asegurar_trimestre(trim)
        estadisticas[trim]['total'] += 1
        if row['estado'] == 'PROCESADA':
            estadisticas[trim]['procesadas'] += 1
        else:
            estadisticas[trim]['pendientes'] += 1

    for row in papelera:
        trim = obtener_trimestre(row['marca_temporal'])
        asegurar_trimestre(trim)
        estadisticas[trim]['borradas'] += 1
        estadisticas[trim]['total'] += 1

    # Transformar a lista de diccionarios para compatibilidad directa con estadisticas.html
    estadisticas_lista = [
        {
            'trimestre': trim,
            'procesadas': datos['procesadas'],
            'pendientes': datos['pendientes'],
            'borradas': datos['borradas'],
            'total': datos['total']
        }
        for trim, datos in estadisticas.items()
    ]

    return render_template('estadisticas.html', estadisticas=estadisticas_lista)

# --- SINCRONIZAR DESDE GOOGLE SHEETS (MÚLTIPLES PESTAÑAS) ---
@solicitudes_bp.route('/solicitudes/sincronizar', methods=['POST', 'GET'])
def sincronizar_todas():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    SHEET_URLS = [
        "https://docs.google.com/spreadsheets/d/1cVtzyJ2Y7X9N1fZ9rGZgLxPazXjnuaGg7eIZFVwgX7k/export?format=csv&gid=1341303465",
        "https://docs.google.com/spreadsheets/d/1cVtzyJ2Y7X9N1fZ9rGZgLxPazXjnuaGg7eIZFVwgX7k/export?format=csv&gid=872085590",
        "https://docs.google.com/spreadsheets/d/1cVtzyJ2Y7X9N1fZ9rGZgLxPazXjnuaGg7eIZFVwgX7k/export?format=csv&gid=2014289934",
        "https://docs.google.com/spreadsheets/d/1cVtzyJ2Y7X9N1fZ9rGZgLxPazXjnuaGg7eIZFVwgX7k/export?format=csv&gid=937866469"
    ]
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS op_procesados (op TEXT PRIMARY KEY)''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros_excluidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, cedula TEXT, marca_temporal TEXT, tipo_documento TEXT
            )
        ''')
        
        nuevos_registros_total = 0

        for SHEET_CSV_URL in SHEET_URLS:
            req = urllib.request.Request(SHEET_CSV_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                csv_data = response.read().decode('utf-8')
                
            io_string = io.StringIO(csv_data)
            reader = csv.reader(io_string)
            
            header = next(reader, None)
            if not header:
                continue

            for row in reader:
                if not row or len(row) < 5:
                    continue
                
                marca_temporal = row[0] if len(row) > 0 else ""
                correo = row[1] if len(row) > 1 and row[1] else (row[6] if len(row) > 6 else "")

                nombre = row[2] if len(row) > 2 else ""
                apellido = row[3] if len(row) > 3 else ""
                cedula = row[4] if len(row) > 4 else ""
                nacionalidad = row[5] if len(row) > 5 else "V"
                
                total_cols = len(row)
                
                if total_cols >= 14:
                    parentesco = row[7] if len(row) > 7 else "Titular"
                    tipo_documento = row[8] if len(row) > 8 else "Acta Registral"
                    numero_copias = row[10] if len(row) > 10 else "1"
                    cont_m = row[11] if len(row) > 11 else ""
                    cont_f = row[12] if len(row) > 12 else ""
                    nombre_titular = f"Contrayentes: {cont_m} / {cont_f}".strip(" /")
                elif total_cols == 13:
                    tipo_documento = row[7] if len(row) > 7 else "Título de Cementerio"
                    parentesco = row[8] if len(row) > 8 else "Titular"
                    numero_copias = row[10] if len(row) > 10 else "1"
                    nombre_titular = row[11] if len(row) > 11 else ""
                elif total_cols == 12:
                    campo_8 = row[8].lower() if len(row) > 8 else ""
                    if "terreno" in campo_8 or "ejido" in campo_8:
                        parentesco = row[7] if len(row) > 7 else "Titular"
                        tipo_documento = row[8] if len(row) > 8 else "Terrenos Ejidos"
                        nombre_titular = row[10] if len(row) > 10 else ""
                        numero_copias = row[11] if len(row) > 11 else "1"
                    else:
                        tipo_documento = row[7] if len(row) > 7 else "OMPU"
                        parentesco = row[8] if len(row) > 8 else "Titular"
                        numero_copias = row[10] if len(row) > 10 else "1"
                        nombre_titular = row[11] if len(row) > 11 else ""
                else:
                    parentesco = "Titular"
                    tipo_documento = "Documento Certificado"
                    numero_copias = "1"
                    nombre_titular = ""

                cursor.execute("""
                    SELECT 1 FROM registros_excluidos 
                    WHERE cedula = ? AND marca_temporal = ? AND tipo_documento = ?
                """, (cedula, marca_temporal, tipo_documento))
                if cursor.fetchone():
                    continue

                cursor.execute("""
                    SELECT id FROM solicitudes_tramites 
                    WHERE cedula_solicitante = ? AND marca_temporal = ? AND tipo_documento = ?
                """, (cedula, marca_temporal, tipo_documento))
                
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO solicitudes_tramites (
                            marca_temporal, correo_solicitante, apellido_solicitante, nombre_solicitante,
                            nacionalidad, cedula_solicitante, tipo_documento, parentesco,
                            numero_copias, nombre_titular, estado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE')
                    """, (marca_temporal, correo, apellido, nombre, nacionalidad, cedula, tipo_documento, parentesco, numero_copias, nombre_titular))
                    nuevos_registros_total += 1

        conn.commit()
        conn.close()

        if nuevos_registros_total > 0:
            flash(f'✅ Sincronización exitosa. Se importaron {nuevos_registros_total} solicitudes nuevas.', 'success')
        else:
            flash('ℹ️ Sincronización completada. No hay solicitudes nuevas por importar.', 'info')

    except Exception as e:
        flash(f'❌ Error al sincronizar con Google Sheets: {str(e)}', 'danger')

    return redirect(url_for('solicitudes_bp.ver_solicitudes'))
