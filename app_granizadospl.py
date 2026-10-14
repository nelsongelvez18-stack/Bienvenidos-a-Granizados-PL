import streamlit as st
import pandas as pd
from datetime import datetime

# =========================================================
# CONFIGURACIÓN DE LA APLICACIÓN
# =========================================================
st.set_page_config(
    page_title="POS Granizados PL",
    page_icon="🍧",
    layout="centered"
)

# Estilos visuales con letra gigante para pantallas táctiles
st.markdown("""
<style>
h1 {
    font-size: 42px !important;
    font-weight: bold !important;
    text-align: center;
    color: #ff4b4b;
}
h2, h3, label, .stMarkdown p {
    font-size: 24px !important;
    font-weight: bold !important;
}
button, div[data-testid="stFormSubmitButton"] button {
    font-size: 26px !important;
    font-weight: bold !important;
    padding: 16px !important;
    border-radius: 12px !important;
    background-color: #ff4b4b !important;
    color: white !important;
    border: 2px solid #ff4b4b !important;
}
div[data-testid="stFormSubmitButton"] button {
    background-color: #ff4b4b !important;
}
[data-testid="stMetricValue"] {
    font-size: 32px !important;
    font-weight: bold !important;
}
table { font-size: 20px !important; width: 100% !important; }
th { background-color: #ff4b4b !important; color: white !important; font-size: 22px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🍧 Granizados PL - Punto de Venta")
st.caption("📍 Túquerres, Nariño | El sabor que nos unee")

# =========================================================
# INVENTARIO INICIAL (EN CEROS PARA CARGA MANUAL)
# =========================================================
INVENTARIO_INICIAL = {
    # Materiales y empaques
    "Vaso 12 oz (und)": 0,
    "Sachet 12 oz (und)": 0,
    "Pitillos (und)": 0,
    "Bolsa de papel (und)": 0,
    "Toppings de dulces (porción)": 0,
    "Barquillo (und)": 0,
    "Lluvia de chocolate (porción)": 0,

    # Licores
    "Ron Blanco (copa)": 0,
    "Tequila (copa)": 0,
    "Vodka (copa)": 0,
    "Whisky (copa)": 0,
    "Aguardiente (copa)": 0,
    "Champaña (copa)": 0,
    "Baileys (copa)": 0,

    # Sin alcohol
    "Sabor Bombombum": 0,
    "Sabor Limonada de Coco": 0,
    "Sabor Limonada de Sandía": 0,
    "Sabor Manzana Verde": 0,
    "Sabor Maracululo": 0,
    "Sabor Maracupíña": 0,
    "Sabor Piña Naranja": 0,
    "Sabor Uva": 0,

    # Granizados con alcohol
    "Sabor Agave Ice": 0,
    "Sabor Andromeda Ice": 0,
    "Sabor Bon Bon Bum Ice": 0,
    "Sabor Candy Ice": 0,
    "Sabor Cherryboom Ice": 0,
    "Sabor Cosmico Ice": 0,
    "Sabor Estelar Ice": 0,
    "Sabor Fresa Salvaje Ice": 0,
    "Sabor Fourloko Ice": 0,
    "Sabor Interestelar Ice": 0,
    "Sabor Luxury Ice": 0,
    "Sabor Mango Explosivo Ice": 0,
    "Sabor Miami Ice": 0,
    "Sabor Monaco Ice": 0,
    "Sabor Mora Azul Ice": 0,
    "Sabor Nebula Ice": 0,
    "Sabor Orion Ice": 0,
    "Sabor Smirnoff Lulo Ice": 0,
    "Sabor Smirnoff Limon Ice": 0,
    "Sabor Tropical Caribeña Ice": 0,
    "Sabor Velvet Ice": 0,

    # Cremosos
    "Sabor Bayleys": 0,
    "Sabor Coco Loco": 0,
    "Sabor Piña Colada": 0,
}

if "inventario" not in st.session_state:
    st.session_state.inventario = INVENTARIO_INICIAL.copy()

if "ventas_detalladas" not in st.session_state:
    st.session_state.ventas_detalladas = []

if "historial_cargas" not in st.session_state:
    st.session_state.historial_cargas = []

# =========================================================
# MENÚ OFICIAL DE PRECIOS Y ENLACES
# =========================================================
SABORES_POR_CATEGORIA = {
    "SIN ALCOHOL (12 oz)": {
        "precio": 13000,
        "toppings": ["Toppings de dulces (porción)"],
        "sabores_inventario": {
            "Bombombum": {"insumos": [], "bodega": "Sabor Bombombum"},
            "Limonada de Coco": {"insumos": [], "bodega": "Sabor Limonada de Coco"},
            "Limonada de Sandía": {"insumos": [], "bodega": "Sabor Limonada de Sandía"},
            "Manzana Verde": {"insumos": [], "bodega": "Sabor Manzana Verde"},
            "Maracululo": {"insumos": [], "bodega": "Sabor Maracululo"},
            "Maracupíña": {"insumos": [], "bodega": "Sabor Maracupíña"},
            "Piña Naranja": {"insumos": [], "bodega": "Sabor Piña Naranja"},
            "Uva": {"insumos": [], "bodega": "Sabor Uva"},
        },
    },
    "CON ALCOHOL (12 oz)": {
        "precio": 15000,
        "toppings": ["Toppings de dulces (porción)"],
        "sabores_inventario": {
            "Agave Ice": {"insumos": ["Ron Blanco (copa)", "Tequila (copa)"], "bodega": "Sabor Agave Ice"},
            "Andromeda Ice": {"insumos": ["Vodka (copa)", "Tequila (copa)"], "bodega": "Sabor Andromeda Ice"},
            "Bon Bon Bum Ice": {"insumos": ["Whisky (copa)"], "bodega": "Sabor Bon Bon Bum Ice"},
            "Candy Ice": {"insumos": ["Ron Blanco (copa)", "Vodka (copa)"], "bodega": "Sabor Candy Ice"},
            "Cherryboom Ice": {"insumos": ["Ron Blanco (copa)", "Whisky (copa)"], "bodega": "Sabor Cherryboom Ice"},
            "Cosmico Ice": {"insumos": ["Vodka (copa)", "Champaña (copa)"], "bodega": "Sabor Cosmico Ice"},
            "Estelar Ice": {"insumos": ["Aguardiente (copa)"], "bodega": "Sabor Estelar Ice"},
            "Fresa Salvaje Ice": {"insumos": ["Tequila (copa)"], "bodega": "Sabor Fresa Salvaje Ice"},
            "Fourloko Ice": {"insumos": ["Vodka (copa)"], "bodega": "Sabor Fourloko Ice"},
            "Interestelar Ice": {"insumos": ["Tequila (copa)"], "bodega": "Sabor Interestelar Ice"},
            "Luxury Ice": {"insumos": ["Vodka (copa)"], "bodega": "Sabor Luxury Ice"},
            "Mango Explosivo Ice": {"insumos": ["Tequila (copa)", "Vodka (copa)"], "bodega": "Sabor Mango Explosivo Ice"},
            "Miami Ice": {"insumos": ["Tequila (copa)"], "bodega": "Sabor Miami Ice"},
            "Monaco Ice": {"insumos": ["Whisky (copa)"], "bodega": "Sabor Monaco Ice"},
            "Mora Azul Ice": {"insumos": ["Whisky (copa)"], "bodega": "Sabor Mora Azul Ice"},
            "Nebula Ice": {"insumos": ["Vodka (copa)", "Whisky (copa)"], "bodega": "Sabor Nebula Ice"},
            "Orion Ice": {"insumos": ["Vodka (copa)"], "bodega": "Sabor Orion Ice"},
            "Smirnoff Lulo Ice": {"insumos": ["Vodka (copa)"], "bodega": "Sabor Smirnoff Lulo Ice"},
            "Smirnoff Limon Ice": {"insumos": ["Vodka (copa)"], "bodega": "Sabor Smirnoff Limon Ice"},
            "Tropical Caribeña Ice": {"insumos": ["Tequila (copa)", "Vodka (copa)"], "bodega": "Sabor Tropical Caribeña Ice"},
            "Velvet Ice": {"insumos": ["Vodka (copa)", "Champaña (copa)"], "bodega": "Sabor Velvet Ice"},
        },
    },
    "CREMOSA CON ALCOHOL (12 oz)": {
        "precio": 16000,
        "toppings": ["Barquillo (und)", "Lluvia de chocolate (porción)"],
        "sabores_inventario": {
            "Bayleys": {"insumos": ["Baileys (copa)", "Whisky (copa)"], "bodega": "Sabor Bayleys"},
            "Coco Loco": {"insumos": ["Ron Blanco (copa)"], "bodega": "Sabor Coco Loco"},
            "Piña Colada": {"insumos": ["Ron Blanco (copa)"], "bodega": "Sabor Piña Colada"},
        },
    },
}

IMAGENES_SECCION = {
    "SIN ALCOHOL (12 oz)": "https://unsplash.com",
    "CON ALCOHOL (12 oz)": "https://unsplash.com",
    "CREMOSA CON ALCOHOL (12 oz)": "https://unsplash.com"
}

def pesos(valor):
    return f"${valor:,.0f} COP"

def receta_pedido(categoria, sabor_nombre, presentacion):
    config = SABORES_POR_CATEGORIA[categoria]
    sabor_info = config["sabores_inventario"][sabor_nombre]
    empaque = "Vaso 12 oz (und)" if presentacion == "Vaso" else "Sachet 12 oz (und)"

    receta = {
        empaque: 1,
        "Pitillos (und)": 1,
        "Bolsa de papel (und)": 1,
        sabor_info["bodega"]: 1,
    }
    for topping in config["toppings"]:
        receta[topping] = receta.get(topping, 0) + 1
    for licor in sabor_info["insumos"]:
        receta[licor] = receta.get(licor, 0) + 1
    return receta

def procesar_pedido(categoria, sabor_nombre, presentacion, cantidad, medio_pago):
    config = SABORES_POR_CATEGORIA[categoria]
    receta_unitaria = receta_pedido(categoria, sabor_nombre, presentacion)
    receta_total = {insumo: unidades * cantidad for insumo, unidades in receta_unitaria.items()}

    faltantes = []
    for insumo, unidades_necesarias in receta_total.items():
        disponible = st.session_state.inventario.get(insumo, 0)
        if disponible < unidades_necesarias:
            faltantes.append(f"{insumo}: disponibles {int(disponible)}, necesarios {unidades_necesarias}")

    if faltantes:
        st.error("❌ No se registró la venta. Inventario insuficiente:")
        for detalle in faltantes:
            st.write(f"- {detalle}")
        return False

    for insumo, unidades in receta_total.items():
        st.session_state.inventario[insumo] -= unidades

    precio_unitario = config["precio"]
    total = precio_unitario * cantidad
    st.session_state.ventas_detalladas.append({
        "Fecha y hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Categoría": categoria,
        "Sabor": sabor_nombre,
        "Presentación": presentacion,
        "Cantidad": cantidad,
        "Medio de Pago": medio_pago,
        "Precio unitario (COP)": precio_unitario,
        "Total (COP)": total,
    })
    return True

# =========================================================
# FORMULARIO DE VENTA DIRECTA
# =========================================================
st.subheader("🛍️ Registrar venta")

with st.container(border=True):
    categoria = st.selectbox("1. Seleccione la categoría del menú:", options=list(SABORES_POR_CATEGORIA.keys()), key="cat_v")
    sabores = list(SABORES_POR_CATEGORIA[categoria]["sabores_inventario"].keys())
    sabor = st.selectbox("2. Seleccione el sabor:", options=sabores, key="sab_v")
