import base64
import bcrypt
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import random

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

st.set_page_config(page_title="Granizados PL - Punto de Venta", page_icon="🍧", layout="wide")

# ---------------------------------------------------------------- CONFIGURACIÓN SUPABASE Y APP
TZ = timezone(timedelta(hours=-5))  # Colombia
UMBRAL_BAJO = 5
LOGO = Path("logo_pl.png")

@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

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


# ---------------------------------------------------------------------- UTILES Y BD SUPABASE
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


# Sincronización con Supabase
def cargar_datos_supabase():
    try:
        # Cargar inventario
        inv_res = supabase.table("inventario").select("*").execute()
        inventario = dict(INVENTARIO_BASE)
        if inv_res.data:
            for row in inv_res.data:
                p = row["producto"]
                if p not in PRODUCTOS_ELIMINADOS:
                    inventario[p] = row["existencias"]
        else:
            # Inicializar inventario base en Supabase si está vacío
            for p, q in INVENTARIO_BASE.items():
                supabase.table("inventario").upsert({"producto": p, "existencias": q}).execute()

        ventas = supabase.table("ventas").select("*").execute().data or []
        compras = supabase.table("compras").select("*").execute().data or []
        gastos = supabase.table("gastos").select("*").execute().data or []
        movimientos = supabase.table("movimientos").select("*").execute().data or []
        anulaciones = supabase.table("anulaciones").select("*").execute().data or []
        cierres_caja = supabase.table("cierres_caja").select("*").execute().data or []

        return {
            "inventario": inventario,
            "ventas": ventas,
            "compras": compras,
            "gastos": gastos,
            "movimientos": movimientos,
            "anulaciones": anulaciones,
            "cierres_caja": cierres_caja
        }
    except Exception as e:
        st.error(f"Error conectando con Supabase: {e}")
        return {k: ([] if k != "inventario" else INVENTARIO_BASE) for k in ["inventario", "ventas", "compras", "gastos", "movimientos", "anulaciones", "cierres_caja"]}


def avisar(mensaje, icono=None):
    st.session_state["_aviso"] = (mensaje, icono)
    st.rerun()


# ---------------------------------------------------------------------- AUTENTICACIÓN
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
        usuario_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password")
        
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            try:
                res = supabase.table("usuarios").select("*").eq("username", usuario_input.strip()).execute()
                if res.data:
                    user_record = res.data[0]
                    # Validar contraseña con bcrypt
                    if bcrypt.checkpw(password_input.encode('utf-8'), user_record["password_hash"].encode('utf-8')):
                        st.session_state["acceso_ok"] = True
                        st.session_state["usuario_actual"] = user_record["username"]
                        st.session_state["rol_usuario"] = user_record["rol"]
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta.")
                else:
                    st.error("El usuario no existe.")
            except Exception as e:
                st.error(f"Error al verificar credenciales: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


verificar_acceso()

# Inicializar estado con datos de Supabase
if "datos_inicializados" not in st.session_state:
    datos_cloud = cargar_datos_supabase()
    for _k, _v in datos_cloud.items():
        st.session_state[_k] = _v
    st.session_state.datos_inicializados = True

if "_aviso" in st.session_state:
    _msg, _ico = st.session_state.pop("_aviso")
    st.toast(_msg, icon=_ico)


# ------------------------------------------------------------------- LÓGICA DE NEGOCIO Y PERSISTENCIA SUPABASE
def registrar_movimiento(producto, tipo, cantidad, detalle="", referencia=""):
    mov = {"fecha": ahora(), "producto": producto, "tipo": tipo, "cantidad": int(cantidad), "detalle": detalle, "referencia": referencia}
    st.session_state.movimientos.append(mov)
    try:
        supabase.table("movimientos").insert(mov).execute()
    except Exception as e:
        st.toast(f"Error sincronizando movimiento: {e}", icon="⚠️")


def registrar_anulacion(tipo, identificador, detalle):
    anul = {"fecha": ahora(), "tipo": tipo, "id_afectado": identificador, "detalle": detalle}
    st.session_state.anulaciones.append(anul)
    try:
        supabase.table("anulaciones").insert(anul).execute()
    except Exception as e:
        st.toast(f"Error sincronizando anulación: {e}", icon="⚠️")


def actualizar_inventario_supabase(producto):
    try:
        supabase.table("inventario").upsert({
            "producto": producto, 
            "existencias": int(st.session_state.inventario[producto])
        }).execute()
    except Exception as e:
        st.toast(f"Error actualizando inventario en nube: {e}", icon="⚠️")


def ventas_vigentes(desde=None, hasta=None):
    resultado = []
    for v in st.session_state.ventas:
        if v.get("estado", "Vigente") != "Vigente":
            continue
        f = v.get("fecha", "")[:10]
        if (desde and f < str(desde)) or (hasta and f > str(hasta)):
            continue
        resultado.append(v)
    return resultado


def compras_vigentes():
    return [c for c in st.session_state.compras if c.get("estado", "Vigente") == "Vigente"]


def gastos_vigentes(fecha=None):
    return [g for g in st.session_state.gastos if not g.get("anulado", False) and (fecha is None or g.get("fecha", "")[:10] == str(fecha))]


def resumen_dia(fecha):
    f = str(fecha)
    ventas, gastos = ventas_vigentes(f, f), gastos_vigentes(f)
    efectivo = suma([v for v in ventas if v.get("medio_pago") == "Efectivo"], "total")
    transf = suma([v for v in ventas if v.get("medio_pago") != "Efectivo"], "total")
    gastos_total = suma(gastos, "valor")
    gastos_efectivo = suma([g for g in gastos if g.get("medio_pago") == "Efectivo"], "valor")
    return {"ventas": ventas, "gastos": gastos, "efectivo": efectivo, "transferencias": transf,
            "gastos_total": gastos_total, "caja_efectivo": efectivo - gastos_efectivo,
            "neto": efectivo + transf - gastos_total, "unidades": suma(ventas, "cantidad")}


def marcar_cierre_desactualizado(fecha):
    for c in st.session_state.cierres_caja:
        if c.get("fecha_cierre") == str(fecha):
            c["desactualizado"] = True
            try:
                supabase.table("cierres_caja").update({"desactualizado": True}).eq("fecha_cierre", str(fecha)).execute()
            except Exception:
                pass


def anular_venta(venta_id):
    venta = next((v for v in st.session_state.ventas if v.get("id") == venta_id and v.get("estado", "Vigente") == "Vigente"), None)
    if not venta:
        return False, "No se encontró la venta vigente."
    for producto, cantidad in venta.get("consumos", {}).items():
        st.session_state.inventario[producto] = int(st.session_state.inventario.get(producto, 0)) + int(cantidad)
        actualizar_inventario_supabase(producto)
        registrar_movimiento(producto, "Entrada por anulación de venta", cantidad, "Devolución de inventario", venta_id)
    
    venta["estado"] = "Anulada"
    venta["fecha_anulacion"] = ahora()
    marcar_cierre_desactualizado(venta["fecha"][:10])
    registrar_anulacion("Venta", venta_id, "Venta anulada")
    
    try:
        supabase.table("ventas").update({"estado": "Anulada"}).eq("id", venta_id).execute()
    except Exception as e:
        return False, f"Error actualizando en nube: {e}"
        
    return True, "Venta anulada; el inventario consumido fue devuelto."


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


# --------------------------------------------------------------------- ESTILO Y COMPONENTES
CSS_GENERAL = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; }
.block-container { padding-top: 1.5rem; max-width: 1250px; }
@keyframes floatDynamic { 0% { transform: translateY(0px) rotate(0deg) scale(1); } 33% { transform: translateY(-10px) rotate(2deg) scale(1.02); } 66% { transform: translateY(5px) rotate(-2deg) scale(0.98); } 100% { transform: translateY(0px) rotate(0deg) scale(1); } }
@keyframes pulseGlow { 0% { box-shadow: 0 0 15px rgba(99, 102, 241, 0.2); } 50% { box-shadow: 0 0 35px rgba(99, 102, 241, 0.4); } 100% { box-shadow: 0 0 15px rgba(99, 102, 241, 0.2); } }
.banner { background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%); border: 1px solid #e2e8f0; border-radius: 28px; padding: 24px 36px; display: flex; align-items: center; gap: 28px; color: #1e293b; margin-bottom: 24px; box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.05); }
.banner img { animation: floatDynamic 5s ease-in-out infinite; box-shadow: 0 12px 25px rgba(99, 102, 241, 0.25); border-radius: 22px; width: 120px; height: 120px; object-fit: cover; }
.granizado-avatar-vaso { width: 110px; height: 115px; background: linear-gradient(135deg, #6366f1 0%, #ec4899 50%, #f59e0b 100%); border-radius: 12px 12px 28px 28px; position: relative; display: flex; align-items: center; justify-content: center; box-shadow: 0 12px 25px rgba(99, 102, 241, 0.3); animation: floatDynamic 5s ease-in-out infinite; }
.banner-texto { flex: 1; }
.banner-titulo { font: 800 38px/1.1 'Outfit', sans-serif; color: #0f172a; }
.banner-sub { font-size: 16px; font-weight: 600; color: #64748b; margin-top: 6px; }
.banner-ventas { background: #ffffff; border: 2px solid #6366f1; color: #0f172a; border-radius: 20px; padding: 18px 28px; min-width: 240px; text-align: right; box-shadow: 0 10px 25px rgba(99, 102, 241, 0.1); animation: pulseGlow 4s infinite ease-in-out; }
.banner-ventas span { display: block; font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 700; }
.banner-ventas b { display: block; font: 800 32px 'Outfit', sans-serif; color: #6366f1; margin-top: 4px; }
.cobro { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border: 2px solid #6366f1; border-radius: 24px; padding: 24px 28px; color: #1e293b; margin-bottom: 14px; box-shadow: 0 15px 30px -5px rgba(99, 102, 241, 0.12); }
.cobro span { display: block; font-size: 15px; color: #64748b; font-weight: 600; }
.cobro b { display: block; font: 800 48px 'Outfit', sans-serif; line-height: 1.1; color: #0f172a; }
.tile { padding: 18px 22px; border-radius: 20px; color: #ffffff; margin-bottom: 14px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); }
.tile span { display: block; font-size: 12px; font-weight: 700; text-transform: uppercase; opacity: 0.9; }
.tile b { display: block; font: 700 28px 'Outfit', sans-serif; margin-top: 4px; }
.chip-cat { display: inline-block; border-radius: 999px; padding: 6px 18px; font-weight: 700; color: #ffffff; font-size: 14px; }
"""
st.markdown("<style>" + CSS_GENERAL + "</style>", unsafe_allow_html=True)


def logo_html():
    if LOGO.exists():
        b64 = base64.b64encode(LOGO.read_bytes()).decode()
        inner = f'<img src="data:image/png;base64,{b64}" alt="Avatar">'
    else:
        inner = '<div class="granizado-avatar-vaso"><span style="font-size:38px;">🍧</span></div>'
    return f'<div style="position:relative;display:inline-block;">{inner}</div>'


def encabezado():
    total_hoy = suma(ventas_vigentes(hoy(), hoy()), "total")
    st.markdown(
        f'<div class="banner">{logo_html()}<div class="banner-texto">'
        '<div class="banner-titulo">Granizados PL</div>'
        '<div class="banner-sub">Sistema POS Conectado a Supabase (Cloud) · Túquerres</div></div>'
        f'<div class="banner-ventas"><span>Ventas de hoy</span><b>{dinero_html(total_hoy)}</b></div></div>',
        unsafe_allow_html=True)
    
    # Frases rotativas + Keep-Alive para evitar suspensión por inactividad
    frases_json = json.dumps(FRASES_MOTIVADORAS)
    components.html(f"""
        <div style="font-family: 'Plus Jakarta Sans', sans-serif; background: linear-gradient(135deg, #e0e7ff 0%, #fae8ff 100%); border: 1px solid #c7d2fe; border-radius: 16px; padding: 14px 20px; color: #312e81; font-weight: 600; font-size: 15px; margin-bottom: 20px; text-align: center; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.08); position: relative; overflow: hidden;">
            <div id="frase-texto" style="transition: opacity 0.5s ease-in-out;">Cargando motivación...</div>
            <div style="position: absolute; bottom: 0; left: 0; height: 3px; background: #6366f1; width: 100%; transition: width 60s linear;" id="barra-progreso"></div>
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

            // Keep-alive loop para evitar cierre por inactividad en la nube
            setInterval(function() {{
                fetch(window.location.href);
            }}, 240000);
        </script>
    """, height=75)


# Barra lateral con información de sesión y cierre de sesión
with st.sidebar:
    st.write(f"👤 **Usuario:** {st.session_state.get('usuario_actual', 'Admin')}")
    st.write(f"🛡️ **Rol:** {st.session_state.get('rol_usuario', 'Administrador').title()}")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()


encabezado()

tab_ventas, tab_inventario, tab_historial, tab_caja = st.tabs(["🛒 Ventas", "📦 Inventario", "🧾 Historial", "💵 Caja"])

with tab_ventas:
    col_form, col_cobro = st.columns([2, 1], gap="large")
    with col_form:
        with st.container(border=True):
            st.subheader("Nueva venta rápida")
            categoria = st.selectbox("1. Elige la categoría", list(SABORES))
            sabor = st.selectbox("2. Elige el sabor", SABORES[categoria])
            presentacion = st.selectbox("Presentación", ["Vaso 12 oz", "Sachet 12 oz"])
            metodo_pago = st.selectbox("Medio de pago", METODOS_PAGO)
            cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
            incluir_bolsa = st.checkbox("Incluir bolsa de papel", value=True)
            cliente = st.text_input("Cliente (opcional)")

    precio_unitario = PRECIOS_VENTA[categoria]
    total = precio_unitario * int(cantidad)
    with col_cobro:
        st.markdown(f'<div class="cobro"><span>Total a cobrar</span><b>{dinero_html(total)}</b></div>', unsafe_allow_html=True)
        guardar_venta = st.button("Registrar Venta", type="primary", use_container_width=True)

    if guardar_venta:
        consumos = {p: q * int(cantidad) for p, q in consumos_venta(sabor, presentacion, incluir_bolsa).items()}
        # Validar stock en Supabase/Session
        faltantes = [p for p, q in consumos.items() if p.startswith("Sabor ") and int(st.session_state.inventario.get(p, 0)) < q]
        if faltantes:
            st.error(f"Inventario insuficiente para: {', '.join(faltantes)}")
        else:
            venta_id = "V-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
            for producto, unidades in consumos.items():
                st.session_state.inventario[producto] = int(st.session_state.inventario.get(producto, 0)) - unidades
                actualizar_inventario_supabase(producto)
                registrar_movimiento(producto, "Salida por venta", unidades, f"Venta de {sabor}", venta_id)
            
            nueva_v = {
                "id": venta_id, "fecha": ahora(), "cliente": cliente.strip() or "Cliente general",
                "categoria": categoria, "sabor": sabor, "presentacion": presentacion,
                "cantidad": int(cantidad), "precio_unitario": precio_unitario, "total": total,
                "medio_pago": metodo_pago, "observacion": "", "consumos": consumos, "estado": "Vigente"
            }
            st.session_state.ventas.append(nueva_v)
            try:
                supabase.table("ventas").insert(nueva_v).execute()
            except Exception as e:
                st.error(f"Error guardando venta en la nube: {e}")
            
            st.balloons()
            avisar(f"¡Venta registrada con éxito y respaldada en la nube por {dinero(total)}!", "🎉")

with tab_inventario:
    st.header("Inventario Actual en la Nube")
    df_inv = pd.DataFrame([{"Producto": p, "Existencias": q} for p, q in st.session_state.inventario.items()])
    st.dataframe(df_inv, use_container_width=True, hide_index=True)

with tab_historial:
    st.header("Historial de Ventas")
    efectivas = ventas_vigentes()
    if efectivas:
        df_v = pd.DataFrame(efectivas).drop(columns=["consumos"], errors="ignore")
        st.dataframe(df_v, use_container_width=True, hide_index=True)
    else:
        st.info("No hay ventas registradas.")

with tab_caja:
    st.header("Caja del Día")
    r = resumen_dia(hoy())
    c1, c2, c3 = st.columns(3)
    c1.metric("Efectivo", dinero(r["efectivo"]))
    c2.metric("Transferencias", dinero(r["transferencias"]))
    c3.metric("Gastos", dinero(r["gastos_total"]))
