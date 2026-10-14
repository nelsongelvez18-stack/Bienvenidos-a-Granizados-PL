
import json
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import streamlit as st

# =========================================================
# CONFIGURACION GENERAL
# =========================================================
st.set_page_config(
    page_title="POS Granizados PL",
    page_icon="🍧",
    layout="wide"
)

CARPETA_DATOS = Path(__file__).resolve().parent / "datos_granizados_pl"
CARPETA_DATOS.mkdir(parents=True, exist_ok=True)
ARCHIVO_DATOS = CARPETA_DATOS / "datos_pos.json"

MEDIOS_PAGO = [
    "Efectivo",
    "Transferencia Nequi / Billeteras virtuales"
]

# =========================================================
# INVENTARIO INICIAL: TODOS LOS PRODUCTOS EN CERO
# =========================================================
INVENTARIO_BASE = {
    "Vaso 12 oz (und)": 0,
    "Sachet 12 oz (und)": 0,
    "Pitillos (und)": 0,
    "Bolsa de papel (und)": 0,
    "Toppings de dulces (porción)": 0,
    "Barquillo (und)": 0,
    "Lluvia de chocolate (porción)": 0,

    "Ron Blanco (copa)": 0,
    "Tequila (copa)": 0,
    "Vodka (copa)": 0,
    "Whisky (copa)": 0,
    "Aguardiente (copa)": 0,
    "Champaña (copa)": 0,
    "Baileys (copa)": 0,

    "Sabor Bombombum": 0,
    "Sabor Limonada de Coco": 0,
    "Sabor Limonada de Sandía": 0,
    "Sabor Manzana Verde": 0,
    "Sabor Maracululo": 0,
    "Sabor Maracupíña": 0,
    "Sabor Piña Naranja": 0,
    "Sabor Uva": 0,

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

    "Sabor Bayleys": 0,
    "Sabor Coco Loco": 0,
    "Sabor Piña Colada": 0
}

# =========================================================
# MENU, PRECIOS Y RECETAS
# Cada ingrediente consume una unidad por granizado.
# Ajustar las recetas si las cantidades reales son distintas.
# =========================================================
MENU = {
    "SIN ALCOHOL (12 oz)": {
        "precio": 13000,
        "toppings": ["Toppings de dulces (porción)"],
        "sabores": {
            "Bombombum": {
                "bodega": "Sabor Bombombum",
                "insumos": []
            },
            "Limonada de Coco": {
                "bodega": "Sabor Limonada de Coco",
                "insumos": []
            },
            "Limonada de Sandía": {
                "bodega": "Sabor Limonada de Sandía",
                "insumos": []
            },
            "Manzana Verde": {
                "bodega": "Sabor Manzana Verde",
                "insumos": []
            },
            "Maracululo": {
                "bodega": "Sabor Maracululo",
                "insumos": []
            },
            "Maracupíña": {
                "bodega": "Sabor Maracupíña",
                "insumos": []
            },
            "Piña Naranja": {
                "bodega": "Sabor Piña Naranja",
                "insumos": []
            },
            "Uva": {
                "bodega": "Sabor Uva",
                "insumos": []
            }
        }
    },

    "CON ALCOHOL (12 oz)": {
        "precio": 15000,
        "toppings": ["Toppings de dulces (porción)"],
        "sabores": {
            "Agave Ice": {
                "bodega": "Sabor Agave Ice",
                "insumos": ["Ron Blanco (copa)", "Tequila (copa)"]
            },
            "Andromeda Ice": {
                "bodega": "Sabor Andromeda Ice",
                "insumos": ["Vodka (copa)", "Tequila (copa)"]
            },
            "Bon Bon Bum Ice": {
                "bodega": "Sabor Bon Bon Bum Ice",
                "insumos": ["Whisky (copa)"]
            },
            "Candy Ice": {
                "bodega": "Sabor Candy Ice",
                "insumos": ["Ron Blanco (copa)", "Vodka (copa)"]
            },
            "Cherryboom Ice": {
                "bodega": "Sabor Cherryboom Ice",
                "insumos": ["Ron Blanco (copa)", "Whisky (copa)"]
            },
            "Cosmico Ice": {
                "bodega": "Sabor Cosmico Ice",
                "insumos": ["Vodka (copa)", "Champaña (copa)"]
            },
            "Estelar Ice": {
                "bodega": "Sabor Estelar Ice",
                "insumos": ["Aguardiente (copa)"]
            },
            "Fresa Salvaje Ice": {
                "bodega": "Sabor Fresa Salvaje Ice",
                "insumos": ["Tequila (copa)"]
            },
            "Fourloko Ice": {
                "bodega": "Sabor Fourloko Ice",
                "insumos": ["Vodka (copa)"]
            },
            "Interestelar Ice": {
                "bodega": "Sabor Interestelar Ice",
                "insumos": ["Tequila (copa)"]
            },
            "Luxury Ice": {
                "bodega": "Sabor Luxury Ice",
                "insumos": ["Vodka (copa)"]
            },
            "Mango Explosivo Ice": {
                "bodega": "Sabor Mango Explosivo Ice",
                "insumos": ["Tequila (copa)", "Vodka (copa)"]
            },
            "Miami Ice": {
                "bodega": "Sabor Miami Ice",
                "insumos": ["Tequila (copa)"]
            },
            "Monaco Ice": {
                "bodega": "Sabor Monaco Ice",
                "insumos": ["Whisky (copa)"]
            },
            "Mora Azul Ice": {
                "bodega": "Sabor Mora Azul Ice",
                "insumos": ["Whisky (copa)"]
            },
            "Nebula Ice": {
                "bodega": "Sabor Nebula Ice",
                "insumos": ["Vodka (copa)", "Whisky (copa)"]
            },
            "Orion Ice": {
                "bodega": "Sabor Orion Ice",
                "insumos": ["Vodka (copa)"]
            },
            "Smirnoff Lulo Ice": {
                "bodega": "Sabor Smirnoff Lulo Ice",
                "insumos": ["Vodka (copa)"]
            },
            "Smirnoff Limon Ice": {
                "bodega": "Sabor Smirnoff Limon Ice",
                "insumos": ["Vodka (copa)"]
            },
            "Tropical Caribeña Ice": {
                "bodega": "Sabor Tropical Caribeña Ice",
                "insumos": ["Tequila (copa)", "Vodka (copa)"]
            },
            "Velvet Ice": {
                "bodega": "Sabor Velvet Ice",
                "insumos": ["Vodka (copa)", "Champaña (copa)"]
            }
        }
    },

    "CREMOSA CON ALCOHOL (12 oz)": {
        "precio": 16000,
        "toppings": [
            "Barquillo (und)",
            "Lluvia de chocolate (porción)"
        ],
        "sabores": {
            "Bayleys": {
                "bodega": "Sabor Bayleys",
                "insumos": ["Baileys (copa)", "Whisky (copa)"]
            },
            "Coco Loco": {
                "bodega": "Sabor Coco Loco",
                "insumos": ["Ron Blanco (copa)"]
            },
            "Piña Colada": {
                "bodega": "Sabor Piña Colada",
                "insumos": ["Ron Blanco (copa)"]
            }
        }
    }
}


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def pesos(valor):
    return "$" + f"{int(valor):,}".replace(",", ".") + " COP"


def guardar_datos():
    datos = {
        "inventario": st.session_state.inventario,
        "ventas": st.session_state.ventas,
        "movimientos": st.session_state.movimientos,
        "gastos": st.session_state.gastos,
        "anulaciones": st.session_state.anulaciones
    }

    temporal = ARCHIVO_DATOS.with_suffix(".tmp")
    temporal.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temporal.replace(ARCHIVO_DATOS)


def cargar_datos():
    if ARCHIVO_DATOS.exists():
        try:
            datos = json.loads(
                ARCHIVO_DATOS.read_text(encoding="utf-8")
            )

            inventario = INVENTARIO_BASE.copy()
            inventario.update({
                nombre: int(cantidad)
                for nombre, cantidad in datos.get(
                    "inventario", {}
                ).items()
            })

            return {
                "inventario": inventario,
                "ventas": datos.get("ventas", []),
                "movimientos": datos.get("movimientos", []),
                "gastos": datos.get("gastos", []),
                "anulaciones": datos.get("anulaciones", [])
            }

        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            st.error(
                "No se pudo leer el archivo de datos. "
                "Revise el archivo JSON y conserve una copia antes "
                "de continuar."
            )

    return {
        "inventario": INVENTARIO_BASE.copy(),
        "ventas": [],
        "movimientos": [],
        "gastos": [],
        "anulaciones": []
    }


def registrar_movimiento(tipo, producto, cantidad, detalle=""):
    st.session_state.movimientos.append({
        "Fecha y hora": ahora(),
        "Tipo": tipo,
        "Producto": producto,
        "Cantidad": int(cantidad),
        "Detalle": detalle
    })


def construir_receta(categoria, sabor, presentacion, cantidad):
    config = MENU[categoria]
    info = config["sabores"][sabor]

    empaque = (
        "Vaso 12 oz (und)"
        if presentacion == "Vaso"
        else "Sachet 12 oz (und)"
    )

    receta = {
        empaque: cantidad,
        "Pitillos (und)": cantidad,
        "Bolsa de papel (und)": cantidad,
        info["bodega"]: cantidad
    }

    for topping in config["toppings"]:
        receta[topping] = receta.get(topping, 0) + cantidad

    for licor in info["insumos"]:
        receta[licor] = receta.get(licor, 0) + cantidad

    return receta


def exportar_csv(datos):
    return pd.DataFrame(datos).to_csv(
        index=False
    ).encode("utf-8-sig")


# =========================================================
# INICIALIZAR DATOS PERSISTENTES
# =========================================================
if "inicializado" not in st.session_state:
    datos = cargar_datos()

    for clave, valor in datos.items():
        st.session_state[clave] = valor

    st.session_state.inicializado = True


# =========================================================
# ESTILOS Y ENCABEZADO
# =========================================================
st.markdown("""
<style>
h1 {
    text-align: center;
    color: #ff4b4b;
    font-weight: 800;
}
[data-testid="stMetricValue"] {
    font-size: 1.7rem;
}
div.stButton > button,
div[data-testid="stFormSubmitButton"] button {
    font-weight: bold;
    border-radius: 9px;
    padding: 0.55rem;
}
</style>
""", unsafe_allow_html=True)

st.title("🍧 Granizados PL — Punto de Venta")
st.caption("📍 Túquerres, Nariño | El sabor que nos une")
st.info(
    "El inventario comienza en cero. Registre las entradas "
    "en la pestaña Inventario antes de vender. "
    "Los datos se guardan localmente en un archivo JSON."
)

tab_ventas, tab_inventario, tab_historial, tab_caja, tab_reportes = st.tabs([
    "🛍️ Ventas",
    "📦 Inventario",
    "🧾 Historial",
    "💵 Caja",
    "📊 Reportes"
])


# =========================================================
# PESTAÑA 1: VENTAS
# =========================================================
with tab_ventas:
    st.header("Registrar venta")

    with st.form("formulario_venta"):
        categoria = st.selectbox(
            "1. Categoría",
            list(MENU.keys())
        )

        sabor = st.selectbox(
            "2. Sabor",
            list(MENU[categoria]["sabores"].keys())
        )

        presentacion = st.radio(
            "3. Presentación",
            ["Vaso", "Sachet"],
            horizontal=True
        )

        medio_pago = st.selectbox(
            "4. Medio de pago",
            MEDIOS_PAGO
        )

        cantidad = st.number_input(
            "5. Cantidad de unidades",
            min_value=1,
            max_value=100,
            value=1,
            step=1
        )

        precio_unitario = MENU[categoria]["precio"]
        total = precio_unitario * int(cantidad)

        st.markdown(
            f"**Precio unitario:** {pesos(precio_unitario)}"
        )
        st.markdown(f"**Total de la venta:** {pesos(total)}")

        confirmar = st.form_submit_button(
            "🚀 REGISTRAR VENTA",
            use_container_width=True
        )

    if confirmar:
        receta = construir_receta(
            categoria,
            sabor,
            presentacion,
            int(cantidad)
        )

        faltantes = []

        for producto, necesario in receta.items():
            disponible = st.session_state.inventario.get(
                producto, 0
            )

            if disponible < necesario:
                faltantes.append(
                    f"{producto}: disponibles {disponible}, "
                    f"necesarios {necesario}"
                )

        if faltantes:
            st.error(
                "Inventario insuficiente. No se registró la venta."
            )

            for falta in faltantes:
                st.write(f"- {falta}")

        else:
            # Descontar todos los insumos de la receta.
            for producto, unidades in receta.items():
                st.session_state.inventario[producto] -= unidades

            venta = {
                "ID": "V" + datetime.now().strftime(
                    "%Y%m%d%H%M%S%f"
                ),
                "Fecha y hora": ahora(),
                "Categoría": categoria,
                "Sabor": sabor,
                "Presentación": presentacion,
                "Cantidad": int(cantidad),
                "Medio de pago": medio_pago,
                "Precio unitario": precio_unitario,
                "Total": total,
                "Estado": "Vigente",
                "Consumos": receta
            }

            st.session_state.ventas.append(venta)

            registrar_movimiento(
                "Salida por venta",
                sabor,
                cantidad,
                f"Venta {venta['ID']}"
            )

            guardar_datos()

            st.success(
                f"Venta registrada correctamente. Total: {pesos(total)}"
            )
            st.rerun()

    st.divider()
    st.subheader("Resumen del día")

    hoy = date.today().isoformat()

    ventas_hoy = [
        v for v in st.session_state.ventas
        if v["Fecha y hora"].startswith(hoy)
        and v["Estado"] == "Vigente"
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric("Ventas", len(ventas_hoy))
    col2.metric(
        "Unidades vendidas",
        sum(v["Cantidad"] for v in ventas_hoy)
    )
    col3.metric(
        "Ingresos",
        pesos(sum(v["Total"] for v in ventas_hoy))
    )


# =========================================================
# PESTAÑA 2: INVENTARIO
# =========================================================
with tab_inventario:
    st.header("Inventario y reabastecimiento")

    st.write(
        "Seleccione el producto recibido e indique la cantidad "
        "que desea agregar a las existencias."
    )

    with st.form("formulario_entrada"):
        producto_entrada = st.selectbox(
            "Producto o insumo",
            list(st.session_state.inventario.keys())
        )

        cantidad_entrada = st.number_input(
            "Cantidad recibida",
            min_value=1,
            max_value=100000,
            value=1,
            step=1
        )

        referencia = st.text_input(
            "Proveedor, factura o nota (opcional)"
        )

        confirmar_entrada = st.form_submit_button(
            "➕ REGISTRAR REABASTECIMIENTO",
            use_container_width=True
        )

    if confirmar_entrada:
        st.session_state.inventario[producto_entrada] += int(
            cantidad_entrada
        )

        registrar_movimiento(
            "Entrada / reabastecimiento",
            producto_entrada,
            cantidad_entrada,
            referencia.strip() or "Entrada manual"
        )

        guardar_datos()

        st.success(
            f"Entrada registrada: {cantidad_entrada} unidades "
            f"de {producto_entrada}."
        )
        st.rerun()

    st.divider()
    st.subheader("Existencias actuales")

    busqueda = st.text_input(
        "Buscar producto",
        placeholder="Escriba el nombre del producto..."
    )

    inventario_tabla = []

    for nombre, unidades in st.session_state.inventario.items():
        if busqueda.lower() not in nombre.lower():
            continue

        if unidades == 0:
            estado = "AGOTADO"
        elif unidades <= 5:
            estado = "EXISTENCIAS BAJAS"
        else:
            estado = "DISPONIBLE"

        inventario_tabla.append({
            "Producto": nombre,
            "Existencias": unidades,
            "Estado": estado
        })

    st.dataframe(
        pd.DataFrame(inventario_tabla),
        use_container_width=True,
        hide_index=True
    )

    agotados = sum(
        unidades == 0
        for unidades in st.session_state.inventario.values()
    )

    bajos = sum(
        0 < unidades <= 5
        for unidades in st.session_state.inventario.values()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Referencias", len(st.session_state.inventario))
    c2.metric("Agotados", agotados)
    c3.metric("Existencias bajas", bajos)

    with st.expander("Consultar movimientos de inventario"):
        if st.session_state.movimientos:
            st.dataframe(
                pd.DataFrame(st.session_state.movimientos),
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Descargar movimientos CSV",
                data=exportar_csv(st.session_state.movimientos),
                file_name="movimientos_inventario.csv",
                mime="text/csv"
            )
        else:
            st.info("Todavía no existen movimientos registrados.")


# =========================================================
# PESTAÑA 3: HISTORIAL DE VENTAS
# =========================================================
with tab_historial:
    st.header("Historial de ventas")

    ventas = st.session_state.ventas

    if ventas:
        df = pd.DataFrame([
            {
                "ID": v["ID"],
                "Fecha y hora": v["Fecha y hora"],
                "Categoría": v["Categoría"],
                "Sabor": v["Sabor"],
                "Presentación": v["Presentación"],
                "Cantidad": v["Cantidad"],
                "Medio de pago": v["Medio de pago"],
                "Precio unitario": v["Precio unitario"],
                "Total": v["Total"],
                "Estado": v["Estado"]
            }
            for v in ventas
        ])

        col1, col2 = st.columns(2)

        with col1:
            desde = st.date_input(
                "Fecha inicial",
                value=date.today().replace(day=1),
                key="hist_desde"
            )

        with col2:
            hasta = st.date_input(
                "Fecha final",
                value=date.today(),
                key="hist_hasta"
            )

        df["Fecha"] = pd.to_datetime(
            df["Fecha y hora"],
            errors="coerce"
        ).dt.date

        if desde > hasta:
            st.warning(
                "La fecha inicial no puede ser posterior a la fecha final."
            )
        else:
            filtrado = df[
                (df["Fecha"] >= desde)
                & (df["Fecha"] <= hasta)
            ]

            st.dataframe(
                filtrado.drop(columns=["Fecha"]),
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "⬇️ DESCARGAR HISTORIAL CSV",
                data=exportar_csv(
                    filtrado.drop(columns=["Fecha"]).to_dict(
                        orient="records"
                    )
                ),
                file_name="historial_ventas_granizados_pl.csv",
                mime="text/csv"
            )

        st.divider()
        st.subheader("Anular una venta")

        vigentes = [
            v for v in ventas
            if v["Estado"] == "Vigente"
        ]

        if vigentes:
            opciones = {
                v["ID"]: (
                    f"{v['ID']} | {v['Sabor']} | "
                    f"{pesos(v['Total'])}"
                )
                for v in vigentes
            }

            with st.form("formulario_anulacion"):
                id_anular = st.selectbox(
                    "Seleccione la venta",
                    list(opciones.keys()),
                    format_func=lambda x: opciones[x]
                )

                motivo = st.text_input(
                    "Motivo de la anulación"
                )

                confirmar_anulacion = st.form_submit_button(
                    "⚠️ ANULAR Y DEVOLVER INSUMOS"
                )

            if confirmar_anulacion:
                venta = next(
                    v for v in st.session_state.ventas
                    if v["ID"] == id_anular
                )

                for producto, unidades in venta.get(
                    "Consumos", {}
                ).items():
                    st.session_state.inventario[producto] = (
                        st.session_state.inventario.get(producto, 0)
                        + int(unidades)
                    )

                venta["Estado"] = "Anulada"
                venta["Motivo de anulación"] = (
                    motivo.strip() or "Sin motivo especificado"
                )
                venta["Anulada el"] = ahora()

                st.session_state.anulaciones.append({
                    "ID": id_anular,
                    "Fecha y hora": ahora(),
                    "Motivo": venta["Motivo de anulación"]
                })

                registrar_movimiento(
                    "Devolución por anulación",
                    id_anular,
                    0,
                    "Devolución de todos los insumos consumidos"
                )

                guardar_datos()

                st.success(
                    "Venta anulada y existencias devueltas al inventario."
                )
                st.rerun()
        else:
            st.info("No hay ventas vigentes para anular.")

    else:
        st.info("Todavía no hay ventas registradas.")


# =========================================================
# PESTAÑA 4: CAJA Y GASTOS
# =========================================================
with tab_caja:
    st.header("Caja y control de gastos")

    fecha_caja = st.date_input(
        "Fecha de consulta",
        value=date.today(),
        key="fecha_caja"
    )

    fecha_texto = fecha_caja.isoformat()

    ventas_fecha = [
        v for v in st.session_state.ventas
        if v["Fecha y hora"].startswith(fecha_texto)
        and v["Estado"] == "Vigente"
    ]

    efectivo = sum(
        v["Total"] for v in ventas_fecha
        if v["Medio de pago"] == "Efectivo"
    )

    transferencias = sum(
        v["Total"] for v in ventas_fecha
        if v["Medio de pago"] != "Efectivo"
    )

    gastos_fecha = [
        g for g in st.session_state.gastos
        if g["Fecha y hora"].startswith(fecha_texto)
    ]

    gastos_efectivo = sum(
        g["Valor"] for g in gastos_fecha
        if g["Medio de pago"] == "Efectivo"
    )

    gastos_digitales = sum(
        g["Valor"] for g in gastos_fecha
        if g["Medio de pago"] != "Efectivo"
    )

    neto_efectivo = efectivo - gastos_efectivo
    neto_digital = transferencias - gastos_digitales
    neto_total = neto_efectivo + neto_digital

    c1, c2 = st.columns(2)
    c1.metric("Ventas en efectivo", pesos(efectivo))
    c2.metric("Ventas por transferencia", pesos(transferencias))

    c3, c4 = st.columns(2)
    c3.metric("Gastos del día", pesos(sum(
        g["Valor"] for g in gastos_fecha
    )))
    c4.metric("Neto estimado", pesos(neto_total))

    st.caption(
        "El neto se calcula restando los gastos registrados a las ventas. "
        "No reemplaza el arqueo físico de caja."
    )

    st.divider()
    st.subheader("Registrar gasto")

    with st.form("formulario_gasto"):
        concepto = st.text_input("Concepto del gasto")

        valor_gasto = st.number_input(
            "Valor del gasto (COP)",
            min_value=0,
            max_value=100000000,
            value=0,
            step=1000
        )

        medio_gasto = st.selectbox(
            "Medio de pago del gasto",
            ["Efectivo", "Transferencia"]
        )

        confirmar_gasto = st.form_submit_button(
            "REGISTRAR GASTO"
        )

    if confirmar_gasto:
        if not concepto.strip() or valor_gasto <= 0:
            st.error(
                "Escriba el concepto e indique un valor mayor que cero."
            )
        else:
            st.session_state.gastos.append({
                "Fecha y hora": ahora(),
                "Concepto": concepto.strip(),
                "Valor": int(valor_gasto),
                "Medio de pago": medio_gasto
            })

            guardar_datos()
            st.success("Gasto registrado correctamente.")
            st.rerun()

    if gastos_fecha:
        st.subheader("Detalle de gastos")
        st.dataframe(
            pd.DataFrame(gastos_fecha),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# PESTAÑA 5: REPORTES
# =========================================================
with tab_reportes:
    st.header("Reportes de ventas")

    ventas_vigentes = [
        v for v in st.session_state.ventas
        if v["Estado"] == "Vigente"
    ]

    if ventas_vigentes:
        col1, col2 = st.columns(2)

        with col1:
            inicio = st.date_input(
                "Inicio del reporte",
                value=date.today().replace(day=1),
                key="reporte_inicio"
            )

        with col2:
            fin = st.date_input(
                "Fin del reporte",
                value=date.today(),
                key="reporte_fin"
            )

        if inicio > fin:
            st.warning(
                "La fecha inicial no puede ser posterior a la fecha final."
            )
        else:
            periodo = [
                v for v in ventas_vigentes
                if inicio <= datetime.strptime(
                    v["Fecha y hora"],
                    "%Y-%m-%d %H:%M:%S"
                ).date() <= fin
            ]

            ingresos = sum(v["Total"] for v in periodo)
            unidades = sum(v["Cantidad"] for v in periodo)

            r1, r2, r3 = st.columns(3)
            r1.metric("Ingresos del periodo", pesos(ingresos))
            r2.metric("Unidades vendidas", unidades)
            r3.metric("Número de ventas", len(periodo))

            if periodo:
                df_periodo = pd.DataFrame(periodo)

                st.subheader("Ventas por sabor")

                resumen_sabor = (
                    df_periodo.groupby("Sabor", as_index=False)
                    .agg(
                        Unidades=("Cantidad", "sum"),
                        Ingresos=("Total", "sum")
                    )
                    .sort_values("Ingresos", ascending=False)
                )

                st.bar_chart(
                    resumen_sabor.set_index("Sabor")["Ingresos"]
                )

                st.dataframe(
                    resumen_sabor,
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("Ingresos por medio de pago")

                resumen_pago = (
                    df_periodo.groupby(
                        "Medio de pago", as_index=False
                    )["Total"].sum()
                )

                st.dataframe(
                    resumen_pago,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    "⬇️ DESCARGAR REPORTE CSV",
                    data=exportar_csv([
                        {
                            "ID": v["ID"],
                            "Fecha y hora": v["Fecha y hora"],
                            "Sabor": v["Sabor"],
                            "Cantidad": v["Cantidad"],
                            "Medio de pago": v["Medio de pago"],
                            "Total": v["Total"]
                        }
                        for v in periodo
                    ]),
                    file_name="reporte_granizados_pl.csv",
                    mime="text/csv"
                )
            else:
                st.info(
                    "No hay ventas vigentes en el periodo seleccionado."
                )
    else:
        st.info(
            "Registre ventas para comenzar a generar reportes."
        )

    st.divider()
    st.subheader("Copia de seguridad")

    st.write(
        f"Archivo de datos: `{ARCHIVO_DATOS}`"
    )

    if ARCHIVO_DATOS.exists():
        st.download_button(
            "⬇️ DESCARGAR RESPALDO COMPLETO JSON",
            data=ARCHIVO_DATOS.read_bytes(),
            file_name="respaldo_granizados_pl.json",
            mime="application/json"
        )

    st.warning(
        "Guarde copias de seguridad periódicamente. "
        "El archivo JSON está en el equipo donde se ejecuta Streamlit; "
        "no sincroniza automáticamente varios computadores."
    )
