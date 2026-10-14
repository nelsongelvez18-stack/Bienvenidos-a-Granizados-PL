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

st.markdown("""
<style>
h1 {
    font-size: 38px !important;
    font-weight: bold !important;
    text-align: center;
    color: #ff4b4b;
}
h2, h3, label, .stMarkdown p {
    font-size: 20px !important;
}
button, div[data-testid="stFormSubmitButton"] button {
    font-size: 20px !important;
    font-weight: bold !important;
    padding: 12px !important;
    border-radius: 10px !important;
}
[data-testid="stMetricValue"] {
    font-size: 25px !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🍧 Granizados PL - Punto de Venta")
st.caption("📍 Túquerres, Nariño | El sabor que nos une")

# =========================================================
# INVENTARIO INICIAL
# Nota: el inventario se conserva durante la sesión de Streamlit.
# Para almacenamiento permanente se necesita una base de datos.
# =========================================================
INVENTARIO_INICIAL = {
    # Materiales y empaques
    "Vaso 12 oz (und)": 200,
    "Sachet 12 oz (und)": 200,
    "Pitillos (und)": 300,
    "Bolsa de papel (und)": 300,
    "Toppings de dulces (porción)": 500,
    "Barquillo (und)": 100,
    "Lluvia de chocolate (porción)": 100,

    # Licores
    "Ron Blanco (copa)": 100,
    "Tequila (copa)": 100,
    "Vodka (copa)": 100,
    "Whisky (copa)": 100,
    "Aguardiente (copa)": 100,
    "Champaña (copa)": 100,
    "Baileys (copa)": 100,

    # Sin alcohol
    "Sabor Bombombum": 50,
    "Sabor Limonada de Coco": 50,
    "Sabor Limonada de Sandía": 50,
    "Sabor Manzana Verde": 50,
    "Sabor Maracululo": 50,
    "Sabor Maracupíña": 50,
    "Sabor Piña Naranja": 50,
    "Sabor Uva": 50,

    # Granizados con alcohol
    "Sabor Agave Ice": 50,
    "Sabor Andromeda Ice": 50,
    "Sabor Bon Bon Bum Ice": 50,
    "Sabor Candy Ice": 50,
    "Sabor Cherryboom Ice": 50,
    "Sabor Cosmico Ice": 50,
    "Sabor Estelar Ice": 50,
    "Sabor Fresa Salvaje Ice": 50,
    "Sabor Fourloko Ice": 50,
    "Sabor Interestelar Ice": 50,
    "Sabor Luxury Ice": 50,
    "Sabor Mango Explosivo Ice": 50,
    "Sabor Miami Ice": 50,
    "Sabor Monaco Ice": 50,
    "Sabor Mora Azul Ice": 50,
    "Sabor Nebula Ice": 50,
    "Sabor Orion Ice": 50,
    "Sabor Smirnoff Lulo Ice": 50,
    "Sabor Smirnoff Limon Ice": 50,
    "Sabor Tropical Caribeña Ice": 50,
    "Sabor Velvet Ice": 50,

    # Cremosos
    "Sabor Bayleys": 50,
    "Sabor Coco Loco": 50,
    "Sabor Piña Colada": 50,
}

if "inventario" not in st.session_state:
    st.session_state.inventario = INVENTARIO_INICIAL.copy()

if "ventas_detalladas" not in st.session_state:
    st.session_state.ventas_detalladas = []

if "historial_cargas" not in st.session_state:
    st.session_state.historial_cargas = []

# =========================================================
# MENÚ OFICIAL
# =========================================================
SABORES_POR_CATEGORIA = {
    "SIN ALCOHOL (12 oz)": {
        "precio": 13000,
        "toppings": ["Toppings de dulces (porción)"],
        "sabores_inventario": {
            "Bombombum": {
                "insumos": [],
                "bodega": "Sabor Bombombum"
            },
            "Limonada de Coco": {
                "insumos": [],
                "bodega": "Sabor Limonada de Coco"
            },
            "Limonada de Sandía": {
                "insumos": [],
                "bodega": "Sabor Limonada de Sandía"
            },
            "Manzana Verde": {
                "insumos": [],
                "bodega": "Sabor Manzana Verde"
            },
            "Maracululo": {
                "insumos": [],
                "bodega": "Sabor Maracululo"
            },
            "Maracupíña": {
                "insumos": [],
                "bodega": "Sabor Maracupíña"
            },
            "Piña Naranja": {
                "insumos": [],
                "bodega": "Sabor Piña Naranja"
            },
            "Uva": {
                "insumos": [],
                "bodega": "Sabor Uva"
            },
        },
    },
    "CON ALCOHOL (12 oz)": {
        "precio": 15000,
        "toppings": ["Toppings de dulces (porción)"],
        "sabores_inventario": {
            "Agave Ice": {
                "insumos": ["Ron Blanco (copa)", "Tequila (copa)"],
                "bodega": "Sabor Agave Ice"
            },
            "Andromeda Ice": {
                "insumos": ["Vodka (copa)", "Tequila (copa)"],
                "bodega": "Sabor Andromeda Ice"
            },
            "Bon Bon Bum Ice": {
                "insumos": ["Whisky (copa)"],
                "bodega": "Sabor Bon Bon Bum Ice"
            },
            "Candy Ice": {
                "insumos": ["Ron Blanco (copa)", "Vodka (copa)"],
                "bodega": "Sabor Candy Ice"
            },
            "Cherryboom Ice": {
                "insumos": ["Ron Blanco (copa)", "Whisky (copa)"],
                "bodega": "Sabor Cherryboom Ice"
            },
            "Cosmico Ice": {
                "insumos": ["Vodka (copa)", "Champaña (copa)"],
                "bodega": "Sabor Cosmico Ice"
            },
            "Estelar Ice": {
                "insumos": ["Aguardiente (copa)"],
                "bodega": "Sabor Estelar Ice"
            },
            "Fresa Salvaje Ice": {
                "insumos": ["Tequila (copa)"],
                "bodega": "Sabor Fresa Salvaje Ice"
            },
            "Fourloko Ice": {
                "insumos": ["Vodka (copa)"],
                "bodega": "Sabor Fourloko Ice"
            },
            "Interestelar Ice": {
                "insumos": ["Tequila (copa)"],
                "bodega": "Sabor Interestelar Ice"
            },
            "Luxury Ice": {
                "insumos": ["Vodka (copa)"],
                "bodega": "Sabor Luxury Ice"
            },
            "Mango Explosivo Ice": {
                "insumos": ["Tequila (copa)", "Vodka (copa)"],
                "bodega": "Sabor Mango Explosivo Ice"
            },
            "Miami Ice": {
                "insumos": ["Tequila (copa)"],
                "bodega": "Sabor Miami Ice"
            },
            "Monaco Ice": {
                "insumos": ["Whisky (copa)"],
                "bodega": "Sabor Monaco Ice"
            },
            "Mora Azul Ice": {
                "insumos": ["Whisky (copa)"],
                "bodega": "Sabor Mora Azul Ice"
            },
            "Nebula Ice": {
                "insumos": ["Vodka (copa)", "Whisky (copa)"],
                "bodega": "Sabor Nebula Ice"
            },
            "Orion Ice": {
                "insumos": ["Vodka (copa)"],
                "bodega": "Sabor Orion Ice"
            },
            "Smirnoff Lulo Ice": {
                "insumos": ["Vodka (copa)"],
                "bodega": "Sabor Smirnoff Lulo Ice"
            },
            "Smirnoff Limon Ice": {
                "insumos": ["Vodka (copa)"],
                "bodega": "Sabor Smirnoff Limon Ice"
            },
            "Tropical Caribeña Ice": {
                "insumos": ["Tequila (copa)", "Vodka (copa)"],
                "bodega": "Sabor Tropical Caribeña Ice"
            },
            "Velvet Ice": {
                "insumos": ["Vodka (copa)", "Champaña (copa)"],
                "bodega": "Sabor Velvet Ice"
            },
        },
    },
    "CREMOSA CON ALCOHOL (12 oz)": {
        "precio": 16000,
        "toppings": [
            "Barquillo (und)",
            "Lluvia de chocolate (porción)"
        ],
        "sabores_inventario": {
            "Bayleys": {
                "insumos": ["Baileys (copa)", "Whisky (copa)"],
                "bodega": "Sabor Bayleys"
            },
            "Coco Loco": {
                "insumos": ["Ron Blanco (copa)"],
                "bodega": "Sabor Coco Loco"
            },
            "Piña Colada": {
                "insumos": ["Ron Blanco (copa)"],
                "bodega": "Sabor Piña Colada"
            },
        },
    },
}

def pesos(valor):
    """Formato de moneda colombiana."""
    return f"${valor:,.0f} COP"

def receta_pedido(categoria, sabor_nombre, presentacion):
    """Devuelve los insumos que debe descontar una venta."""
    config = SABORES_POR_CATEGORIA[categoria]
    sabor_info = config["sabores_inventario"][sabor_nombre]

    empaque = (
        "Vaso 12 oz (und)"
        if presentacion == "Vaso"
        else "Sachet 12 oz (und)"
    )

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

def procesar_pedido(categoria, sabor_nombre, presentacion, cantidad=1):
    """Valida todo el stock antes de descontarlo y registrar la venta."""
    config = SABORES_POR_CATEGORIA[categoria]
    receta_unitaria = receta_pedido(categoria, sabor_nombre, presentacion)
    receta_total = {
        insumo: unidades * cantidad
        for insumo, unidades in receta_unitaria.items()
    }

    faltantes = []
    for insumo, unidades_necesarias in receta_total.items():
        disponible = st.session_state.inventario.get(insumo, 0)
        if disponible < unidades_necesarias:
            faltantes.append(
                f"{insumo}: disponibles {disponible}, "
                f"necesarios {unidades_necesarias}"
            )

    if faltantes:
        st.error("No se registró la venta. Inventario insuficiente:")
        for detalle in faltantes:
            st.write(f"- {detalle}")
        return False

    # Descontar solo después de validar todos los insumos.
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
        "Precio unitario (COP)": precio_unitario,
        "Total (COP)": total,
    })
    return True

# =========================================================
# FORMULARIO DE VENTA
# =========================================================
st.subheader("🛍️ Registrar venta")

with st.container(border=True):
    categoria = st.selectbox(
        "1. Seleccione la categoría:",
        options=list(SABORES_POR_CATEGORIA.keys()),
        key="categoria_venta"
    )

    sabores = list(
        SABORES_POR_CATEGORIA[categoria]["sabores_inventario"].keys()
    )

    sabor = st.selectbox(
        "2. Seleccione el sabor:",
        options=sabores,
        key="sabor_venta"
    )

    presentacion = st.radio(
        "3. Seleccione la presentación:",
        options=["Vaso", "Sachet"],
        horizontal=True,
        key="presentacion_venta"
    )

    cantidad_venta = st.number_input(
        "4. Cantidad de unidades:",
        min_value=1,
        max_value=100,
        value=1,
        step=1,
        key="cantidad_venta"
    )

    precio_actual = SABORES_POR_CATEGORIA[categoria]["precio"]
    st.markdown(f"### Precio unitario: {pesos(precio_actual)}")
    st.markdown(f"### Total de la venta: {pesos(precio_actual * cantidad_venta)}")

    if st.button("🚀 REGISTRAR VENTA", use_container_width=True):
        if procesar_pedido(
            categoria,
            sabor,
            presentacion,
            int(cantidad_venta)
        ):
            st.success(
                f"Venta registrada: {cantidad_venta} x {sabor}. "
                f"Total: {pesos(precio_actual * cantidad_venta)}"
            )
            st.rerun()

st.divider()

# =========================================================
# PESTAÑAS DE CONTROL
# =========================================================
tab1, tab2, tab3 = st.tabs([
    "📊 Cuadre de turno",
    "📦 Existencias en bodega",
    "🔄 Cargar insumos"
])

# =========================================================
# PESTAÑA 1: CUADRE DE TURNO
# =========================================================
with tab1:
    st.subheader("📊 Ventas e ingresos del turno")

    ventas = st.session_state.ventas_detalladas

    if ventas:
        df_ventas = pd.DataFrame(ventas)
        total_unidades = int(df_ventas["Cantidad"].sum())
        total_ingresos = int(df_ventas["Total (COP)"].sum())

        col1, col2 = st.columns(2)
        col1.metric("🍧 Unidades vendidas", total_unidades)
        col2.metric("💰 Total recaudado", pesos(total_ingresos))

        resumen = (
            df_ventas.groupby(
                ["Categoría", "Sabor", "Presentación"],
                as_index=False
            )
            .agg(
                **{
                    "Unidades vendidas": ("Cantidad", "sum"),
                    "Ingresos (COP)": ("Total (COP)", "sum")
                }
            )
        )

        st.markdown("#### Resumen por producto")
        st.dataframe(resumen, use_container_width=True, hide_index=True)

        st.markdown("#### Historial de ventas")
        st.dataframe(
            df_ventas.sort_values("Fecha y hora", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        csv_ventas = df_ventas.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Descargar reporte de ventas (CSV)",
            data=csv_ventas,
            file_name="reporte_ventas_granizados_pl.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.warning(
            "El botón de cierre elimina el historial de ventas de esta sesión. "
            "Descargue el reporte antes de cerrar el turno."
        )
        if st.button("🧾 Cerrar turno y limpiar ventas", use_container_width=True):
            st.session_state.ventas_detalladas = []
            st.rerun()
    else:
        st.info(
            "Todavía no hay ventas registradas. "
            "Registre una venta para ver el cuadre del turno."
        )

# =========================================================
# PESTAÑA 2: EXISTENCIAS EN BODEGA
# =========================================================
with tab2:
    st.subheader("📦 Existencias actuales")

    df_inventario = pd.DataFrame([
        {
            "Insumo o producto": nombre,
            "Existencias": cantidad,
            "Estado": (
                "🔴 Agotado" if cantidad <= 0
                else "🟠 Stock bajo" if cantidad <= 10
                else "🟢 Disponible"
            )
        }
        for nombre, cantidad in st.session_state.inventario.items()
    ])

    c1, c2, c3 = st.columns(3)
    c1.metric("Referencias", len(df_inventario))
    c2.metric(
        "Agotados",
        int((df_inventario["Existencias"] <= 0).sum())
    )
    c3.metric(
        "Stock bajo",
        int(
            (
                (df_inventario["Existencias"] > 0)
                & (df_inventario["Existencias"] <= 10)
            ).sum()
        )
    )

    busqueda = st.text_input(
        "Buscar insumo:",
        placeholder="Escriba vaso, vodka, uva..."
    )

    df_mostrar = df_inventario
    if busqueda.strip():
        df_mostrar = df_inventario[
            df_inventario["Insumo o producto"].str.contains(
                busqueda,
                case=False,
                na=False
            )
        ]

    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

    csv_inventario = df_inventario.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Descargar inventario (CSV)",
        data=csv_inventario,
        file_name="inventario_granizados_pl.csv",
        mime="text/csv",
        use_container_width=True
    )

# =========================================================
# PESTAÑA 3: CARGAR INSUMOS
# =========================================================
with tab3:
    st.subheader("🔄 Entrada de mercancía a bodega")
    st.write(
        "Seleccione el insumo recibido. La cantidad ingresada se suma "
        "a las existencias actuales."
    )

    with st.form("formulario_reabastecimiento", clear_on_submit=True):
        insumo = st.selectbox(
            "Seleccione el insumo:",
            options=list(st.session_state.inventario.keys()),
            key="insumo_reabastecer"
        )

        st.info(
            f"Existencia actual: "
            f"{st.session_state.inventario[insumo]}"
        )

        cantidad_recibida = st.number_input(
            "Cantidad recibida:",
            min_value=1,
            max_value=100000,
            value=10,
            step=1
        )

        nota_carga = st.text_input(
            "Observación (opcional):",
            placeholder="Ej. Compra al proveedor"
        )

        enviar_carga = st.form_submit_button(
            "➕ CARGAR INSUMOS A BODEGA",
            use_container_width=True
        )

        if enviar_carga:
            st.session_state.inventario[insumo] += int(cantidad_recibida)
            st.session_state.historial_cargas.append({
                "Fecha y hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Insumo": insumo,
                "Cantidad recibida": int(cantidad_recibida),
                "Observación": nota_carga
            })
            st.success(
                f"Se agregaron {cantidad_recibida} unidades de {insumo}. "
                f"Nuevo saldo: {st.session_state.inventario[insumo]}."
            )
            st.rerun()

    if st.session_state.historial_cargas:
        st.markdown("#### Historial de entradas")
        df_cargas = pd.DataFrame(st.session_state.historial_cargas)
        st.dataframe(df_cargas, use_container_width=True, hide_index=True)
        csv_cargas = df_cargas.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Descargar historial de entradas (CSV)",
            data=csv_cargas,
            file_name="entradas_bodega_granizados_pl.csv",
            mime="text/csv",
            use_container_width=True
        )

st.divider()
st.caption(
    "Granizados PL | Los datos se conservan en la sesión actual de Streamlit. "
    "Reiniciar el servidor puede reiniciar el inventario y los reportes."
)
