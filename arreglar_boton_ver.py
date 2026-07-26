import os
import re

for filename in os.listdir('templates'):
    if filename.endswith('.html'):
        path = os.path.join('templates', filename)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Busca cualquier enlace que apunte a ver_detalle y reemplázalo por un botón estilizado con icono
        pattern = r"<a[^>]*url_for\('ver_detalle'[^>]*>[\s\S]*?</a>"
        
        def replace_tag(match):
            original_tag = match.group(0)
            href_match = re.search(r"href\s*=\s*[\"']([^\"']*)[\"']", original_tag)
            if href_match:
                href_val = href_match.group(1)
                return f'<a href="{href_val}" class="btn btn-sm btn-outline-info" title="Ver detalle"><i class="fas fa-eye"></i></a>'
            return original_tag

        new_content, count = re.subn(pattern, replace_tag, content)
        if count > 0:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[OK] Botón 'Ver' actualizado en {filename} ({count} reemplazos)")

