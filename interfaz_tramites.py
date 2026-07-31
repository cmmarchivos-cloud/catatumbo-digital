import sys
import sqlite3
import random
import string
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QMessageBox, QDialog, QFormLayout, QLineEdit, QLabel)

class DialogoProcesar(QDialog):
    def __init__(self, registro, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏛️ Procesar Solicitud y Emitir Comprobante - CMBM")
        self.setMinimumWidth(450)
        
        self.reg_id = registro[0]
        self.nombre = registro[2] or ""
        self.apellido = registro[3] or ""
        self.cedula = registro[4] or ""
        self.correo = registro[5] or ""
        self.doc_tipo = registro[6] or ""

        layout = QVBoxLayout(self)
        
        info_label = QLabel(f"<b>Solicitante:</b> {self.nombre} {self.apellido}<br><b>Cédula:</b> {self.cedula}<br><b>Documento:</b> {self.doc_tipo}")
        info_label.setStyleSheet("background-color: #f8fafc; padding: 10px; border-radius: 5px; border: 1px solid #cbd5e0;")
        layout.addWidget(info_label)

        form_layout = QFormLayout()
        
        self.input_ano = QLineEdit()
        self.input_tomo = QLineEdit()
        self.input_folio = QLineEdit()
        self.input_acta = QLineEdit()
        self.input_monto = QLineEdit()
        self.input_monto.setPlaceholderText("Ej. 150,00")

        form_layout.addRow("Año del Archivo Físico:", self.input_ano)
        form_layout.addRow("Tomo:", self.input_tomo)
        form_layout.addRow("Folio:", self.input_folio)
        form_layout.addRow("Número de Acta:", self.input_acta)
        form_layout.addRow("Monto en Bs.:", self.input_monto)

        layout.addLayout(form_layout)

        btn_enviar = QPushButton("🚀 Procesar, Generar QR y Enviar Correo")
        btn_enviar.setStyleSheet("background-color: #03254c; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        btn_enviar.clicked.connect(self.procesar_y_enviar)
        layout.addWidget(btn_enviar)

    def procesar_y_enviar(self):
        ano = self.input_ano.text().strip()
        tomo = self.input_tomo.text().strip()
        folio = self.input_folio.text().strip()
        num_acta = self.input_acta.text().strip()
        monto_txt = self.input_monto.text().strip()

        if not ano or not tomo or not folio or not num_acta or not monto_txt:
            QMessageBox.warning(self, "Campos Incompletos", "Por favor llene todos los datos solicitados.")
            return

        monto = f"Bs. {monto_txt}"
        codigo_seguridad = "CMBM-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        id_full = f"V-{self.cedula}"

        texto_qr = (f"🏛️ CMBM - ARCHIVO MUNICIPAL\nSOLICITANTE: {self.nombre} {self.apellido}\n"
                    f"ID: {id_full}\nDOCUMENTO: {self.doc_tipo}\nMONTO: {monto}\n"
                    f"UBICACIÓN: AÑO {ano}/T:{tomo}/F:{folio}\nSEGURIDAD: {codigo_seguridad}")
        
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(texto_qr)}"

        html_cuerpo_correo = f"""
        <div style="background-color: #f4f7f9; padding: 40px 10px; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
          <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #e1e8ed;">
            <div style="background: linear-gradient(135deg, #03254c 0%, #064b99 100%); color: white; padding: 30px; text-align: center;">
              <div style="font-size: 24px; font-weight: 800; letter-spacing: 1px; margin-bottom: 5px;">ARCHIVO MUNICIPAL</div>
              <div style="font-size: 12px; text-transform: uppercase; opacity: 0.9; letter-spacing: 2px;">Concejo Municipal Bolivariano de Maracaibo</div>
            </div>
            <div style="padding: 30px; line-height: 1.6;">
              <h3 style="color: #03254c; margin-top: 0;">¡Solicitud Procesada con Éxito!</h3>
              <p style="color: #555; font-size: 15px;">Estimado(a) ciudadano(a) <b>{self.nombre} {self.apellido}</b>, se ha generado su comprobante digital de validación.</p>
              
              <div style="background-color: #f8fafc; border-radius: 10px; padding: 20px; border: 1px solid #edf2f7; margin: 25px 0;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                  <tr><td style="padding: 8px 0; color: #718096;">👤 Titular:</td><td style="padding: 8px 0; text-align: right; font-weight: bold; color: #2d3748;">{self.nombre} {self.apellido}</td></tr>
                  <tr><td style="padding: 8px 0; color: #718096;">🆔 Identificación:</td><td style="padding: 8px 0; text-align: right; font-weight: bold; color: #2d3748;">{id_full}</td></tr>
                  <tr><td style="padding: 8px 0; color: #718096;">📄 Documento:</td><td style="padding: 8px 0; text-align: right; font-weight: bold; color: #2d3748;">{self.doc_tipo}</td></tr>
                  <tr><td style="padding: 8px 0; color: #718096;">📂 Archivo Físico:</td><td style="padding: 8px 0; text-align: right; font-weight: bold; color: #2d3748;">AÑO {ano} | T: {tomo} | F: {folio}</td></tr>
                  <tr><td style="padding: 8px 0; color: #718096;">💰 Monto a Pagar:</td><td style="padding: 8px 0; text-align: right; font-weight: bold; color: #e53e3e; font-size: 15px;">{monto}</td></tr>
                  <tr><td style="padding: 15px 0 5px 0; color: #718096;">🔐 Código de Seguridad:</td><td style="padding: 15px 0 5px 0; text-align: right;"><span style="background-color: #03254c; color: white; padding: 4px 10px; border-radius: 4px; font-family: monospace; font-size: 16px;">{codigo_seguridad}</span></td></tr>
                </table>
              </div>

              <div style="border-left: 4px solid #f6ad55; background-color: #fffaf0; padding: 20px; border-radius: 0 8px 8px 0;">
                <div style="color: #9c4221; font-weight: bold; margin-bottom: 10px; font-size: 14px;">📍 PASOS OBLIGATORIOS PARA RETIRAR:</div>
                <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #744210;">
                  <li style="margin-bottom: 8px;">Asistir a <b>SEDEMAT</b> (Sector Valle Frío).</li>
                  <li style="margin-bottom: 8px;">Realizar el pago de aranceles municipales.</li>
                  <li>Presentar el pago para la certificación y retiro (3 días hábiles).</li>
                </ul>
              </div>

              <div style="text-align: center; margin-top: 35px; padding-top: 25px; border-top: 1px solid #edf2f7;">
                <div style="font-size: 11px; font-weight: bold; color: #a0aec0; margin-bottom: 15px; text-transform: uppercase;">Validación de Integridad de Datos</div>
                <img src="{qr_url}" width="160" height="160" style="border: 1px solid #e2e8f0; padding: 5px; border-radius: 5px;">
              </div>
            </div>
          </div>
        </div>"""

        try:
            remitente = "cmbmarchivos@gmail.com"
            password_smtp = "grkbdicflorubcrv"

            msg = MIMEMultipart()
            msg['From'] = remitente
            msg['To'] = self.correo
            msg['Subject'] = f"🏛️ COMPROBANTE DIGITAL: {self.nombre} {self.apellido}"
            msg.attach(MIMEText(html_cuerpo_correo, 'html'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(remitente, password_smtp)
            server.sendmail(remitente, self.correo, msg.as_string())
            server.quit()

            conn = sqlite3.connect("catatumbo.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE solicitudes_tramites 
                SET tomo = ?, folio = ?, num_acta = ?, monto = ?, codigo_seguridad = ?, estado = 'PROCESADO'
                WHERE id = ?
            """, (tomo, folio, num_acta, monto, codigo_seguridad, self.reg_id))
            conn.commit()
            conn.close()

            QMessageBox.information(self, "Éxito", "Comprobante procesado y correo enviado correctamente.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo completar el envío:\n{e}")

class VentanaGestionTramites(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🏛️ Catatumbo Digital - Gestión de Solicitudes y Trámites")
        self.resize(1100, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        btn_actualizar = QPushButton("🔄 Actualizar Tabla desde la Base de Datos")
        btn_actualizar.setStyleSheet("background-color: #03254c; color: white; font-weight: bold; padding: 8px;")
        btn_actualizar.clicked.connect(self.cargar_datos)
        layout.addWidget(btn_actualizar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Fecha", "Nombre", "Apellido", "Cédula", "Correo", "Tipo Documento", "Estado", "Acción"
        ])
        layout.addWidget(self.tabla)

        self.cargar_datos()

    def cargar_datos(self):
        try:
            conn = sqlite3.connect("catatumbo.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, marca_temporal, nombre_solicitante, apellido_solicitante, 
                       cedula_solicitante, correo_solicitante, tipo_documento, estado 
                FROM solicitudes_tramites
            """)
            registros = cursor.fetchall()
            conn.close()

            self.tabla.setRowCount(len(registros))
            for row_idx, reg in enumerate(registros):
                for col_idx, val in enumerate(reg):
                    self.tabla.setItem(row_idx, col_idx, QTableWidgetItem(str(val or "")))
                
                btn_procesar = QPushButton("⚙️ Procesar / Enviar QR")
                estado_actual = reg[7]
                
                if estado_actual == 'PROCESADO':
                    btn_procesar.setText("✅ Procesado")
                    btn_procesar.setEnabled(False)
                    btn_procesar.setStyleSheet("background-color: #48bb78; color: white;")
                else:
                    btn_procesar.setStyleSheet("background-color: #2b6cb0; color: white; font-weight: bold;")
                    reg_completo = reg
                    btn_procesar.clicked.connect(lambda _, r=reg_completo: self.abrir_formulario_procesar(r))

                self.tabla.setCellWidget(row_idx, 8, btn_procesar)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar los datos:\n{e}")

    def abrir_formulario_procesar(self, registro):
        dialogo = DialogoProcesar(registro, self)
        if dialogo.exec():
            self.cargar_datos()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaGestionTramites()
    ventana.show()
    sys.exit(app.exec())
