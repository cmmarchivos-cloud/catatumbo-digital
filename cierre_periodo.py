"""
Módulo de Cierre de Período y Estadísticas Oficiales
Catatumbo Digital - Archivo Municipal de Maracaibo

Proporciona la lógica para:
- Corte Trimestral de solicitudes procesadas.
- Cierre Anual de solicitudes procesadas.
- Cálculo de estadísticas y métricas analíticas.
- Generación de informe técnico y acta de cierre oficial.
- Registro histórico y trazabilidad de cierres.
"""

import re
import json
from datetime import datetime
from base_datos import get_db

MESES_NOMBRES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

def inicializar_tabla_cierres(conn=None):
    """Crea la tabla cierres_periodo y asegura las columnas necesarias en solicitudes_tramites."""
    debe_cerrar = False
    if conn is None:
        conn = get_db()
        debe_cerrar = True
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cierres_periodo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_cierre TEXT UNIQUE NOT NULL,
            tipo_cierre TEXT NOT NULL, /* TRIMESTRAL o ANUAL */
            anio INTEGER NOT NULL,
            trimestre INTEGER, /* 1, 2, 3, 4 o NULL si es Anual */
            periodo_nombre TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            fecha_cierre TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            usuario TEXT NOT NULL,
            total_procesadas INTEGER DEFAULT 0,
            total_pendientes INTEGER DEFAULT 0,
            total_papelera INTEGER DEFAULT 0,
            total_general INTEGER DEFAULT 0,
            total_monto REAL DEFAULT 0.0,
            estadisticas_json TEXT,
            solicitudes_ids TEXT,
            observaciones TEXT,
            estado TEXT DEFAULT 'CERRADO'
        )
    ''')

    for col, col_tipo in [("fecha_proceso", "TIMESTAMP"), ("cierre_id", "INTEGER")]:
        try:
            cursor.execute(f"ALTER TABLE solicitudes_tramites ADD COLUMN {col} {col_tipo};")
        except Exception:
            pass

    for col, col_tipo in [("cierre_id", "INTEGER")]:
        try:
            cursor.execute(f"ALTER TABLE op_procesados ADD COLUMN {col} {col_tipo};")
        except Exception:
            pass

    conn.commit()
    if debe_cerrar:
        conn.close()

def parsear_monto(monto_raw):
    """Convierte cualquier cadena de monto (ej. 'Bs. 1.250,50' o '500') a float."""
    if not monto_raw:
        return 0.0
    s = str(monto_raw).replace('Bs.', '').replace('Bs', '').replace('$', '').strip()
    if not s or any(w in s.lower() for w in ['taquilla', 'exonerado', 'pendiente', 'n/a', 'por', 'gratis']):
        return 0.0
    try:
        if '.' in s and ',' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except Exception:
        return 0.0

def extraer_fecha(fecha_str):
    """Extrae un objeto datetime desde múltiples formatos de fecha comunes."""
    if not fecha_str:
        return None
    s = str(fecha_str).strip()
    formatos = (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y"
    )
    for fmt in formatos:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    # Regex para día/mes/año
    m = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', s)
    if m:
        p1, p2, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Asume día <= 31 y mes <= 12
        if p2 <= 12:
            try:
                return datetime(y, p2, p1)
            except Exception:
                pass
        if p1 <= 12:
            try:
                return datetime(y, p1, p2)
            except Exception:
                pass

    # Regex para año-mes-día
    m2 = re.search(r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', s)
    if m2:
        y, mth, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        try:
            return datetime(y, mth, d)
        except Exception:
            pass

    return None

def obtener_anios_disponibles(conn=None):
    """Devuelve la lista de años disponibles en el sistema para cierres."""
    debe_cerrar = False
    if conn is None:
        conn = get_db()
        debe_cerrar = True
    cursor = conn.cursor()
    anios = set([datetime.now().year, 2026, 2025])

    try:
        filas = cursor.execute("SELECT marca_temporal, fecha_proceso FROM solicitudes_tramites").fetchall()
        for f in filas:
            for campo in ['fecha_proceso', 'marca_temporal']:
                dt = extraer_fecha(f[campo])
                if dt:
                    anios.add(dt.year)
    except Exception:
        pass

    try:
        filas_op = cursor.execute("SELECT fecha_proceso FROM op_procesados").fetchall()
        for f in filas_op:
            dt = extraer_fecha(f['fecha_proceso'])
            if dt:
                anios.add(dt.year)
    except Exception:
        pass

    try:
        filas_c = cursor.execute("SELECT anio FROM cierres_periodo").fetchall()
        for f in filas_c:
            if f['anio']:
                anios.add(int(f['anio']))
    except Exception:
        pass

    if debe_cerrar:
        conn.close()
    return sorted(list(anios), reverse=True)

def obtener_rango_fechas(tipo='TRIMESTRAL', anio=2026, trimestre=4):
    """Calcula los límites exactos de fechas y la denominación del período."""
    anio = int(anio)
    if tipo == 'TRIMESTRAL':
        trimestre = int(trimestre) if trimestre else 1
        if trimestre == 1:
            f_ini_str = f"{anio}-01-01 00:00:00"
            f_fin_str = f"{anio}-03-31 23:59:59"
            periodo_nombre = f"1er Trimestre {anio} (Enero - Marzo)"
            meses = [1, 2, 3]
        elif trimestre == 2:
            f_ini_str = f"{anio}-04-01 00:00:00"
            f_fin_str = f"{anio}-06-30 23:59:59"
            periodo_nombre = f"2do Trimestre {anio} (Abril - Junio)"
            meses = [4, 5, 6]
        elif trimestre == 3:
            f_ini_str = f"{anio}-07-01 00:00:00"
            f_fin_str = f"{anio}-09-30 23:59:59"
            periodo_nombre = f"3er Trimestre {anio} (Julio - Septiembre)"
            meses = [7, 8, 9]
        else:
            f_ini_str = f"{anio}-10-01 00:00:00"
            f_fin_str = f"{anio}-12-31 23:59:59"
            periodo_nombre = f"4to Trimestre {anio} (Octubre - Diciembre)"
            meses = [10, 11, 12]
    else:
        # Cierre Anual
        trimestre = None
        f_ini_str = f"{anio}-01-01 00:00:00"
        f_fin_str = f"{anio}-12-31 23:59:59"
        periodo_nombre = f"Cierre Anual Ejercicio Fiscal {anio}"
        meses = list(range(1, 13))

    f_ini_dt = datetime.strptime(f_ini_str, "%Y-%m-%d %H:%M:%S")
    f_fin_dt = datetime.strptime(f_fin_str, "%Y-%m-%d %H:%M:%S")

    return {
        'tipo': tipo,
        'anio': anio,
        'trimestre': trimestre,
        'periodo_nombre': periodo_nombre,
        'fecha_inicio_str': f_ini_str,
        'fecha_fin_str': f_fin_str,
        'fecha_inicio_dt': f_ini_dt,
        'fecha_fin_dt': f_fin_dt,
        'meses': meses
    }

def obtener_datos_periodo(conn, tipo='TRIMESTRAL', anio=2026, trimestre=4):
    """
    Calcula exhaustivamente las estadísticas y listas de solicitudes procesadas,
    pendientes y en papelera para el período dado.
    """
    inicializar_tabla_cierres(conn)
    rango = obtener_rango_fechas(tipo=tipo, anio=anio, trimestre=trimestre)
    f_ini = rango['fecha_inicio_dt']
    f_fin = rango['fecha_fin_dt']

    cursor = conn.cursor()

    # 1. Obtener todas las solicitudes activas
    solicitudes_raw = cursor.execute("SELECT * FROM solicitudes_tramites").fetchall()
    # 2. Obtener historial OP procesadas
    op_raw = cursor.execute("SELECT * FROM op_procesados").fetchall()
    # 3. Obtener papelera de solicitudes
    papelera_raw = cursor.execute("SELECT * FROM papelera_solicitudes").fetchall()

    # Mapa de OP procesados para resolver fechas y datos
    mapa_op = {str(r['op']).strip(): dict(r) for r in op_raw if r['op']}

    solicitudes_procesadas = []
    solicitudes_pendientes = []
    solicitudes_papelera = []
    ids_procesadas_set = set()

    # Procesar solicitudes_tramites
    for s_row in solicitudes_raw:
        s = dict(s_row)
        sid_str = str(s['id'])
        op_info = mapa_op.get(sid_str, {})

        # Determinar fecha de proceso si está procesada
        dt_proceso = None
        if s.get('fecha_proceso'):
            dt_proceso = extraer_fecha(s['fecha_proceso'])
        elif op_info.get('fecha_proceso'):
            dt_proceso = extraer_fecha(op_info['fecha_proceso'])
        elif s.get('estado') == 'PROCESADA':
            dt_proceso = extraer_fecha(s.get('marca_temporal'))

        dt_solicitud = extraer_fecha(s.get('marca_temporal')) or dt_proceso or f_ini

        es_procesada = (s.get('estado') == 'PROCESADA' or sid_str in mapa_op)

        if es_procesada and dt_proceso and (f_ini <= dt_proceso <= f_fin):
            # Enriquecer datos de la procesada
            monto_val = parsear_monto(s.get('monto') or op_info.get('monto'))
            tomo = s.get('tomo') or op_info.get('tomo') or ''
            folio = s.get('folio') or op_info.get('folio') or ''
            acta = s.get('num_acta') or op_info.get('num_acta') or ''
            anio_exp = s.get('anio_expediente_titulo') or op_info.get('anio_expediente_titulo') or ''

            item = {
                'id': s['id'],
                'op': sid_str,
                'cedula': f"{s.get('nacionalidad', 'V')}-{s.get('cedula_solicitante', '')}".strip('-'),
                'solicitante': f"{s.get('nombre_solicitante', '')} {s.get('apellido_solicitante', '')}".strip() or 'Ciudadano',
                'tipo_documento': s.get('tipo_documento') or 'Acta / Trámite Municipal',
                'parentesco': s.get('parentesco', 'Titular'),
                'fecha_solicitud': dt_solicitud.strftime('%d/%m/%Y %H:%M') if dt_solicitud else (s.get('marca_temporal') or 'N/D'),
                'fecha_proceso': dt_proceso.strftime('%d/%m/%Y %H:%M') if dt_proceso else 'N/D',
                'fecha_proceso_dt': dt_proceso,
                'ubicacion': f"Año {anio_exp} | T:{tomo} | F:{folio} | Acta:{acta}" if (tomo or folio or acta or anio_exp) else "En archivo general",
                'tomo': tomo,
                'folio': folio,
                'num_acta': acta,
                'anio_exp': anio_exp,
                'monto_raw': s.get('monto') or op_info.get('monto') or 'Bs. 0,00',
                'monto': monto_val,
                'codigo_seguridad': s.get('codigo_seguridad') or f"CMBM-{sid_str}",
                'correo': s.get('correo_solicitante') or s.get('correo_google') or '',
                'cierre_id': s.get('cierre_id')
            }
            solicitudes_procesadas.append(item)
            ids_procesadas_set.add(sid_str)

        elif not es_procesada and dt_solicitud and (f_ini <= dt_solicitud <= f_fin):
            solicitudes_pendientes.append({
                'id': s['id'],
                'cedula': f"{s.get('nacionalidad', 'V')}-{s.get('cedula_solicitante', '')}".strip('-'),
                'solicitante': f"{s.get('nombre_solicitante', '')} {s.get('apellido_solicitante', '')}".strip() or 'Ciudadano',
                'tipo_documento': s.get('tipo_documento') or 'Acta / Trámite Municipal',
                'fecha_solicitud': dt_solicitud.strftime('%d/%m/%Y %H:%M') if dt_solicitud else (s.get('marca_temporal') or 'N/D'),
                'estado': s.get('estado', 'PENDIENTE')
            })

    # Verificar si hay OP en op_procesados que no estaban en solicitudes_tramites (archivadas/eliminadas)
    for op_row in op_raw:
        op_dict = dict(op_row)
        op_num = str(op_dict.get('op', '')).strip()
        if op_num and op_num not in ids_procesadas_set:
            dt_proceso = extraer_fecha(op_dict.get('fecha_proceso'))
            if dt_proceso and (f_ini <= dt_proceso <= f_fin):
                monto_val = parsear_monto(op_dict.get('monto'))
                tomo = op_dict.get('tomo', '')
                folio = op_dict.get('folio', '')
                acta = op_dict.get('num_acta', '')
                anio_exp = op_dict.get('anio_expediente_titulo', '')
                item = {
                    'id': op_num,
                    'op': op_num,
                    'cedula': 'N/D',
                    'solicitante': f'Trámite Archivado OP-{op_num}',
                    'tipo_documento': 'Documento Municipal Certificado',
                    'parentesco': 'Interesado',
                    'fecha_solicitud': dt_proceso.strftime('%d/%m/%Y %H:%M'),
                    'fecha_proceso': dt_proceso.strftime('%d/%m/%Y %H:%M'),
                    'fecha_proceso_dt': dt_proceso,
                    'ubicacion': f"Año {anio_exp} | T:{tomo} | F:{folio} | Acta:{acta}" if (tomo or folio or acta or anio_exp) else "En archivo",
                    'tomo': tomo,
                    'folio': folio,
                    'num_acta': acta,
                    'anio_exp': anio_exp,
                    'monto_raw': op_dict.get('monto') or 'Bs. 0,00',
                    'monto': monto_val,
                    'codigo_seguridad': f"CMBM-{op_num}",
                    'correo': '',
                    'cierre_id': op_dict.get('cierre_id')
                }
                solicitudes_procesadas.append(item)
                ids_procesadas_set.add(op_num)

    # Procesar papelera en el período
    for p_row in papelera_raw:
        p = dict(p_row)
        dt_p = extraer_fecha(p.get('marca_temporal'))
        if dt_p and (f_ini <= dt_p <= f_fin):
            solicitudes_papelera.append({
                'id': p['id'],
                'cedula': f"{p.get('nacionalidad', 'V')}-{p.get('cedula_solicitante', '')}".strip('-'),
                'solicitante': f"{p.get('nombre_solicitante', '')} {p.get('apellido_solicitante', '')}".strip(),
                'tipo_documento': p.get('tipo_documento', 'Trámite'),
                'fecha_solicitud': dt_p.strftime('%d/%m/%Y %H:%M') if dt_p else 'N/D'
            })

    # Ordenar procesadas cronológicamente inverso
    solicitudes_procesadas.sort(
        key=lambda x: x['fecha_proceso_dt'] if x.get('fecha_proceso_dt') else datetime.min,
        reverse=True
    )

    # 4. Totales y KPIs
    tot_proc = len(solicitudes_procesadas)
    tot_pend = len(solicitudes_pendientes)
    tot_pap = len(solicitudes_papelera)
    tot_gen = tot_proc + tot_pend + tot_pap
    tasa_efectividad = round((tot_proc / tot_gen * 100.0), 1) if tot_gen > 0 else 0.0
    total_monto = sum(s['monto'] for s in solicitudes_procesadas)

    # 5. Desglose por Tipo de Trámite
    tipos_dict = {}
    for s in solicitudes_procesadas:
        t = s['tipo_documento']
        if t not in tipos_dict:
            tipos_dict[t] = {'tipo': t, 'cantidad': 0, 'monto': 0.0}
        tipos_dict[t]['cantidad'] += 1
        tipos_dict[t]['monto'] += s['monto']

    desglose_tipos = []
    for t_nom, t_data in sorted(tipos_dict.items(), key=lambda x: x[1]['cantidad'], reverse=True):
        pct = round((t_data['cantidad'] / tot_proc * 100.0), 1) if tot_proc > 0 else 0.0
        desglose_tipos.append({
            'tipo': t_nom,
            'cantidad': t_data['cantidad'],
            'porcentaje': pct,
            'monto': round(t_data['monto'], 2)
        })

    # 6. Desglose Temporal (Meses o Trimestres)
    desglose_temporal = []
    if tipo == 'TRIMESTRAL':
        # 3 meses del trimestre
        for m_num in rango['meses']:
            m_nombre = MESES_NOMBRES[m_num - 1]
            procs_m = [s for s in solicitudes_procesadas if s.get('fecha_proceso_dt') and s['fecha_proceso_dt'].month == m_num]
            monto_m = sum(s['monto'] for s in procs_m)
            desglose_temporal.append({
                'etiqueta': f"{m_nombre}",
                'mes_num': m_num,
                'procesadas': len(procs_m),
                'monto': round(monto_m, 2)
            })
    else:
        # 4 trimestres del año
        trimestres_def = [
            (1, "1er Trimestre (Ene-Mar)", [1, 2, 3]),
            (2, "2do Trimestre (Abr-Jun)", [4, 5, 6]),
            (3, "3er Trimestre (Jul-Sep)", [7, 8, 9]),
            (4, "4to Trimestre (Oct-Dic)", [10, 11, 12])
        ]
        for t_id, t_lbl, m_lista in trimestres_def:
            procs_t = [s for s in solicitudes_procesadas if s.get('fecha_proceso_dt') and s['fecha_proceso_dt'].month in m_lista]
            monto_t = sum(s['monto'] for s in procs_t)
            desglose_temporal.append({
                'etiqueta': t_lbl,
                'trimestre': t_id,
                'procesadas': len(procs_t),
                'monto': round(monto_t, 2)
            })

    return {
        'rango': rango,
        'solicitudes_procesadas': solicitudes_procesadas,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_papelera': solicitudes_papelera,
        'totales': {
            'total_procesadas': tot_proc,
            'total_pendientes': tot_pend,
            'total_papelera': tot_pap,
            'total_general': tot_gen,
            'tasa_efectividad': tasa_efectividad,
            'total_monto': round(total_monto, 2)
        },
        'desglose_tipos': desglose_tipos,
        'desglose_temporal': desglose_temporal
    }

def generar_codigo_cierre(conn, tipo, anio, trimestre=None):
    """Genera un código correlativo único institucional para el cierre."""
    cursor = conn.cursor()
    if tipo == 'TRIMESTRAL':
        prefijo = f"CT-{anio}-T{trimestre}"
    else:
        prefijo = f"CA-{anio}"

    cursor.execute("SELECT COUNT(*) FROM cierres_periodo WHERE codigo_cierre LIKE ?", (f"{prefijo}%",))
    count = cursor.fetchone()[0] + 1
    return f"{prefijo}-{count:03d}"

def ejecutar_cierre_formal(conn, tipo='TRIMESTRAL', anio=2026, trimestre=4, usuario='ADMIN', observaciones=''):
    """
    Ejecuta y asienta formalmente el cierre de período en la base de datos,
    congelando estadísticas y emitiendo el código de cierre.
    """
    inicializar_tabla_cierres(conn)
    cursor = conn.cursor()

    datos = obtener_datos_periodo(conn, tipo=tipo, anio=anio, trimestre=trimestre)
    rango = datos['rango']
    totales = datos['totales']

    codigo = generar_codigo_cierre(conn, tipo=tipo, anio=anio, trimestre=trimestre)

    solicitudes_ids = [s['id'] for s in datos['solicitudes_procesadas']]

    # Empacar estadísticas completas en JSON
    stats_pack = {
        'rango': {
            'tipo': rango['tipo'],
            'anio': rango['anio'],
            'trimestre': rango['trimestre'],
            'periodo_nombre': rango['periodo_nombre'],
            'fecha_inicio_str': rango['fecha_inicio_str'],
            'fecha_fin_str': rango['fecha_fin_str']
        },
        'totales': totales,
        'desglose_tipos': datos['desglose_tipos'],
        'desglose_temporal': datos['desglose_temporal'],
        'solicitudes_procesadas': [
            {
                'id': s['id'],
                'op': s['op'],
                'cedula': s['cedula'],
                'solicitante': s['solicitante'],
                'tipo_documento': s['tipo_documento'],
                'fecha_solicitud': s['fecha_solicitud'],
                'fecha_proceso': s['fecha_proceso'],
                'ubicacion': s['ubicacion'],
                'monto': s['monto'],
                'monto_raw': s['monto_raw'],
                'codigo_seguridad': s['codigo_seguridad']
            }
            for s in datos['solicitudes_procesadas']
        ]
    }
    stats_json_str = json.dumps(stats_pack, ensure_ascii=False)
    ids_json_str = json.dumps(solicitudes_ids)

    cursor.execute('''
        INSERT INTO cierres_periodo (
            codigo_cierre, tipo_cierre, anio, trimestre, periodo_nombre,
            fecha_inicio, fecha_fin, fecha_cierre, usuario,
            total_procesadas, total_pendientes, total_papelera, total_general,
            total_monto, estadisticas_json, solicitudes_ids, observaciones, estado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CERRADO')
    ''', (
        codigo, tipo, anio, trimestre, rango['periodo_nombre'],
        rango['fecha_inicio_str'], rango['fecha_fin_str'], usuario,
        totales['total_procesadas'], totales['total_pendientes'], totales['total_papelera'],
        totales['total_general'], totales['total_monto'], stats_json_str, ids_json_str,
        observaciones
    ))

    cierre_id = cursor.lastrowid

    # Asociar solicitudes al cierre
    if solicitudes_ids:
        placeholders = ','.join(['?'] * len(solicitudes_ids))
        cursor.execute(f"UPDATE solicitudes_tramites SET cierre_id = ? WHERE id IN ({placeholders})", [cierre_id] + solicitudes_ids)
        cursor.execute(f"UPDATE op_procesados SET cierre_id = ? WHERE op IN ({placeholders})", [cierre_id] + [str(i) for i in solicitudes_ids])

    conn.commit()
    return codigo, cierre_id

def obtener_cierre_por_codigo(conn, codigo_cierre):
    """Recupera un cierre existente por su código oficial y desempaqueta los datos."""
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM cierres_periodo WHERE codigo_cierre = ?", (codigo_cierre,)).fetchone()
    if not row:
        return None
    cierre = dict(row)
    try:
        cierre['estadisticas'] = json.loads(cierre['estadisticas_json'])
    except Exception:
        cierre['estadisticas'] = {}
    return cierre

def obtener_historial_cierres(conn=None):
    """Devuelve la lista completa de cierres registrados en el sistema."""
    debe_cerrar = False
    if conn is None:
        conn = get_db()
        debe_cerrar = True
    inicializar_tabla_cierres(conn)
    cursor = conn.cursor()
    filas = cursor.execute("SELECT * FROM cierres_periodo ORDER BY id DESC").fetchall()
    historial = [dict(f) for f in filas]
    if debe_cerrar:
        conn.close()
    return historial

def anular_cierre(conn, cierre_id):
    """Anula un cierre oficial y desvincula las solicitudes asociadas."""
    cursor = conn.cursor()
    cursor.execute("UPDATE solicitudes_tramites SET cierre_id = NULL WHERE cierre_id = ?", (cierre_id,))
    cursor.execute("UPDATE op_procesados SET cierre_id = NULL WHERE cierre_id = ?", (cierre_id,))
    cursor.execute("UPDATE cierres_periodo SET estado = 'ANULADO' WHERE id = ?", (cierre_id,))
    conn.commit()
    return True
