import os
import json

os.makedirs('templates', exist_ok=True)
os.makedirs('storage_pdf', exist_ok=True)

# 1. ACTUALIZAR APP.PY
codigo_app = '''import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'catatumbo_digital_secure_secret_key'
UPLOAD_FOLDER = 'storage_pdf'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_NAME = 'catatumbo.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(\x27\x27\x27
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            nombre TEXT NOT NULL
        )
    \x27\x27\x27)
    
    cursor.execute(\x27\x27\x27
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
            fecha_egreso_lab TEXT
        )
    \x27\x27\x27)
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("master", "123", "master", "Administrador Master"),
            ("consultor", "123", "consultor", "Usuario Consultor"),
            ("gestor", "123", "gestor", "Gestor de Carga"),
            ("supervisor", "123", "supervisor", "Supervisor IT")
        ]
        cursor.executemany(\x27\x27\x27
            INSERT INTO usuarios (username, password, rol, nombre)
            VALUES (?, ?, ?, ?)
        \x27\x27\x27, default_users)
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
        cursor.execute(\x27\x27\x27
            INSERT INTO usuarios (id, username, password, rol, nombre)
            VALUES (?, ?, ?, ?, ?)
        \x27\x27\x27, (u.get('id'), u['username'], u['password'], u['rol'], u['nombre']))
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
        cursor.execute(\x27\x27\x27
            UPDATE documentos SET
                tipo_documento = ?, fecha_ingreso = ?, archivos = ?,
                nombre_masculino = ?, nombre_femenino = ?, nombre_titular = ?,
                numero_acta = ?, anio_documento = ?, sub_tipo_cementerio = ?,
                fecha_acta = ?, fecha_gaceta = ?, numero_gaceta = ?,
                fecha_documento = ?, numero_registro = ?, fecha_ingreso_lab = ?,
                fecha_egreso_lab = ?
            WHERE id = ?
        \x27\x27\x27, (
            doc.get('tipo_documento'), doc.get('fecha_ingreso'), archivos_json,
            doc.get('nombre_masculino', ''), doc.get('nombre_femenino', ''), doc.get('nombre_titular', ''),
            doc.get('numero_acta', ''), doc.get('anio_documento', ''), doc.get('sub_tipo_cementerio', ''),
            doc.get('fecha_acta', ''), doc.get('fecha_gaceta', ''), doc.get('numero_gaceta', ''),
            doc.get('fecha_documento', ''), doc.get('numero_registro', ''), doc.get('fecha_ingreso_lab', ''),
            doc.get('fecha_egreso_lab', ''), doc_id
        ))
    else:
        cursor.execute(\x27\x27\x27
            INSERT INTO documentos (
                tipo_documento, fecha_ingreso, archivos, nombre_masculino,
                nombre_femenino, nombre_titular, numero_acta, anio_documento,
                sub_tipo_cementerio, fecha_acta, fecha_gaceta, numero_gaceta,
                fecha_documento, numero_registro, fecha_ingreso_lab, fecha_egreso_lab
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        \x27\x27\x27, (
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
'''

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(codigo_app)

# 2. REPARAR buscar.html PARA ASEGURAR QUE TENGA EL BOTÓN CORRECTO CON EL ICONO DE OJO
buscar_html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Buscar Documentos - Catatumbo Digital</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">Catatumbo Digital - CMM</a>
            <div class="collapse navbar-collapse">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('index') }}">Inicio</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Cerrar Sesión</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        <div class="row mb-3">
            <div class="col-md-12">
                <h3>Consulta y Búsqueda de Expedientes</h3>
                <form method="GET" action="{{ url_for('buscar') }}" class="row g-3 mt-2">
                    <div class="col-md-6">
                        <input type="text" name="q" class="form-control" placeholder="Buscar por nombre, acta, gaceta o registro..." value="{{ query }}">
                    </div>
                    <div class="col-md-4">
                        <select name="tipo" class="form-select">
                            <option value="">Todos los tipos</option>
                            {% for t in tipos %}
                                <option value="{{ t }}" {% if tipo_filtro == t %}selected{% endif %}>{{ t }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="col-md-2">
                        <button type="submit" class="btn btn-primary w-100">Buscar</button>
                    </div>
                </form>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped table-hover align-middle">
                        <thead class="table-dark">
                            <tr>
                                <th>ID</th>
                                <th>Tipo de Documento</th>
                                <th>Fecha de Ingreso</th>
                                <th>Identificador / Titular</th>
                                <th class="text-center">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for doc in resultados %}
                            <tr>
                                <td>{{ doc.index_id }}</td>
                                <td>{{ doc.tipo_documento }}</td>
                                <td>{{ doc.fecha_ingreso }}</td>
                                <td>
                                    {{ doc.nombre_titular or doc.nombre_masculino or doc.nombre_femenino or doc.numero_acta or doc.numero_gaceta or doc.numero_registro or 'Sin especificar' }}
                                </td>
                                <td class="text-center">
                                    <a href="{{ url_for('ver_detalle', id=doc.index_id) }}" class="btn btn-sm btn-outline-info" title="Ver detalle"><i class="fas fa-eye"></i></a>
                                    {% if session['rol'] in ['master', 'supervisor'] %}
                                    <a href="{{ url_for('editar', idx=doc.index_id) }}" class="btn btn-sm btn-outline-primary" title="Editar"><i class="bi bi-pencil"></i></a>
                                    {% endif %}
                                    {% if session['rol'] == 'master' %}
                                    <a href="{{ url_for('eliminar', idx=doc.index_id) }}" class="btn btn-sm btn-outline-danger" title="Eliminar" onclick="return confirm('¿Está seguro de eliminar este registro?');"><i class="bi bi-trash"></i></a>
                                    {% endif %}
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="5" class="text-center text-muted">No se encontraron registros.</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

with open('templates/buscar.html', 'w', encoding='utf-8') as f:
    f.write(buscar_html_content)

print("[OK] ¡Sistema y plantilla buscar.html actualizados y reparados con éxito!")
