import os
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

# Blueprint independiente para el módulo de escaneo y adjuntos
adjuntos_bp = Blueprint('adjuntos_bp', __name__)

# Base de datos independiente para este módulo
DB_ADJUNTOS = 'adjuntos_digitales.db'

def get_adjuntos_db():
    conn = sqlite3.connect(DB_ADJUNTOS)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_base_datos_adjuntos():
    conn = get_adjuntos_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS registros_adjuntos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            responsable TEXT NOT NULL,
            nombre_solicitante TEXT,
            apellido_solicitante TEXT,
            nacionalidad TEXT,
            cedula_solicitante TEXT,
            tipo_documento TEXT,
            num_acta TEXT,
            anio TEXT,
            tomo TEXT,
            folio TEXT,
            url_adjunto_copia TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Inicializar la tabla al cargar el módulo
inicializar_base_datos_adjuntos()

# --- VISTA PRINCIPAL ---
@adjuntos_bp.route('/adjuntos')
def vista_adjuntos():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_adjuntos_db()
    adjuntos = conn.execute(
        "SELECT * FROM registros_adjuntos ORDER BY id DESC"
    ).fetchall()
    conn.close()
    
    return render_template('adjuntos.html', adjuntos=adjuntos)

# --- RUTA: GUARDAR ADJUNTO ---
@adjuntos_bp.route('/guardar-adjunto', methods=['POST'])
def guardar_adjunto():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Validar campo obligatorio
    responsable = request.form.get('responsable', '').strip()
    if not responsable:
        flash('❌ El nombre del responsable es obligatorio para registrar el documento.', 'danger')
        return redirect(url_for('adjuntos_bp.vista_adjuntos'))
    
    nombre_solicitante = request.form.get('nombre_solicitante', '').strip()
    apellido_solicitante = request.form.get('apellido_solicitante', '').strip()
    nacionalidad = request.form.get('nacionalidad', 'V')
    cedula_solicitante = request.form.get('cedula_solicitante', '').strip()
    tipo_documento = request.form.get('tipo_documento', '').strip()
    num_acta = request.form.get('num_acta', '').strip()
    anio = request.form.get('anio', '').strip()
    tomo = request.form.get('tomo', '').strip()
    folio = request.form.get('folio', '').strip()
    
    # Guardar archivo PDF o Imagen en servidor
    archivo = request.files.get('url_adjunto_copia')
    url_adjunto = None
    
    if archivo and archivo.filename != '':
        filename = secure_filename(archivo.filename)
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        ruta_guardado = os.path.join(upload_folder, filename)
        archivo.save(ruta_guardado)
        url_adjunto = url_for('static', filename=f'uploads/{filename}')

    try:
        conn = get_adjuntos_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO registros_adjuntos (
                responsable, nombre_solicitante, apellido_solicitante, nacionalidad, 
                cedula_solicitante, tipo_documento, num_acta, anio, 
                tomo, folio, url_adjunto_copia
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            responsable, nombre_solicitante, apellido_solicitante, nacionalidad,
            cedula_solicitante, tipo_documento, num_acta, anio, tomo, folio, url_adjunto
        ))
        conn.commit()
        conn.close()
        flash('✅ Archivo PDF y registro guardados exitosamente.', 'success')
    except Exception as e:
        flash(f'❌ Error al guardar en la base de datos: {str(e)}', 'danger')

    return redirect(url_for('adjuntos_bp.vista_adjuntos'))

# --- RUTA: ACTUALIZAR ADJUNTO ---
@adjuntos_bp.route('/adjuntos/actualizar/<int:id>', methods=['POST'])
def actualizar_adjunto(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    responsable = request.form.get('responsable', '').strip()
    if not responsable:
        flash('❌ El nombre del responsable es obligatorio.', 'danger')
        return redirect(url_for('adjuntos_bp.vista_adjuntos'))

    nombre_solicitante = request.form.get('nombre_solicitante', '').strip()
    apellido_solicitante = request.form.get('apellido_solicitante', '').strip()
    nacionalidad = request.form.get('nacionalidad', 'V')
    cedula_solicitante = request.form.get('cedula_solicitante', '').strip()
    tipo_documento = request.form.get('tipo_documento', '').strip()
    num_acta = request.form.get('num_acta', '').strip()
    anio = request.form.get('anio', '').strip()
    tomo = request.form.get('tomo', '').strip()
    folio = request.form.get('folio', '').strip()

    archivo = request.files.get('url_adjunto_copia')
    
    try:
        conn = get_adjuntos_db()
        
        if archivo and archivo.filename != '':
            filename = secure_filename(archivo.filename)
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            ruta_guardado = os.path.join(upload_folder, filename)
            archivo.save(ruta_guardado)
            url_adjunto = url_for('static', filename=f'uploads/{filename}')

            conn.execute("""
                UPDATE registros_adjuntos SET
                    responsable=?, nombre_solicitante=?, apellido_solicitante=?, nacionalidad=?,
                    cedula_solicitante=?, tipo_documento=?, num_acta=?, anio=?,
                    tomo=?, folio=?, url_adjunto_copia=?
                WHERE id=?
            """, (
                responsable, nombre_solicitante, apellido_solicitante, nacionalidad,
                cedula_solicitante, tipo_documento, num_acta, anio, tomo, folio, url_adjunto, id
            ))
        else:
            conn.execute("""
                UPDATE registros_adjuntos SET
                    responsable=?, nombre_solicitante=?, apellido_solicitante=?, nacionalidad=?,
                    cedula_solicitante=?, tipo_documento=?, num_acta=?, anio=?, tomo=?, folio=?
                WHERE id=?
            """, (
                responsable, nombre_solicitante, apellido_solicitante, nacionalidad,
                cedula_solicitante, tipo_documento, num_acta, anio, tomo, folio, id
            ))

        conn.commit()
        conn.close()
        flash(f'✅ Registro #{id} actualizado correctamente.', 'success')
    except Exception as e:
        flash(f'❌ Error al actualizar registro: {str(e)}', 'danger')

    return redirect(url_for('adjuntos_bp.vista_adjuntos'))

# --- RUTA: ELIMINAR ADJUNTO ---
@adjuntos_bp.route('/adjuntos/eliminar/<int:id>')
def eliminar_adjunto(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_adjuntos_db()
        registro = conn.execute("SELECT url_adjunto_copia FROM registros_adjuntos WHERE id=?", (id,)).fetchone()

        if registro and registro['url_adjunto_copia']:
            relative_path = registro['url_adjunto_copia'].lstrip('/')
            if os.path.exists(relative_path):
                os.remove(relative_path)

        conn.execute("SELECT * FROM registros_adjuntos WHERE id=?", (id,))
        conn.execute("DELETE FROM registros_adjuntos WHERE id=?", (id,))
        conn.commit()
        conn.close()

        flash(f'✅ Registro #{id} y su archivo fueron eliminados exitosamente.', 'success')
    except Exception as e:
        flash(f'❌ Error al eliminar el registro: {str(e)}', 'danger')

    return redirect(url_for('adjuntos_bp.vista_adjuntos'))
