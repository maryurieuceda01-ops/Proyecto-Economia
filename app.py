
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import re
from difflib import SequenceMatcher
from datetime import datetime
import random

# ── CONFIGURACIÓN ──────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'securevision2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'database', 'tienda.db')

# Ruta para blog de noticias
@app.route('/blog')
def blog():
    return render_template('blog.html')


# ── BASE DE DATOS ───────────────────────────────────────────
def get_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        # Mensaje de verificación silencioso o log
        return conn
    except sqlite3.Error as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

def init_db():
    # Verificamos si el archivo existe antes de intentar cualquier cosa
    if os.path.exists(DB_PATH):
        print(f"Conexión exitosa: Detectada base de datos en {DB_PATH}")
    else:
        print(f"Advertencia: No se encontró la DB en {DB_PATH}. Se creará una nueva.")

    conn = get_db()
    if conn is None:
        return

    cursor = conn.cursor()

    # Tablas necesarias para la tienda online
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre    TEXT NOT NULL,
            apellido  TEXT NOT NULL,
            email     TEXT UNIQUE NOT NULL,
            telefono  TEXT,
            password  TEXT NOT NULL,
            fecha     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT NOT NULL,
            descripcion TEXT,
            precio      REAL NOT NULL,
            categoria   TEXT,
            stock       INTEGER DEFAULT 0,
            emoji       TEXT DEFAULT '📦',
            sku         TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id  INTEGER,
            numero      TEXT NOT NULL,
            total       REAL NOT NULL,
            estado      TEXT DEFAULT 'pagado',
            fecha       TEXT DEFAULT CURRENT_TIMESTAMP,
            nombre      TEXT,
            email       TEXT,
            direccion   TEXT,
            ciudad      TEXT,
            pais        TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS detalle_pedido (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id   INTEGER NOT NULL,
            producto_id INTEGER,
            nombre      TEXT NOT NULL,
            precio      REAL NOT NULL,
            cantidad    INTEGER NOT NULL,
            subtotal    REAL NOT NULL,
            FOREIGN KEY (pedido_id)   REFERENCES pedidos(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    ''')

    # Población de datos (solo si está vacía)
    cursor.execute('SELECT COUNT(*) FROM productos')
    if cursor.fetchone()[0] == 0:
        productos = [
            ('Cámara IP 4K Exterior Hikvision', 'Visión nocturna 40m, IP67, detección IA', 89.99,  'camaras',    47, '📹', 'CAM-HIK-4K-01'),
            ('Cámara Domo 2MP Interior Dahua',  'Full HD, gran angular 120°',              45.99,  'camaras',    30, '📷', 'CAM-DAH-2MP'),
            ('Cámara PTZ 360° Zoom 30x',         'Seguimiento automático, IR 100m',         320.00, 'camaras',    12, '🎥', 'CAM-PTZ-30X'),
            ('Monitor NVR 16 Canales',           'Pantalla 21", grabación continua',        245.00, 'monitores',  20, '🖥️', 'MON-NVR-16'),
            ('Control Biométrico Facial',        'Reconocimiento facial + huella, WiFi',    135.00, 'biometricos',25, '👆', 'BIO-FAC-3000'),
            ('Kit Alarma Inalámbrica 6 Zonas',   'Central + sensores + sirena, app móvil',  120.00, 'alarmas',    18, '🔔', 'ALR-KIT-6Z'),
            ('Kit Cerca Eléctrica 500m',         'Energizador 5J, alarma integrada',        189.00, 'cercas',     10, '⚡', 'CER-KIT-500'),
            ('Fuente 12V 10A con Respaldo',      'Para 8 cámaras, batería incluida',         38.00, 'fuentes',    50, '🔌', 'FUE-12V-10A'),
        ]
        cursor.executemany('''
            INSERT INTO productos (nombre, descripcion, precio, categoria, stock, emoji, sku)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', productos)

    conn.commit()
    conn.close()
    print('Base de datos verificada y lista para operar.')


# ══════════════════════════════════════════════════════════════
# ── RUTAS PRINCIPALES ─────────────────────────────────────────
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    conn = get_db()
    productos = conn.execute('SELECT * FROM productos LIMIT 4').fetchall()
    conn.close()
    return render_template('index.html', productos=productos)


@app.route('/catalogo')
def catalogo():
    # Parámetros de búsqueda y página
    categoria = request.args.get('categoria', 'todos')
    page = request.args.get('page', 1, type=int)
    per_page = 16
    offset = (page - 1) * per_page

    conn = get_db()

    # Lógica de filtrado y conteo para la paginación
    if categoria == 'todos':
        total = conn.execute('SELECT COUNT(*) FROM productos').fetchone()[0]
        productos = conn.execute('SELECT * FROM productos LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    else:
        total = conn.execute('SELECT COUNT(*) FROM productos WHERE categoria = ?', (categoria,)).fetchone()[0]
        productos = conn.execute('SELECT * FROM productos WHERE categoria = ? LIMIT ? OFFSET ?',
                                 (categoria, per_page, offset)).fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    # Asegurarse de que carrito siempre esté definido y serializable
    carrito = session.get('carrito', [])

    return render_template('catalogo.html',
                           productos=productos,
                           categoria=categoria,
                           current_page=page,
                           total_pages=total_pages,
                           carrito=carrito)


@app.route('/producto/<int:id>')
def producto(id):
    conn = get_db()
    prod = conn.execute('SELECT * FROM productos WHERE id = ?', (id,)).fetchone()
    if not prod:
        return redirect(url_for('catalogo'))
    relacionados = conn.execute(
        'SELECT * FROM productos WHERE categoria = ? AND id != ? LIMIT 4',
        (prod['categoria'], id)
    ).fetchall()
    conn.close()
    return render_template('producto.html', producto=prod, relacionados=relacionados)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        conn = get_db()
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE email = ? AND password = ?',
            (email, password)
        ).fetchone()
        conn.close()
        if usuario:
            session['usuario_id']     = usuario['id']
            session['usuario_nombre'] = usuario['nombre']
            flash('¡Bienvenido de vuelta, ' + usuario['nombre'] + '!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.', 'error')
    return render_template('login.html')


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre   = request.form['nombre']
        apellido = request.form['apellido']
        email    = request.form['email']
        telefono = request.form.get('telefono', '')
        password = request.form['password']
        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO usuarios (nombre, apellido, email, telefono, password)
                VALUES (?, ?, ?, ?, ?)
            ''', (nombre, apellido, email, telefono, password))
            conn.commit()
            flash('¡Cuenta creada exitosamente! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Ese correo ya está registrado.', 'error')
        finally:
            conn.close()
    return render_template('registro.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('index'))


@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    subtotal  = sum(item['precio'] * item['cantidad'] for item in carrito)
    impuestos = subtotal * 0.15
    total     = subtotal + impuestos
    return render_template('carrito.html',
        carrito=carrito,
        subtotal=round(subtotal, 2),
        impuestos=round(impuestos, 2),
        total=round(total, 2)
    )


@app.route('/agregar_carrito/<int:producto_id>', methods=['POST'])
def agregar_carrito(producto_id):
    cantidad = int(request.form.get('cantidad', 1))
    conn = get_db()
    prod = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    conn.close()
    if not prod:
        return redirect(url_for('catalogo'))
    carrito = session.get('carrito', [])
    for item in carrito:
        if item['id'] == producto_id:
            item['cantidad'] += cantidad
            session['carrito'] = carrito
            flash(prod['nombre'] + ' actualizado en el carrito.', 'success')
            return redirect(request.referrer or url_for('catalogo'))
    carrito.append({
        'id':        producto_id,
        'nombre':    prod['nombre'],
        'precio':    prod['precio'],
        'emoji':     prod['emoji'],
        'cantidad':  cantidad,
        'categoria': prod['categoria']
    })
    session['carrito'] = carrito
    flash(prod['nombre'] + ' agregado al carrito.', 'success')
    return redirect(request.referrer or url_for('catalogo'))


@app.route('/eliminar_carrito/<int:producto_id>')
def eliminar_carrito(producto_id):
    carrito = session.get('carrito', [])
    carrito = [item for item in carrito if item['id'] != producto_id]
    session['carrito'] = carrito
    return redirect(url_for('carrito'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    carrito = session.get('carrito', [])
    if not carrito:
        return redirect(url_for('carrito'))
    subtotal  = sum(item['precio'] * item['cantidad'] for item in carrito)
    impuestos = subtotal * 0.15
    total     = subtotal + impuestos
    if request.method == 'POST':
        nombre    = request.form['nombre']
        apellido  = request.form['apellido']
        email     = request.form['email']
        telefono  = request.form['telefono']
        pais      = request.form['pais']
        direccion = request.form['direccion']
        ciudad    = request.form['ciudad']
        numero_pedido = '#SV-' + str(random.randint(10000, 99999))
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pedidos (usuario_id, numero, total, nombre, email, direccion, ciudad, pais)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.get('usuario_id'), numero_pedido, round(total, 2),
            nombre + ' ' + apellido, email, direccion, ciudad, pais
        ))
        pedido_id = cursor.lastrowid
        for item in carrito:
            cursor.execute('''
                INSERT INTO detalle_pedido (pedido_id, producto_id, nombre, precio, cantidad, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (pedido_id, item['id'], item['nombre'], item['precio'],
                  item['cantidad'], item['precio'] * item['cantidad']))
        conn.commit()
        conn.close()
        session['ultimo_pedido'] = {
            'numero':    numero_pedido,
            'nombre':    nombre + ' ' + apellido,
            'email':     email,
            'direccion': direccion,
            'ciudad':    ciudad,
            'pais':      pais,
            'carrito':   carrito,
            'subtotal':  round(subtotal, 2),
            'impuestos': round(impuestos, 2),
            'total':     round(total, 2),
            'fecha':     datetime.now().strftime('%d de %B, %Y')
        }
        session['carrito'] = []
        return redirect(url_for('factura'))
    return render_template('checkout.html',
        carrito=carrito,
        subtotal=round(subtotal, 2),
        impuestos=round(impuestos, 2),
        total=round(total, 2)
    )


@app.route('/factura')
def factura():
    pedido = session.get('ultimo_pedido')
    if not pedido:
        return redirect(url_for('index'))
    return render_template('factura.html', pedido=pedido)



# ══════════════════════════════════════════════════════════════
# ── RUTA POLÍTICA DE PRIVACIDAD ───────────────────────────────
# ══════════════════════════════════════════════════════════════

@app.route('/privacidad')
def privacidad():
    return render_template('privacidad.html')

# Ruta para devoluciones
@app.route('/devoluciones')
def devoluciones():
    return render_template('devoluciones.html')

# Ruta para garantía
@app.route('/garantia')
def garantia():
    return render_template('garantia.html')

# Ruta para envíos
@app.route('/envios')
def envios():
    return render_template('envios.html')

# Ruta para términos generales
@app.route('/terminos')
def terminos():
    return render_template('terminos.html')

# ══════════════════════════════════════════════════════════════
# ── RUTAS .HTML ───────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════

@app.route('/index.html')
def index_html():
    return redirect(url_for('index'))

# Ruta para preguntas frecuentes (FAQ)
@app.route('/FAQ')
def FAQ():
    return render_template('FAQ.html')

@app.route('/catalogo.html')
def catalogo_html():
    return redirect(url_for('catalogo'))

@app.route('/producto.html')
def producto_html():
    return redirect(url_for('catalogo'))

@app.route('/login.html')
def login_html():
    return redirect(url_for('login'))

@app.route('/registro.html')
def registro_html():
    return redirect(url_for('registro'))

@app.route('/carrito.html')
def carrito_html():
    return redirect(url_for('carrito'))

@app.route('/checkout.html')
def checkout_html():
    return redirect(url_for('checkout'))

@app.route('/factura.html')
def factura_html():
    return redirect(url_for('factura'))

@app.route('/nosotros')
def nosotros():
    return render_template('nosotros.html')

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/nosotros.html')
def nosotros_html():
    return redirect(url_for('nosotros'))

@app.route('/contacto.html')
def contacto_html():
    return redirect(url_for('contacto'))


@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    paso = 'verificar'
    if request.method == 'POST':
        accion = request.form.get('accion', 'verificar')

        if accion == 'verificar':
            email    = request.form['email']
            password = request.form['password']
            conn = get_db()
            usuario = conn.execute(
                'SELECT * FROM usuarios WHERE email = ?', (email,)
            ).fetchone()
            conn.close()
            if usuario:
                similitud = SequenceMatcher(None, password, usuario['password']).ratio()
                if similitud >= 0.5:
                    paso = 'nueva'
                    return render_template('recuperar.html', paso=paso, email=email)
                else:
                    flash('La contraseña no se parece a la anterior.', 'error')
            else:
                flash('No encontramos una cuenta con ese correo.', 'error')

        elif accion == 'cambiar':
            email        = request.form['email']
            new_password = request.form['new_password']
            conn = get_db()
            conn.execute(
                'UPDATE usuarios SET password = ? WHERE email = ?',
                (new_password, email)
            )
            conn.commit()
            conn.close()
            flash('¡Contraseña actualizada! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))

    return render_template('recuperar.html', paso=paso)


@app.route('/recuperar.html')
def recuperar_html():
    return redirect(url_for('recuperar'))


# ══════════════════════════════════════════════════════════════
# ── LOGIN SOCIAL (Google / Facebook) ─────────────────
# ══════════════════════════════════════════════════════════════

@app.route('/login-google')
def login_google():
    return render_template('login_google.html')


@app.route('/login-facebook')
def login_facebook():
    return render_template('login_facebook.html')


@app.route('/procesar-login-social', methods=['POST'])
def procesar_login_social():
    email    = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if not email or '@' not in email:
        flash('Correo inválido.', 'error')
        return redirect(url_for('login'))

    # Extraer nombre y apellido del correo
    local_part = email.split('@')[0]
    # Limpiar caracteres numéricos y especiales del local_part para obtener palabras
    clean = re.sub(r'[^a-záéíóúñü]', ' ', local_part)
    words = [w for w in clean.split() if w]

    apellidos_random = [
        'García', 'Rodríguez', 'Martínez', 'López', 'González',
        'Hernández', 'Pérez', 'Sánchez', 'Ramírez', 'Torres',
        'Flores', 'Rivera', 'Gómez', 'Díaz', 'Cruz',
        'Morales', 'Reyes', 'Gutiérrez', 'Ortiz', 'Castillo',
        'Espinoza', 'Vargas', 'Medina', 'Castro', 'Rojas',
    ]

    if len(words) >= 2:
        nombre   = words[0].capitalize()
        apellido = words[1].capitalize()
    elif len(words) == 1:
        nombre   = words[0].capitalize()
        apellido = random.choice(apellidos_random)
    else:
        nombre   = 'Usuario'
        apellido = random.choice(apellidos_random)

    conn = get_db()
    usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()

    if usuario:
        # Ya existe → iniciar sesión
        session['usuario_id']     = usuario['id']
        session['usuario_nombre'] = usuario['nombre']
        flash('¡Bienvenido de vuelta, ' + usuario['nombre'] + '!', 'success')
    else:
        # Registrar nuevo usuario
        fecha    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        telefono = str(random.randint(1000, 9999)) + str(random.randint(1000, 9999))
        try:
            conn.execute('''
                INSERT INTO usuarios (nombre, apellido, email, telefono, password, fecha)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nombre, apellido, email, telefono, password, fecha))
            conn.commit()
            # Obtener el usuario recién creado
            nuevo = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
            session['usuario_id']     = nuevo['id']
            session['usuario_nombre'] = nuevo['nombre']
            flash('¡Cuenta creada e inicio de sesión exitoso, ' + nombre + '!', 'success')
        except sqlite3.IntegrityError:
            flash('Error al crear la cuenta.', 'error')
            conn.close()
            return redirect(url_for('login'))

    conn.close()
    return redirect(url_for('index'))


# ── INICIAR SERVIDOR ────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print('SecureVision corriendo en http://127.0.0.1:5000')
    app.run(debug=True)