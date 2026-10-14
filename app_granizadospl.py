import json
from pathlib import Path
from datetime import datetime, date
from collections import Counter

import pandas as pd
import streamlit as st


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="Granizados PL - Punto de Venta",
    page_icon="🍧",
    layout="wide",
)

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}
h1, h2, h3 {
    color: #087f5b;
}
div[data-testid="stMetric"] {
    background-color: #f4fbf7;
    border: 1px solid #d8eee2;
    padding: 12px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# ARCHIVOS Y CONFIGURACIÓN
# =========================================================

CARPETA_DATOS = Path(__file__).resolve().parent / "datos_granizados_pl"
ARCHIVO_DATOS = CARPETA_DATOS / "datos_pos.json"
CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

MEDIOS_PAGO = [
    "Efectivo",
    "Transferencia Nequi / Billeteras virtuales",
]

CATEGORIAS = ["SIN ALCOHOL", "CON ALCOHOL", "CREMOSOS"]

PRECIO_MENU = {
    "SIN ALCOHOL": 13000,
    "CON ALCOHOL": 15000,
    "CREMOSOS": 15000,
}


# =========================================================
# TOPPINGS
# =========================================================

TOPPINGS = {
    "Minichicles": "Topping Minichicles (porción)",
    "Goma bandera": "Topping Goma bandera (porción)",
    "Bombón": "Topping Bombón (und)",
    "Sal pimienta": "Topping Sal pimienta (porción)",
    "Bolas de chicle": "Topping Bolas de chicle (porción)",
    "Goma gusano": "Topping Goma gusano (porción)",
    "Goma splash": "Topping Goma splash (porción)",
}

TOPPINGS_BASE = {
    "SIN ALCOHOL": ["Minichicles", "Goma bandera", "Goma gusano"],
    "CON ALCOHOL": ["Goma gusano", "Goma splash"],
    "CREMOSOS": [],
}


# =========================================================
# SABORES
# =========================================================

SABORES_SIN_ALCOHOL = [
    "Bombombum", "Chicle", "Frutos Rojos", "Limonada Cerezada",
    "Limonada de Coco", "Limonada de Sandía", "Mango Biche",
    "Manzana Rosada", "Manzana Verde", "Maracumango", "Maracululo",
    "Maracupiña", "Mora Azul", "Uva",
]

SABORES_CON_ALCOHOL = [
    "Agave Ice", "Andromeda Ice", "Bon Bon Bum Ice", "Candy Ice",
    "Cherryboom Ice", "Cosmico Ice", "Estelar Ice",
    "Fresa Salvaje Ice", "Fourloko Ice", "Interestelar Ice",
    "Luxury Ice", "Mango Explosivo Ice", "Miami Ice", "Monaco Ice",
    "Mora Azul Ice", "Nebula Ice", "Orion Ice", "Smirnoff Lulo Ice",
    "Smirnoff Limon Ice", "Tropical Caribeña Ice", "Velvet Ice",
]

SABORES_CREMOSOS = ["Bayleys", "Coco Loco", "Piña Colada"]

SABORES_POR_CATEGORIA = {
    "SIN ALCOHOL": SABORES_SIN_ALCOHOL,
    "CON ALCOHOL": SABORES_CON_ALCOHOL,
    "CREMOSOS": SABORES_CREMOSOS,
}


# =========================================================
# INVENTARIO BASE
# =========================================================

INVENTARIO_BASE = {
    "Sachet 12 oz (und)": 0,
    "Vaso 12 oz (und)": 0,
    "Pitillos (und)": 0,
    "Bolsa de papel (und)": 0,
    "Topping Minichicles (porción)": 0,
    "Topping Goma bandera (porción)": 0,
    "Topping Bombón (und)": 0,
    "Topping Sal pimienta (porción)": 0,
    "Topping Bolas de chicle (porción)": 0,
    "Topping Goma gusano (porción)": 0,
    "Topping Goma splash (porción)": 0,
    "Lluvia de chocolate (porción)": 0,
    "Barquillo (und)": 0,
}

for sabores in SABORES_POR_CATEGORIA.values():
    for sabor in sabores:
        nombre = "Sabor Maracupíña" if sabor == "Maracupiña" else f"Sabor {sabor}"
        INVENTARIO_BASE[nombre] = 0

PRODUCTOS_EXCLUIDOS = {
    "Aguardiente (copa)",
    "Baileys (copa)",
    "Champaña (copa)",
    "Ron Blanco (copa)",
    "Tequila (copa)",
    "Vodka (copa)",
    "Whisky (copa)",
}


# =========================================================
# FUNCIONES GENERALES Y PERSISTENCIA
# =========================================================

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pesos(valor):
    return f"${float(valor):,.0f}".replace(",", ".")


def guardar_datos():
    datos = {
        "inventario": st.session_state.inventario,
        "ventas": st.session_state.ventas,
        "movimientos": st.session_state.movimientos,
        "gastos": st.session_state.gastos,
        "anulaciones": st.session_state.anulaciones,
    }

    temporal = CARPETA_DATOS / "datos_pos_temp.json"

    try:
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=4)

        temporal.replace(ARCHIVO_DATOS)

    except Exception as error:
        st.error(f"No fue posible guardar los datos: {error}")


def cargar_datos():
    datos = {
        "inventario": INVENTARIO_BASE.copy(),
        "ventas": [],
        "movimientos": [],
        "gastos": [],
        "an
