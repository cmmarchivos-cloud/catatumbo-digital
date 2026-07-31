@app.route('/api/recibir_solicitud', methods=['POST'])
def recibir_solicitud():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Sin datos recibidos"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO solicitudes_tramites (
            marca_temporal, correo_google, nombre_solicitante, apellido_solicitante,
            cedula_solicitante, nacionalidad, correo_solicitante, parentesco,
            tipo_documento, numero_copias, anio_expediente_titulo, fecha_acta,
            nombre_titular, contrayente_masculino, contrayente_femenino,
            datos_expediente, url_adjunto_copia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('marca_temporal'),
        data.get('correo_google'),
        data.get('nombre'),
        data.get('apellido'),
        data.get('cedula'),
        data.get('nacionalidad'),
        data.get('correo_contacto'),
        data.get('parentesco'),
        data.get('tipo_documento'),
        data.get('numero_copias'),
        data.get('anio_expediente_titulo'),
        data.get('fecha_acta'),
        data.get('nombre_titular'),
        data.get('contrayente_masculino'),
        data.get('contrayente_femenino'),
        data.get('datos_expediente'),
        data.get('adjunto_copia')
    ))
    
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Solicitud guardada con éxito"}), 200
