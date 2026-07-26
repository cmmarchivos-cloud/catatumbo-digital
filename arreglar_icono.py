import os
import re

for archivo_nombre in os.listdir('templates'):
    if archivo_nombre.endswith('.html'):
        ruta = os.path.join('templates', archivo_nombre)
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        patron = r"(<a[^>]*url_for\('ver_detalle'[^>]*>)([^<]*)(</a>)"
        nuevo_contenido, count = re.subn(patron, r'\1<i class="fas fa-eye"></i>\3', contenido)
        
        if count > 0:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(nuevo_contenido)
            print(f"[OK] Icono agregado en {ruta}")

