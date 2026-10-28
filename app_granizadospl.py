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

# ---------------------------------------------------------------- CONFIGURACIÓN
TZ = timezone(timedelta(hours=-5))  # Colombia
UMBRAL_BAJO = 5
LOGO = Path("logo_pl.png")

# CONTRASEÑA DIRECTA DEL SISTEMA
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


# ---------------------------------------------------------------------- SUPABASE & UTILS
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
    return sum(int(i.get(campo, i.get(campo.lower(), 0))) for i in items)


# ------------------------------------------------------------------------ CARGA DIRECTA Y PERSISTENTE
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
            registros = []
            for row in res.data:
                item = dict(row)
                item["ID"] = str(item.get("ID", item.get("id", item.get("venta_id", ""))))
                item["Fecha"] = str(item.get("Fecha", item.get("fecha", "")))
                item["Cliente"] = str(item.get("Cliente", item.get("cliente", "Cliente general")))
                item["Sabor"] = str(item.get("Sabor", item.get("sabor", "")))
                item["Categoría"] = str(item.get("Categoría", item.get("categoria", "")))
                item["Presentación"] = str(item.get("Presentación", item.get("presentacion", "Vaso 12 oz")))
                item["Total"] = int(float(item.get("Total", item.get("total", item.get("precio", 0)))))
                item["Precio unitario"] = int(float(item.get("Precio unitario", item.get("precio_unitario", 0))))
                item["Cantidad"] = int(float(item.get("Cantidad", item.get("cantidad", 1))))
                item["Medio de pago"] = str(item.get("Medio de pago", item.get("medio_pago", item.get("metodo_pago", "Efectivo"))))
                item["Estado"] = str(item.get("Estado", item.get("estado", "Vigente")))
                item["Valor"] = float(item.get("Valor", item.get("valor", item.get("monto", item.get("costo_total", 0)))))
                item["Concepto"] = str(item.get("Concepto", item.get("concepto", item.get("descripcion", ""))))
                item["Consumos"] = item.get("Consumos", item.get("consumos", "{}"))
                registros.append(item)
            return registros
        return []
    except Exception:
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


# SINCRONIZACIÓN OBLIGATORIA EN CADA CARGA DE SESIÓN
st.session_state.inventario = cargar_inventario_supabase()
st.session_state.ventas = cargar_tabla_supabase("ventas")
st.session_state.movimientos = cargar_tabla_supabase("movimientos")
st.session_state.gastos = cargar_tabla_supabase("gastos")
st.session_state.anulaciones = cargar_tabla_supabase("anulaciones")
st.session_state.cierres_caja = cargar_tabla_supabase("cierres_caja")
st.session_state.compras = cargar_tabla_supabase("compras")

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
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.04); 
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
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


verificar_acceso()

if "_aviso" in st.session_state:
    _msg, _ico = st.session_state.pop("_aviso")
    st.toast(_msg, icon=_ico)


# ------------------------------------------------------------------- LÓGICA DE NEGOCIO ORIGINAL
def registrar_movimiento(producto, tipo, cantidad, detalle="", referencia=""):
    mov = {
        "fecha": ahora(),
        "Fecha": ahora(),
        "producto": producto,
        "Producto": producto,
        "tipo": tipo,
        "Tipo": tipo,
        "cantidad": int(cantidad),
        "Cantidad": int(cantidad),
        "detalle": detalle,
        "Detalle": detalle,
        "referencia": referencia,
        "Referencia": referencia
    }
    st.session_state.movimientos.append(mov)
    guardar_registro_supabase("movimientos", mov)


def registrar_anulacion(tipo, identificador, detalle):
    anul = {
        "fecha": ahora(),
        "Fecha": ahora(),
        "tipo": tipo,
        "Tipo": tipo,
        "id": str(identificador),
        "ID": str(identificador),
        "detalle": detalle,
        "Detalle": detalle
    }
    st.session_state.anulaciones.append(anul)
    guardar_registro_supabase("anulaciones", anul)


def ventas_vigentes(desde=None, hasta=None):
    resultado = []
    for v in st.session_state.ventas:
        if v.get("Estado", v.get("estado", "Vigente")) != "Vigente":
            continue
        f = str(v.get("Fecha", v.get("fecha", "")))[:10]
        if (desde and f < str(desde)) or (hasta and f > str(hasta)):
            continue
        resultado.append(v)
    return resultado


def compras_vigentes():
    return [c for c in st.session_state.compras if c.get("Estado", c.get("estado", "Vigente")) == "Vigente"]


def gastos_vigentes(fecha=None):
    return [g for g in st.session_state.gastos if not g.get("Anulado", g.get("anulado", False)) and (fecha is None or str(g.get("Fecha", g.get("fecha", "")))[:10] == str(fecha))]


def resumen_dia(fecha):
    f = str(fecha)
    ventas, gastos = ventas_vigentes(f, f), gastos_vigentes(f)
    efectivo = suma([v for v in ventas if v.get("Medio de pago", v.get("medio_pago", "")) == "Efectivo"])
    transf = suma([v for v in ventas if v.get("Medio de pago", v.get("medio_pago", "")) != "Efectivo"])
    gastos_total = suma(gastos, "Valor") if suma(gastos, "Valor") > 0 else suma(gastos, "valor")
    gastos_efectivo = suma([g for g in gastos if g.get("Medio de pago", g.get("medio_pago", "")) == "Efectivo"], "Valor")
    return {"ventas": ventas, "gastos": gastos, "efectivo": efectivo, "transferencias": transf,
            "gastos_total": gastos_total, "caja_efectivo": efectivo - gastos_efectivo,
            "neto": efectivo + transf - gastos_total, "unidades": suma(ventas, "Cantidad")}


def marcar_cierre_desactualizado(fecha):
    for c in st.session_state.cierres_caja:
        if c.get("Fecha cierre") == fecha:
            c["Desactualizado"] = True
            actualizar_registro_supabase("cierres_caja", {"Desactualizado": True}, "Fecha cierre", fecha)


def anular_venta(venta_id):
    venta = next((v for v in st.session_state.ventas if str(v.get("ID", v.get("id", ""))) == str(venta_id) and v.get("Estado", v.get("estado", "Vigente")) == "Vigente"), None)
    if not venta:
        return False, "No se encontró la venta vigente."
    consumos = venta.get("Consumos", venta.get("consumos", {}))
    if isinstance(consumos, str):
        try:
            consumos = json.loads(consumos)
        except Exception:
            consumos = {}
    for producto, cantidad in consumos.items():
        nuevo_stock = int(st.session_state.inventario.get(producto, 0)) + int(cantidad)
        st.session_state.inventario[producto] = nuevo_stock
        guardar_stock_supabase(producto, nuevo_stock)
        registrar_movimiento(producto, "Entrada por anulación de venta", cantidad, "Devolución de inventario", str(venta_id))
    venta["Estado"] = "Anulada"
    venta["Fecha anulación"] = ahora()
    actualizar_registro_supabase("ventas", {"Estado": "Anulada", "estado": "Anulada", "Fecha anulación": venta["Fecha anulación"]}, "ID", str(venta_id))
    marcar_cierre_desactualizado(str(venta.get("Fecha", ""))[:10])
    registrar_anulacion("Venta", str(venta_id), "Venta anulada")
    return True, "Venta anulada; el inventario consumido fue devuelto."


def ids_del_pedido(venta_id):
    vid = str(venta_id)
    if vid.count("-") < 2:
        return [vid]
    base = vid.rsplit("-", 1)[0]
    ids = [str(v.get("ID", v.get("id", ""))) for v in st.session_state.ventas
           if str(v.get("ID", v.get("id", ""))).startswith(base + "-") and v.get("Estado", v.get("estado", "Vigente")) == "Vigente"]
    return ids or [vid]


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


# --------------------------------------------------------------------- ESTILO CSS
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
    ".cobro p { margin: 8px 0 0; font-size: 14px; color: #6366f1; font-weight: 600; }"
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
        '<path d="M 28 42 L 36 104 Q 60 114 84 104 L 92 42 Z" fill="none" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>'
        '<g class="avatar-eye"><circle cx="48" cy="65" r="5" fill="#1e293b"/><circle cx="50" cy="63" r="2" fill="#ffffff"/></g>'
        '<g class="avatar-eye"><circle cx="72" cy="65" r="5" fill="#1e293b"/><circle cx="74" cy="63" r="2" fill="#ffffff"/></g>'
        '<path d="M 52 76 Q 60 84 68 76" fill="none" stroke="#1e293b" stroke-width="3" stroke-linecap="round"/>'
        '<circle cx="40" cy="73" r="4" fill="#f43f5e" opacity="0.5"/>'
        '<circle cx="80" cy="73" r="4" fill="#f43f5e" opacity="0.5"/>'
        '<polygon points="45,48 50,42 55,48" fill="#ffffff" opacity="0.8"/>'
        '<polygon points="65,52 70,45 75,52" fill="#ffffff" opacity="0.8"/>'
        '</svg>'
        '</div>'
    )


def header_media_html():
    if LOGO.exists():
        b64 = base64.b64encode(LOGO.read_bytes()).decode()
        logo_img = f'<img src="data:image/png;base64,{b64}" alt="Logo Granizados PL">'
    else:
        logo_img = '<div class="granizado-avatar-vaso"><span style="font-size:40px;">🍧</span></div>'

    return f'<div class="header-media-wrapper"><div class="banner-logo-container">{logo_img}</div>{avatar_svg_html()}</div>'


def encabezado():
    total_hoy = suma(ventas_vigentes(hoy(), hoy()))
    st.markdown(
        f'<div class="banner">{header_media_html()}<div class="banner-texto">'
        '<div class="banner-titulo">Granizados PL</div>'
        '<div class="banner-sub">Sistema de Punto de Venta Inteligente Cloud · Túquerres, Nariño</div></div>'
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


def alerta_inventario():
    bajo = [(p, int(q)) for p, q in st.session_state.inventario.items() if int(q) <= UMBRAL_BAJO and p not in EXTRAS]
    if not bajo:
        return
    agotados = sum(1 for _, q in bajo if q == 0)
    titulo = f"⚠️ {len(bajo)} productos con poco stock" + (f" · {agotados} agotados" if agotados else "")
    grupos = {"🍧 Sabores": [], "🥤 Insumos": []}
    for p, q in sorted(bajo, key=lambda x: (x[1], x[0])):
        grupos["🍧 Sabores" if p.startswith("Sabor ") else "🥤 Insumos"].append((p.removeprefix("Sabor "), q))
    with st.expander(titulo):
        for col, (nombre, items) in zip(st.columns(2), grupos.items()):
            with col:
                st.markdown(f"**{nombre}** ({len(items)})")
                if not items:
                    st.caption("Todo en orden")
                for p, q in items:
                    estado = "agotado" if q == 0 else f"{q} und"
                    st.markdown(f":{'red' if q == 0 else 'orange'}[●] {p}: **{estado}**")


def elegir(etiqueta, opciones, defecto, clave, **kw):
    valor = st.segmented_control(etiqueta, opciones, default=defecto, key=clave, **kw)
    if valor is None:
        return defecto
    return valor


CFG_DINERO = {c: st.column_config.NumberColumn(c, format="$ %d") for c in
              ["Total", "Precio unitario", "Costo unitario", "Valor", "Efectivo", "Transferencias", "Gastos", "Saldo neto estimado", "Caja en efectivo", "Efectivo contado", "Diferencia"]}


def tabla(df):
    st.dataframe(df, hide_index=True, use_container_width=True, column_config=CFG_DINERO)


def sin_consumos(registros):
    return pd.DataFrame([{k: v for k, v in r.items() if k != "Consumos"} for r in registros])


# ------------------------------------------------------------------------ APP
encabezado()
alerta_inventario()

tab_ventas, tab_inventario, tab_historial, tab_caja, tab_reportes, tab_cierre = st.tabs(
    ["🛒 Ventas", "📦 Inventario", "🧾 Historial", "💵 Caja y compras", "📊 Reportes", "🔒 Cerrar caja"])

# ---------------------------------------------------------------------- VENTAS
with tab_ventas:
    col_form, col_cobro = st.columns([2, 1], gap="large")

    with col_form:
        with st.container(border=True):
            st.subheader("1. Agrega los granizados del cliente")
            categoria = elegir("Categoría", list(SABORES), "SIN ALCOHOL", "categoria_venta",
                               format_func=lambda c: f"{c.title()} · {dinero(PRECIOS_VENTA[c])}")
            st.markdown(f'<span class="chip-cat" style="background:{COLORES[categoria]}">{categoria.title()}</span>', unsafe_allow_html=True)
            sabores = list(dict.fromkeys(SABORES[categoria]))
            sabor = st.pills("Sabor", sabores, default=sabores[0], key=f"sabor_venta_{categoria}")
            c1, c2 = st.columns(2)
            with c1:
                presentacion = elegir("Presentación", ["Vaso 12 oz", "Sachet 12 oz"], "Vaso 12 oz", "presentacion_venta")
            with c2:
                cantidad = st.number_input("Cantidad", min_value=1, max_value=50, value=1, step=1, key="cantidad_venta")
            precio_unitario = PRECIOS_VENTA[categoria]
            if sabor:
                st.caption(f"Esta línea: {int(cantidad)} × {sabor} = {dinero_md(precio_unitario * int(cantidad))}")
            if st.button("➕ Agregar al pedido", use_container_width=True, disabled=sabor is None, key="btn_agregar"):
                st.session_state.carrito.append({
                    "Categoría": categoria, "Sabor": sabor, "Presentación": presentacion,
                    "Cantidad": int(cantidad), "Precio unitario": precio_unitario})
                st.session_state.pop("cantidad_venta", None)
                st.rerun()

        with st.container(border=True):
            st.subheader("2. Datos del pedido")
            d1, d2 = st.columns(2)
            with d1:
                metodo_pago = elegir("Medio de pago", METODOS_PAGO, METODOS_PAGO[0], "pago_venta",
                                     format_func=lambda m: "Efectivo" if m == "Efectivo" else "Nequi / Billeteras")
            with d2:
                bolsas = st.number_input("Bolsas de papel del pedido", min_value=0, max_value=20, value=1, step=1, key="bolsas_venta")
            d3, d4 = st.columns(2)
            cliente = d3.text_input("Cliente (opcional)", key="cliente_venta")
            observacion = d4.text_input("Observación (opcional)", key="obs_venta")

    carrito = st.session_state.carrito
    total = sum(l["Cantidad"] * l["Precio unitario"] for l in carrito)
    unidades_pedido = sum(l["Cantidad"] for l in carrito)

    with col_cobro:
        with st.container(border=True):
            st.markdown("**Pedido actual**")
            if not carrito:
                st.caption("Aún no has agregado granizados.")
            for i, l in enumerate(carrito):
                ca, cb = st.columns([5, 1])
                ca.markdown(f"{l['Cantidad']} × **{l['Sabor']}** · {l['Presentación']}  \n"
                            f"{l['Categoría'].title()} · {dinero_md(l['Cantidad'] * l['Precio unitario'])}")
                if cb.button("✕", key=f"quitar_{i}", help="Quitar esta línea"):
                    st.session_state.carrito.pop(i)
                    st.rerun()

        pago_corto = "Efectivo" if metodo_pago == "Efectivo" else "Nequi"
        st.markdown(
            f'<div class="cobro"><span>Total a cobrar</span><b>{dinero_html(total)}</b>'
            f'<p>{unidades_pedido} granizado(s) · {pago_corto}</p></div>',
            unsafe_allow_html=True)
        guardar_venta = st.button("Registrar Venta", type="primary", use_container_width=True, disabled=not carrito)
        if carrito and st.button("Vaciar pedido", use_container_width=True, key="btn_vaciar"):
            st.session_state.carrito = []
            st.rerun()

        r_hoy = resumen_dia(hoy())
        st.markdown("**Resumen de hoy**")
        st.markdown(
            tile("Ventas", len(r_hoy["ventas"]), "#10b981")
            + tile("Efectivo", dinero_html(r_hoy["efectivo"]), "#f59e0b")
            + tile("Transferencias", dinero_html(r_hoy["transferencias"]), "#ec4899"),
            unsafe_allow_html=True)

    if guardar_venta and carrito:
        lineas = []
        for n, l in enumerate(carrito):
            cons = {p: q * l["Cantidad"] for p, q in consumos_venta(l["Sabor"], l["Presentación"], False).items()}
            if n == 0 and bolsas > 0:
                cons["Bolsa de papel (und)"] = int(bolsas)
            lineas.append((l, cons))

        consumo_total = {}
        for _, cons in lineas:
            for p, q in cons.items():
                consumo_total[p] = consumo_total.get(p, 0) + q

        faltantes = [(p, q, int(st.session_state.inventario.get(p, 0))) for p, q in consumo_total.items() if p.startswith("Sabor ") and int(st.session_state.inventario.get(p, 0)) < q]
        if faltantes:
            st.error("Inventario insuficiente del sabor: " + "; ".join(f"{p}: requiere {q}, disponible {d}" for p, q, d in faltantes))
        else:
            with st.spinner("Registrando el pedido..."):
                pedido_id = "V-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
                for producto, unidades in consumo_total.items():
                    nuevo_stock = int(st.session_state.inventario.get(producto, 0)) - unidades
                    st.session_state.inventario[producto] = nuevo_stock
                    guardar_stock_supabase(producto, nuevo_stock)
                    registrar_movimiento(producto, "Salida por venta", unidades, f"Pedido {pedido_id}", pedido_id)
                for n, (l, cons) in enumerate(lineas, 1):
                    obs = observacion.strip()
                    if len(lineas) > 1:
                        obs = f"{obs} · Pedido {pedido_id} ({n}/{len(lineas)})".strip(" ·")
                    
                    id_linea = f"{pedido_id}-{n}"
                    fecha_actual = ahora()
                    cliente_val = cliente.strip() or "Cliente general"
                    cat_val = l["Categoría"]
                    sabor_val = l["Sabor"]
                    pres_val = l["Presentación"]
                    cant_val = l["Cantidad"]
                    precio_val = l["Precio unitario"]
                    total_val = l["Cantidad"] * l["Precio unitario"]
                    pago_val = metodo_pago
                    consumos_val = json.dumps(cons)

                    nueva_venta = {
                        "id": id_linea,
                        "ID": id_linea,
                        "venta_id": id_linea,
                        "fecha": fecha_actual,
                        "Fecha": fecha_actual,
                        "cliente": cliente_val,
                        "Cliente": cliente_val,
                        "categoria": cat_val,
                        "Categoría": cat_val,
                        "sabor": sabor_val,
                        "Sabor": sabor_val,
                        "presentacion": pres_val,
                        "Presentación": pres_val,
                        "cantidad": cant_val,
                        "Cantidad": cant_val,
                        "precio_unitario": precio_val,
                        "Precio unitario": precio_val,
                        "total": total_val,
                        "Total": total_val,
                        "medio_pago": pago_val,
                        "Medio de pago": pago_val,
                        "metodo_pago": pago_val,
                        "observacion": obs,
                        "Observación": obs,
                        "consumos": consumos_val,
                        "Consumos": consumos_val,
                        "estado": "Vigente",
                        "Estado": "Vigente"
                    }
                    st.session_state.ventas.append(nueva_venta)
                    guardar_registro_supabase("ventas", nueva_venta)
            st.session_state.carrito = []
            for k in ("cliente_venta", "obs_venta", "bolsas_venta"):
                st.session_state.pop(k, None)
            st.balloons()
            avisar(f"¡Venta registrada con éxito por {dinero(total)}!", "🎉")

# ------------------------------------------------------------------- INVENTARIO
with tab_inventario:
    st.header("Gestión de Inventario")
    st.caption("Consulta el stock categorizado y corrige existencias en caso de errores en compras.")

    sub_inv1, sub_inv2, sub_inv3, sub_inv4, sub_inv5, sub_inv_corr = st.tabs([
        "🍧 Sin alcohol", "🍹 Con alcohol", "🍨 Cremosos", "🍬 Adicionales y toppings", "🥤 Insumos y otros", "✏️ Corrección de Stock"
    ])

    keys_sin_alcohol = {clave_sabor(s) for s in SABORES["SIN ALCOHOL"]}
    keys_con_alcohol = {clave_sabor(s) for s in SABORES["CON ALCOHOL"]}
    keys_cremosos = {clave_sabor(s) for s in SABORES["CREMOSOS"]}
    keys_extras = set(EXTRAS)
    keys_insumos = {"Vaso 12 oz (und)", "Pitillos (und)", "Bolsa de papel (und)"}

    def render_sub_inventario(filtro_set, titulo_cat):
        st.subheader(titulo_cat)
        items = [(p, q) for p, q in st.session_state.inventario.items() if p in filtro_set]
        df = pd.DataFrame([
            {"Producto": p, "Existencias": int(q),
             "Estado": "⚠️ Bajo" if int(q) <= UMBRAL_BAJO and p not in EXTRAS else ("Sin control" if p in EXTRAS else "Disponible")}
            for p, q in sorted(items)
        ])
        tabla(df)
        st.download_button(f"Descargar {titulo_cat.lower()} CSV", df.to_csv(index=False).encode("utf-8-sig"), f"inventario_{titulo_cat.lower().replace(' ', '_')}.csv", "text/csv")

    with sub_inv1:
        render_sub_inventario(keys_sin_alcohol, "Granizados Sin Alcohol")
    with sub_inv2:
        render_sub_inventario(keys_con_alcohol, "Granizados Con Alcohol")
    with sub_inv3:
        render_sub_inventario(keys_cremosos, "Granizados Cremosos")
    with sub_inv4:
        render_sub_inventario(keys_extras, "Adicionales y Toppings")
    with sub_inv5:
        render_sub_inventario(keys_insumos, "Insumos y Otros Artículos")

    with sub_inv_corr:
        st.subheader("Corrección y Ajuste Directo de Inventario por Categorías")
        st.caption("Selecciona la categoría y luego el producto individual para corregir existencias.")

        cat_corr = st.selectbox("1. Elige la categoría del producto", ["Sin alcohol", "Con alcohol", "Cremosos", "Adicionales y toppings", "Insumos y otros"], key="cat_corr_sel")

        if cat_corr == "Sin alcohol":
            lista_prods_corr = sorted([p for p in st.session_state.inventario.keys() if p in keys_sin_alcohol])
        elif cat_corr == "Con alcohol":
            lista_prods_corr = sorted([p for p in st.session_state.inventario.keys() if p in keys_con_alcohol])
        elif cat_corr == "Cremosos":
            lista_prods_corr = sorted([p for p in st.session_state.inventario.keys() if p in keys_cremosos])
        elif cat_corr == "Adicionales y toppings":
            lista_prods_corr = sorted([p for p in st.session_state.inventario.keys() if p in keys_extras])
        else:
            lista_prods_corr = sorted([p for p in st.session_state.inventario.keys() if p in keys_insumos])

        with st.form("form_correccion_stock"):
            prod_corr = st.selectbox("2. Selecciona el producto individual", lista_prods_corr)
            stock_actual = int(st.session_state.inventario.get(prod_corr, 0))
            st.info(f"Existencias actuales de **{prod_corr}**: **{stock_actual} unidades**")

            nueva_cantidad = st.number_input("Nueva cantidad exacta", min_value=0, max_value=100000, value=stock_actual, step=1)
            detalle_corr = st.text_input("Motivo de la corrección (obligatorio)", placeholder="Ej. Corrección por error de cantidad en inventario")

            btn_guardar_corr = st.form_submit_button("Actualizar y guardar cantidad", type="primary")

        if btn_guardar_corr:
            if not detalle_corr.strip():
                st.error("Debes escribir el motivo de la corrección para auditoría.")
            else:
                dif = nueva_cantidad - stock_actual
                st.session_state.inventario[prod_corr] = nueva_cantidad
                guardar_stock_supabase(prod_corr, nueva_cantidad)
                tipo_mov = "Corrección manual a 0" if nueva_cantidad == 0 else ("Ajuste manual (aumento)" if dif > 0 else "Ajuste manual (reducción)")
                registrar_movimiento(prod_corr, tipo_mov, abs(dif), detalle_corr)
                avisar(f"Inventario de {prod_corr} actualizado correctamente a {nueva_cantidad}.", "✏️")

# -------------------------------------------------------------------- HISTORIAL
with tab_historial:
    st.header("Historial de ventas")
    efectivas = ventas_vigentes()
    if efectivas:
        tabla(sin_consumos(efectivas[::-1]).drop(columns=["ID"], errors="ignore"))
        etiquetas = {v["ID"]: f"{v['Fecha'][5:16]} · {v['Sabor']} ×{v['Cantidad']} · {dinero(v['Total'])}" for v in efectivas[::-1]}
        with st.form("form_anular_venta"):
            id_venta = st.selectbox("Venta vigente para anular", list(etiquetas), format_func=etiquetas.get)
            todo_pedido = st.checkbox("Anular también las demás líneas del mismo pedido (si tiene varios granizados)")
            confirmar = st.checkbox("Confirmo que deseo anular esta venta")
            enviar = st.form_submit_button("Anular venta")
        if enviar:
            if not confirmar:
                st.error("Debes confirmar la anulación.")
            else:
                ids = ids_del_pedido(id_venta) if todo_pedido else [str(id_venta)]
                resultados = [anular_venta(i) for i in ids]
                if all(ok for ok, _ in resultados):
                    avisar(f"{len(ids)} línea(s) anulada(s); el inventario fue devuelto.", "↩️")
                else:
                    st.error(" ".join(m for ok, m in resultados if not ok))
    else:
        st.info("No hay ventas efectivas registradas.")
    if st.session_state.anulaciones:
        with st.expander("Registro de anulaciones (auditoría)"):
            tabla(pd.DataFrame(st.session_state.anulaciones[::-1]))

# ------------------------------------------------------------------------- CAJA Y COMPRAS
with tab_caja:
    st.header("Caja, Gastos y Compras")
    r = resumen_dia(hoy())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ventas en efectivo", dinero(r["efectivo"]), border=True)
    m2.metric("Transferencias", dinero(r["transferencias"]), border=True)
    m3.metric("Gastos de hoy", dinero(r["gastos_total"]), border=True)
    m4.metric("Efectivo en caja estimado", dinero(r["caja_efectivo"]), border=True)

    st.divider()
    sub_caja1, sub_caja2, sub_caja3 = st.tabs(["📥 Registrar Compra", "💸 Registrar Gasto", "📋 Movimientos de Caja"])

    with sub_caja1:
        st.subheader("Registrar Compra de Insumos / Sabores")
        comp_cat = st.selectbox("Elige la categoría de compra", ["Sin alcohol", "Con alcohol", "Cremosos", "Adicionales y toppings", "Insumos y otros"])

        if comp_cat == "Sin alcohol":
            prod_lista = [clave_sabor(s) for s in SABORES["SIN ALCOHOL"]]
            costo_sugerido = 3100.0
        elif comp_cat == "Con alcohol":
            prod_lista = [clave_sabor(s) for s in SABORES["CON ALCOHOL"]]
            costo_sugerido = 3300.0
        elif comp_cat == "Cremosos":
            prod_lista = [clave_sabor(s) for s in SABORES["CREMOSOS"]]
            costo_sugerido = 4100.0
        elif comp_cat == "Adicionales y toppings":
            prod_lista = EXTRAS
            costo_sugerido = 500.0
        else:
            prod_lista = ["Vaso 12 oz (und)", "Pitillos (und)", "Bolsa de papel (und)"]
            costo_sugerido = 200.0

        with st.form(f"form_registrar_compra_{comp_cat}"):
            prod_compra = st.selectbox("Producto a comprar", sorted(prod_lista))
            cant_compra = st.number_input("Cantidad comprada", min_value=1, value=10, step=1)
            costo_unitario_compra = st.number_input("Costo unitario ($)", min_value=0.0, value=costo_sugerido, step=100.0)

            costo_total_calculado = cant_compra * costo_unitario_compra
            st.info(f"Costo total calculado automáticamente: **{dinero_md(costo_total_calculado)}**")

            proveedor = st.text_input("Proveedor o fuente")
            medio_pago_compra = st.selectbox("Medio de pago compra", METODOS_PAGO)

            btn_compra = st.form_submit_button("Registrar compra e ingresar al inventario", type="primary")

        if btn_compra:
            compra_id = "C-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
            nuevo_stock = int(st.session_state.inventario.get(prod_compra, 0)) + int(cant_compra)
            st.session_state.inventario[prod_compra] = nuevo_stock
            guardar_stock_supabase(prod_compra, nuevo_stock)
            registrar_movimiento(prod_compra, "Entrada por compra", cant_compra, f"Compra a {proveedor or 'Proveedor general'}", compra_id)

            id_compra = "C-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
            fecha_compra = ahora()
            
            descripcion_compra = f"Compra de {cant_compra} und de {prod_compra} a {proveedor or 'Proveedor general'}"
            
            nueva_compra = {
                "id": id_compra,
                "ID": id_compra,
                "producto": prod_compra,
                "Producto": prod_compra,
                "cantidad": int(cant_compra),
                "Cantidad": int(cant_compra),
                "costo_total": costo_total_calculado,
                "Costo total": costo_total_calculado,
                "monto": costo_total_calculado,       # <-- Añadido para evitar error not-null constraint en 'monto'
                "Monto": costo_total_calculado,       # <-- Versión con mayúscula por compatibilidad
                "proveedor": proveedor,
                "Proveedor": proveedor,
                "descripcion": descripcion_compra,
                "medio_pago": medio_pago_compra,
                "Medio de pago": medio_pago_compra,
                "estado": "Vigente",
                "Estado": "Vigente",
                "fecha": fecha_compra,
                "Fecha": fecha_compra
            }
            st.session_state.compras.append(nueva_compra)
            guardar_registro_supabase("compras", nueva_compra)

            id_gasto = "G-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
            nuevo_gasto = {
                "id": id_gasto,
                "ID": id_gasto,
                "fecha": fecha_compra,
                "Fecha": fecha_compra,
                "concepto": descripcion_compra,
                "Concepto": descripcion_compra,
                "valor": costo_total_calculado,
                "Valor": costo_total_calculado,
                "monto": costo_total_calculado,
                "medio_pago": medio_pago_compra,
                "Medio de pago": medio_pago_compra,
                "compra_id": id_compra,
                "Compra ID": id_compra,
                "anulado": False,
                "Anulado": False
            }
            st.session_state.gastos.append(nuevo_gasto)
            guardar_registro_supabase("gastos", nuevo_gasto)

            avisar(f"Compra registrada por {dinero(costo_total_calculado)} y {cant_compra} unidades de {prod_compra} sumadas.", "📦")

    with sub_caja2:
        st.subheader("Registrar Gasto Operativo")
        with st.form("form_registrar_gasto"):
            concepto_gasto = st.text_input("Concepto o descripción del gasto")
            valor_gasto = st.number_input("Valor del gasto ($)", min_value=0.0, value=5000.0, step=500.0)
            medio_pago_gasto = st.selectbox("Medio de pago gasto", METODOS_PAGO, key="pago_gasto_sel")

            btn_gasto = st.form_submit_button("Registrar gasto", type="primary")

        if btn_gasto:
            if not concepto_gasto.strip():
                st.error("Debes escribir el concepto del gasto.")
            else:
                id_gasto = "G-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
                fecha_gasto = ahora()
                nuevo_gasto = {
                    "id": id_gasto,
                    "ID": id_gasto,
                    "fecha": fecha_gasto,
                    "Fecha": fecha_gasto,
                    "concepto": concepto_gasto.strip(),
                    "Concepto": concepto_gasto.strip(),
                    "valor": valor_gasto,
                    "Valor": valor_gasto,
                    "monto": valor_gasto,
                    "medio_pago": medio_pago_gasto,
                    "Medio de pago": medio_pago_gasto,
                    "compra_id": "",
                    "Compra ID": "",
                    "anulado": False,
                    "Anulado": False
                }
                st.session_state.gastos.append(nuevo_gasto)
                guardar_registro_supabase("gastos", nuevo_gasto)
                avisar("Gasto registrado con éxito.", "💸")

    with sub_caja3:
        st.subheader("Movimientos de Caja y Gastos de Hoy")
        gs = gastos_vigentes(hoy())
        if gs:
            tabla(pd.DataFrame(gs)[["Fecha", "Concepto", "Valor", "Medio de pago"]])
        else:
            st.info("No hay gastos registrados hoy.")

# -------------------------------------------------------------------- REPORTES
with tab_reportes:
    st.header("Reportes y Estadísticas")
    st.caption("Consulta el rendimiento financiero y analíticas de ventas por sabor.")
    vs = ventas_vigentes()
    if vs:
        df_v = pd.DataFrame(vs)
        total_gen = df_v["Total"].sum()
        unidades_gen = df_v["Cantidad"].sum()
        m1, m2 = st.columns(2)
        m1.metric("Ventas acumuladas totales", dinero(total_gen), border=True)
        m2.metric("Unidades vendidas totales", int(unidades_gen), border=True)

        st.markdown("---")
        st.subheader("📊 Ventas Detalladas por Nombre de Sabor")
        cat_filtro = st.selectbox("Filtrar por Categoría:", ["Todas"] + list(SABORES.keys()))
        
        df_f = df_v.copy()
        if cat_filtro != "Todas":
            df_f = df_f[df_f["Categoría"] == cat_filtro]
            
        if not df_f.empty and "Sabor" in df_f.columns:
            df_sabores = df_f.groupby(["Categoría", "Sabor"]).agg(
                Cantidad_Vendida=("Cantidad", "sum"),
                Total_Recaudado=("Total", "sum")
            ).reset_index().sort_values(by="Cantidad_Vendida", ascending=False)

            st.dataframe(df_sabores, use_container_width=True)
            
            mejor = df_sabores.iloc[0]
            peor = df_sabores.iloc[-1]
            
            c1, c2 = st.columns(2)
            c1.success(f"🔥 **Sabor Más Vendido:** {mejor['Sabor']} ({mejor['Cantidad_Vendida']} und)")
            c2.warning(f"⚠️ **Sabor Con Menor Salida:** {peor['Sabor']} ({peor['Cantidad_Vendida']} und)")
        else:
            st.info("No hay registros para la categoría seleccionada.")
            
        st.subheader("Ventas por Categoría")
        st.bar_chart(df_v.groupby("Categoría")["Total"].sum())
    else:
        st.info("Aún no hay suficientes ventas para generar reportes.")

# -------------------------------------------------------------------- CIERRE DE CAJA
with tab_cierre:
    st.header("Cierre de Caja Diario")
    fecha_cierre_sel = st.date_input("Fecha de cierre", value=hoy())
    r_cierre = resumen_dia(fecha_cierre_sel)

    st.markdown(f"### Resumen para el día {fecha_cierre_sel}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ventas totales", dinero(r_cierre["efectivo"] + r_cierre["transferencias"]))
    c2.metric("Gastos totales", dinero(r_cierre["gastos_total"]))
    c3.metric("Neto estimado", dinero(r_cierre["neto"]))

    efectivo_contado = st.number_input("Dinero en efectivo contado en caja ($)", min_value=0.0, value=max(0.0, float(r_cierre["caja_efectivo"])), step=1000.0)
    diferencia = efectivo_contado - r_cierre["caja_efectivo"]
    if diferencia != 0:
        st.warning(f"Diferencia en efectivo: {dinero_md(diferencia)}")
    else:
        st.success("¡Caja cuadrada perfectamente!")

    if st.button("Guardar Cierre de Caja", type="primary"):
        cierre_data = {
            "Fecha cierre": str(fecha_cierre_sel), "Fecha registro": ahora(),
            "Ventas efectivo": r_cierre["efectivo"], "Ventas transferencias": r_cierre["transferencias"],
            "Gastos": r_cierre["gastos_total"], "Caja efectivo esperada": r_cierre["caja_efectivo"],
            "Efectivo contado": efectivo_contado, "Diferencia": diferencia, "Desactualizado": False
        }
        st.session_state.cierres_caja.append(cierre_data)
        guardar_registro_supabase("cierres_caja", cierre_data)
        avisar("¡Cierre de caja guardado con éxito!", "🔒")
