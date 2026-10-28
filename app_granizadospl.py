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
for _cat, _sabores in SABORES.items():
    for _s in _sabores:
        INVENTARIO_BASE[clave_sabor(_s)] = 0

# ---------------------------------------------------------------- CONEXIÓN SUPABASE
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        st.error("⚠️ Falta configurar SUPABASE_URL y SUPABASE_KEY en los Secrets de Streamlit.")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

# ---------------------------------------------------------------- FUNCIONES DE PERSISTENCIA (SUPABASE)
def cargar_inventario_desde_supabase():
    """Lee el inventario guardado en Supabase; mapea 'nombre' y 'stock'."""
    try:
        res = supabase.table("inventario").select("*").execute()
        if res.data and len(res.data) > 0:
            inv = {row["nombre"]: row["stock"] for row in res.data}
            for k, v in INVENTARIO_BASE.items():
                if k not in inv:
                    inv[k] = v
            return inv
        else:
            return INVENTARIO_BASE.copy()
    except Exception as e:
        st.warning(f"Error consultando inventario: {e}")
        return INVENTARIO_BASE.copy()

def guardar_item_inventario(nombre_item, nuevo_stock):
    """Guarda o actualiza el stock de un producto en Supabase."""
    try:
        supabase.table("inventario").upsert(
            {"nombre": nombre_item, "stock": int(nuevo_stock)}, 
            on_conflict="nombre"
        ).execute()
    except Exception as e:
        st.error(f"Error guardando inventario en Supabase: {e}")

def registrar_compra_db(item, cantidad, costo_total):
    """Registra una compra en la tabla 'compras' y suma al stock persistente."""
    try:
        supabase.table("compras").insert({
            "item": item,
            "cantidad": int(cantidad),
            "costo_total": int(costo_total),
            "fecha": datetime.now(TZ).isoformat()
        }).execute()
        
        st.session_state.inventario[item] = st.session_state.inventario.get(item, 0) + int(cantidad)
        guardar_item_inventario(item, st.session_state.inventario[item])
        return True
    except Exception as e:
        st.error(f"Error registrando compra: {e}")
        return False

def registrar_venta_db(categoria, sabor, precio, metodo_pago, notas=""):
    """Registra la venta en 'ventas' y descuenta del stock en Supabase."""
    try:
        supabase.table("ventas").insert({
            "categoria": categoria,
            "sabor": sabor,
            "precio": int(precio),
            "metodo_pago": metodo_pago,
            "notas": notas,
            "fecha": datetime.now(TZ).isoformat()
        }).execute()

        cs = clave_sabor(sabor)
        if cs in st.session_state.inventario and st.session_state.inventario[cs] > 0:
            st.session_state.inventario[cs] -= 1
            guardar_item_inventario(cs, st.session_state.inventario[cs])

        for insumo in ["Vaso 12 oz (und)", "Pitillos (und)"]:
            if insumo in st.session_state.inventario and st.session_state.inventario[insumo] > 0:
                st.session_state.inventario[insumo] -= 1
                guardar_item_inventario(insumo, st.session_state.inventario[insumo])
                
        return True
    except Exception as e:
        st.error(f"Error registrando venta: {e}")
        return False

# ---------------------------------------------------------------- ESTADO DE SESIÓN
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "inventario" not in st.session_state:
    st.session_state.inventario = cargar_inventario_desde_supabase()

# ---------------------------------------------------------------- AUTENTICACIÓN
if not st.session_state.autenticado:
    st.title("🍧 Granizados PL - Acceso al Sistema")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if LOGO.exists():
            st.image(str(LOGO), width=200)
        st.subheader("Iniciar Sesión")
        pwd_input = st.text_input("Ingrese la contraseña de acceso:", type="password")
        if st.button("Ingresar", use_container_width=True):
            if pwd_input == CLAVE_ACCESO:
                st.session_state.autenticado = True
                st.session_state.inventario = cargar_inventario_desde_supabase()
                st.success("¡Bienvenido!")
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop()

# ---------------------------------------------------------------- NAVEGACIÓN
st.sidebar.title("🍧 Granizados PL")
if LOGO.exists():
    st.sidebar.image(str(LOGO), width=150)

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

opcion = st.sidebar.radio(
    "Menú de Opciones:",
    ["🛒 Registrar Venta", "📦 Compras e Inventario", "📊 Reportes y Estadística"]
)

st.sidebar.markdown("---")
st.sidebar.info(random.choice(FRASES_MOTIVADORAS))

# ---------------------------------------------------------------- 1. REGISTRAR VENTA
if opcion == "🛒 Registrar Venta":
    st.header("🛒 Registrar Nueva Venta")
    
    cat = st.selectbox("Categoría:", list(SABORES.keys()))
    sab = st.selectbox("Sabor:", SABORES[cat])
    pago = st.selectbox("Método de Pago:", METODOS_PAGO)
    precio = PRECIOS_VENTA[cat]
    notas = st.text_input("Notas adicionales (opcional):")
    
    st.write(f"**Precio:** ${precio:,}")
    
    if st.button("✅ Confirmar Venta", type="primary", use_container_width=True):
        if registrar_venta_db(cat, sab, precio, pago, notas):
            st.balloons()
            st.success(f"¡Venta de {sab} registrada con éxito!")

# ---------------------------------------------------------------- 2. COMPRAS E INVENTARIO
elif opcion == "📦 Compras e Inventario":
    st.header("📦 Gestión de Inventario y Registro de Compras")
    
    tab1, tab2 = st.tabs(["Ingresar Compra", "Estado del Inventario"])
    
    with tab1:
        st.subheader("Registrar Nueva Compra / Reabastecimiento")
        item_compra = st.selectbox("Seleccione el producto o insumo:", list(INVENTARIO_BASE.keys()))
        cant_compra = st.number_input("Cantidad que ingresa:", min_value=1, value=10, step=1)
        costo_compra = st.number_input("Costo total ($):", min_value=0, value=0, step=500)
        
        if st.button("📥 Guardar Compra", use_container_width=True):
            if registrar_compra_db(item_compra, cant_compra, costo_compra):
                st.success(f"Se agregaron {cant_compra} unidades a '{item_compra}'.")
                st.rerun()

    with tab2:
        st.subheader("Inventario Actual en Tiempo Real")
        if st.button("🔄 Recargar Inventario desde Supabase"):
            st.session_state.inventario = cargar_inventario_desde_supabase()
            st.rerun()
            
        df_inv = pd.DataFrame([
            {"Producto / Insumo": k, "Cantidad Disponible": v} 
            for k, v in st.session_state.inventario.items()
        ])
        
        st.dataframe(df_inv, use_container_width=True)

# ---------------------------------------------------------------- 3. REPORTES Y ESTADÍSTICAS
elif opcion == "📊 Reportes y Estadística":
    st.header("📊 Reportes y Métricas de Ventas")
    
    try:
        res = supabase.table("ventas").select("*").execute()
        if res.data:
            df_v = pd.DataFrame(res.data)
            
            total_recaudado = df_v["precio"].sum()
            total_unidades = len(df_v)
            
            col1, col2 = st.columns(2)
            col1.metric("💰 Ventas Totales ($)", f"${total_recaudado:,}")
            col2.metric("🍧 Granizados Vendidos", f"{total_unidades} und")
            
            st.markdown("---")
            st.subheader("🍧 Ventas Detalladas por Nombre de Sabor")
            
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
                
                m1, m2 = st.columns(2)
                m1.success(f"🔥 **Sabor Más Vendido:** {mejor_sabor['sabor']} ({mejor_sabor['Cantidad_Vendida']} unidades)")
                m2.warning(f"⚠️ **Sabor Con Menor Salida:** {peor_sabor['sabor']} ({peor_sabor['Cantidad_Vendida']} unidades)")
            else:
                st.info("No hay registros para la categoría seleccionada.")
        else:
            st.info("Aún no se han registrado ventas en la base de datos.")
    except Exception as e:
        st.error(f"Error al cargar reportes desde Supabase: {e}")
