import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash
# Importa tus modelos de base de datos y la lógica de sincronización con Google Sheets
# from .models import db, Solicitud

solicitudes_bp = Blueprint('solicitudes_bp', __name__, template_folder='templates')

@solicitudes_bp.route('/solicitudes')
def listar_solicitudes():
    # Consulta todas las solicitudes de la base de datos local SQLite
    # solicitudes = Solicitud.query.order_by(Solicitud.id.desc()).all()
    return render_template('solicitudes.html', solicitudes=solicitudes)

@solicitudes_bp.route('/solicitudes/sincronizar', methods=['GET'])
def sincronizar_todas():
    try:
        # Aquí va tu lógica que conecta con la API de Google Sheets para traer registros nuevos
        # sincronizar_google_sheets_a_sqlite()
        flash('¡Sincronización con Google Sheets completada exitosamente!', 'success')
    except Exception as e:
        flash(f'Error al sincronizar: {str(e)}', 'danger')
    return redirect(url_for('solicitudes_bp.listar_solicitudes'))

@solicitudes_bp.route('/solicitudes/procesar/<int:id>', methods=['POST'])
def procesar_y_guardar(id):
    # solicitud = Solicitud.query.get_or_404(id)
    
    # Recoger datos del formulario de verificación física
    solicitud.anio_expediente_titulo = request.form.get('anio_expediente_titulo')
    solicitud.tomo = request.form.get('tomo')
    solicitud.folio = request.form.get('folio')
    solicitud.num_acta = request.form.get('num_acta')
    solicitud.monto = request.form.get('monto')
    nuevo_estado = request.form.get('estado')
    
    # Si pasa a procesada y no tiene código de seguridad / QR, generarlo
    if nuevo_estado == 'PROCESADA' and not solicitud.codigo_seguridad:
        solicitud.codigo_seguridad = f"CMM-{uuid.uuid4().hex[:8].upper()}"
        # Opcional: Enviar correo electrónico automatizado con el QR al ciudadano
        # enviar_correo_con_qr(solicitud.correo_solicitante, solicitud.codigo_seguridad)

    solicitud.estado = nuevo_estado
    # db.session.commit()

    flash(f'Expediente OP-{id} actualizado y procesado correctamente.', 'success')
    return redirect(url_for('solicitudes_bp.listar_solicitudes'))
