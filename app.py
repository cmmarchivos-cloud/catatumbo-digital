import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.secret_key = 'catatumbo_digital_secure_secret_key'

# --- CONFIGURACIÓN HÍBRIDA CON NGROK ---
LOCAL_PC_TUNNEL = "https://unspoken-energy-stiffly.ngrok-free.dev"
IS_PYTHONANYWHERE = 'PYTHONANYWHERE_SITE' in os.environ or os.path.exists('/home/cmmarchivos')

if IS_PYTHONANYWHERE:
    @app.before_request
    def handle_pythonanywhere_proxy():
        try:
            headers = {key: value for (key, value) in request.headers if key.lower() != 'host'}
            url = f"{LOCAL_PC_TUNNEL}{request.path}"
            if request.query_string:
                url += f"?{request.query_string.decode('utf-8')}"
            
            files = []
            for key in request.files:
                for storage in request.files.getlist(key):
                    files.append((key, (storage.filename, storage.stream, storage.content_type)))
            
            resp = requests.request(
                method=request.method,
                url=url,
                headers=headers,
                data=request.form if request.method in ['POST', 'PUT', 'PATCH'] else None,
                files=files if files else None,
                params=request.args,
                cookies=request.cookies,
                allow_redirects=False,
                timeout=30
            )
            
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            resp_headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
            
            return resp.content, resp.status_code, resp_headers
        except Exception as e:
            return f"<h3>Error de conexión con la PC local a través de Ngrok:</h3><p>{e}</p><p>Verifica que tu laptop tenga encendido el servidor Flask y el túnel de Ngrok.</p>", 502

# Configuración inteligente de rutas compatible con PythonAnywhere y entorno local
if os.path.exists('/home/cmmarchivos'):
    DB_NAME = '/home/cmmarchivos/catatumbo.db'
    UPLOAD_FOLDER = '/home/cmmarchivos/storage_pdf'
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_NAME = os.path.join(BASE_DIR, 'catatumbo.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'storage_pdf')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            nombre TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_documento TEXT,
            fecha_ingreso TEXT,
            archivos TEXT,
            nombre_masculino TEXT,
            nombre_femenino TEXT,
            nombre_titular TEXT,
            numero_acta TEXT,
            anio_documento TEXT,
            sub_tipo_cementerio TEXT,
            fecha_acta TEXT,
            fecha_gaceta TEXT,
            numero_gaceta TEXT,
            fecha_documento TEXT,
            numero_registro TEXT,
            fecha_ingreso_lab TEXT,
            fecha_egreso_lab TEXT,
            sincronizado INTEGER DEFAULT 0
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE documentos ADD COLUMN sincronizado INTEGER DEFAULT 0;")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cursor.execute("UPDATE documentos SET sincronizado = 0 WHERE sincronizado IS NULL;")
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("master", "123", "master", "Administrador Master"),
            ("consultor", "123", "consultor", "Usuario Consultor"),
            ("gestor", "123", "gestor", "Gestor de Carga"),
            ("supervisor", "123", "supervisor", "Supervisor IT")
        ]
        cursor.executemany('''
            INSERT INTO usuarios (username, password, rol, nombre)
            VALUES (?, ?, ?, ?)
        ''', default_users)
        conn.commit()
        
    conn.close()

init_db()

@app.context_processor
def inject_verse():
    versiculos = [
        ("Proverbios 2:6", "Porque Jehová da la sabiduría, y de su boca viene el conocimiento y la inteligencia."),
        ("Colosenses 3:23", "Y todo lo que hagáis, hacedlo de corazón, como para el Señor y no para los hombres;"),
        ("Salmos 90:17", "Sea la luz de Jehová nuestro Dios sobre nosotros, y la obra de nuestras manos confirma sobre nosotros."),
        ("Romanos 11:36", "Porque de él, y por él, y para él, son todas las cosas. A él sea la gloria por los siglos. Amén."),
        ("Salmos 37:5", "Encomienda a Jehová tu camino, y confía en él; y él hará."),
        ("Proverbios 16:3", "Encomienda a Jehová tus obras, y tus pensamientos serán afirmados."),
        ("Filipenses 4:13", "Todo lo puedo en Cristo que me fortalece."),
        ("Salmos 119:105", "Lámpara es a mis pies tu palabra, y lumbrera a mi camino."),
        ("Isaías 41:10", "No temas, porque yo estoy contigo; no desmayes, porque yo soy tu Dios que te fortalezco.")
    ]
    idx = datetime.now().toordinal() % len(versiculos)
    ref, texto = versiculos[idx]
    return dict(versiculo_ref=ref, versiculo_texto=texto)

TIPOS_DOCUMENTO = [
    "Acta de nacimiento", "Acta de matrimonio", "Sentencia de divorcio",
    "Título de cementerio", "Expediente de venta terrenos ejidos",
    "Actas de sesiones", "Gaceta oficial",
    "Expedientes de construcción de urbanismo de Maracaibo OMPU",
    "Expedientes laborales"
]

def load_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM usuarios').fetchall()
    conn.close()
    return [dict(u) for u in users]

def save_users(users):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM usuarios')
    for u in users:
        cursor.execute('''
            INSERT INTO usuarios (id, username, password, rol, nombre)
            VALUES (?, ?, ?, ?, ?)
        ''', (u.get('id'), u['username'], u['password'], u['rol'], u['nombre']))
    conn.commit()
    conn.close()

def load_db():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM documentos').fetchall()
    conn.close()
    docs = []
    for r in rows:
        d = dict(r)
        d['index_id'] = d['id']
        try:
            d['archivos'] = json.loads(d['archivos']) if d['archivos'] else []
        except:
            d['archivos'] = []
        docs.append(d)
    return docs

def save_db_doc(doc, doc_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    archivos_json = json.dumps(doc.get('archivos', []), ensure_ascii=False)
    
    if doc_id is not None:
        cursor.execute('''
            UPDATE documentos SET
                tipo_documento = ?, fecha_ingreso = ?, archivos = ?,
                nombre_masculino = ?, nombre_femenino = ?, nombre_titular = ?,
                numero_acta = ?, anio_documento = ?, sub_tipo_cementerio = ?,
                fecha_acta = ?, fecha_gaceta = ?, numero_gaceta = ?,
                fecha_documento = ?, numero_registro = ?, fecha_ingreso_lab = ?,
                fecha_egreso_lab = ?
            WHERE id = ?
        ''', (
            doc.get('tipo_documento'), doc.get('fecha_ingreso'), archivos_json,
            doc.get('nombre_masculino', ''), doc.get('nombre_femenino', ''), doc.get('nombre_titular', ''),
            doc.get('numero_acta', ''), doc.get('anio_documento', ''), doc.get('sub_tipo_cementerio', ''),
            doc.get('fecha_acta', ''), doc.get('fecha_gaceta', ''), doc.get('numero_gaceta', ''),
            doc.get('fecha_documento', ''), doc.get('numero_registro', ''), doc.get('fecha_ingreso_lab', ''),
            doc.get('fecha_egreso_lab', ''), doc_id
        ))
    else:
        cursor.execute('''
            INSERT INTO documentos (
                tipo_documento, fecha_ingreso, archivos, nombre_masculino,
                nombre_femenino, nombre_titular, numero_acta, anio_documento,
                sub_tipo_cementerio, fecha_acta, fecha_gaceta, numero_gaceta,
                fecha_documento, numero_registro, fecha_ingreso_lab, fecha_egreso_lab, sincronizado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (
            doc.get('tipo_documento'), doc.get('fecha_ingreso'), archivos_json,
            doc.get('nombre_masculino', ''), doc.get('nombre_femenino', ''), doc.get('nombre_titular', ''),
            doc.get('numero_acta', ''), doc.get('anio_documento', ''), doc.get('sub_tipo_cementerio', ''),
            doc.get('fecha_acta', ''), doc.get('fecha_gaceta', ''), doc.get('numero_gaceta', ''),
            doc.get('fecha_documento', ''), doc.get('numero_registro', ''), doc.get('fecha_ingreso_lab', ''),
            doc.get('fecha_egreso_lab', '')
        ))
    conn.commit()
    conn.close()

def delete_db_doc(doc_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM documentos WHERE id = ?', (doc_id,))
    conn.commit()
    conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        users = load_users()
        user = next((u for u in users if u['username'] == username and u['password'] == password), None)
        if user:
            session['user'] = user['username']
            session['rol'] = user['rol']
            session['nombre'] = user['nombre']
            return redirect(url_for('index'))
        flash('Credenciales inválidas, intente nuevamente.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    docs = load_db()
    return render_template('index.html', total_docs=len(docs))

@app.route('/buscar', methods=['GET'])
def buscar():
    if 'user' not in session: return redirect(url_for('login'))
    if session['rol'] == 'gestor': return redirect(url_for('subir'))
    
    query = request.args.get('q', '').lower()
    tipo_filtro = request.args.get('tipo', '')
    docs = load_db()
    resultados = []
    
    for d in docs:
        match_query = (
            query in str(d.get('nombre_masculino') or '').lower() or 
            query in str(d.get('nombre_femenino') or '').lower() or 
            query in str(d.get('nombre_titular') or '').lower() or 
            query in str(d.get('numero_acta') or '').lower() or
            query in str(d.get('numero_gaceta') or '').lower() or
            query in str(d.get('numero_registro') or '').lower()
        )
        match_tipo = (tipo_filtro == '' or d.get('tipo_documento') == tipo_filtro)
        if (not query or match_query) and match_tipo:
            resultados.append(d)
            
    return render_template('buscar.html', resultados=resultados, query=query, tipo_filtro=tipo_filtro, tipos=TIPOS_DOCUMENTO)

@app.route('/subir', methods=['GET', 'POST'])
def subir():
    if 'user' not in session: return redirect(url_for('login'))
    if session['rol'] not in ['master', 'gestor', 'supervisor']:
        flash('No tiene permisos para cargar expedientes.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        tipo_documento = request.form.get('tipo_documento')
        archivos_subidos = []
        uploaded_files = request.files.getlist('pdfs')
        
        if len(uploaded_files) > 12:
            flash('Error: Puede adjuntar un máximo de 12 archivos PDF.', 'danger')
            return redirect(url_for('subir'))

        for file in uploaded_files:
            if file and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(filepath)
                archivos_subidos.append(unique_filename)
                
        nuevo_doc = {
            'tipo_documento': tipo_documento,
            'fecha_ingreso': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'archivos': archivos_subidos,
            'nombre_masculino': request.form.get('nombre_masculino', ''),
            'nombre_femenino': request.form.get('nombre_femenino', ''),
            'nombre_titular': request.form.get('nombre_titular', ''),
            'numero_acta': request.form.get('numero_acta', ''),
            'anio_documento': request.form.get('anio_documento', ''),
            'sub_tipo_cementerio': request.form.get('sub_tipo_cementerio', ''),
            'fecha_acta': request.form.get('fecha_acta', ''),
            'fecha_gaceta': request.form.get('fecha_gaceta', ''),
            'numero_gaceta': request.form.get('numero_gaceta', ''),
            'fecha_documento': request.form.get('fecha_documento', ''),
            'numero_registro': request.form.get('numero_registro', ''),
            'fecha_ingreso_lab': request.form.get('fecha_ingreso_lab', ''),
            'fecha_egreso_lab': request.form.get('fecha_egreso_lab', '')
        }
        
        save_db_doc(nuevo_doc)
        flash('Expediente cargado con éxito.', 'success')
        return redirect(url_for('buscar') if session['rol'] != 'gestor' else url_for('subir'))
        
    return render_template('subir.html', tipos=TIPOS_DOCUMENTO)

@app.route('/editar/<int:idx>', methods=['GET', 'POST'])
def editar(idx):
    if 'user' not in session or session['rol'] not in ['master', 'supervisor']:
        flash('Acceso restringido.', 'danger')
        return redirect(url_for('index'))
    
    db = load_db()
    doc = next((d for d in db if d['id'] == idx), None)
    if not doc: return redirect(url_for('buscar'))
        
    if request.method == 'POST':
        doc['tipo_documento'] = request.form.get('tipo_documento')
        doc['nombre_masculino'] = request.form.get('nombre_masculino', '')
        doc['nombre_femenino'] = request.form.get('nombre_femenino', '')
        doc['nombre_titular'] = request.form.get('nombre_titular', '')
        doc['numero_acta'] = request.form.get('numero_acta', '')
        doc['anio_documento'] = request.form.get('anio_documento', '')
        
        archivos_a_eliminar = request.form.getlist('eliminar_archivos')
        for arc in archivos_a_eliminar:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, arc))
            except:
                pass
        doc['archivos'] = [a for a in doc.get('archivos', []) if a not in archivos_a_eliminar]
        
        uploaded_files = request.files.getlist('pdfs')
        total_actual = len(doc['archivos'])
        for file in uploaded_files:
            if file and file.filename.endswith('.pdf'):
                if total_actual >= 12: break
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(UPLOAD_FOLDER, unique_filename))
                doc['archivos'].append(unique_filename)
                total_actual += 1

        save_db_doc(doc, doc_id=idx)
        flash('Registro actualizado correctamente.', 'success')
        return redirect(url_for('buscar'))
        
    return render_template('editar.html', doc=doc, idx=idx, tipos=TIPOS_DOCUMENTO)

@app.route('/eliminar/<int:idx>')
def eliminar(idx):
    if 'user' not in session or session['rol'] != 'master': return redirect(url_for('index'))
    delete_db_doc(idx)
    flash('Registro eliminado exitosamente.', 'success')
    return redirect(url_for('buscar'))

@app.route('/usuarios', methods=['GET'])
def gestionar_usuarios():
    if 'user' not in session or session['rol'] != 'master': return redirect(url_for('index'))
    return render_template('usuarios.html', usuarios=load_users())

@app.route('/usuarios/crear', methods=['POST'])
def crear_usuario():
    if 'user' not in session or session['rol'] != 'master': return redirect(url_for('index'))
    users = load_users()
    new_username = request.form.get('username')
    if any(u['username'] == new_username for u in users):
        flash('El nombre de usuario ya existe.', 'danger')
        return redirect(url_for('gestionar_usuarios'))
        
    users.append({
        "id": max([u['id'] for u in users], default=0) + 1,
        "username": new_username,
        "password": request.form.get('password'),
        "rol": request.form.get('rol'),
        "nombre": request.form.get('nombre')
    })
    save_users(users)
    flash('Usuario creado exitosamente.', 'success')
    return redirect(url_for('gestionar_usuarios'))

@app.route('/usuarios/editar', methods=['POST'])
def editar_usuario():
    if 'user' not in session or session['rol'] != 'master': return redirect(url_for('index'))
    users = load_users()
    user_id = int(request.form.get('user_id'))
    for u in users:
        if u['id'] == user_id:
            if request.form.get('password').strip(): u['password'] = request.form.get('password')
            if request.form.get('nombre').strip(): u['nombre'] = request.form.get('nombre')
            if request.form.get('rol') and u['username'] != 'master': u['rol'] = request.form.get('rol')
            break
    save_users(users)
    flash('Usuario actualizado.', 'success')
    return redirect(url_for('gestionar_usuarios'))

@app.route('/usuarios/eliminar/<username>')
def eliminar_usuario(username):
    if 'user' not in session or session['rol'] != 'master' or username == 'master': return redirect(url_for('gestionar_usuarios'))
    save_users([u for u in load_users() if u['username'] != username])
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('gestionar_usuarios'))

@app.route('/descargar/<filename>', endpoint='descargar_archivo')
def descargar(filename):
    if 'user' not in session or session['rol'] == 'gestor': return redirect(url_for('index'))
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/ver/<filename>')
def ver_archivo(filename):
    if 'user' not in session or session['rol'] == 'gestor': return redirect(url_for('index'))
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)

@app.route('/documento/<int:id>')
def ver_detalle(id):
    if 'user' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM documentos WHERE id = ?', (id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        flash('El documento no fue encontrado.', 'danger')
        return redirect(url_for('buscar'))
        
    documento = dict(row)
    try:
        documento['archivos'] = json.loads(documento['archivos']) if documento['archivos'] else []
    except:
        documento['archivos'] = []
        
    return render_template('detalle.html', documento=documento)

# --- ENDPOINT DE SINCRONIZACION AUTOMATICA ---
TOKEN_SECRETO = "Archivoscmm"

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
                lista_archivos = json.loads(reg.get('archivos')) if reg.get('archivos') else []
            except:
                lista_archivos = []
            reg['lista_pdfs'] = [f"https://{request.host}/descargar/{nombre}" for nombre in lista_archivos]
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
