
import json
from pathlib import Path
from datetime import datetime, date
from collections import Counter

import pandas as pd
import streamlit as st

# =========================================================
# CONFIGURACIÓN
# =========================================================
st.set_page_config(
    page_title="Granizados PL - Punto de Venta",
    page_icon="🍧",
    layout="wide",
)

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
h1, h2, h3 {font-weight: 800;}
div.stButton > button {font-weight: bold; min-height: 2.7rem;}
div[data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
""", unsafe_allow_html=True)

CARPETA_DATOS = Path(__file__).resolve().parent / "datos_granizados_pl"
ARCHIVO_DATOS = CARPETA_DATOS / "datos_pos.json"

MEDIOS_PAGO = [
    "Efectivo",
    "Transferencia Nequi / Billeteras virtuales",
]

PRESENTACIONES = ["Vaso 12 oz", "Sachet 12 oz"]

# Estos productos no aparecerán en el selector de reabastecimiento.
# Se conservan en el inventario porque algunas recetas los consumen.
PRODUCTOS_OCULTOS_REABASTECIMIENTO = {
    "Aguardiente (copa)",
    "Baileys (copa)",
    "Barquillo (und)",
    "Champaña (copa)",
    "Ron Blanco (copa)",
    "Tequila (copa)",
    "Vodka (copa)",
    "Whisky (copa)",
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

# =========================================================
# INVENTARIO INICIAL
# =========================================================
INVENTARIO_BASE = {
    "Vaso 12 oz (und)": 0,
    "Sachet 12 oz (und)": 0,
    "Pitillos (und)": 0,
    "Bolsa de papel (und)": 0,
    "Barquillo (und)": 0,
    "Lluvia de chocolate (porción)": 0,

    "Topping Minichicles (porción)": 0,
    "Topping Goma bandera (porción)": 0,
    "Topping Bombón (und)": 0,
    "Topping Sal pimienta (porción)": 0,
    "Topping Bolas de chicle (porción)": 0,
    "Topping Goma gusano (porción)": 0,
    "Topping Goma splash (porción)": 0,

    "Ron Blanco (copa)": 0,
    "Tequila (copa)": 0,
    "Vodka (copa)": 0,
    "Whisky (copa)": 0,
    "Aguardiente (copa)": 0,
    "Champaña (copa)": 0,
    "Baileys (copa)": 0,
}

SABORES_INVENTARIO = [
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
    "Nebula Ice",
    "Orion Ice",
    "Smirnoff Lulo Ice",
    "Smirnoff Limon Ice",
    "Tropical Caribeña Ice",
    "Velvet Ice",
    "Bayleys",
    "Coco Loco",
    "Piña Colada",
]

for nombre_sabor in SABORES_INVENTARIO:
    nombre_bodega = (
        "Sabor Maracupíña"
        if nombre_sabor == "Maracupiña"
        else "Sabor " + nombre_sabor
    )
    INVENTARIO_BASE[nombre_bodega] = 0

# =========================================================
# CARTA Y RECETAS
# =========================================================
MENU = {
    "SIN ALCOHOL": {
        "precio": 13000,
        "toppings_base": [
            "Topping Minichicles (porción)",
            "Topping Goma bandera (porción)",
            "Topping Goma gusano (porción)",
        ],
        "sabores": {
            "Bombombum": {
                "bodega": "Sabor Bombombum",
                "insumos": ["Topping Bombón (und)"],
            },
            "Chicle": {
                "bodega": "Sabor Chicle",
                "insumos": ["Topping Bolas de chicle (porción)"],
            },
            "Frutos Rojos": {
                "bodega": "Sabor Frutos Rojos",
                "insumos": [],
            },
            "Limonada Cerezada": {
                "bodega": "Sabor Limonada Cerezada",
                "insumos": [],
            },
            "Limonada de Coco": {
                "bodega": "Sabor Limonada de Coco",
                "insumos": [],
            },
            "Limonada de Sandía": {
                "bodega": "Sabor Limonada de Sandía",
                "insumos": [],
            },
            "Mango Biche": {
                "bodega": "Sabor Mango Biche",
                "insumos": ["Topping Sal pimienta (porción)"],
            },
            "Manzana Rosada": {
                "bodega": "Sabor Manzana Rosada",
                "insumos": [],
            },
            "Manzana Verde": {
                "bodega": "Sabor Manzana Verde",
                "insumos": [],
            },
            "Maracumango": {
                "bodega": "Sabor Maracumango",
                "insumos": [],
            },
            "Maracululo": {
                "bodega": "Sabor Maracululo",
                "insumos": [],
            },
            "Maracupiña": {
                "bodega": "Sabor Maracupíña",
                "insumos": [],
            },
            "Mora Azul": {
                "bodega": "Sabor Mora Azul",
                "insumos": [],
            },
            "Uva": {
                "bodega": "Sabor Uva",
                "insumos": [],
            },
        },
    },

    "CON ALCOHOL": {
        "precio": 15000,
        "toppings_base": [
            "Topping Goma gusano (porción)",
            "Topping Goma splash (porción)",
        ],
        "sabores": {
            "Agave Ice": {
                "bodega": "Sabor Agave Ice",
                "insumos": ["Ron Blanco (copa)", "Tequila (copa)"],
            },
            "Andromeda Ice": {
                "bodega": "Sabor Andromeda Ice",
                "insumos": ["Vodka (copa)", "Tequila (copa)"],
            },
            "Bon Bon Bum Ice": {
                "bodega": "Sabor Bon Bon Bum Ice",
                "insumos": ["Whisky (copa)", "Topping Bombón (und)"],
            },
            "Candy Ice": {
                "bodega": "Sabor Candy Ice",
                "insumos": ["Ron Blanco (copa)", "Vodka (copa)"],
            },
            "Cherryboom Ice": {
                "bodega": "Sabor Cherryboom Ice",
                "insumos": ["Ron Blanco (copa)", "Whisky (copa)"],
            },
            "Cosmico Ice": {
                "bodega": "Sabor Cosmico Ice",
                "insumos": ["Vodka (copa)", "Champaña (copa)"],
            },
            "Estelar Ice": {
                "bodega": "Sabor Estelar Ice",
                "insumos": ["Aguardiente (copa)"],
            },
            "Fresa Salvaje Ice": {
                "bodega": "Sabor Fresa Salvaje Ice",
                "insumos": ["Tequila (copa)"],
            },
            "Fourloko Ice": {
                "bodega": "Sabor Fourloko Ice",
                "insumos": ["Vodka (copa)"],
            },
            "Interestelar Ice": {
                "bodega": "Sabor Interestelar Ice",
                "insumos": ["Tequila (copa)"],
            },
            "Luxury Ice": {
                "bodega": "Sabor Luxury Ice",
                "insumos": ["Vodka (copa)"],
            },
            "Mango Explosivo Ice": {
                "bodega": "Sabor Mango Explosivo Ice",
                "insumos": [
                    "Tequila (copa)",
                    "Vodka (copa)",
                    "Topping Sal pimienta (porción)",
                ],
            },
            "Miami Ice": {
                "bodega": "Sabor Miami Ice",
                "insumos": ["Tequila (copa)"],
            },
            "Monaco Ice": {
                "bodega": "Sabor Monaco Ice",
                "insumos": ["Whisky (copa)"],
            },
            "Mora Azul Ice": {
                "bodega": "Sabor Mora Azul Ice",
                "insumos": ["Whisky (copa)"],
            },
            "Nebula Ice": {
                "bodega": "Sabor Nebula Ice",
                "insumos": ["Vodka (copa)", "Whisky (copa)"],
            },
            "Orion Ice": {
                "bodega": "Sabor Orion Ice",
                "insumos": ["Vodka (copa)"],
            },
            "Smirnoff Lulo Ice": {
                "bodega": "Sabor Smirnoff Lulo Ice",
                "insumos": ["Vodka (copa)"],
            },
            "Smirnoff Limon Ice": {
                "bodega": "Sabor Smirnoff Limon Ice",
                "insumos": ["Vodka (copa)"],
            },
            "Tropical Caribeña Ice": {
                "bodega": "Sabor Tropical Caribeña Ice",
                "insumos": ["Tequila (copa)", "Vodka (copa)"],
            },
            "Velvet Ice": {
                "bodega": "Sabor Velvet Ice",
                "insumos": ["Vodka (copa)", "Champaña (copa)"],
            },
        },
    },

    "CREMOSOS": {
        "precio": 15000,
        "toppings_base": [
            "Barquillo (und)",
            "Lluvia de chocolate (porción)",
        ],
        "sabores": {
            "Bayleys": {
                "bodega": "Sabor Bayleys",
                "insumos": ["Baileys (copa)", "Whisky (copa)"],
            },
            "Coco Loco": {
                "bodega": "Sabor Coco Loco",
                "insumos": ["Ron Blanco (copa)"],
            },
            "Piña Colada": {
                "bodega": "Sabor Piña Colada",
                "insumos": ["Ron Blanco (copa)"],
            },
        },
    },
}

# =========================================================
# FUNCIONES DE DATOS
# =========================================================
def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pesos(valor):
    return "$" + f"{int(valor):,}".replace(",", ".")


def guardar_datos():
    CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

    datos = {
        "inventario": st.session_state.inventario,
        "ventas": st.session_state.ventas,
        "movimientos": st.session_state.movimientos,
        "gastos": st.session_state.gastos,
        "anulaciones": st.session_state.anulaciones,
    }

    temporal = ARCHIVO_DATOS.with_suffix(".tmp")
    temporal.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporal.replace(ARCHIVO_DATOS)


def cargar_datos():
    inventario = INVENTARIO_BASE.copy()
    ventas = []
    movimientos = []
    gastos = []
    anulaciones = []

    if ARCHIVO_DATOS.exists():
        try:
            datos = json.loads(
                ARCHIVO_DATOS.read_text(encoding="utf-8")
            )

            inventario.update({
                producto: int(cantidad)
                for producto, cantidad
                in datos.get("inventario", {}).items()
            })

            ventas = datos.get("ventas", [])
            movimientos = datos.get("movimientos", [])
            gastos = datos.get("gastos", [])
            anulaciones = datos.get("anulaciones", [])

        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            st.error(
                "No se pudo leer el archivo de datos. "
                "Realiza una copia de datos_pos.json antes de modificarlo."
            )

    st.session_state.inventario = inventario
    st.session_state.ventas = ventas
    st.session_state.movimientos = movimientos
    st.session_state.gastos = gastos
    st.session_state.anulaciones = anulaciones


if "inventario" not in st.session_state:
    cargar_datos()


def crear_receta(categoria, sabor, presentacion, toppings_adicionales):
    receta = Counter()
    datos_sabor = MENU[categoria]["sabores"][sabor]

    receta[datos_sabor["bodega"]] += 1

    for insumo in datos_sabor["insumos"]:
        receta[insumo] += 1

    for topping in MENU[categoria]["toppings_base"]:
        receta[topping] += 1

    for topping in toppings_adicionales:
        receta[topping] += 1

    if presentacion == "Vaso 12 oz":
        receta["Vaso 12 oz (und)"] += 1
    else:
        receta["Sachet 12 oz (und)"] += 1

    receta["Pitillos (und)"] += 1
    receta["Bolsa de papel (und)"] += 1

    return dict(receta)


def calcular_faltantes(receta, cantidad):
    faltantes = {}

    for producto, unidades in receta.items():
        requerido = unidades * cantidad
        disponible = st.session_state.inventario.get(producto, 0)

        if disponible < requerido:
            faltantes[producto] = {
                "Requerido": requerido,
                "Disponible": disponible,
                "Faltan": requerido - disponible,
            }

    return faltantes


def registrar_movimiento(tipo, producto, cantidad, detalle):
    st.session_state.movimientos.append({
        "Fecha": ahora(),
        "Tipo": tipo,
        "Producto": producto,
        "Cantidad": int(cantidad),
        "Detalle": detalle,
    })


def ventas_vigentes():
    return [
        venta for venta in st.session_state.ventas
        if venta.get("Estado", "Vigente") == "Vigente"
    ]


# =========================================================
# ENCABEZADO Y PESTAÑAS
# =========================================================
st.title("🍧 Granizados PL - Punto de Venta")
st.subheader("El sabor que nos une")
st.caption("📍 Túquerres, Nariño")
st.divider()

pestanas = st.tabs([
    "🛍️ Ventas",
    "📦 Inventario",
    "📋 Historial",
    "💵 Caja y gastos",
    "📊 Reportes",
])

# =========================================================
# 1. REGISTRAR VENTAS
# =========================================================
with pestanas[0]:
    st.header("Registrar nueva venta")

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            categoria = st.selectbox(
                "Categoría",
                list(MENU.keys()),
            )

        with col2:
            sabor = st.selectbox(
                "Sabor",
                list(MENU[categoria]["sabores"].keys()),
            )

        with col3:
            cantidad = st.number_input(
                "Cantidad de granizados",
                min_value=1,
                max_value=50,
                value=1,
                step=1,
            )

        col4, col5 = st.columns(2)

        with col4:
            presentacion = st.selectbox(
                "Presentación",
                PRESENTACIONES,
            )

        with col5:
            medio_pago = st.selectbox(
                "Medio de pago",
                MEDIOS_PAGO,
            )

        toppings_seleccionados = st.multiselect(
            "Toppings adicionales",
            list(TOPPINGS.keys()),
            help=(
                "Los toppings incluidos por categoría se descuentan "
                "automáticamente. Esta selección agrega toppings extra."
            ),
        )

        nombre_cliente = st.text_input(
            "Cliente (opcional)",
            placeholder="Cliente general",
        )

        observacion = st.text_input("Observación (opcional)")

        precio_unitario = MENU[categoria]["precio"]
        total_venta = precio_unitario * int(cantidad)

        st.markdown(f"### Total de la venta: {pesos(total_venta)}")
        st.write(f"Precio por unidad: {pesos(precio_unitario)}")

        toppings_adicionales = [
            TOPPINGS[nombre] for nombre in toppings_seleccionados
        ]

        receta = crear_receta(
            categoria,
            sabor,
            presentacion,
            toppings_adicionales,
        )

        with st.expander("Ver consumo de inventario"):
            st.dataframe(
                pd.DataFrame([
                    {
                        "Producto": producto,
                        "Por granizado": unidades,
                        "Total requerido": unidades * int(cantidad),
                        "Existencias": st.session_state.inventario.get(
                            producto, 0
                        ),
                    }
                    for producto, unidades in receta.items()
                ]),
                hide_index=True,
                use_container_width=True,
            )

        faltantes = calcular_faltantes(receta, int(cantidad))

        if faltantes:
            st.warning(
                "No hay existencias suficientes. "
                "Reabastece los productos antes de registrar la venta."
            )
            st.dataframe(
                pd.DataFrame([
                    {"Producto": producto, **detalle}
                    for producto, detalle in faltantes.items()
                ]),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.success("Hay existencias suficientes.")

        if st.button(
            "✅ Registrar venta",
            type="primary",
            use_container_width=True,
            disabled=bool(faltantes),
        ):
            consumos = {
                producto: unidades * int(cantidad)
                for producto, unidades in receta.items()
            }

            venta = {
                "ID": "V-" + datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "Fecha": ahora(),
                "Cliente": nombre_cliente.strip() or "Cliente general",
                "Categoria": categoria,
                "Sabor": sabor,
                "Presentacion": presentacion,
                "Cantidad": int(cantidad),
                "Precio unitario": precio_unitario,
                "Total": total_venta,
                "Medio de pago": medio_pago,
                "Toppings adicionales": (
                    ", ".join(toppings_seleccionados)
                    if toppings_seleccionados else "Ninguno"
                ),
                "Observacion": observacion.strip(),
                "Estado": "Vigente",
                "Consumos": consumos,
            }

            for producto, unidades in consumos.items():
                st.session_state.inventario[producto] -= unidades
                registrar_movimiento(
                    "Salida por venta",
                    producto,
                    unidades,
                    venta["ID"],
                )

            st.session_state.ventas.append(venta)
            guardar_datos()
            st.success(
                f"Venta registrada por {pesos(total_venta)}."
            )
            st.rerun()

    st.divider()
    st.subheader("Resumen de hoy")

    fecha_hoy = date.today().isoformat()
    ventas_hoy = [
        venta for venta in ventas_vigentes()
        if venta.get("Fecha", "").startswith(fecha_hoy)
    ]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Número de ventas", len(ventas_hoy))
    col_b.metric(
        "Unidades vendidas",
        sum(int(v["Cantidad"]) for v in ventas_hoy),
    )
    col_c.metric(
        "Total vendido",
        pesos(sum(float(v["Total"]) for v in ventas_hoy)),
    )

# =========================================================
# 2. INVENTARIO, REABASTECIMIENTO Y CORRECCIONES
# =========================================================
with pestanas[1]:
    st.header("Inventario y reabastecimiento")

    st.info(
        "Agrega las cantidades que ingresen físicamente al negocio. "
        "Las existencias se guardan automáticamente."
    )

    # ---------- REABASTECIMIENTO ----------
    st.subheader("➕ Agregar existencias")

    productos_disponibles = sorted([
        producto
        for producto in st.session_state.inventario.keys()
        if producto not in PRODUCTOS_OCULTOS_REABASTECIMIENTO
    ])

    with st.form("form_reabastecimiento"):
        producto_reponer = st.selectbox(
            "Producto a reabastecer",
            productos_disponibles,
            key="producto_reponer",
        )

        cantidad_reponer = st.number_input(
            "Cantidad que ingresa",
            min_value=1,
            max_value=10000,
            value=1,
            step=1,
            key="cantidad_reponer",
        )

        detalle_reponer = st.text_input(
            "Detalle del ingreso",
            placeholder="Ej. compra a proveedor",
        )

        confirmar_reabastecimiento = st.form_submit_button(
            "Guardar reabastecimiento",
            use_container_width=True,
        )

    if confirmar_reabastecimiento:
        st.session_state.inventario[producto_reponer] += int(
            cantidad_reponer
        )

        registrar_movimiento(
            "Entrada / reabastecimiento",
            producto_reponer,
            int(cantidad_reponer),
            detalle_reponer.strip() or "Reabastecimiento manual",
        )

        guardar_datos()
        st.success(
            f"Se agregaron {cantidad_reponer} unidades a "
            f"{producto_reponer}."
        )
        st.rerun()

    # ---------- EXISTENCIAS ACTUALES ----------
    st.divider()
    st.subheader("📦 Existencias actuales")

    busqueda = st.text_input(
        "Buscar producto en inventario",
        key="buscar_inventario",
    )

    filas_inventario = [
        {
            "Producto": producto,
            "Existencias": cantidad,
        }
        for producto, cantidad in sorted(
            st.session_state.inventario.items()
        )
        if busqueda.lower() in producto.lower()
    ]

    st.dataframe(
        pd.DataFrame(filas_inventario),
        hide_index=True,
        use_container_width=True,
    )

    csv_inventario = pd.DataFrame(filas_inventario).to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "⬇️ Descargar inventario CSV",
        data=csv_inventario,
        file_name="inventario_granizados_pl.csv",
        mime="text/csv",
    )

    # ---------- CORREGIR EXISTENCIAS ----------
    st.divider()
    st.subheader("✏️ Corregir una existencia")

    st.warning(
        "Esta opción reemplaza la cantidad registrada por la cantidad "
        "real que tienes físicamente. No suma existencias."
    )

    productos_corregibles = sorted(
        st.session_state.inventario.keys()
    )

    with st.form("form_corregir_existencia"):
        producto_corregir = st.selectbox(
            "Producto que deseas corregir",
            productos_corregibles,
            key="producto_corregir",
        )

        valor_actual = int(
            st.session_state.inventario.get(producto_corregir, 0)
        )

        st.write(
            f"Existencia registrada actualmente: **{valor_actual}**"
        )

        nueva_existencia = st.number_input(
            "Nueva existencia correcta",
            min_value=0,
            max_value=1000000,
            value=valor_actual,
            step=1,
            key="nueva_existencia_correcta",
        )

        motivo_correccion = st.text_input(
            "Motivo de la corrección",
            placeholder="Ej. error al digitar la cantidad",
        )

        confirmar_correccion = st.form_submit_button(
            "Guardar corrección",
            use_container_width=True,
        )

    if confirmar_correccion:
        valor_anterior = int(
            st.session_state.inventario.get(producto_corregir, 0)
        )
        valor_nuevo = int(nueva_existencia)

        if valor_anterior == valor_nuevo:
            st.info("La existencia no cambió.")
        else:
            diferencia = valor_nuevo - valor_anterior

            st.session_state.inventario[producto_corregir] = valor_nuevo

            registrar_movimiento(
                "Corrección manual de inventario",
                producto_corregir,
                diferencia,
                (
                    f"Antes: {valor_anterior}; "
                    f"después: {valor_nuevo}; "
                    f"motivo: {motivo_correccion.strip() or 'No especificado'}"
                ),
            )

            guardar_datos()
            st.success(
                f"Existencia corregida. Antes: {valor_anterior}; "
                f"ahora: {valor_nuevo}."
            )
            st.rerun()

    # ---------- MOVIMIENTOS ----------
    st.divider()

    with st.expander("Historial de movimientos de inventario"):
        if st.session_state.movimientos:
            st.dataframe(
                pd.DataFrame(st.session_state.movimientos[::-1]),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Todavía no hay movimientos registrados.")

# =========================================================
# 3. HISTORIAL DE VENTAS Y ANULACIONES
# =========================================================
with pestanas[2]:
    st.header("Historial de ventas")

    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)

        columnas = [
            "ID", "Fecha", "Cliente", "Categoria", "Sabor",
            "Presentacion", "Cantidad", "Precio unitario", "Total",
            "Medio de pago", "Toppings adicionales", "Estado",
            "Observacion",
        ]

        columnas_disponibles = [
            columna for columna in columnas
            if columna in df_ventas.columns
        ]

        st.dataframe(
            df_ventas[columnas_disponibles].sort_values(
                "Fecha", ascending=False
            ),
            hide_index=True,
            use_container_width=True,
        )

        ventas_csv = df_ventas.drop(
            columns=["Consumos"], errors="ignore"
        ).to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "⬇️ Descargar historial de ventas",
            data=ventas_csv,
            file_name="historial_ventas_granizados_pl.csv",
            mime="text/csv",
        )

        vigentes = ventas_vigentes()

        if vigentes:
            st.subheader("Anular una venta")

            opciones = {
                (
                    f'{v["ID"]} | {v["Fecha"]} | '
                    f'{v["Sabor"]} | {pesos(v["Total"])}'
                ): v["ID"]
                for v in vigentes
            }

            seleccion = st.selectbox(
                "Seleccionar venta",
                list(opciones.keys()),
            )

            motivo = st.text_input("Motivo de anulación")

            if st.button(
                "↩️ Anular venta y devolver existencias",
                use_container_width=True,
            ):
                id_venta = opciones[seleccion]

                venta = next(
                    v for v in st.session_state.ventas
                    if v["ID"] == id_venta
                )

                if venta.get("Estado", "Vigente") != "Vigente":
                    st.error("Esta venta ya fue anulada.")
                else:
                    for producto, unidades in venta.get(
                        "Consumos", {}
                    ).items():
                        st.session_state.inventario[producto] = (
                            st.session_state.inventario.get(producto, 0)
                            + int(unidades)
                        )

                        registrar_movimiento(
                            "Devolución por anulación",
                            producto,
                            int(unidades),
                            id_venta,
                        )

                    venta["Estado"] = "Anulada"

                    st.session_state.anulaciones.append({
                        "Fecha": ahora(),
                        "ID venta": id_venta,
                        "Motivo": motivo.strip() or "Sin motivo indicado",
                        "Total": venta["Total"],
                    })

                    guardar_datos()
                    st.success(
                        "Venta anulada y existencias devueltas."
                    )
                    st.rerun()
    else:
        st.info("Todavía no hay ventas registradas.")

    with st.expander("Registro de anulaciones"):
        if st.session_state.anulaciones:
            st.dataframe(
                pd.DataFrame(st.session_state.anulaciones[::-1]),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No hay anulaciones registradas.")

# =========================================================
# 4. CAJA Y GASTOS
# =========================================================
with pestanas[3]:
    st.header("Caja y gastos")

    ventas_activas = ventas_vigentes()

    efectivo = sum(
        float(v["Total"])
        for v in ventas_activas
        if v["Medio de pago"] == "Efectivo"
    )

    transferencias = sum(
        float(v["Total"])
        for v in ventas_activas
        if v["Medio de pago"] != "Efectivo"
    )

    gastos_totales = sum(
        float(g["Valor"])
        for g in st.session_state.gastos
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Ventas en efectivo", pesos(efectivo))
    col2.metric("Transferencias", pesos(transferencias))
    col3.metric("Gastos registrados", pesos(gastos_totales))
    col4.metric(
        "Balance estimado",
        pesos(efectivo + transferencias - gastos_totales),
    )

    st.divider()
    st.subheader("Registrar gasto")

    with st.form("form_gasto"):
        concepto = st.text_input(
            "Concepto",
            placeholder="Ej. compra de hielo o transporte",
        )

        valor = st.number_input(
            "Valor del gasto (COP)",
            min_value=0,
            max_value=100000000,
            value=0,
            step=1000,
        )

        medio_gasto = st.selectbox(
            "Medio de pago del gasto",
            MEDIOS_PAGO,
        )

        detalle_gasto = st.text_input("Detalle adicional")

        guardar_gasto = st.form_submit_button(
            "💾 Guardar gasto",
            use_container_width=True,
        )

    if guardar_gasto:
        if not concepto.strip() or valor <= 0:
            st.error(
                "Escribe el concepto e indica un valor mayor que cero."
            )
        else:
            st.session_state.gastos.append({
                "Fecha": ahora(),
                "Concepto": concepto.strip(),
                "Valor": int(valor),
                "Medio de pago": medio_gasto,
                "Detalle": detalle_gasto.strip(),
            })

            guardar_datos()
            st.success("Gasto guardado.")
            st.rerun()

    st.subheader("Gastos registrados")

    if st.session_state.gastos:
        st.dataframe(
            pd.DataFrame(st.session_state.gastos[::-1]),
            hide_index=True,
            use_container_width=True,
        )

        gastos_csv = pd.DataFrame(
            st.session_state.gastos
        ).to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "⬇️ Descargar gastos CSV",
            data=gastos_csv,
            file_name="gastos_granizados_pl.csv",
            mime="text/csv",
        )
    else:
        st.info("Todavía no hay gastos registrados.")

# =========================================================
# 5. REPORTES
# =========================================================
with pestanas[4]:
    st.header("Reportes de ventas")

    ventas_activas = ventas_vigentes()

    if ventas_activas:
        df = pd.DataFrame(ventas_activas)
        df["Día"] = df["Fecha"].str[:10]

        col1, col2 = st.columns(2)

        with col1:
            fecha_inicio = st.date_input(
                "Fecha inicial",
                value=date.today().replace(day=1),
                key="fecha_inicio_reporte",
            )

        with col2:
            fecha_fin = st.date_input(
                "Fecha final",
                value=date.today(),
                key="fecha_fin_reporte",
            )

        if fecha_inicio > fecha_fin:
            st.error(
                "La fecha inicial no puede ser posterior a la fecha final."
            )
        else:
            df_periodo = df[
                (df["Día"] >= fecha_inicio.isoformat())
                & (df["Día"] <= fecha_fin.isoformat())
            ].copy()

            total_periodo = (
                float(df_periodo["Total"].sum())
                if not df_periodo.empty else 0
            )

            unidades_periodo = (
                int(df_periodo["Cantidad"].sum())
                if not df_periodo.empty else 0
            )

            col_a, col_b, col_c = st.columns(3)

            col_a.metric("Número de ventas", len(df_periodo))
            col_b.metric("Unidades vendidas", unidades_periodo)
            col_c.metric("Ingresos", pesos(total_periodo))

            if not df_periodo.empty:
                st.subheader("Ventas por categoría")

                por_categoria = (
                    df_periodo.groupby("Categoria", as_index=False)
                    .agg(
                        Ventas=("ID", "count"),
                        Unidades=("Cantidad", "sum"),
                        Ingresos=("Total", "sum"),
                    )
                )

                st.dataframe(
                    por_categoria,
                    hide_index=True,
                    use_container_width=True,
                )

                st.subheader("Sabores más vendidos")

                por_sabor = (
                    df_periodo.groupby("Sabor", as_index=False)
                    .agg(
                        Unidades=("Cantidad", "sum"),
                        Ingresos=("Total", "sum"),
                    )
                    .sort_values("Unidades", ascending=False)
                )

                st.dataframe(
                    por_sabor,
                    hide_index=True,
                    use_container_width=True,
                )

                st.bar_chart(
                    por_sabor.set_index("Sabor")["Unidades"]
                )

                reporte_csv = df_periodo.drop(
                    columns=["Consumos"], errors="ignore"
                ).to_csv(index=False).encode("utf-8-sig")

                st.download_button(
                    "⬇️ Descargar reporte del periodo",
                    data=reporte_csv,
                    file_name="reporte_ventas_granizados_pl.csv",
                    mime="text/csv",
                )
            else:
                st.info(
                    "No hay ventas vigentes en el periodo seleccionado."
                )
    else:
        st.info("Registra ventas para generar reportes.")

# =========================================================
# PIE DE PÁGINA
# =========================================================
st.divider()
st.caption(
    "Granizados PL · Los datos se guardan localmente en "
    "la carpeta datos_granizados_pl."
)
