import os
import io
import json
import sqlite3
import shutil
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from PIL import Image

# Blueprint para el módulo de escaneo y adjuntos
adjuntos_bp = Blueprint('adjuntos_bp', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'catatumbo.db')
STORAGE_DIR = os.path.join(BASE_DIR, 'storage_pdf')
UPLOADS_DIR = os.path.join(BASE_DIR, 'static', 'uploads')

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

def get_adjuntos_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def procesar_archivo_a_pdf(file_storage, base_filename):
    """
    Guarda el archivo en storage_pdf y static/uploads.
    Si el archivo es una imagen (JPG, PNG, WEBP, etc.), la convierte automáticamente a PDF.
    Retorna el nombre final del archivo guardado (con extensión .pdf si era imagen).
    """
    root, ext = os.path.splitext(base_filename)
    ext_lower = ext.lower()
    
    # Extensiones de imagen que convertiremos a PDF
    image_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}
    
    if ext_lower in image_exts:
        nombre_final = f"{root}.pdf"
        ruta_storage = os.path.join(STORAGE_DIR, nombre_final)
        ruta_uploads = os.path.join(UPLOADS_DIR, nombre_final)
        try:
            image = Image.open(file_storage)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(ruta_storage, format="PDF", resolution=150.0)
            shutil.copy2(ruta_storage, ruta_uploads)
            return nombre_final
        except Exception as e:
            print(f"Error al convertir imagen a PDF con Pillow: {e}")
            file_storage.seek(0)
            # Si falla la conversión, guardar como archivo original
            ruta_orig_storage = os.path.join(STORAGE_DIR, base_filename)
            ruta_orig_uploads = os.path.join(UPLOADS_DIR, base_filename)
            file_storage.save(ruta_orig_storage)
            try:
                shutil.copy2(ruta_orig_storage, ruta_orig_uploads)
            except Exception:
                pass
            return base_filename
    else:
        # Ya es PDF u otro formato
        ruta_storage = os.path.join(STORAGE_DIR, base_filename)
        ruta_uploads = os.path.join(UPLOADS_DIR, base_filename)
        file_storage.save(ruta_storage)
        try:
            shutil.copy2(ruta_storage, ruta_uploads)
        except Exception:
            pass
        return base_filename

# --- VISTA PRINCIPAL (Lee directamente de la tabla 'documentos') ---
@adjuntos_bp.route('/adjuntos')
def vista_adjuntos():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    conn = get_adjuntos_db()
    cursor = conn.execute("""
        SELECT id, tipo_documento, fecha_ingreso, nombre_titular, 
               nombre_masculino, nombre_femenino, numero_acta AS num_acta, 
               anio_documento AS anio, tomo, folio, archivos
        FROM documentos ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    adjuntos = []
    for r in rows:
        d = dict(r)
        try:
            archivos_list = json.loads(d['archivos']) if d.get('archivos') else []
        except Exception:
            archivos_list = []
        
        primer_archivo = archivos_list[0] if archivos_list else None
        if primer_archivo:
            if primer_archivo.startswith('/static/'):
                d['url_archivo'] = primer_archivo
            elif '/' in primer_archivo:
                d['url_archivo'] = '/' + primer_archivo.lstrip('/')
            else:
                d['url_archivo'] = url_for('ver_archivo', filename=primer_archivo)
            d['primer_archivo'] = primer_archivo
        else:
            d['url_archivo'] = None
            d['primer_archivo'] = None
            
        adjuntos.append(d)
        
    return render_template('adjuntos.html', adjuntos=adjuntos)

# --- RUTA: GUARDAR ADJUNTO (Inserta en la tabla general 'documentos') ---
@adjuntos_bp.route('/guardar-adjunto', methods=['POST'])
def guardar_adjunto():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    tipo_documento = request.form.get('tipo_documento', '').strip()
    if not tipo_documento:
        flash('❌ Debe seleccionar un tipo de documento válido.', 'danger')
        return redirect(url_for('adjuntos_bp.vista_adjuntos'))

    numero_acta = request.form.get('numero_acta', '').strip()
    tomo = request.form.get('tomo', '').strip()
    folio = request.form.get('folio', '').strip()
    anio_documento = request.form.get('anio_documento', '').strip()

    nombre_masculino = request.form.get('nombre_masculino', '').strip()
    nombre_femenino = request.form.get('nombre_femenino', '').strip()
    nombre_titular = request.form.get('nombre_titular', '').strip()
    if not nombre_titular and (nombre_masculino or nombre_femenino):
        nombre_titular = f"{nombre_masculino} / {nombre_femenino}".strip(' /')

    sub_tipo_cementerio = request.form.get('sub_tipo_cementerio', '').strip()
    fecha_acta = request.form.get('fecha_acta', '').strip()
    fecha_gaceta = request.form.get('fecha_gaceta', '').strip()
    numero_gaceta = request.form.get('numero_gaceta', '').strip()
    fecha_documento = request.form.get('fecha_documento', '').strip()
    numero_registro = request.form.get('numero_registro', '').strip()
    fecha_ingreso_lab = request.form.get('fecha_ingreso_lab', '').strip()
    fecha_egreso_lab = request.form.get('fecha_egreso_lab', '').strip()

    # Manejar archivo PDF / captura
    archivo = request.files.get('url_adjunto_copia') or request.files.get('archivo')
    filename_guardado = None

    if archivo and archivo.filename != '':
        raw_name = secure_filename(archivo.filename)
        timestamp_prefix = datetime.now().strftime('%Y%m%d%H%M%S')
        if not raw_name.startswith('documento_escaneado_') and not raw_name.startswith('202'):
            base_filename = f"{timestamp_prefix}_{raw_name}"
        else:
            base_filename = raw_name

        filename_guardado = procesar_archivo_a_pdf(archivo, base_filename)

    archivos_json = json.dumps([filename_guardado]) if filename_guardado else '[]'
    fecha_ingreso = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = get_adjuntos_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documentos (
                tipo_documento, fecha_ingreso, archivos,
                nombre_masculino, nombre_femenino, nombre_titular,
                numero_acta, anio_documento, tomo, folio,
                sub_tipo_cementerio, fecha_acta, fecha_gaceta, numero_gaceta,
                fecha_documento, numero_registro, fecha_ingreso_lab, fecha_egreso_lab,
                sincronizado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            tipo_documento, fecha_ingreso, archivos_json,
            nombre_masculino, nombre_femenino, nombre_titular,
            numero_acta, anio_documento, tomo, folio,
            sub_tipo_cementerio, fecha_acta, fecha_gaceta, numero_gaceta,
            fecha_documento, numero_registro, fecha_ingreso_lab, fecha_egreso_lab
        ))
        conn.commit()
        conn.close()
        flash('✅ Documento y archivo PDF guardados exitosamente en la base de datos.', 'success')
    except Exception as e:
        flash(f'❌ Error al guardar en la base de datos: {str(e)}', 'danger')

    return redirect(url_for('adjuntos_bp.vista_adjuntos'))

# --- RUTA: ACTUALIZAR ADJUNTO ---
@adjuntos_bp.route('/adjuntos/actualizar/<int:id>', methods=['POST'])
def actualizar_adjunto(id):
    if 'user' not in session:
        return redirect(url_for('login'))

    tipo_documento = request.form.get('tipo_documento', '').strip()
    numero_acta = request.form.get('numero_acta', '').strip()
    tomo = request.form.get('tomo', '').strip()
    folio = request.form.get('folio', '').strip()
    anio_documento = request.form.get('anio_documento', '').strip()
    nombre_titular = request.form.get('nombre_titular', '').strip()

    archivo = request.files.get('url_adjunto_copia') or request.files.get('archivo')
    filename_guardado = None

    if archivo and archivo.filename != '':
        raw_name = secure_filename(archivo.filename)
        timestamp_prefix = datetime.now().strftime('%Y%m%d%H%M%S')
        base_filename = f"{timestamp_prefix}_{raw_name}"
        filename_guardado = procesar_archivo_a_pdf(archivo, base_filename)

    try:
        conn = get_adjuntos_db()
        if filename_guardado:
            archivos_json = json.dumps([filename_guardado])
            conn.execute("""
                UPDATE documentos SET
                    tipo_documento=?, nombre_titular=?, numero_acta=?,
                    anio_documento=?, tomo=?, folio=?, archivos=?
                WHERE id=?
            """, (tipo_documento, nombre_titular, numero_acta, anio_documento, tomo, folio, archivos_json, id))
        else:
            conn.execute("""
                UPDATE documentos SET
                    tipo_documento=?, nombre_titular=?, numero_acta=?,
                    anio_documento=?, tomo=?, folio=?
                WHERE id=?
            """, (tipo_documento, nombre_titular, numero_acta, anio_documento, tomo, folio, id))

        conn.commit()
        conn.close()
        flash(f'✅ Expediente #{id} actualizado correctamente.', 'success')
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
        registro = conn.execute("SELECT archivos FROM documentos WHERE id=?", (id,)).fetchone()
        if registro and registro['archivos']:
            try:
                archivos_list = json.loads(registro['archivos'])
                for arc in archivos_list:
                    # Limpiar de storage_pdf
                    p1 = os.path.join(STORAGE_DIR, os.path.basename(arc))
                    if os.path.exists(p1):
                        os.remove(p1)
                    # Limpiar de static/uploads
                    p2 = os.path.join(UPLOADS_DIR, os.path.basename(arc))
                    if os.path.exists(p2):
                        os.remove(p2)
            except Exception:
                pass

        conn.execute("DELETE FROM documentos WHERE id=?", (id,))
        conn.commit()
        conn.close()
        flash(f'✅ Expediente #{id} y sus archivos fueron eliminados exitosamente.', 'success')
    except Exception as e:
        flash(f'❌ Error al eliminar el registro: {str(e)}', 'danger')

    return redirect(url_for('adjuntos_bp.vista_adjuntos'))
