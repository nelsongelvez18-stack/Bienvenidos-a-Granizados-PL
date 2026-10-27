import base64
import hmac
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Granizados PL - Punto de Venta PRO", page_icon="🍧", layout="wide")

# ---------------------------------------------------------------- CONFIGURACIÓN
TZ = timezone(timedelta(hours=-5))  # Colombia (sin horario de verano)
UMBRAL_BAJO = 5
CARPETA_DATOS = Path("datos_granizados_pl")
ARCHIVO_DATOS = CARPETA_DATOS / "datos_pos.json"
LOGO = Path("logo_pl.png")
CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

PRECIOS_VENTA = {"SIN ALCOHOL": 13000, "CON ALCOHOL": 15000, "CREMOSOS": 15000}
PRECIOS_COMPRA = {"SIN ALCOHOL": 3100, "CON ALCOHOL": 3300, "CREMOSOS": 4100}
COLORES = {"SIN ALCOHOL": "#7dff3a", "CON ALCOHOL": "#ff8fc2", "CREMOSOS": "#ffe27a"}
METODOS_PAGO = ["Efectivo", "Transferencia Nequi / Billeteras virtuales"]
SABORES = {
    "SIN ALCOHOL": ["Bombombum", "Chicle", "Frutos Rojos", "Limonada Cerezada", "Limonada de Coco", "Limonada de Sandía", "Mango Biche", "Manzana Rosada", "Manzana Verde", "Maracumango", "Maracululo", "Maracupiña", "Mora Azul", "Uva"],
    "CON ALCOHOL": ["Agave Ice", "Andromeda Ice", "Bon Bon Bum Ice", "Candy Ice", "Cherryboom Ice", "Cosmico Ice", "Estelar Ice", "Fresa Salvaje Ice", "Fourloko Ice", "Interestelar Ice", "Luxury Ice", "Mango Explosivo Ice", "Miami Ice", "Monaco Ice", "Mora Azul Ice", "Nebula Ice", "Orion Ice", "Smirnoff Lulo Ice", "Smirnoff Limon Ice", "Tropical Caribeña Ice", "Velvet Ice"],
    "CREMOSOS": ["Bayleys", "Coco Loco", "Piña Colada"],
}
EXTRAS = ["Minichicles (porción)", "Goma bandera (porción)", "Bombón (porción)", "Sal pimienta (porción)", "Bolas de chicle (porción)", "Goma gusano (porción)", "Goma splash (porción)", "Barquillo (und)"]


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
    
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 30px;
        background: rgba(20, 20, 28, 0.85);
        border: 2px solid #ff3d9a;
        border-radius: 20px;
        box-shadow: 0 0 30px rgba(255, 61, 154, 0.4);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

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
    for v in st.session_state.ventas
