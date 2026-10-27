import base64
import hmac
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import random

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Granizados PL - Punto de Venta", page_icon="🍧", layout="wide")

# ---------------------------------------------------------------- CONFIGURACIÓN
TZ = timezone(timedelta(hours=-5))  # Colombia (sin horario de verano)
UMBRAL_BAJO = 5
CARPETA_DATOS = Path("datos_granizados_pl")
ARCHIVO_DATOS = CARPETA_DATOS / "datos_pos.json"
LOGO = Path("logo_pl.png")
CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

PRECIOS_VENTA = {"SIN ALCOHOL": 13000, "CON ALCOHOL": 15000, "CREMOSOS": 15000}
PRECIOS_COMPRA = {"SIN ALCOHOL": 3100, "CON ALCOHOL": 3300, "CREMOSOS": 4100}
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
CLAVES = ["inventario", "ventas", "movimientos", "gastos", "anulaciones", "cierres_caja", "compras"]


# ---------------------------------------------------------------------- UTILES
def ahora():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def hoy():
    return datetime.now(TZ).date()


def dinero(valor):
    return f"${int(round(valor)):,.0f}".replace(",", ".")


def dinero_html(valor):
    return dinero(valor).replace("$", "&#36;")


def suma(items, campo="Total"):
    return sum(int(i.get(campo, 0)) for i in items)


# ------------------------------------------------------------------------ DATOS
def cargar_datos():
    datos = {}
    if ARCHIVO_DATOS.exists():
        try:
            datos = json.loads(ARCHIVO_DATOS.read_text(encoding="utf-8"))
            if not isinstance(datos, dict):
                raise ValueError("estructura inesperada")
        except (ValueError, OSError):
            copia = ARCHIVO_DATOS.with_name(f"datos_pos.danado.{datetime.now(TZ):%Y%m%d%H%M%S}.json")
            try:
                ARCHIVO_DATOS.replace(copia)
            except OSError:
                pass
            datos = {}
            st.error(f"No se pudo leer datos_pos.json. Se guardó una copia ({copia.name}) y se inicia vacío.")
    inventario = dict(INVENTARIO_BASE)
    for k, v in datos.get("inventario", {}).items():
        if k not in PRODUCTOS_ELIMINADOS:
            try:
                inventario[k] = int(v)
            except (ValueError, TypeError):
                inventario[k] = 0
    resultado = {k: datos.get(k, []) for k in CLAVES if k != "inventario"}
    resultado["inventario"] = inventario
    return resultado


def guardar_datos():
    temporal = ARCHIVO_DATOS.with_suffix(".tmp")
    temporal.write_text(json.dumps({k: st.session_state[k] for k in CLAVES}, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ARCHIVO_DATOS)


def avisar(mensaje, icono=None):
    st.session_state["_aviso"] = (mensaje, icono)
    st.rerun()


def verificar_acceso():
    try:
        clave = st.secrets.get("clave_app", None)
    except Exception:
        clave = None
    if not clave or st.session_state.get("acceso_ok"):
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
        st.caption("Acceso Seguro - Sistema POS")
        intento = st.text_input("Contraseña de acceso", type="password")
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            if hmac.compare_digest(str(intento), str(clave)):
                st.session_state["acceso_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


verificar_acceso()

if "datos_inicializados" not in st.session_state:
    for _k, _v in cargar_datos().items():
        st.session_state[_k] = _v
    st.session_state.datos_inicializados = True

if "_aviso" in st.session_state:
    _msg, _ico = st.session_state.pop("_aviso")
    st.toast(_msg, icon=_ico)


# ------------------------------------------------------------------- LÓGICA
def registrar_movimiento(producto, tipo, cantidad, detalle="", referencia=""):
    st.session_state.movimientos.append({"Fecha": ahora(), "Producto": producto, "Tipo": tipo, "Cantidad": int(cantidad), "Detalle": detalle, "Referencia": referencia})


def registrar_anulacion(tipo, identificador, detalle):
    st.session_state.anulaciones.append({"Fecha": ahora(), "Tipo": tipo, "ID": identificador, "Detalle": detalle})


def ventas_vigentes(desde=None, hasta=None):
    resultado = []
    for v in st.session_state.ventas:
        if v.get("Estado", "Vigente") != "Vigente":
            continue
        f = v.get("Fecha", "")[:10]
        if (desde and f < str(desde)) or (hasta and f > str(hasta)):
            continue
        resultado.append(v)
    return resultado


def compras_vigentes():
    return [c for c in st.session_state.compras if c.get("Estado", "Vigente") == "Vigente"]


def gastos_vigentes(fecha=None):
    return [g for g in st.session_state.gastos if not g.get("Anulado", False) and (fecha is None or g.get("Fecha", "")[:10] == str(fecha))]


def resumen_dia(fecha):
    f = str(fecha)
    ventas, gastos = ventas_vigentes(f, f), gastos_vigentes(f)
    efectivo = suma([v for v in ventas if v.get("Medio de pago") == "Efectivo"])
    transf = suma([v for v in ventas if v.get("Medio de pago") != "Efectivo"])
    gastos_total = suma(gastos, "Valor")
    gastos_efectivo = suma([g for g in gastos if g.get("Medio de pago") == "Efectivo"], "Valor")
    return {"ventas": ventas, "gastos": gastos, "efectivo": efectivo, "transferencias": transf,
            "gastos_total": gastos_total, "caja_efectivo": efectivo - gastos_efectivo,
            "neto": efectivo + transf - gastos_total, "unidades": suma(ventas, "Cantidad")}


def marcar_cierre_desactualizado(fecha):
    for c in st.session_state.cierres_caja:
        if c.get("Fecha cierre") == fecha:
            c["Desactualizado"] = True


def anular_venta(venta_id):
    venta = next((v for v in st.session_state.ventas if v.get("ID") == venta_id and v.get("Estado", "Vigente") == "Vigente"), None)
    if not venta:
        return False, "No se encontró la venta vigente."
    for producto, cantidad in venta.get("Consumos", {}).items():
        st.session_state.inventario[producto] = int(st.session_state.inventario.get(producto, 0)) + int(cantidad)
        registrar_movimiento(producto, "Entrada por anulación de venta", cantidad, "Devolución de inventario", venta_id)
    venta["Estado"], venta["Fecha anulación"] = "Anulada", ahora()
    marcar_cierre_desactualizado(venta["Fecha"][:10])
    registrar_anulacion("Venta", venta_id, "Venta anulada")
    guardar_datos()
    return True, "Venta anulada; el inventario consumido fue devuelto."


def anular_compra(compra_id):
    compra = next((c for c in compras_vigentes() if c.get("ID") == compra_id), None)
    if not compra:
        return False, "No se encontró la compra vigente."
    producto, cantidad = compra["Producto"], int(compra["Cantidad"])
    disponible = int(st.session_state.inventario.get(producto, 0))
    if disponible < cantidad:
        return False, f"No se puede anular: hay {disponible} unidades de {producto} y se deben retirar {cantidad}."
    st.session_state.inventario[producto] = disponible - cantidad
    registrar_movimiento(producto, "Salida por anulación de compra", cantidad, "Reversión de compra", compra_id)
    compra["Estado"], compra["Fecha anulación"] = "Anulada", ahora()
    for g in st.session_state.gastos:
        if g.get("Compra ID") == compra_id:
            g["Anulado"] = True
            marcar_cierre_desactualizado(g["Fecha"][:10])
    registrar_anulacion("Compra", compra_id, "Compra anulada")
    guardar_datos()
    return True, "Compra anulada; se retiraron las unidades y el gasto quedó excluido."


def anular_gasto(gasto_id):
    gasto = next((g for g in gastos_vigentes() if g.get("ID") == gasto_id), None)
    if not gasto:
        return False, "No se encontró el gasto vigente."
    if gasto.get("Compra ID"):
        return False, "Este gasto viene de una compra; anúlalo desde la sección correspondiente."
    producto, unidades = gasto.get("Producto"), int(gasto.get("Unidades", 0))
    if producto and unidades:
        disponible = int(st.session_state.inventario.get(producto, 0))
        if disponible < unidades:
            return False, f"No se puede anular: hay {disponible} de {producto} y se deben retirar {unidades}."
        st.session_state.inventario[producto] = disponible - unidades
        registrar_movimiento(producto, "Salida por anulación de gasto", unidades, "Reversión de gasto", gasto_id)
    gasto["Anulado"], gasto["Fecha anulación"] = True, ahora()
    marcar_cierre_desactualizado(gasto["Fecha"][:10])
    registrar_anulacion("Gasto", gasto_id, "Gasto anulado")
    guardar_datos()
    return True, "Gasto anulado."


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


# --------------------------------------------------------------------- ESTILO LUMINOSO Y DINÁMICO
CSS_GENERAL = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; }
.block-container { padding-top: 1.5rem; max-width: 1250px; }
@keyframes floatDynamic { 0% { transform: translateY(0px) rotate(0deg) scale(1); } 33% { transform: translateY(-10px) rotate(2deg) scale(1.02); } 66% { transform: translateY(5px) rotate(-2deg) scale(0.98); } 100% { transform: translateY(0px) rotate(0deg) scale(1); } }
@keyframes pulseGlow { 0% { box-shadow: 0 0 15px rgba(99, 102, 241, 0.2); } 50% { box-shadow: 0 0 35px rgba(99, 102, 241, 0.4); } 100% { box-shadow: 0 0 15px rgba(99, 102, 241, 0.2); } }
@keyframes floatBadge1 { 0% { transform: translate(0, 0) rotate(0deg); } 50% { transform: translate(-8px, -12px) rotate(5deg); } 100% { transform: translate(0, 0) rotate(0deg); } }
@keyframes floatBadge2 { 0% { transform: translate(0, 0) rotate(0deg); } 50% { transform: translate(10px, 8px) rotate(-5deg); } 100% { transform: translate(0, 0) rotate(0deg); } }
.banner { background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%); border: 1px solid #e2e8f0; border-radius: 28px; padding: 24px 36px; display: flex; align-items: center; gap: 28px; color: #1e293b; margin-bottom: 24px; box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.05); position: relative; overflow: visible; }
.banner-logo-container { position: relative; display: inline-block; }
.banner img { animation: floatDynamic 5s ease-in-out infinite; box-shadow: 0 12px 25px rgba(99, 102, 241, 0.25); border-radius: 22px; width: 120px; height: 120px; object-fit: cover; }
.granizado-avatar-vaso { width: 110px; height: 115px; background: linear-gradient(135deg, #6366f1 0%, #ec4899 50%, #f59e0b 100%); border-radius: 12px 12px 28px 28px; position: relative; display: flex; align-items: center; justify-content: center; box-shadow: 0 12px 25px rgba(99, 102, 241, 0.3); animation: floatDynamic 5s ease-in-out infinite; }
.granizado-avatar-vaso::before { content: ''; position: absolute; top: -14px; left: -6px; right: -6px; height: 22px; background: #ffffff; border-radius: 50%; box-shadow: 0 3px 8px rgba(0,0,0,0.1); }
.granizado-avatar-vaso::after { content: ''; position: absolute; top: -32px; right: 22px; width: 8px; height: 45px; background: #10b981; transform: rotate(25deg); border-radius: 4px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
.avatar-emoji { font-size: 38px; z-index: 2; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2)); }
.floating-badge-1 { position: absolute; top: -10px; right: -15px; background: #10b981; color: white; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; animation: floatBadge1 4s ease-in-out infinite; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3); }
.floating-badge-2 { position: absolute; bottom: -8px; left: -15px; background: #f59e0b; color: white; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; animation: floatBadge2 4.5s ease-in-out infinite; box-shadow: 0 4px 10px rgba(245, 158, 11, 0.3); }
.banner-texto { flex: 1; }
.banner-titulo { font: 800 38px/1.1 'Outfit', sans-serif; color: #0f172a; letter-spacing: -0.5px; }
.banner-sub { font-size: 16px; font-weight: 600; color: #64748b; margin-top: 6px; }
.banner-ventas { background: #ffffff; border: 2px solid #6366f1; color: #0f172a; border-radius: 20px; padding: 18px 28px; min-width: 240px; text-align: right; box-shadow: 0 10px 25px rgba(99, 102, 241, 0.1); animation: pulseGlow 4s infinite ease-in-out; }
.banner-ventas span { display: block; font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 700; }
.banner-ventas b { display: block; font: 800 32px 'Outfit', sans-serif; color: #6366f1; margin-top: 4px; }
.cobro { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border: 2px solid #6366f1; border-radius: 24px; padding: 24px 28px; color: #1e293b; margin-bottom: 14px; box-shadow: 0 15px 30px -5px rgba(99, 102, 241, 0.12); }
.cobro span { display: block; font-size: 15px; color: #64748b; font-weight: 600; }
.cobro b { display: block; font: 800 48px 'Outfit', sans-serif; line-height: 1.1; color: #0f172a; }
.cobro p { margin: 8px 0 0; font-size: 14px; color: #6366f1; font-weight: 600; }
.tile { padding: 18px 22px; border-radius: 20px; color: #ffffff; margin-bottom: 14px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); transition: transform 0.2s; }
.tile:hover { transform: translateY(-3px); }
.tile span { display: block; font-size: 12px; font-weight: 700; text-transform: uppercase; opacity: 0.9; letter-spacing: 0.5px; }
.tile b { display: block; font: 700 28px 'Outfit', sans-serif; margin-top: 4px; }
.chip-cat { display: inline-block; border-radius: 999px; padding: 6px 18px; font-weight: 700; color: #ffffff; font-size: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
[data-testid="stBaseButton-primary"] { background: linear-gradient(135deg, #6366f1, #4f46e5); border: 0; min-height: 3.5rem; border-radius: 16px; box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35); transition: all 0.3s; }
[data-testid="stBaseButton-primary"]:hover { background: linear-gradient(135deg, #4f46e5, #4338ca); box-shadow: 0 12px 25px rgba(99, 102, 241, 0.5); transform: translateY(-2px); }
[data-testid="stBaseButton-primary"] p { color: #ffffff; font-weight: 700; font-size: 16px; letter-spacing: 0.3px; }
div[data-testid="stMetric"] { background: #ffffff; border: 1px solid #e2e8f0; padding: 18px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
"""
st.markdown(f"<style>{CSS_
