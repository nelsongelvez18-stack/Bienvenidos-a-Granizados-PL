import base64
import hmac
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import random

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client
import bcrypt

st.set_page_config(page_title="Granizados PL - Punto de Venta", page_icon="🍧", layout="wide")

# ---------------------------------------------------------------- CONFIGURACIÓN GENERAL
TZ = timezone(timedelta(hours=-5))  # Colombia
UMBRAL_BAJO = 5
LOGO = Path("logo_pl.png")

CLAVE_ACCESO = "Granizadospl2026**"

PRECIOS_VENTA = {"SIN ALCOHOL": 13000, "CON ALCOHOL": 15000, "CREMOSOS": 15000}
COLORES = {"SIN ALCOHOL": "#10b981", "CON ALCOHOL": "#ec4899", "CREMOSOS": "#f59e0b"}
METODOS_PAGO = ["Efectivo", "Transferencia Nequi / Billeteras virtuales"]
SABORES = {
    "SIN ALCOHOL": ["Bombombum", "Chicle", "Frutos Rojos", "Limonada Cerezada", "Limonada de Coco", "Limonada de Sandía", "Mango Biche", "Manzana Rosada", "Manzana Verde", "Maracumango", "Maracululo", "Maracupiña", "Mora Azul", "Uva"],
    "CON ALCOHOL": ["Agave Ice", "Andromeda Ice", "Bon Bon Bum Ice", "Candy Ice", "Cherryboom Ice", "Cosmico Ice", "Estelar Ice", "Fresa Salvaje Ice", "Fourloko Ice", "Interestelar Ice", "Luxury Ice", "Mango Explosivo Ice", "Miami Ice", "Monaco Ice", "Mora Azul Ice", "Nebula Ice", "Orion Ice", "Smirnoff Lulo Ice", "Smirnoff Limon Ice", "Tropical Caribeña Ice", "Velvet Ice"],
    "CREMOSOS": ["Bayleys", "Coco Loco", "Piña Colada"],
}
EXTRAS = ["Minichicles (porción)", "Goma bandera (porción)", "Bombón (porción)", "Sal pimienta (porción)", "Bolas de chicle (porción)", "Goma gusano (porción)", "Goma splash (porción)", "Barquillo (und)"]

FRASES_MOTIVADORAS = [
    "🚀 ¡Hoy es un gran día para romper récords de ventas en Granizados PL!",
    "🍧 Cada granizado que preparas dibuja una sonrisa en tus clientes.",
    "💡 El éxito es la suma de pequeños esfuerzos repetidos día tras día. ¡A darla toda!",
    "⭐ ¡Tu energía y actitud positiva son el mejor ingrediente de la casa!",
    "🌟 Construye el negocio de tus sueños con constancia, pasión y el mejor sabor.",
    "🎯 ¡A por todas! Hoy tu esfuerzo se convertirá en grandes resultados.",
    "🔥 Calidad, rapidez y una sonrisa: la fórmula secreta del éxito en Túquerres."
]


def clave_sabor(sabor):
    return "Sabor Maracupíña" if sabor == "Maracupiña" else f"Sabor {sabor}"


INVENTARIO_BASE = {"Vaso 12 oz (und)": 0, "Pitillos (und)": 0, "Bolsa de papel (und)": 0}
INVENTARIO_BASE.update({e: 0 for e in EXTRAS})
for _sabores in SABORES.values():
    for _s in _sabores:
        INVENTARIO_BASE[clave_sabor(_s)] = 0

PRODUCTOS_ELIMINADOS = {"Sachet 12 oz (und)", "Aguardiente (copa)", "Baileys (copa)", "Champaña (copa)", "Ron Blanco (copa)", "Tequila (copa)", "Vodka (copa)", "Whisky (copa)", "Lluvia de chocolate (porción)"}


# ---------------------------------------------------------------- SUPABASE Y PERSISTENCIA REAL
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", st.secrets.get("supabase", {}).get("url", ""))
    key = st.secrets.get("SUPABASE_KEY", st.secrets.get("supabase", {}).get("key", ""))
    if not url or not key:
        st.error("⚠️ Falta configurar SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit.")
        st.stop()
    return create_client(url.strip(), key.strip())


supabase = init_supabase()


def ahora():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def hoy():
    return datetime.now(TZ).date()


def dinero(valor):
    return f"${int(round(valor)):,.0f}".replace(",", ".")


def dinero_html(valor):
    return dinero(valor).replace("$", "&#36;")


def dinero_md(valor):
    return dinero(valor).replace("$", "\\$")


def suma(items, campo="Total"):
    return sum(int(i.get(campo, 0)) for i in items)


# FUNCIONES DE CARGAPERSISTENTE DESDE SUPABASE AL INICIAR
def cargar_inventario_supabase():
    try:
        res = supabase.table("inventario").select("*").execute()
        inventario = dict(INVENTARIO_BASE)
        if res.data:
            for row in res.data:
                nombre = row.get("nombre")
                if nombre and nombre not in PRODUCTOS_ELIMINADOS:
                    inventario[nombre] = int(row.get("stock", 0))
        return inventario
    except Exception:
        return dict(INVENTARIO_BASE)


def guardar_stock_supabase(producto, stock):
    try:
        res = supabase.table("inventario").select("*").eq("nombre", producto).execute()
        if res.data:
            supabase.table("inventario").update({"stock": int(stock)}).eq("nombre", producto).execute()
        else:
            supabase.table("inventario").insert({"nombre": producto, "stock": int(stock), "precio": 0, "costo": 0}).execute()
    except Exception as e:
        st.error(f"Error sincronizando stock con Supabase: {e}")


def cargar_tabla_supabase(nombre_tabla):
    try:
        res = supabase.table(nombre_tabla).select("*").execute()
        if res.data:
            # Mapeo universal de campos para unificar minusculas y mayusculas
            registros = []
            for row in res.data:
                item = dict(row)
                item["ID"] = str(item.get("ID", item.get("id", item.get("venta_id", ""))))
                item["Fecha"] = str(item.get("Fecha", item.get("fecha", "")))
                item["Sabor"] = str(item.get("Sabor", item.get("sabor", "")))
                item["Categoría"] = str(item.get("Categoría", item.get("categoria", "")))
                item["Total"] = int(item.get("Total", item.get("total", item.get("precio", 0))))
                item["Cantidad"] = int(item.get("Cantidad", item.get("cantidad", 1)))
                item["Medio de pago"] = str(item.get("Medio de pago", item.get("medio_pago", item.get("metodo_pago", "Efectivo"))))
                item["Estado"] = str(item.get("Estado", item.get("estado", "Vigente")))
                item["Valor"] = float(item.get("Valor", item.get("valor", item.get("monto", item.get("costo_total", 0)))))
                item["Concepto"] = str(item.get("Concepto", item.get("concepto", item.get("descripcion", ""))))
                item["Consumos"] = item.get("Consumos", item.get("consumos", "{}"))
                registros.append(item)
            return registros
        return []
    except Exception as e:
        st.error(f"Error consultando {nombre_tabla}: {e}")
        return []


def guardar_registro_supabase(nombre_tabla, data):
    try:
        supabase.table(nombre_tabla).insert(data).execute()
    except Exception as e:
        st.error(f"Error guardando en {nombre_tabla}: {e}")


def actualizar_registro_supabase(nombre_tabla, data_update, match_col, match_val):
    try:
        supabase.table(nombre_tabla).update(data_update).eq(match_col, match_val).execute()
    except Exception as e:
        st.error(f"Error actualizando {nombre_tabla}: {e}")


# INICIALIZACIÓN PERSISTENTE DE DATOS EN CADA SESIÓN
def sincronizar_todo_desde_supabase():
    st.session_state.inventario = cargar_inventario_supabase()
    st.session_state.ventas = cargar_tabla_supabase("ventas")
    st.session_state.movimientos = cargar_tabla_supabase("movimientos")
    st.session_state.gastos = cargar_tabla_supabase("gastos")
    st.session_state.anulaciones = cargar_tabla_supabase("anulaciones")
    st.session_state.cierres_caja = cargar_tabla_supabase("cierres_caja")
    st.session_state.compras = cargar_tabla_supabase("compras")


if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "inventario" not in st.session_state or not st.session_state.get("sincronizado_db"):
    sincronizar_todo_desde_supabase()
    st.session_state["sincronizado_db"] = True

if "carrito" not in st.session_state:
    st.session_state.carrito = []


def avisar(mensaje, icono=None):
    st.session_state["_aviso"] = (mensaje, icono)
    st.rerun()


def verificar_acceso():
    if st.session_state.get("acceso_ok"):
        return

    CSS_LOGIN = """
    .login-container { 
        max-width: 420px; 
        margin: 100px auto; 
        padding: 35px; 
        background: #ffffff; 
        border: 1px solid #e2e8f0; 
        border-radius: 24px; 
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05); 
        text-align: center; 
    }
    """
    st.markdown(f"<style>{CSS_LOGIN}</style>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.title("🍧 Granizados PL")
        st.caption("Acceso Seguro - Sistema POS Cloud")
        intento = st.text_input("Contraseña de acceso", type="password")
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            if hmac.compare_digest(str(intento), str(CLAVE_ACCESO)):
                st.session_state["acceso_ok"] = True
                sincronizar_todo_desde_supabase()
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


verificar_acceso()

if "_aviso" in st.session_state:
    _msg, _ico = st.session_state.pop("_aviso")
    st.toast(_msg, icon=_ico)


# ---------------------------------------------------------------- LÓGICA DE NEGOCIO
def registrar_movimiento(producto, tipo, cantidad, detalle="", referencia=""):
    mov = {"Fecha": ahora(), "Producto": producto, "Tipo": tipo, "Cantidad": int(cantidad), "Detalle": detalle, "Referencia": referencia}
    st.session_state.movimientos.append(mov)
    guardar_registro_supabase("movimientos", mov)


def registrar_anulacion(tipo, identificador, detalle):
    anul = {"Fecha": ahora(), "Tipo": tipo, "ID": str(identificador), "Detalle": detalle}
    st.session_state.anulaciones.append(anul)
    guardar_registro_supabase("anulaciones", anul)


def ventas_vigentes(desde=None, hasta=None):
    resultado = []
    for v in st.session_state.ventas:
        if v.get("Estado", "Vigente") != "Vigente":
            continue
        f = str(v.get("Fecha", ""))[:10]
        if (desde and f < str(desde)) or (hasta and f > str(hasta)):
            continue
        resultado.append(v)
    return resultado


def gastos_vigentes(fecha=None):
    return [g for g in st.session_state.gastos if not g.get("Anulado", False) and (fecha is None or str(g.get("Fecha", ""))[:10] == str(fecha))]


def resumen_dia(fecha):
    f = str(fecha)
    ventas, gastos = ventas_vigentes(f, f), gastos_vigentes(f)
    efectivo = suma([v for v in ventas if v.get("Medio de pago") == "Efectivo"])
    transf = suma([v for v in ventas if v.get("Medio de pago") != "Efectivo"])
    gastos_total = sum(float(g.get("Valor", 0)) for g in gastos)
    gastos_efectivo = sum(float(g.get("Valor", 0)) for g in gastos if g.get("Medio de pago") == "Efectivo")
    return {"ventas": ventas, "gastos": gastos, "efectivo": efectivo, "transferencias": transf,
            "gastos_total": gastos_total, "caja_efectivo": efectivo - gastos_efectivo,
            "neto": efectivo + transf - gastos_total, "unidades": suma(ventas, "Cantidad")}


def consumos_venta(sabor, presentacion, incluir_bolsa):
    consumos = {
        clave_sabor(sabor): 1,
        "Pitillos (und)": 1
    }
    if incluir_bolsa:
        consumos["Bolsa de papel (und)"] = 1
    if presentacion == "Vaso 12 oz":
        consumos["Vaso 12 oz (und)"] = 1
    for extra in EXTRAS:
        consumos[extra] = 1
    return consumos


# ---------------------------------------------------------------- ESTILOS Y COMPONENTES VISUALES
CSS_GENERAL = (
    "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');"
    "html, body, [class*='css'] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; }"
    ".block-container { padding-top: 1.5rem; max-width: 1250px; }"
    ".banner { background: linear-gradient(135deg, #fef08a 0%, #fde047 100%); border: 1px solid #facc15; border-radius: 28px; padding: 24px 36px; display: flex; align-items: center; gap: 24px; color: #713f12; margin-bottom: 24px; box-shadow: 0 10px 30px -5px rgba(234, 179, 8, 0.2); position: relative; overflow: visible; }"
    "@keyframes floatAnim { 0%, 100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(-8px) rotate(1.5deg); } }"
    "@keyframes blinkAnim { 0%, 90%, 100% { transform: scaleY(1); } 95% { transform: scaleY(0.1); } }"
    "@keyframes bubbleAnim { 0% { transform: translateY(0) scale(0.6); opacity: 0.8; } 100% { transform: translateY(-35px) scale(1.1); opacity: 0; } }"
    ".header-media-wrapper { display: flex; align-items: center; gap: 16px; margin-top: -15px; }"
    ".banner-logo-container { animation: floatAnim 4s ease-in-out infinite; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.15)); }"
    ".banner-logo-container img { border-radius: 22px; width: 110px; height: 110px; object-fit: cover; border: 3px solid #ffffff; }"
    ".avatar-container { position: relative; width: 105px; height: 115px; animation: floatAnim 3.5s ease-in-out infinite 0.5s; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.12)); }"
    ".avatar-bubble { position: absolute; background: rgba(255, 255, 255, 0.7); border-radius: 50%; animation: bubbleAnim 2.5s infinite ease-in; }"
    ".avatar-eye { animation: blinkAnim 4s infinite; transform-origin: center; }"
    ".banner-texto { flex: 1; }"
    ".banner-titulo { font: 800 38px/1.1 'Outfit', sans-serif; color: #713f12; letter-spacing: -0.5px; }"
    ".banner-sub { font-size: 16px; font-weight: 600; color: #854d0e; margin-top: 6px; }"
    ".banner-ventas { background: #ffffff; border: 2px solid #ca8a04; color: #713f12; border-radius: 20px; padding: 18px 28px; min-width: 240px; text-align: right; box-shadow: 0 10px 25px rgba(202, 138, 4, 0.15); }"
    ".banner-ventas span { display: block; font-size: 12px; color: #854d0e; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 700; }"
    ".banner-ventas b { display: block; font: 800 32px 'Outfit', sans-serif; color: #a16207; margin-top: 4px; }"
    ".cobro { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border: 2px solid #6366f1; border-radius: 24px; padding: 24px 28px; color: #1e293b; margin-bottom: 14px; box-shadow: 0 15px 30px -5px rgba(99, 102, 241, 0.12); }"
    ".cobro span { display: block; font-size: 15px; color: #64748b; font-weight: 600; }"
    ".cobro b { display: block; font: 800 48px 'Outfit', sans-serif; line-height: 1.1; color: #0f172a; }"
    ".tile { padding: 18px 22px; border-radius: 20px; color: #ffffff; margin-bottom: 14px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); }"
    ".tile span { display: block; font-size: 12px; font-weight: 700; text-transform: uppercase; opacity: 0.9; }"
    ".tile b { display: block; font: 700 28px 'Outfit', sans-serif; margin-top: 4px; }"
    ".chip-cat { display: inline-block; border-radius: 999px; padding: 6px 18px; font-weight: 700; color: #ffffff; font-size: 14px; }"
    "div[data-testid='stMetric'] { background: #ffffff; border: 1px solid #e2e8f0; padding: 18px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }"
)
st.markdown("<style>" + CSS_GENERAL + "</style>", unsafe_allow_html=True)


def tile(etiqueta, valor, color):
    return f'<div class="tile" style="background:{color}"><span>{etiqueta}</span><b>{valor}</b></div>'


def avatar_svg_html():
    return (
        '<div class="avatar-container">'
        '<div class="avatar-bubble" style="width:10px; height:10px; left:20%; bottom:20%; animation-delay:0s;"></div>'
        '<div class="avatar-bubble" style="width:8px; height:8px; left:75%; bottom:25%; animation-delay:0.8s;"></div>'
        '<div class="avatar-bubble" style="width:12px; height:12px; left:45%; bottom:15%; animation-delay:1.5s;"></div>'
        '<svg viewBox="0 0 120 130" width="100%" height="100%">'
        '<defs>'
        '<linearGradient id="cupGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#ec4899" />'
        '<stop offset="50%" stop-color="#f59e0b" />'
        '<stop offset="100%" stop-color="#10b981" />'
        '</linearGradient>'
        '<linearGradient id="strawGrad" x1="0%" y1="0%" x2="100%" y2="0%">'
        '<stop offset="0%" stop-color="#3b82f6" />'
        '<stop offset="100%" stop-color="#60a5fa" />'
        '</linearGradient>'
        '</defs>'
        '<rect x="68" y="5" width="10" height="45" rx="5" fill="url(#strawGrad)" transform="rotate(15 68 5)"/>'
        '<path d="M 25 35 Q 60 15 95 35 Z" fill="#ffffff" opacity="0.9"/>'
        '<path d="M 22 38 L 32 110 Q 60 122 88 110 L 98 38 Z" fill="url(#cupGrad)" stroke="#ffffff" stroke-width="3"/>'
        '<g class="avatar-eye"><circle cx="48" cy="65" r="5" fill="#1e293b"/><circle cx="50" cy="63" r="2" fill="#ffffff"/></g>'
        '<g class="avatar-eye"><circle cx="72" cy="65" r="5" fill="#1e293b"/><circle cx="74" cy="63" r="2" fill="#ffffff"/></g>'
        '<path d="M 52 76 Q 60 84 68 76" fill="none" stroke="#1e293b" stroke-width="3" stroke-linecap="round"/>'
        '</svg>'
        '</div>'
    )


def header_media_html():
    if LOGO.exists():
        b64 = base64.b64encode(LOGO.read_bytes()).decode()
        logo_img = f'<img src="data:image/png;base64,{b64}" alt="Logo Granizados PL">'
    else:
        logo_img = '<div style="font-size:40px;">🍧</div>'
    return f'<div class="header-media-wrapper"><div class="banner-logo-container">{logo_img}</div>{avatar_svg_html()}</div>'


def encabezado():
    r_hoy = resumen_dia(hoy())
    total_hoy = r_hoy["efectivo"] + r_hoy["transferencias"]
    st.markdown(
        f'<div class="banner">{header_media_html()}<div class="banner-texto">'
        '<div class="banner-titulo">Granizados PL</div>'
        '<div class="banner-sub">Sistema POS Cloud Persistente · Túquerres, Nariño</div></div>'
        f'<div class="banner-ventas"><span>Ventas de hoy</span><b>{dinero_html(total_hoy)}</b></div></div>',
        unsafe_allow_html=True)

    frases_json = json.dumps(FRASES_MOTIVADORAS)
    components.html(f"""
        <div style="font-family: 'Plus Jakarta Sans', sans-serif; background: linear-gradient(135deg, #fef9c3 0%, #fef08a 100%); border: 1px solid #fde047; border-radius: 16px; padding: 14px 20px; color: #713f12; font-weight: 600; font-size: 15px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 12px rgba(234, 179, 8, 0.1); position: relative; overflow: hidden;">
            <div id="frase-texto" style="transition: opacity 0.5s ease-in-out;">Cargando motivación...</div>
            <div style="position: absolute; bottom: 0; left: 0; height: 3px; background: #ca8a04; width: 100%; transition: width 60s linear;" id="barra-progreso"></div>
        </div>
        <script>
            const frases = {frases_json};
            let index = Math.floor(Math.random() * frases.length);
            const el = document.getElementById("frase-texto");
            const barra = document.getElementById("barra-progreso");

            function actualizarFrase() {{
                el.style.opacity = 0;
                setTimeout(() => {{
                    el.innerText = frases[index];
                    el.style.opacity = 1;
                    index = (index + 1) % frases.length;
                }}, 500);

                barra.style.transition = 'none';
                barra.style.width = '0%';
                setTimeout(() => {{
                    barra.style.transition = 'width 60s linear';
                    barra.style.width = '100%';
                }}, 50);
            }}

            actualizarFrase();
            setInterval(actualizarFrase, 60000);
        </script>
    """, height=75)


encabezado()

# ---------------------------------------------------------------- PESTAÑAS PRINCIPALES
tab_ventas, tab_inventario, tab_historial, tab_caja, tab_reportes, tab_cierre = st.tabs(
    ["🛒 Ventas", "📦 Inventario", "🧾 Historial", "💵 Caja y compras", "📊 Reportes", "🔒 Cerrar caja"])

# 1. VENTAS
with tab_ventas:
    col_form, col_cobro = st.columns([2, 1], gap="large")

    with col_form:
        with st.container(border=True):
            st.subheader("1. Agrega los granizados del cliente")
            categoria = st.segmented_control("Categoría", list(SABORES), default="SIN ALCOHOL", key="cat_v")
            st.markdown(f'<span class="chip-cat" style="background:{COLORES[categoria]}">{categoria.title()}</span>', unsafe_allow_html=True)
            sabores = list(dict.fromkeys(SABORES[categoria]))
            sabor = st.pills("Sabor", sabores, default=sabores[0], key=f"sab_v_{categoria}")
            c1, c2 = st.columns(2)
            presentacion = c1.segmented_control("Presentación", ["Vaso 12 oz", "Sachet 12 oz"], default="Vaso 12 oz", key="pres_v")
            cantidad = c2.number_input("Cantidad", min_value=1, max_value=50, value=1, step=1, key="cant_v")
            
            precio_unitario = PRECIOS_VENTA[categoria]
            if st.button("➕ Agregar al pedido", use_container_width=True):
                st.session_state.carrito.append({
                    "Categoría": categoria, "Sabor": sabor, "Presentación": presentacion,
                    "Cantidad": int(cantidad), "Precio unitario": precio_unitario, "Total": precio_unitario * int(cantidad)
                })
                st.rerun()

    carrito = st.session_state.carrito
    total = sum(l["Total"] for l in carrito)

    with col_cobro:
        with st.container(border=True):
            st.markdown("**Pedido actual**")
            for i, l in enumerate(carrito):
                st.markdown(f"{l['Cantidad']} × **{l['Sabor']}** ({l['Categoría']}) - {dinero_md(l['Total'])}")
            
        metodo_pago = st.segmented_control("Medio de pago", METODOS_PAGO, default=METODOS_PAGO[0], key="pago_v")
        st.markdown(f'<div class="cobro"><span>Total a cobrar</span><b>{dinero_html(total)}</b></div>', unsafe_allow_html=True)
        
        guardar_venta = st.button("Registrar Venta", type="primary", use_container_width=True, disabled=not carrito)
        
        if guardar_venta and carrito:
            pedido_id = "V-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
            for n, l in enumerate(carrito, 1):
                cs = clave_sabor(l["Sabor"])
                nuevo_stock = max(0, int(st.session_state.inventario.get(cs, 0)) - l["Cantidad"])
                st.session_state.inventario[cs] = nuevo_stock
                guardar_stock_supabase(cs, nuevo_stock)
                
                if l["Presentación"] == "Vaso 12 oz":
                    v_stock = max(0, int(st.session_state.inventario.get("Vaso 12 oz (und)", 0)) - l["Cantidad"])
                    st.session_state.inventario["Vaso 12 oz (und)"] = v_stock
                    guardar_stock_supabase("Vaso 12 oz (und)", v_stock)

                cons = consumos_venta(l["Sabor"], l["Presentación"], True)

                venta_data = {
                    "ID": f"{pedido_id}-{n}",
                    "venta_id": f"{pedido_id}-{n}",
                    "Categoría": l["Categoría"], "categoria": l["Categoría"],
                    "Sabor": l["Sabor"], "sabor": l["Sabor"],
                    "Presentación": l["Presentación"], "presentacion": l["Presentación"],
                    "Cantidad": l["Cantidad"], "cantidad": l["Cantidad"],
                    "Precio unitario": l["Precio unitario"], "precio_unitario": l["Precio unitario"],
                    "Total": l["Total"], "total": l["Total"], "precio": l["Total"],
                    "Medio de pago": metodo_pago, "medio_pago": metodo_pago, "metodo_pago": metodo_pago,
                    "Consumos": json.dumps(cons), "consumos": json.dumps(cons),
                    "Estado": "Vigente", "estado": "Vigente",
                    "Fecha": ahora(), "fecha": ahora()
                }
                guardar_registro_supabase("ventas", venta_data)
                st.session_state.ventas.append(venta_data)
                
            st.session_state.carrito = []
            st.balloons()
            avisar(f"¡Venta guardada exitosamente en Supabase por {dinero(total)}!", "🎉")

# 2. INVENTARIO
with tab_inventario:
    st.header("Inventario Real en Tiempo Real")
    if st.button("🔄 Sincronizar desde Supabase"):
        sincronizar_todo_desde_supabase()
        st.rerun()

    df_inv = pd.DataFrame([{"Producto / Sabor": k, "Stock Disponible": v} for k, v in st.session_state.inventario.items()])
    st.dataframe(df_inv, use_container_width=True, height=450)

# 3. HISTORIAL
with tab_historial:
    st.header("Historial de Ventas")
    v_vig = ventas_vigentes()
    if v_vig:
        df_hist = pd.DataFrame(v_vig)[::-1]
        cols_mostrar = [c for c in ["Fecha", "Categoría", "Sabor", "Cantidad", "Total", "Medio de pago", "Estado"] if c in df_hist.columns]
        st.dataframe(df_hist[cols_mostrar], use_container_width=True)
    else:
        st.info("No hay ventas registradas aún.")

# 4. CAJA Y COMPRAS
with tab_caja:
    st.header("Registrar Compras e Insumos")
    col1, col2 = st.columns(2)
    with col1:
        with st.form("form_compra"):
            item_compra = st.selectbox("Producto a Comprar", list(INVENTARIO_BASE.keys()))
            cant_compra = st.number_input("Cantidad que Ingresa", min_value=1, value=10)
            costo_total = st.number_input("Costo Total Invertido ($)", min_value=0, value=0)
            btn_compra = st.form_submit_button("📥 Guardar e Incrementar Inventario", type="primary")

        if btn_compra:
            compra_data = {
                "Producto": item_compra, "producto": item_compra,
                "Cantidad": int(cant_compra), "cantidad": int(cant_compra),
                "Costo total": float(costo_total), "costo_total": float(costo_total),
                "Concepto": f"Ingreso de {cant_compra} und de {item_compra}", "descripcion": f"Ingreso de {cant_compra} und de {item_compra}",
                "Valor": float(costo_total), "monto": float(costo_total),
                "Fecha": ahora(), "fecha": ahora()
            }
            guardar_registro_supabase("compras", compra_data)
            st.session_state.compras.append(compra_data)

            nuevo_s = int(st.session_state.inventario.get(item_compra, 0)) + int(cant_compra)
            st.session_state.inventario[item_compra] = nuevo_s
            guardar_stock_supabase(item_compra, nuevo_s)

            avisar(f"Se agregaron {cant_compra} und a '{item_compra}' y se guardó en Supabase.", "📦")

# 5. REPORTES Y METRICAS
with tab_reportes:
    st.header("📊 Reportes y Métricas por Nombre de Sabor")
    v_reporte = ventas_vigentes()
    if v_reporte:
        df_v = pd.DataFrame(v_reporte)
        if "Sabor" in df_v.columns and not df_v.empty:
            cat_filtro = st.selectbox("Filtrar por Categoría:", ["Todas"] + list(SABORES.keys()))
            if cat_filtro != "Todas":
                df_v = df_v[df_v["Categoría"] == cat_filtro]

            df_sabores = df_v.groupby(["Categoría", "Sabor"]).agg(
                Cantidad_Vendida=("Cantidad", "sum"),
                Total_Recaudado=("Total", "sum")
            ).reset_index().sort_values(by="Cantidad_Vendida", ascending=False)

            st.dataframe(df_sabores, use_container_width=True)
            
            if not df_sabores.empty:
                mejor = df_sabores.iloc[0]
                peor = df_sabores.iloc[-1]
                
                c1, c2 = st.columns(2)
                c1.success(f"🔥 **Sabor Más Vendido:** {mejor['Sabor']} ({mejor['Cantidad_Vendida']} und)")
                c2.warning(f"⚠️ **Sabor Con Menor Salida:** {peor['Sabor']} ({peor['Cantidad_Vendida']} und)")
        else:
            st.info("Aún no hay ventas suficientes para mostrar métricas de sabores.")
    else:
        st.info("Aún no hay datos de ventas registrados.")

# 6. CIERRE DE CAJA
with tab_cierre:
    st.header("🔒 Cierre de Caja Diario")
    fecha_cierre = st.date_input("Fecha de cierre", value=hoy())
    r_cierre = resumen_dia(fecha_cierre)
    
    st.metric("Total Recaudado hoy", dinero(r_cierre["efectivo"] + r_cierre["transferencias"]))
    if st.button("Guardar Cierre"):
        cierre_data = {
            "Fecha cierre": str(fecha_cierre),
            "Ventas efectivo": r_cierre["efectivo"],
            "Ventas transferencias": r_cierre["transferencias"],
            "Caja efectivo esperada": r_cierre["caja_efectivo"],
            "Fecha registro": ahora()
        }
        guardar_registro_supabase("cierres_caja", cierre_data)
        st.session_state.cierres_caja.append(cierre_data)
        st.success("¡Cierre de caja guardado con éxito en Supabase!")
