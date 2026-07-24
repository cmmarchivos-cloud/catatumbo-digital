import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'catatumbo_digital_secure_secret_key'
UPLOAD_FOLDER = 'storage_pdf'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_FILE = 'documentos.json'
USERS_FILE = 'usuarios.json'

def init_users():
    if not os.path.exists(USERS_FILE):
        default_users = [
            {"id": 1, "username": "master", "password": "123", "rol": "master", "nombre": "Administrador Master"},
            {"id": 2, "username": "consultor", "password": "123", "rol": "consultor", "nombre": "Usuario Consultor"},
            {"id": 3, "username": "gestor", "password": "123", "rol": "gestor", "nombre": "Gestor de Carga"},
            {"id": 4, "username": "supervisor", "password": "123", "rol": "supervisor", "nombre": "Supervisor IT"}
        ]
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, ensure_ascii=False, indent=4)

init_users()

# Versículo diario dinámico basado en el día del año
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

def load_users():
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def load_db():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_db(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

TIPOS_DOCUMENTO = [
    "Acta de nacimiento", "Acta de matrimonio", "Sentencia de divorcio",
    "Título de cementerio", "Expediente de venta terrenos ejidos",
    "Actas de sesiones", "Gaceta oficial",
    "Expedientes de construcción de urbanismo de Maracaibo OMPU",
    "Expedientes laborales"
]

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
    
    for idx, d in enumerate(docs):
        d['index_id'] = idx
        match_query = (
            query in d.get('nombre_masculino', '').lower() or 
            query in d.get('nombre_femenino', '').lower() or 
            query in d.get('nombre_titular', '').lower() or 
            query in d.get('numero_acta', '').lower() or
            query in d.get('numero_gaceta', '').lower() or
            query in d.get('numero_registro', '').lower()
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
        
        db = load_db()
        db.append(nuevo_doc)
        save_db(db)
        flash('Expediente cargado con éxito.', 'success')
        return redirect(url_for('buscar') if session['rol'] != 'gestor' else url_for('subir'))
        
    return render_template('subir.html', tipos=TIPOS_DOCUMENTO)

@app.route('/editar/<int:idx>', methods=['GET', 'POST'])
def editar(idx):
    if 'user' not in session or session['rol'] not in ['master', 'supervisor']:
        flash('Acceso restringido.', 'danger')
        return redirect(url_for('index'))
    
    db = load_db()
    if idx < 0 or idx >= len(db): return redirect(url_for('buscar'))
        
    doc = db[idx]
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

        db[idx] = doc
        save_db(db)
        flash('Registro actualizado correctamente.', 'success')
        return redirect(url_for('buscar'))
        
    return render_template('editar.html', doc=doc, idx=idx, tipos=TIPOS_DOCUMENTO)

@app.route('/eliminar/<int:idx>')
def eliminar(idx):
    if 'user' not in session or session['rol'] != 'master': return redirect(url_for('index'))
    db = load_db()
    if 0 <= idx < len(db):
        db.pop(idx)
        save_db(db)
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

@app.route('/descargar/<filename>')
def descargar(filename):
    if 'user' not in session or session['rol'] == 'gestor': return redirect(url_for('index'))
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/ver/<filename>')
def ver_archivo(filename):
    if 'user' not in session or session['rol'] == 'gestor': return redirect(url_for('index'))
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True, port=5000)