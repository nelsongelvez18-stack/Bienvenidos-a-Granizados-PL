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

st.set_page_config(
    page_title="Granizados PL - Punto de Venta", 
    page_icon="🍧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------- ESTILOS CSS PERSONALIZADOS
st.markdown("""
    <style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stCard {
        background: rgba(30, 41, 59, 0.7);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }
    .stButton>button {
        border-radius: 12px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
    }
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #10b981 !important;
        font-weight: 800;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- CONFIGURACIÓN DE DATOS
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
for _cat, _sabores in SABORES.items():
    for _s in _sabores:
        INVENTARIO_BASE[clave_sabor(_s)] = 0

PRODUCTOS_ELIMINADOS = {"Sachet 12 oz (und)", "Aguardiente (copa)", "Baileys (copa)", "Champaña (copa)", "Ron Blanco (copa)", "Tequila (copa)", "Vodka (copa)", "Whisky (copa)", "Lluvia de chocolate (porción)"}

# ---------------------------------------------------------------- CONEXIÓN SUPABASE
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
    return datetime.now(TZ).isoformat()

def hoy():
    return datetime.now(TZ).date()

def dinero(valor):
    return f"${int(round(valor)):,.0f}".replace(",", ".")

def dinero_html(valor):
    return dinero(valor).replace("$", "&#36;")

def dinero_md(valor):
    return dinero(valor).replace("$", "\\$")

# ---------------------------------------------------------------- FUNCIONES DE PERSISTENCIA
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
    except Exception as e:
        st.warning(f"Error consultando inventario: {e}")
        return dict(INVENTARIO_BASE)

def guardar_stock_supabase(producto, stock):
    try:
        res = supabase.table("inventario").select("*").eq("nombre", producto).execute()
        if res.data:
            supabase.table("inventario").update({"stock": int(stock)}).eq("nombre", producto).execute()
        else:
            supabase.table("inventario").insert({"nombre": producto, "stock": int(stock), "precio": 0, "costo": 0}).execute()
    except Exception as e:
        st.error(f"Error sincronizando stock: {e}")

def registrar_compra_db(item, cantidad, costo_total):
    try:
        desc = f"Compra/Ingreso de {cantidad} unidades de {item}"
        supabase.table("compras").insert({
            "descripcion": desc,
            "monto": float(costo_total),
            "proveedor": "General",
            "fecha": ahora()
        }).execute()
        
        st.session_state.inventario[item] = st.session_state.inventario.get(item, 0) + int(cantidad)
        guardar_stock_supabase(item, st.session_state.inventario[item])
        return True
    except Exception as e:
        st.error(f"Error registrando compra: {e}")
        return False

def registrar_venta_db(categoria, sabor, precio, metodo_pago, notas=""):
    try:
        supabase.table("ventas").insert({
            "categoria": categoria,
            "sabor": sabor,
            "precio": float(precio),
            "metodo_pago": metodo_pago,
            "notas": notas,
            "fecha": ahora()
        }).execute()

        cs = clave_sabor(sabor)
        if cs in st.session_state.inventario and st.session_state.inventario[cs] > 0:
            st.session_state.inventario[cs] -= 1
            guardar_stock_supabase(cs, st.session_state.inventario[cs])

        for insumo in ["Vaso 12 oz (und)", "Pitillos (und)"]:
            if insumo in st.session_state.inventario and st.session_state.inventario[insumo] > 0:
                st.session_state.inventario[insumo] -= 1
                guardar_stock_supabase(insumo, st.session_state.inventario[insumo])
                
        return True
    except Exception as e:
        st.error(f"Error registrando venta: {e}")
        return False

# ---------------------------------------------------------------- ESTADO DE SESIÓN
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_inventario_supabase()

# ---------------------------------------------------------------- AUTENTICACIÓN
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🍧 Granizados PL - Acceso al Sistema</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if LOGO.exists():
            st.image(str(LOGO), use_container_width=True)
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("🔐 Iniciar Sesión")
        pwd_input = st.text_input("Ingrese la contraseña de acceso:", type="password")
        if st.button("🚀 Ingresar al Sistema", use_container_width=True, type="primary"):
            if pwd_input == CLAVE_ACCESO:
                st.session_state.autenticado = True
                st.session_state.inventario = cargar_inventario_supabase()
                st.success("¡Bienvenido a Granizados PL!")
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------------- BARRA LATERAL
st.sidebar.markdown("<h2 style='text-align: center;'>🍧 Granizados PL</h2>", unsafe_allow_html=True)
if LOGO.exists():
    st.sidebar.image(str(LOGO), use_container_width=True)

opcion = st.sidebar.radio(
    "Navegación:",
    ["🛒 Registrar Venta", "📦 Compras e Inventario", "📊 Reportes y Estadística"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(random.choice(FRASES_MOTIVADORAS))

# ---------------------------------------------------------------- 1. REGISTRAR VENTA
if opcion == "🛒 Registrar Venta":
    st.title("🛒 Punto de Venta - Granizados PL")
    
    tab_sin, tab_con, tab_crem = st.tabs([
        "🟢 SIN ALCOHOL ($13,000)", 
        "💗 CON ALCOHOL ($15,000)", 
        "🟡 CREMOSOS ($15,000)"
    ])
    
    def formulario_venta(categoria):
        st.markdown(f"<div class='stCard' style='border-left: 5px solid {COLORES[categoria]};'>", unsafe_allow_html=True)
        st.subheader(f"Categoría: {categoria}")
        
        col_a, col_b = st.columns(2)
        with col_a:
            sabor_sel = st.selectbox("Seleccione el Sabor:", SABORES[categoria], key=f"sab_{categoria}")
            pago_sel = st.selectbox("Método de Pago:", METODOS_PAGO, key=f"pago_{categoria}")
        
        with col_b:
            precio_unitario = PRECIOS_VENTA[categoria]
            st.markdown(f"### Precio: **${precio_unitario:,}**")
            notas_input = st.text_input("Notas adicionales (opcional):", key=f"notas_{categoria}")
        
        cs = clave_sabor(sabor_sel)
        stock_sabor = st.session_state.inventario.get(cs, 0)
        st.caption(f"📦 Unidades de **{sabor_sel}** disponibles en inventario: **{stock_sabor}**")
        
        if st.button(f"✅ Confirmar Venta de {sabor_sel}", type="primary", use_container_width=True, key=f"btn_{categoria}"):
            if registrar_venta_db(categoria, sabor_sel, precio_unitario, pago_sel, notas_input):
                st.balloons()
                st.success(f"¡Venta registrada con éxito! ({sabor_sel} - ${precio_unitario:,})")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_sin:
        formulario_venta("SIN ALCOHOL")
    with tab_con:
        formulario_venta("CON ALCOHOL")
    with tab_crem:
        formulario_venta("CREMOSOS")

# ---------------------------------------------------------------- 2. COMPRAS E INVENTARIO
elif opcion == "📦 Compras e Inventario":
    st.title("📦 Gestión de Compras y Control de Stock")
    
    tab1, tab2 = st.tabs(["📥 Ingresar Compras", "📋 Estado del Inventario Real"])
    
    with tab1:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Registrar Nueva Compra / Reabastecimiento")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            item_compra = st.selectbox("Seleccione Producto o Insumo:", list(INVENTARIO_BASE.keys()))
            cant_compra = st.number_input("Cantidad que ingresa:", min_value=1, value=10, step=1)
        with col_c2:
            costo_compra = st.number_input("Costo Total Invertido ($):", min_value=0, value=0, step=1000)
        
        if st.button("📥 Guardar e Incrementar Inventario", type="primary", use_container_width=True):
            if registrar_compra_db(item_compra, cant_compra, costo_compra):
                st.success(f"¡Genial! Se agregaron {cant_compra} unidades a '{item_compra}' y se guardó en Supabase.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<div class='stCard'>", unsafe_allow_html=True)
        st.subheader("Inventario en Tiempo Real (Sincronizado con Supabase)")
        
        if st.button("🔄 Recargar Datos de la Base de Datos"):
            st.session_state.inventario = cargar_inventario_supabase()
            st.rerun()
            
        filtro_inv = st.text_input("🔍 Buscar insumo o sabor en inventario:")
        datos_inv = [
            {"Producto / Insumo / Sabor": k, "Stock Disponible": v, "Estado": "⚠️ Bajo Stock" if v <= UMBRAL_BAJO else "✅ Disponible"} 
            for k, v in st.session_state.inventario.items()
            if filtro_inv.lower() in k.lower()
        ]
        df_inv = pd.DataFrame(datos_inv)
        st.dataframe(df_inv, use_container_width=True, height=450)
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------- 3. REPORTES Y ESTADÍSTICA
elif opcion == "📊 Reportes y Estadística":
    st.title("📊 Reportes y Métricas de Rendimiento")
    
    try:
        res = supabase.table("ventas").select("*").execute()
        if res.data:
            df_v = pd.DataFrame(res.data)
            total_recaudado = df_v["precio"].sum()
            total_unidades = len(df_v)
            
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.markdown(f"<div class='stCard'><h3>💰 Total Recaudado</h3><h2>${total_recaudado:,}</h2></div>", unsafe_allow_html=True)
            with m_col2:
                st.markdown(f"<div class='stCard'><h3>🍧 Total Granizados Vendidos</h3><h2>{total_unidades} und</h2></div>", unsafe_allow_html=True)
            
            st.markdown("<div class='stCard'>", unsafe_allow_html=True)
            st.subheader("📊 Desglose de Ventas por Nombre de Sabor")
            
            cat_filtro = st.selectbox("Filtrar por Categoría:", ["Todas"] + list(SABORES.keys()))
            if cat_filtro != "Todas":
                df_v = df_v[df_v["categoria"] == cat_filtro]
            
            if not df_v.empty:
                df_sabores = df_v.groupby(["categoria", "sabor"]).agg(
                    Cantidad_Vendida=("sabor", "count"),
                    Total_Recaudado=("precio", "sum")
                ).reset_index().sort_values(by="Cantidad_Vendida", ascending=False)
                
                st.dataframe(df_sabores, use_container_width=True)
                
                mejor_sabor = df_sabores.iloc[0]
                peor_sabor = df_sabores.iloc[-1]
                
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.success(f"🔥 **Sabor Más Vendido:** {mejor_sabor['sabor']} ({mejor_sabor['Cantidad_Vendida']} unidades)")
                with res_col2:
                    st.warning(f"⚠️ **Sabor Con Menor Salida:** {peor_sabor['sabor']} ({peor_sabor['Cantidad_Vendida']} unidades)")
            else:
                st.info("No hay registros para la categoría seleccionada.")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Aún no se han registrado ventas en la base de datos.")
    except Exception as e:
        st.error(f"Error al cargar reportes desde la base de datos: {e}")
