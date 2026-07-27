import os

os.makedirs('templates', exist_ok=True)

usuarios_html_content = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Gestión de Usuarios - Catatumbo Digital</title>
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
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('buscar') }}">Buscar</a></li>
                    <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Cerrar Sesión</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="row mb-4">
            <div class="col-md-12">
                <h3>Gestión de Usuarios del Sistema</h3>
                <button class="btn btn-success mt-2" data-bs-toggle="modal" data-bs-target="#modalCrearUsuario"><i class="fas fa-user-plus"></i> Nuevo Usuario</button>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-striped table-hover align-middle">
                        <thead class="table-dark">
                            <tr>
                                <th>ID</th>
                                <th>Usuario</th>
                                <th>Nombre Completo</th>
                                <th>Rol</th>
                                <th class="text-center">Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for u in usuarios %}
                            <tr>
                                <td>{{ u.id }}</td>
                                <td>{{ u.username }}</td>
                                <td>{{ u.nombre }}</td>
                                <td><span class="badge bg-secondary">{{ u.rol }}</span></td>
                                <td class="text-center">
                                    <button class="btn btn-sm btn-outline-info" data-bs-toggle="modal" data-bs-target="#modalDetalleUsuario{{ u.id }}" title="Ver detalle"><i class="fas fa-eye"></i></button>
                                    <button class="btn btn-sm btn-outline-primary" data-bs-toggle="modal" data-bs-target="#modalEditarUsuario{{ u.id }}" title="Editar"><i class="bi bi-pencil"></i></button>
                                    {% if u.username != 'master' %}
                                    <a href="{{ url_for('eliminar_usuario', username=u.username) }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('¿Está seguro de eliminar este usuario?');" title="Eliminar"><i class="bi bi-trash"></i></a>
                                    {% endif %}
                                </td>
                            </tr>

                            <!-- Modal Ver Detalle Usuario -->
                            <div class="modal fade" id="modalDetalleUsuario{{ u.id }}" tabindex="-1">
                              <div class="modal-dialog">
                                <div class="modal-content">
                                  <div class="modal-header bg-info text-white">
                                    <h5 class="modal-title"><i class="fas fa-user"></i> Detalle del Usuario: {{ u.username }}</h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                  </div>
                                  <div class="modal-body">
                                      <ul class="list-group list-group-flush">
                                          <li class="list-group-item"><strong>ID de Usuario:</strong> {{ u.id }}</li>
                                          <li class="list-group-item"><strong>Nombre de usuario:</strong> {{ u.username }}</li>
                                          <li class="list-group-item"><strong>Nombre Completo:</strong> {{ u.nombre }}</li>
                                          <li class="list-group-item"><strong>Rol en el Sistema:</strong> <span class="badge bg-secondary">{{ u.rol }}</span></li>
                                      </ul>
                                  </div>
                                  <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                                  </div>
                                </div>
                              </div>
                            </div>

                            <!-- Modal Editar Usuario -->
                            <div class="modal fade" id="modalEditarUsuario{{ u.id }}" tabindex="-1">
                              <div class="modal-dialog">
                                <div class="modal-content">
                                  <form method="POST" action="{{ url_for('editar_usuario') }}">
                                      <input type="hidden" name="user_id" value="{{ u.id }}">
                                      <div class="modal-header">
                                        <h5 class="modal-title">Editar Usuario: {{ u.username }}</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                      </div>
                                      <div class="modal-body">
                                          <div class="mb-3">
                                              <label class="form-label">Nombre completo</label>
                                              <input type="text" name="nombre" class="form-control" value="{{ u.nombre }}" required>
                                          </div>
                                          <div class="mb-3">
                                              <label class="form-label">Nueva Contraseña (dejar en blanco para mantener la actual)</label>
                                              <input type="password" name="password" class="form-control" placeholder="******">
                                          </div>
                                          <div class="mb-3">
                                              <label class="form-label">Rol</label>
                                              <select name="rol" class="form-select" {% if u.username == 'master' %}disabled{% endif %} required>
                                                  <option value="consultor" {% if u.rol == 'consultor' %}selected{% endif %}>Consultor</option>
                                                  <option value="gestor" {% if u.rol == 'gestor' %}selected{% endif %}>Gestor de Carga</option>
                                                  <option value="supervisor" {% if u.rol == 'supervisor' %}selected{% endif %}>Supervisor IT</option>
                                                  <option value="master" {% if u.rol == 'master' %}selected{% endif %}>Master</option>
                                              </select>
                                              {% if u.username == 'master' %}
                                              <input type="hidden" name="rol" value="master">
                                              {% endif %}
                                          </div>
                                      </div>
                                      <div class="modal-footer">
                                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                        <button type="submit" class="btn btn-primary">Actualizar Usuario</button>
                                      </div>
                                  </form>
                                </div>
                              </div>
                            </div>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Crear Usuario -->
    <div class="modal fade" id="modalCrearUsuario" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <form method="POST" action="{{ url_for('crear_usuario') }}">
              <div class="modal-header">
                <h5 class="modal-title">Crear Nuevo Usuario</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                  <div class="mb-3">
                      <label class="form-label">Nombre de usuario</label>
                      <input type="text" name="username" class="form-control" required>
                  </div>
                  <div class="mb-3">
                      <label class="form-label">Nombre completo</label>
                      <input type="text" name="nombre" class="form-control" required>
                  </div>
                  <div class="mb-3">
                      <label class="form-label">Contraseña</label>
                      <input type="password" name="password" class="form-control" required>
                  </div>
                  <div class="mb-3">
                      <label class="form-label">Rol</label>
                      <select name="rol" class="form-select" required>
                          <option value="consultor">Consultor</option>
                          <option value="gestor">Gestor de Carga</option>
                          <option value="supervisor">Supervisor IT</option>
                          <option value="master">Master</option>
                      </select>
                  </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="submit" class="btn btn-primary">Guardar Usuario</button>
              </div>
          </form>
        </div>
      </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

with open('templates/usuarios.html', 'w', encoding='utf-8') as f:
    f.write(usuarios_html_content)

print("[OK] Plantilla usuarios.html actualizada con detalle, edición y creación de usuarios.")
