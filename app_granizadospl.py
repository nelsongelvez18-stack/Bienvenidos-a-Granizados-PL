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

CATEGORIAS = [
    "SIN ALCOHOL",
    "CON ALCOHOL",
    "CREMOSOS",
]

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
    "SIN ALCOHOL": [
        "Minichicles",
        "Goma bandera",
        "Goma gusano",
    ],
    "CON ALCOHOL": [
        "Goma gusano",
        "Goma splash",
    ],
    "CREMOSOS": [],
}


# =========================================================
# SABORES DISPONIBLES
# =========================================================

SABORES_SIN_ALCOHOL = [
    "Bombombum",
    "Chicle",
    "Frutos Rojos",
    "Limonada Cerezada",
    "Limonada de Coco",
    "Limonada de Sandía",
    "Mango Biche",
    "Manzana Rosada",
    "Manzana Verde",
    "Maracumango",
    "Maracululo",
    "Maracupiña",
    "Mora Azul",
    "Uva",
]

SABORES_CON_ALCOHOL = [
    "Agave Ice",
    "Andromeda Ice",
    "Bon Bon Bum Ice",
    "Candy Ice",
    "Cherryboom Ice",
    "Cosmico Ice",
    "Estelar Ice",
    "Fresa Salvaje Ice",
    "Fourloko Ice",
    "Interestelar Ice",
    "Luxury Ice",
    "Mango Explosivo Ice",
    "Miami Ice",
    "Monaco Ice",
    "Mora Azul Ice",
    "Nebula Ice",
    "Orion Ice",
    "Smirnoff Lulo Ice",
    "Smirnoff Limon Ice",
    "Tropical Caribeña Ice",
    "Velvet Ice",
]

SABORES_CREMOSOS = [
    "Bayleys",
    "Coco Loco",
    "Piña Colada",
]

SABORES_POR_CATEGORIA = {
    "SIN ALCOHOL": SABORES_SIN_ALCOHOL,
    "CON ALCOHOL": SABORES_CON_ALCOHOL,
    "CREMOSOS": SABORES_CREMOSOS,
}


# =========================================================
# INVENTARIO BASE
# =========================================================

INVENTARIO_BASE = {
    # Empaques
    "Sachet 12 oz (und)": 0,
    "Vaso 12 oz (und)": 0,
    "Pitillos (und)": 0,
    "Bolsa de papel (und)": 0,

    # Toppings adicionales
    "Topping Minichicles (porción)": 0,
    "Topping Goma bandera (porción)": 0,
    "Topping Bombón (und)": 0,
    "Topping Sal pimienta (porción)": 0,
    "Topping Bolas de chicle (porción)": 0,
    "Topping Goma gusano (porción)": 0,
    "Topping Goma splash (porción)": 0,

    # Complementos de cremosos
    "Lluvia de chocolate (porción)": 0,
    "Barquillo (und)": 0,
}

# Se agrega un producto de inventario por cada sabor.
for sabores in SABORES_POR_CATEGORIA.values():
    for sabor in sabores:
        if sabor == "Maracupiña":
            clave = "Sabor Maracupíña"
        else:
            clave = f"Sabor {sabor}"

        INVENTARIO_BASE[clave] = 0


# =========================================================
# PRODUCTOS QUE NO SE CONTROLARÁN COMO INVENTARIO
# =========================================================

# Se excluyen los licores por copa, porque el producto se
# compra elaborado y listo para vender.
PRODUCTOS_EXCLUIDOS = {
    "Aguardiente (copa)",
    "Baileys (copa)",
    "Champaña (copa)",
    "Ron Blanco (copa)",
    "Tequila (copa)",
    "Vodka (copa)",
    "Whisky (copa)",
}

# Barquillo se conserva como complemento de los cremosos.
# No se considera un licor ni se elimina del inventario.


# =========================================================
# FUNCIONES GENERALES
# =========================================================

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pesos(valor):
    return f"${float(valor):,.0f}".replace(",", ".")


def guardar_datos():
    """Guarda la información actual en un archivo JSON."""

    datos = {
        "inventario": st.session_state.inventario,
        "ventas": st.session_state.ventas,
        "movimientos": st.session_state.movimientos,
        "gastos": st.session_state.gastos,
        "anulaciones": st.session_state.anulaciones,
    }

    try:
        ARCHIVO_TEMPORAL = CARPETA_DATOS / "datos_pos_temp.json"

        with open(ARCHIVO_TEMPORAL, "w", encoding="utf-8") as archivo:
            json.dump(
                datos,
                archivo,
                ensure_ascii=False,
                indent=4,
            )

        ARCHIVO_TEMPORAL.replace(ARCHIVO_DATOS)

    except Exception as error:
        st.error(f"No fue posible guardar los datos: {error}")


def cargar_datos():
    """Carga los datos guardados y conserva el inventario inicial en cero."""

    datos = {
        "inventario": INVENTARIO_BASE.copy(),
        "ventas": [],
        "movimientos": [],
        "gastos": [],
        "anulaciones": [],
    }

    if ARCHIVO_DATOS.exists():
        try:
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as archivo:
                datos_guardados = json.load(archivo)

            inventario_guardado = datos_guardados.get("inventario", {})

            # Recupera las existencias guardadas, excepto los licores
            # por copa que ya no se manejarán.
            for producto, cantidad in inventario_guardado.items():
                if producto not in PRODUCTOS_EXCLUIDOS:
                    datos["inventario"][producto] = cantidad

            datos["ventas"] = datos_guardados.get("ventas", [])
            datos["movimientos"] = datos_guardados.get(
                "movimientos", []
            )
            datos["gastos"] = datos_guardados.get("gastos", [])
            datos["anulaciones"] = datos_guardados.get(
                "anulaciones", []
            )

        except Exception as error:
            st.error(
                "No fue posible leer el archivo de datos. "
                f"Detalle: {error}"
            )

    return datos


# =========================================================
# INICIALIZACIÓN DE SESIÓN
# =========================================================

if "datos_inicializados" not in st.session_state:
    datos = cargar_datos()

    st.session_state.inventario = datos["inventario"]
    st.session_state.ventas = datos["ventas"]
    st.session_state.movimientos = datos["movimientos"]
    st.session_state.gastos = datos["gastos"]
    st.session_state.anulaciones = datos["anulaciones"]

    st.session_state.datos_inicializados = True

# Asegura que existan todas las claves nuevas del inventario.
for producto, cantidad in INVENTARIO_BASE.items():
    if producto not in st.session_state.inventario:
        st.session_state.inventario[producto] = cantidad

# Elimina los productos por copa de la sesión actual.
for producto in PRODUCTOS_EXCLUIDOS:
    st.session_state.inventario.pop(producto, None)


# =========================================================
# FUNCIONES DE INVENTARIO Y RECETAS
# =========================================================

def clave_sabor(sabor):
    if sabor == "Maracupiña":
        return "Sabor Maracupíña"

    return f"Sabor {sabor}"


def crear_receta(
    categoria,
    sabor,
    usar_vaso,
    toppings_adicionales=None,
):
    """
    Calcula los productos que se descuentan por cada venta.

    El sachet es el empaque predeterminado.
    Si el cliente solicita vaso, se descuenta el vaso en lugar
    del sachet.

    Los granizados con alcohol se consideran productos elaborados:
    no descuentan licores por copa.
    """

    receta = Counter()

    # Una unidad del sabor vendido.
    receta[clave_sabor(sabor)] += 1

    # Toppings incluidos según la categoría.
    for topping in TOPPINGS_BASE.get(categoria, []):
        receta[TOPPINGS[topping]] += 1

    # Complementos incluidos en los cremosos.
    if categoria == "CREMOSOS":
        receta["Lluvia de chocolate (porción)"] += 1
        receta["Barquillo (und)"] += 1

    # Toppings adicionales seleccionados en la venta.
    if toppings_adicionales:
        for topping in toppings_adicionales:
            if topping in TOPPINGS:
                receta[TOPPINGS[topping]] += 1

    # Empaque: sachet predeterminado o vaso opcional.
    if usar_vaso:
        receta["Vaso 12 oz (und)"] += 1
    else:
        receta["Sachet 12 oz (und)"] += 1

    # Complementos de empaque.
    receta["Pitillos (und)"] += 1
    receta["Bolsa de papel (und)"] += 1

    return receta


def calcular_faltantes(receta, cantidad=1):
    faltantes = {}

    for producto, unidades in receta.items():
        requerido = unidades * cantidad
        disponible = st.session_state.inventario.get(producto, 0)

        if disponible < requerido:
            faltantes[producto] = {
                "requerido": requerido,
                "disponible": disponible,
                "faltante": requerido - disponible,
            }

    return faltantes


def registrar_movimiento(
    producto,
    tipo,
    cantidad,
    detalle="",
):
    st.session_state.movimientos.append({
        "fecha": ahora(),
        "producto": producto,
        "tipo": tipo,
        "cantidad": cantidad,
        "detalle": detalle,
    })


def ventas_vigentes():
    return [
        venta
        for venta in st.session_state.ventas
        if not venta.get("anulada", False)
    ]


def registrar_venta(
    categoria,
    sabor,
    cantidad,
    usar_vaso,
    metodo_pago,
    toppings_adicionales,
    cliente,
    observacion,
):
    receta = crear_receta(
        categoria,
        sabor,
        usar_vaso,
        toppings_adicionales,
    )

    faltantes = calcular_faltantes(receta, cantidad)

    if faltantes:
        return False, faltantes

    precio_unitario = PRECIO_MENU[categoria]
    total = precio_unitario * cantidad

    # Descuento automático de inventario.
    for producto, unidades in receta.items():
        descuento = unidades * cantidad

        st.session_state.inventario[producto] -= descuento

        registrar_movimiento(
            producto=producto,
            tipo="Venta",
            cantidad=-descuento,
            detalle=f"{categoria} - {sabor}",
        )

    numero_venta = (
        max(
            [
                int(v.get("id", 0))
                for v in st.session_state.ventas
            ],
            default=0,
        ) + 1
    )

    venta = {
        "id": numero_venta,
        "fecha": ahora(),
        "categoria": categoria,
        "sabor": sabor,
        "cantidad": cantidad,
        "presentacion": "Vaso 12 oz" if usar_vaso else "Sachet 12 oz",
        "precio_unitario": precio_unitario,
        "total": total,
        "metodo_pago": metodo_pago,
        "toppings_adicionales": ", ".join(toppings_adicionales),
        "cliente": cliente,
        "observacion": observacion,
        "consumo": dict(receta),
        "anulada": False,
    }

    st.session_state.ventas.append(venta)
    guardar_datos()

    return True, venta


# =========================================================
# ENCABEZADO
# =========================================================

st.title("🍧 Granizados PL - Punto de Venta")
st.caption(
    "Sistema de ventas, inventario, caja, gastos y reportes."
)

st.info(
    "El sachet es el empaque predeterminado. El cliente solo "
    "selecciona si desea un vaso de 12 oz. Los granizados con "
    "alcohol se controlan como productos elaborados, sin descontar "
    "licores por copa."
)


# =========================================================
# PESTAÑAS
# =========================================================

tab_ventas, tab_inventario, tab_historial, tab_caja, tab_reportes = (
    st.tabs([
        "🛒 Ventas",
        "📦 Inventario",
        "🧾 Historial",
        "💵 Caja y gastos",
        "📊 Reportes",
    ])
)


# =========================================================
# PESTAÑA 1: VENTAS
# =========================================================

with tab_ventas:
    st.header("Registrar venta")

    with st.form("formulario_venta"):
        col1, col2, col3 = st.columns(3)

        with col1:
            categoria = st.selectbox(
                "Categoría del granizado",
                CATEGORIAS,
            )

        with col2:
            sabor = st.selectbox(
                "Sabor",
                SABORES_POR_CATEGORIA[categoria],
            )

        with col3:
            cantidad = st.number_input(
                "Cantidad",
                min_value=1,
                max_value=100,
                value=1,
                step=1,
            )

        col4, col5 = st.columns(2)

        with col4:
            usar_vaso = st.checkbox(
                "El cliente desea vaso de 12 oz",
                value=False,
                help=(
                    "Si no se marca, el granizado se entrega "
                    "en su sachet habitual."
                ),
            )

        with col5:
            metodo_pago = st.selectbox(
                "Medio de pago",
                MEDIOS_PAGO,
            )

        st.markdown("#### Toppings adicionales")

        toppings_disponibles = list(TOPPINGS.keys())

        toppings_adicionales = st.multiselect(
            "Seleccione los toppings adicionales, si aplica",
            toppings_disponibles,
        )

        col6, col7 = st.columns(2)

        with col6:
            cliente = st.text_input(
                "Nombre del cliente (opcional)"
            )

        with col7:
            observacion = st.text_input(
                "Observaciones (opcional)"
            )

        precio_unitario = PRECIO_MENU[categoria]
        total_estimado = precio_unitario * cantidad

        st.markdown(
            f"**Precio unitario:** {pesos(precio_unitario)}"
        )
        st.markdown(
            f"**Total de la venta:** {pesos(total_estimado)}"
        )

        receta_vista = crear_receta(
            categoria,
            sabor,
            usar_vaso,
            toppings_adicionales,
        )

        with st.expander("Ver consumo estimado de inventario"):
            filas_receta = []

            for producto, unidades in receta_vista.items():
                filas_receta.append({
                    "Producto": producto,
                    "Consumo por unidad": unidades,
                    "Consumo total": unidades * cantidad,
                    "Existencia actual": (
                        st.session_state.inventario.get(producto, 0)
                    ),
                })

            st.dataframe(
                pd.DataFrame(filas_receta),
                use_container_width=True,
                hide_index=True,
            )

        confirmar_venta = st.form_submit_button(
            "Registrar venta",
            type="primary",
            use_container_width=True,
        )

    if confirmar_venta:
        resultado, informacion = registrar_venta(
            categoria=categoria,
            sabor=sabor,
            cantidad=int(cantidad),
            usar_vaso=usar_vaso,
            metodo_pago=metodo_pago,
            toppings_adicionales=toppings
