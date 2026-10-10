import csv
import io
import json
import random
import string
import urllib.request
import urllib.parse
import smtplib
import traceback
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename

from base_datos import get_db

solicitudes_bp = Blueprint('solicitudes_bp', __name__)

def generar_codigo_seguridad():
    letras = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CMBM-{letras}"

def obtener_trimestre(fecha_str):
    if not fecha_str:
        return "Sin Fecha"
    fecha_limpia = fecha_str.strip()
    
    formatos = (
        "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", 
        "%m/%d/%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y/%d/%m"
    )
    for fmt in formatos:
        try:
            dt = datetime.strptime(fecha_limpia, fmt)
            mes = dt.month
            trimestre = (mes - 1) // 3 + 1
            return f"Q{trimestre} - {dt.year}"
        except ValueError:
            continue
            
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

# --- VISTA PRINCIPAL DE SOLICITUDES ---

@solicitudes_bp.route('/solicitudes')
def ver_solicitudes():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    solicitudes = conn.execute("SELECT * FROM solicitudes_tramites ORDER BY id DESC").fetchall()
    conn.close()
    
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
                  <li style="margin-bottom: 3px;">Asistir a <b>SEDEMAT</b> (Sedes de Atencion y Tramites "Valle Frio , Alcaldia de Maraciabo,Costa Verde,Plaza de Toros,Curva de Molina,Vereda del Lago , CC.Lago.Mall ").</li>
                  <li style="margin-bottom: 3px;">Realizar el pago de aranceles municipales correspondientes.</li>
                  <li>Presentar el pago del SEDEMAT en el 3er piso del Palacio Municipal "Archivo General Municipal"para la certificación del documento y su posterior retiro (3 días hábiles).</li>
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
        cursor.execute('''
            UPDATE solicitudes_tramites 
            SET anio_expediente_titulo = ?, tomo = ?, folio = ?, num_acta = ?, monto = ?, estado = ?, codigo_seguridad = ?
            WHERE id = ?
        ''', (anio_expediente, tomo, folio, num_acta, monto, estado, codigo_seguridad, id))

        # Registrar o actualizar en el historial acumulativo si el estado es PROCESADA
        if estado == 'PROCESADA':
            cursor.execute("SELECT id FROM op_procesados WHERE op = ?", (str(id),))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO op_procesados (op, tomo, folio, num_acta, monto, anio_expediente_titulo, fecha_proceso)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """, (str(id), tomo, folio, num_acta, monto, anio_expediente))

        conn.commit()
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

    anio_expediente = request.form.get('anio_expediente_titulo')
    tomo = request.form.get('tomo')
    folio = request.form.get('folio')
    num_acta = request.form.get('num_acta')
    monto = request.form.get('monto')
    estado = request.form.get('estado', 'PROCESADA')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO op_procesados (op, tomo, folio, num_acta, monto, anio_expediente_titulo, fecha_proceso) 
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (num_op, tomo, folio, num_acta, monto, anio_expediente))

    cursor.execute("DELETE FROM solicitudes_tramites WHERE id = ?", (num_op,))
    
    conn.commit()
    conn.close()

    flash(f"Trámite OP-{num_op} procesado, verificado y archivado con éxito en el historial.", "success")
    return redirect(url_for('solicitudes_bp.ver_solicitudes'))

# --- VISTA HISTORIAL DE OP PROCESADAS ---
@solicitudes_bp.route('/solicitudes/historial-op')
def ver_historial_op():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS op_procesados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            op TEXT, tomo TEXT, folio TEXT, num_acta TEXT, monto TEXT, anio_expediente_titulo TEXT, fecha_proceso TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papelera_op_procesados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            op TEXT, tomo TEXT, folio TEXT, num_acta TEXT, monto TEXT, anio_expediente_titulo TEXT, fecha_proceso TIMESTAMP
        )
    ''')
    
    historial = cursor.execute("SELECT * FROM op_procesados ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('historial_op.html', historial=historial)

@solicitudes_bp.route('/solicitudes/historial-op/editar/<int:id>', methods=['POST'])
def editar_historial_op(id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    op = request.form.get('op')
    anio_expediente = request.form.get('anio_expediente_titulo')
    tomo = request.form.get('tomo')
    folio = request.form.get('folio')
    num_acta = request.form.get('num_acta')
    monto = request.form.get('monto')
    
    conn = get_db()
    conn.execute('''
        UPDATE op_procesados 
        SET op = ?, anio_expediente_titulo = ?, tomo = ?, folio = ?, num_acta = ?, monto = ?
        WHERE id = ?
    ''', (op, anio_expediente, tomo, folio, num_acta, monto, id))
    conn.commit()
    conn.close()
    
    flash('✏️ Registro del historial actualizado con éxito.', 'success')
    return redirect(url_for('solicitudes_bp.ver_historial_op'))

@solicitudes_bp.route('/solicitudes/historial-op/eliminar/<int:id>')
def eliminar_historial_op(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM op_procesados WHERE id = ?", (id,))
    row = cursor.fetchone()

    if row:
        cursor.execute('''
            INSERT INTO papelera_op_procesados (op, tomo, folio, num_acta, monto, anio_expediente_titulo, fecha_proceso)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (row['op'], row['tomo'], row['folio'], row['num_acta'], row['monto'], row['anio_expediente_titulo'], row['fecha_proceso']))

        cursor.execute("DELETE FROM op_procesados WHERE id = ?", (id,))

    conn.commit()
    conn.close()
    
    flash('🗑️ Registro del historial enviado a la papelera.', 'info')
    return redirect(url_for('solicitudes_bp.ver_historial_op'))

@solicitudes_bp.route('/solicitudes/historial-op/papelera')
def ver_papelera_historial():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    cursor = conn.cursor()
    papelera = cursor.execute("SELECT * FROM papelera_op_procesados ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('papelera_historial.html', papelera=papelera)

@solicitudes_bp.route('/solicitudes/historial-op/papelera/restaurar/<int:id>')
def restaurar_historial_op(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM papelera_op_procesados WHERE id = ?", (id,)).fetchone()

    if row:
        cursor.execute('''
            INSERT INTO op_procesados (op, tomo, folio, num_acta, monto, anio_expediente_titulo, fecha_proceso)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (row['op'], row['tomo'], row['folio'], row['num_acta'], row['monto'], row['anio_expediente_titulo'], row['fecha_proceso']))
        cursor.execute("DELETE FROM papelera_op_procesados WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    flash('♻️ Registro del historial restaurado con éxito.', 'success')
    return redirect(url_for('solicitudes_bp.ver_papelera_historial'))

@solicitudes_bp.route('/solicitudes/historial-op/papelera/eliminar-definitivo/<int:id>')
def eliminar_definitivo_historial_op(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM papelera_op_procesados WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash('⚡ Registro eliminado permanentemente de la papelera.', 'warning')
    return redirect(url_for('solicitudes_bp.ver_papelera_historial'))

@solicitudes_bp.route('/solicitudes/eliminar/<int:id>')
def eliminar_solicitud(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
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

@solicitudes_bp.route('/solicitudes/papelera')
def ver_papelera():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_db()
    cursor = conn.cursor()
    papelera = cursor.execute("SELECT * FROM papelera_solicitudes ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('papelera.html', papelera=papelera)

@solicitudes_bp.route('/solicitudes/papelera/restaurar/<int:id>', methods=['GET', 'POST'])
def restaurar_solicitud(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM papelera_solicitudes WHERE id = ?", (id,)).fetchone()

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

@solicitudes_bp.route('/solicitudes/estadisticas')
def estadisticas_trimestrales():
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
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

@solicitudes_bp.route('/solicitudes/sincronizar', methods=['POST', 'GET'])
def sincronizar_todas():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    SPREADSHEET_ID = "1cVtzyJ2Y7X9N1fZ9rGZgLxPazXjnuaGg7eIZFVwgX7k"
    SHEET_CSV_URLS = [
        (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=1341303465", "Título de Cementerio"),
        (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=872085590", "Solicitud de OMPU"),
        (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=2014289934", "Actas de Matrimonio, Nacimiento y Divorcio"),
        (f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=937866469", "Terrenos Ejidos")
    ]
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        for col, col_tipo in [("anio_expediente_titulo", "TEXT"), ("url_adjunto_copia", "TEXT"), ("datos_expediente", "TEXT"), ("contrayente_masculino", "TEXT"), ("contrayente_femenino", "TEXT"), ("fecha_acta", "TEXT")]:
            try:
                cursor.execute(f"ALTER TABLE solicitudes_tramites ADD COLUMN {col} {col_tipo};")
            except Exception:
                pass

        nuevos_registros_total = 0

        for url, nombre_pestana in SHEET_CSV_URLS:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
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
                
                total_cols = len(row)
                marca_temporal = row[0] if total_cols > 0 else ""
                correo_google = row[1] if total_cols > 1 else ""
                nombre_solicitante = row[2] if total_cols > 2 else ""
                apellido_solicitante = row[3] if total_cols > 3 else ""
                cedula_solicitante = row[4] if total_cols > 4 else ""
                nacionalidad = row[5] if total_cols > 5 else "V"
                correo_solicitante = row[6] if total_cols > 6 else correo_google

                parentesco, tipo_documento, numero_copias, anio_expediente_titulo, fecha_acta, nombre_titular, contrayente_masculino, contrayente_femenino, datos_expediente, url_adjunto_copia = "", nombre_pestana, "", "", "", "", "", "", "", ""

                if "Matrimonio" in nombre_pestana:
                    parentesco = row[7] if total_cols > 7 else ""
                    tipo_documento = row[8] if total_cols > 8 else nombre_pestana
                    fecha_acta = row[9] if total_cols > 9 else ""
                    numero_copias = row[10] if total_cols > 10 else ""
                    contrayente_masculino = row[11] if total_cols > 11 else ""
                    contrayente_femenino = row[12] if total_cols > 12 else ""
                    nombre_titular = f"Contrayentes: {contrayente_masculino} / {contrayente_femenino}".strip(" /")
                    if total_cols > 13: url_adjunto_copia = row[13]

                elif "Cementerio" in nombre_pestana:
                    tipo_documento = row[7] if total_cols > 7 else nombre_pestana
                    parentesco = row[8] if total_cols > 8 else ""
                    anio_expediente_titulo = row[9] if total_cols > 9 else ""
                    numero_copias = row[10] if total_cols > 10 else ""
                    nombre_titular = row[11] if total_cols > 11 else ""
                    if total_cols > 12: url_adjunto_copia = row[12]

                elif "OMPU" in nombre_pestana:
                    tipo_documento = row[7] if total_cols > 7 else nombre_pestana
                    parentesco = row[8] if total_cols > 8 else ""
                    anio_expediente_titulo = row[9] if total_cols > 9 else ""
                    numero_copias = row[10] if total_cols > 10 else ""
                    datos_expediente = row[11] if total_cols > 11 else ""
                    if total_cols > 12: url_adjunto_copia = row[12]

                elif "Ejidos" in nombre_pestana:
                    parentesco = row[7] if total_cols > 7 else ""
                    tipo_documento = row[8] if total_cols > 8 else nombre_pestana
                    anio_expediente_titulo = row[9] if total_cols > 9 else ""
                    nombre_titular = row[10] if total_cols > 10 else ""
                    numero_copias = row[11] if total_cols > 11 else ""
                    if total_cols > 12: url_adjunto_copia = row[12]

                cursor.execute("""
                    SELECT 1 FROM registros_excluidos 
                    WHERE cedula = ? AND marca_temporal = ? AND tipo_documento = ?
                """, (cedula_solicitante, marca_temporal, tipo_documento))
                if cursor.fetchone():
                    continue

                cursor.execute("""
                    SELECT id FROM solicitudes_tramites 
                    WHERE cedula_solicitante = ? AND marca_temporal = ? AND tipo_documento = ?
                """, (cedula_solicitante, marca_temporal, tipo_documento))
                
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO solicitudes_tramites (
                            marca_temporal, correo_google, correo_solicitante, apellido_solicitante, nombre_solicitante,
                            nacionalidad, cedula_solicitante, tipo_documento, parentesco,
                            numero_copias, anio_expediente_titulo, fecha_acta, nombre_titular,
                            contrayente_masculino, contrayente_femenino, datos_expediente, 
                            url_adjunto_copia, estado, sincronizado
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', 1)
                    """, (
                        marca_temporal, correo_google, correo_solicitante, apellido_solicitante, nombre_solicitante,
                        nacionalidad, cedula_solicitante, tipo_documento, parentesco,
                        numero_copias, anio_expediente_titulo, fecha_acta, nombre_titular,
                        contrayente_masculino, contrayente_femenino, datos_expediente, 
                        url_adjunto_copia
                    ))
                    nuevos_registros_total += 1

        conn.commit()
        conn.close()

        if nuevos_registros_total > 0:
            flash(f'✅ Sincronización exitosa. Se importaron {nuevos_registros_total} solicitudes con sus años y adjuntos.', 'success')
        else:
            flash('ℹ️ Sincronización completada. No hay solicitudes nuevas por importar.', 'info')

    except Exception as e:
        flash(f'❌ Error al sincronizar con Google Sheets: {str(e)}', 'danger')

    return redirect(url_for('solicitudes_bp.ver_solicitudes'))
