import json
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Granizados PL - Punto de Venta", page_icon="🍧", layout="wide")
CARPETA_DATOS = Path("datos_granizados_pl")
ARCHIVO_DATOS = CARPETA_DATOS / "datos_pos.json"
CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

PRECIOS_VENTA = {"SIN ALCOHOL": 13000, "CON ALCOHOL": 15000, "CREMOSOS": 15000}
PRECIOS_COMPRA = {"SIN ALCOHOL": 3100, "CON ALCOHOL": 3300, "CREMOSOS": 4100}
METODOS_PAGO = ["Efectivo", "Transferencia Nequi / Billeteras virtuales"]
SABORES = {
    "SIN ALCOHOL": ["Bombombum", "Chicle", "Frutos Rojos", "Limonada Cerezada", "Limonada de Coco", "Limonada de Sandía", "Mango Biche", "Manzana Rosada", "Manzana Verde", "Maracumango", "Maracululo", "Maracupiña", "Mora Azul", "Uva"],
    "CON ALCOHOL": ["Agave Ice", "Andromeda Ice", "Bon Bon Bum Ice", "Candy Ice", "Cherryboom Ice", "Cosmico Ice", "Estelar Ice", "Fresa Salvaje Ice", "Fourloko Ice", "Interestelar Ice", "Luxury Ice", "Mango Explosivo Ice", "Miami Ice", "Monaco Ice", "Mora Azul Ice", "Nebula Ice", "Orion Ice", "Smirnoff Lulo Ice", "Smirnoff Limon Ice", "Tropical Caribeña Ice", "Velvet Ice"],
    "CREMOSOS": ["Bayleys", "Coco Loco", "Piña Colada"],
}
EXTRAS = ["Minichicles (porción)", "Goma bandera (porción)", "Bombón (porción)", "Sal pimienta (porción)", "Bolas de chicle (porción)", "Goma gusano (porción)", "Goma splash (porción)", "Lluvia de chocolate (porción)", "Barquillo (und)"]

def clave_sabor(sabor):
    return "Sabor Maracupíña" if sabor == "Maracupiña" else f"Sabor {sabor}"

INVENTARIO_BASE = {
    "Vaso 12 oz (und)": 0, "Pitillos (und)": 0, "Bolsa de papel (und)": 0,
    "Lluvia de chocolate (porción)": 0, "Minichicles (porción)": 0,
    "Goma bandera (porción)": 0, "Bombón (porción)": 0, "Sal pimienta (porción)": 0,
    "Bolas de chicle (porción)": 0, "Goma gusano (porción)": 0,
    "Goma splash (porción)": 0, "Barquillo (und)": 0,
}
for sabores in SABORES.values():
    for sabor in sabores:
        INVENTARIO_BASE[clave_sabor(sabor)] = 0

PRODUCTOS_ELIMINADOS = {"Sachet 12 oz (und)", "Aguardiente (copa)", "Baileys (copa)", "Champaña (copa)", "Ron Blanco (copa)", "Tequila (copa)", "Vodka (copa)", "Whisky (copa)"}

def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def dinero(valor):
    return f"${int(round(valor)):,.0f}".replace(",", ".")

def cargar_datos():
    datos = {}
    if ARCHIVO_DATOS.exists():
        try:
            datos = json.loads(ARCHIVO_DATOS.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            st.warning("No fue posible leer datos_pos.json. Se usará una estructura nueva; revisa si tienes copia de seguridad.")
    inventario = dict(INVENTARIO_BASE)
    for k, v in datos.get("inventario", {}).items():
        if k not in PRODUCTOS_ELIMINADOS:
            try: inventario[k] = int(v)
            except (ValueError, TypeError): inventario[k] = 0
    return {
        "inventario": inventario, "ventas": datos.get("ventas", []),
        "movimientos": datos.get("movimientos", []), "gastos": datos.get("gastos", []),
        "anulaciones": datos.get("anulaciones", []), "cierres_caja": datos.get("cierres_caja", []),
        "compras": datos.get("compras", []),
    }

def guardar_datos():
    claves = ["inventario", "ventas", "movimientos", "gastos", "anulaciones", "cierres_caja", "compras"]
    datos = {k: st.session_state[k] for k in claves}
    temporal = ARCHIVO_DATOS.with_suffix(".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ARCHIVO_DATOS)

if "datos_inicializados" not in st.session_state:
    for clave, valor in cargar_datos().items():
        st.session_state[clave] = valor
    st.session_state.datos_inicializados = True

def registrar_movimiento(producto, tipo, cantidad, detalle="", referencia=""):
    st.session_state.movimientos.append({"Fecha": ahora(), "Producto": producto, "Tipo": tipo, "Cantidad": int(cantidad), "Detalle": detalle, "Referencia": referencia})

def ventas_vigentes(desde=None, hasta=None):
    resultado = []
    for venta in st.session_state.ventas:
        if venta.get("Estado", "Vigente") != "Vigente": continue
        f = venta.get("Fecha", "")[:10]
        if desde and f < str(desde): continue
        if hasta and f > str(hasta): continue
        resultado.append(venta)
    return resultado

def compras_vigentes():
    return [c for c in st.session_state.compras if c.get("Estado", "Vigente") == "Vigente"]

def registrar_anulacion(tipo, identificador, detalle):
    st.session_state.anulaciones.append({"Fecha": ahora(), "Tipo": tipo, "ID": identificador, "Detalle": detalle})

def anular_venta(venta_id):
    for venta in st.session_state.ventas:
        if venta.get("ID") == venta_id and venta.get("Estado", "Vigente") == "Vigente":
            for producto, cantidad in venta.get("Consumos", {}).items():
                st.session_state.inventario[producto] = int(st.session_state.inventario.get(producto, 0)) + int(cantidad)
                registrar_movimiento(producto, "Entrada por anulación de venta", cantidad, "Devolución de inventario", venta_id)
            venta["Estado"] = "Anulada"
            venta["Fecha anulación"] = ahora()
            registrar_anulacion("Venta", venta_id, "Venta anulada")
            guardar_datos()
            return True
    return False

def anular_compra(compra_id):
    compra = next((c for c in st.session_state.compras if c.get("ID") == compra_id and c.get("Estado", "Vigente") == "Vigente"), None)
    if not compra: return False, "No se encontró la compra vigente."
    producto, cantidad = compra["Producto"], int(compra["Cantidad"])
    disponible = int(st.session_state.inventario.get(producto, 0))
    if disponible < cantidad:
        return False, f"No se puede anular: hay {disponible} unidades disponibles de {producto} y se deben retirar {cantidad}. Revisa ventas o ajustes de inventario."
    st.session_state.inventario[producto] = disponible - cantidad
    registrar_movimiento(producto, "Salida por anulación de compra", cantidad, "Reversión de compra", compra_id)
    compra["Estado"] = "Anulada"
    compra["Fecha anulación"] = ahora()
    for gasto in st.session_state.gastos:
        if gasto.get("Compra ID") == compra_id:
            gasto["Anulado"] = True
    registrar_anulacion("Compra", compra_id, "Compra anulada")
    guardar_datos()
    return True, "Compra anulada; se retiraron las unidades del inventario y el gasto quedó excluido."

def consumos_venta(sabor, presentacion, extras):
    consumos = {clave_sabor(sabor): 1, "Pitillos (und)": 1, "Bolsa de papel (und)": 1}
    if presentacion == "Vaso 12 oz": consumos["Vaso 12 oz (und)"] = 1
    for extra in extras: consumos[extra] = consumos.get(extra, 0) + 1
    return consumos

st.title("🍧 Granizados PL - Punto de Venta")
st.subheader("El sabor que nos une")
st.caption("📍 Túquerres, Nariño")
bajo = [(p, int(q)) for p, q in st.session_state.inventario.items() if int(q) <= 5]
if bajo:
    st.warning("⚠️ **Alerta de inventario (5 unidades o menos):** " + "; ".join(f"{p}: {q}" for p, q in sorted(bajo)))

tab_ventas, tab_inventario, tab_historial, tab_caja, tab_reportes, tab_cierre = st.tabs(["🛒 Ventas", "📦 Inventario", "🧾 Historial", "💵 Caja y gastos", "📊 Reportes", "🔒 Cerrar caja"])

with tab_ventas:
    st.header("Registrar venta")
    with st.form("form_venta", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            cliente = st.text_input("Cliente (opcional)")
            categoria = st.selectbox("Categoría", list(SABORES.keys()))
            sabor = st.selectbox("Sabor", SABORES[categoria])
            presentacion = st.selectbox("Presentación", ["Vaso 12 oz", "Sachet 12 oz"])
        with c2:
            cantidad = st.number_input("Cantidad", min_value=1, max_value=50, value=1, step=1)
            metodo_pago = st.selectbox("Medio de pago", METODOS_PAGO)
            extras = st.multiselect("Adiciones", EXTRAS)
            observacion = st.text_input("Observación (opcional)")
        precio_unitario = PRECIOS_VENTA[categoria]
        st.write(f"Precio unitario: **{dinero(precio_unitario)}** · Total estimado: **{dinero(precio_unitario * int(cantidad))}**")
        guardar_venta = st.form_submit_button("Registrar venta")
    if guardar_venta:
        consumos_unitarios = consumos_venta(sabor, presentacion, extras)
        consumos = {p: q * int(cantidad) for p, q in consumos_unitarios.items()}
        faltantes = [(p, q, int(st.session_state.inventario.get(p, 0))) for p, q in consumos.items() if int(st.session_state.inventario.get(p, 0)) < q]
        if faltantes:
            st.error("Inventario insuficiente: " + "; ".join(f"{p}: requiere {q}, disponible {disp}" for p, q, disp in faltantes))
        else:
            venta_id = "V-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
            for producto, unidades in consumos.items():
                st.session_state.inventario[producto] -= unidades
                registrar_movimiento(producto, "Salida por venta", unidades, f"Venta de {sabor}", venta_id)
            st.session_state.ventas.append({"ID": venta_id, "Fecha": ahora(), "Cliente": cliente.strip() or "Cliente general", "Categoría": categoria, "Sabor": sabor, "Presentación": presentacion, "Cantidad": int(cantidad), "Precio unitario": precio_unitario, "Total": precio_unitario * int(cantidad), "Medio de pago": metodo_pago, "Observación": observacion, "Adiciones": extras, "Consumos": consumos, "Estado": "Vigente"})
            guardar_datos()
            st.success(f"Venta registrada por {dinero(precio_unitario * int(cantidad))}.")
            st.rerun()
    ventas_hoy = ventas_vigentes(date.today(), date.today())
    efectivo_hoy = sum(int(v.get("Total", 0)) for v in ventas_hoy if v.get("Medio de pago") == "Efectivo")
    transferencias_hoy = sum(int(v.get("Total", 0)) for v in ventas_hoy if v.get("Medio de pago") != "Efectivo")
    a, b, c = st.columns(3)
    a.metric("Ventas vigentes de hoy", len(ventas_hoy)); b.metric("Efectivo", dinero(efectivo_hoy)); c.metric("Transferencias", dinero(transferencias_hoy))

with tab_inventario:
    st.header("Inventario")
    with st.expander("Registrar entrada o ajuste manual"):
        with st.form("form_inventario"):
            producto_inv = st.selectbox("Producto", sorted(st.session_state.inventario.keys()))
            tipo_inv = st.selectbox("Tipo", ["Entrada / reabastecimiento", "Ajuste: sumar", "Ajuste: restar"])
            cantidad_inv = st.number_input("Unidades", min_value=1, max_value=10000, value=1, step=1)
            detalle_inv = st.text_input("Detalle del movimiento")
            guardar_inv = st.form_submit_button("Guardar movimiento")
        if guardar_inv:
            actual = int(st.session_state.inventario.get(producto_inv, 0))
            if tipo_inv == "Ajuste: restar" and actual < int(cantidad_inv):
                st.error("El ajuste dejaría el inventario negativo.")
            else:
                sumar = tipo_inv != "Ajuste: restar"
                st.session_state.inventario[producto_inv] = actual + int(cantidad_inv) if sumar else actual - int(cantidad_inv)
                registrar_movimiento(producto_inv, "Entrada manual" if sumar else "Ajuste de salida", cantidad_inv, detalle_inv)
                guardar_datos(); st.success("Inventario actualizado."); st.rerun()
    df_inv = pd.DataFrame([{"Producto": p, "Existencias": int(q), "Estado": "⚠️ Bajo" if int(q) <= 5 else "Disponible"} for p, q in sorted(st.session_state.inventario.items())])
    st.dataframe(df_inv, use_container_width=True, hide_index=True)
    st.download_button("Descargar inventario CSV", df_inv.to_csv(index=False).encode("utf-8-sig"), "inventario_granizados_pl.csv", "text/csv")
    if st.session_state.movimientos:
        st.subheader("Últimos movimientos")
        st.dataframe(pd.DataFrame(st.session_state.movimientos[-100:][::-1]), use_container_width=True, hide_index=True)

with tab_historial:
    st.header("Historial de ventas")
    if st.session_state.ventas:
        dfv = pd.DataFrame([{k: v for k, v in venta.items() if k != "Consumos"} for venta in st.session_state.ventas[::-1]])
        st.dataframe(dfv, use_container_width=True, hide_index=True)
        ids = [v["ID"] for v in st.session_state.ventas if v.get("Estado", "Vigente") == "Vigente"]
        if ids:
            with st.form("form_anular_venta"):
                id_venta = st.selectbox("Venta vigente para anular", ids)
                confirmar = st.checkbox("Confirmo que deseo anular esta venta")
                enviar = st.form_submit_button("Anular venta")
            if enviar:
                if confirmar and anular_venta(id_venta): st.success("Venta anulada; el inventario consumido fue devuelto."); st.rerun()
                elif not confirmar: st.error("Debes confirmar la anulación.")
    else: st.info("Todavía no hay ventas registradas.")
    if st.session_state.anulaciones:
        with st.expander("Registro de anulaciones"):
            st.dataframe(pd.DataFrame(st.session_state.anulaciones[::-1]), use_container_width=True, hide_index=True)

with tab_caja:
    st.header("Caja y gastos")
    fecha_caja = date.today().isoformat()
    ventas_caja = ventas_vigentes(fecha_caja, fecha_caja)
    efectivo = sum(int(v.get("Total", 0)) for v in ventas_caja if v.get("Medio de pago") == "Efectivo")
    transferencias = sum(int(v.get("Total", 0)) for v in ventas_caja if v.get("Medio de pago") != "Efectivo")
    gastos_hoy = [g for g in st.session_state.gastos if g.get("Fecha", "")[:10] == fecha_caja and not g.get("Anulado", False)]
    gastos_totales = sum(int(g.get("Valor", 0)) for g in gastos_hoy)
    a, b, c, d = st.columns(4)
    a.metric("Ventas en efectivo", dinero(efectivo)); b.metric("Transferencias", dinero(transferencias)); c.metric("Gastos de hoy", dinero(gastos_totales)); d.metric("Saldo neto estimado", dinero(efectivo + transferencias - gastos_totales))

    st.subheader("Registrar compra de granizados")
    st.caption("Costo unitario automático: sin alcohol $3.100, con alcohol $3.300 y cremosos $4.100.")
    with st.form("form_compra", clear_on_submit=True):
        categoria_compra = st.selectbox("Categoría de compra", list(SABORES.keys()))
        sabor_compra = st.selectbox("Sabor comprado", SABORES[categoria_compra])
        cantidad_compra = st.number_input("Cantidad comprada", min_value=1, max_value=10000, value=1, step=1)
        costo_unitario = PRECIOS_COMPRA[categoria_compra]
        st.write(f"Costo unitario: **{dinero(costo_unitario)}** · Total: **{dinero(costo_unitario * int(cantidad_compra))}**")
        medio_compra = st.selectbox("Medio de pago", METODOS_PAGO, key="medio_pago_compra")
        detalle_compra = st.text_input("Proveedor / detalle (opcional)")
        guardar_compra = st.form_submit_button("Registrar compra y sumar al inventario")
    if guardar_compra:
        producto = clave_sabor(sabor_compra)
        compra_id = "C-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        total_compra = int(cantidad_compra) * costo_unitario
        st.session_state.compras.append({"ID": compra_id, "Fecha": ahora(), "Categoría": categoria_compra, "Sabor": sabor_compra, "Producto": producto, "Cantidad": int(cantidad_compra), "Costo unitario": costo_unitario, "Valor": total_compra, "Medio de pago": medio_compra, "Detalle": detalle_compra, "Estado": "Vigente"})
        st.session_state.inventario[producto] = int(st.session_state.inventario.get(producto, 0)) + int(cantidad_compra)
        registrar_movimiento(producto, "Entrada por compra de granizados", cantidad_compra, detalle_compra, compra_id)
        st.session_state.gastos.append({"ID": "G-" + compra_id, "Fecha": ahora(), "Concepto": f"Compra de granizados: {sabor_compra}", "Valor": total_compra, "Medio de pago": medio_compra, "Detalle": detalle_compra, "Compra ID": compra_id, "Anulado": False})
        guardar_datos(); st.success(f"Compra registrada por {dinero(total_compra)}; inventario actualizado."); st.rerun()

    st.subheader("Compras vigentes")
    compras = compras_vigentes()
    if compras:
        st.dataframe(pd.DataFrame(compras[::-1]), use_container_width=True, hide_index=True)
        with st.form("form_anular_compra"):
            compra_id_anular = st.selectbox("Compra para anular", [c["ID"] for c in compras])
            confirmar_compra = st.checkbox("Confirmo que deseo anular esta compra")
            enviar_anulacion_compra = st.form_submit_button("Anular compra")
        if enviar_anulacion_compra:
            if not confirmar_compra: st.error("Debes confirmar la anulación.")
            else:
                ok, mensaje = anular_compra(compra_id_anular)
                if ok: st.success(mensaje); st.rerun()
                else: st.error(mensaje)
    else: st.info("No hay compras vigentes registradas.")

    st.subheader("Registrar otro gasto")
    with st.form("form_gasto", clear_on_submit=True):
        concepto = st.text_input("Concepto del gasto", placeholder="Ej. transporte, servicios, bolsas")
        valor_gasto = st.number_input("Valor ($)", min_value=0, max_value=100000000, value=0, step=500)
        metodo_gasto = st.selectbox("Medio de pago", METODOS_PAGO, key="medio_pago_gasto")
        detalle_gasto = st.text_input("Detalle del gasto")
        guardar_gasto = st.form_submit_button("Guardar gasto")
    if guardar_gasto:
        if not concepto.strip() or valor_gasto <= 0: st.error("Escribe el concepto y un valor mayor que cero.")
        else:
            st.session_state.gastos.append({"ID": "G-" + datetime.now().strftime("%Y%m%d%H%M%S%f"), "Fecha": ahora(), "Concepto": concepto.strip(), "Valor": int(valor_gasto), "Medio de pago": metodo_gasto, "Detalle": detalle_gasto, "Anulado": False})
            guardar_datos(); st.success("Gasto registrado."); st.rerun()
    st.subheader("Gastos vigentes de hoy")
    gastos_hoy = [g for g in st.session_state.gastos if g.get("Fecha", "")[:10] == fecha_caja and not g.get("Anulado", False)]
    if gastos_hoy:
        st.dataframe(pd.DataFrame(gastos_hoy[::-1]), use_container_width=True, hide_index=True)
        st.download_button("Descargar gastos CSV", pd.DataFrame(gastos_hoy).to_csv(index=False).encode("utf-8-sig"), "gastos_granizados_pl.csv", "text/csv")
    else: st.info("No hay gastos vigentes registrados hoy.")

with tab_reportes:
    st.header("Reportes")
    col1, col2 = st.columns(2)
    desde = col1.date_input("Desde", value=date.today(), key="reporte_desde")
    hasta = col2.date_input("Hasta", value=date.today(), key="reporte_hasta")
    if desde > hasta: st.error("La fecha inicial no puede ser posterior a la fecha final.")
    else:
        periodo = ventas_vigentes(desde, hasta)
        total = sum(int(v.get("Total", 0)) for v in periodo)
        a, b, c = st.columns(3)
        a.metric("Ventas vigentes", len(periodo)); b.metric("Unidades vendidas", sum(int(v.get("Cantidad", 0)) for v in periodo)); c.metric("Ingresos", dinero(total))
        if periodo:
            dfp = pd.DataFrame([{k: v for k, v in venta.items() if k != "Consumos"} for venta in periodo])
            st.dataframe(dfp, use_container_width=True, hide_index=True)
            st.subheader("Ingresos por categoría")
            st.bar_chart(pd.DataFrame(periodo).groupby("Categoría")["Total"].sum())
            st.download_button("Descargar reporte CSV", dfp.to_csv(index=False).encode("utf-8-sig"), "reporte_ventas_granizados_pl.csv", "text/csv")
        else: st.info("No hay ventas vigentes para el período seleccionado.")

with tab_cierre:
    st.header("Cerrar caja")
    st.write("Genera un resumen diario. El cierre se guarda en el historial; no elimina las ventas ni los gastos.")
    fecha_cierre = st.date_input("Fecha que desea cerrar", value=date.today(), key="fecha_cierre")
    ftxt = fecha_cierre.isoformat()
    ventas_dia = ventas_vigentes(ftxt, ftxt)
    efectivo_dia = sum(int(v.get("Total", 0)) for v in ventas_dia if v.get("Medio de pago") == "Efectivo")
    transferencias_dia = sum(int(v.get("Total", 0)) for v in ventas_dia if v.get("Medio de pago") != "Efectivo")
    gastos_dia = [g for g in st.session_state.gastos if g.get("Fecha", "")[:10] == ftxt and not g.get("Anulado", False)]
    total_gastos_dia = sum(int(g.get("Valor", 0)) for g in gastos_dia)
    saldo_dia = efectivo_dia + transferencias_dia - total_gastos_dia
    a, b, c, d = st.columns(4)
    a.metric("Efectivo", dinero(efectivo_dia)); b.metric("Transferencias", dinero(transferencias_dia)); c.metric("Gastos", dinero(total_gastos_dia)); d.metric("Saldo neto estimado", dinero(saldo_dia))
    st.write(f"**Ventas vigentes:** {len(ventas_dia)} · **Unidades vendidas:** {sum(int(v.get('Cantidad', 0)) for v in ventas_dia)}")
    with st.expander("Detalle de ventas"):
        if ventas_dia: st.dataframe(pd.DataFrame([{k: v for k, v in x.items() if k != "Consumos"} for x in ventas_dia]), use_container_width=True, hide_index=True)
        else: st.info("No hay ventas vigentes en esa fecha.")
    with st.expander("Detalle de gastos"):
        if gastos_dia: st.dataframe(pd.DataFrame(gastos_dia), use_container_width=True, hide_index=True)
        else: st.info("No hay gastos vigentes en esa fecha.")
    if st.button("Guardar cierre de caja", type="primary"):
        if any(cierre.get("Fecha cierre") == ftxt for cierre in st.session_state.cierres_caja): st.warning("Ya existe un cierre guardado para esa fecha.")
        else:
            st.session_state.cierres_caja.append({"Fecha cierre": ftxt, "Fecha y hora de registro": ahora(), "Cantidad de ventas": len(ventas_dia), "Unidades vendidas": sum(int(v.get("Cantidad", 0)) for v in ventas_dia), "Efectivo": efectivo_dia, "Transferencias": transferencias_dia, "Gastos": total_gastos_dia, "Saldo neto estimado": saldo_dia})
            guardar_datos(); st.success("Cierre de caja guardado."); st.rerun()
    if st.session_state.cierres_caja:
        st.subheader("Historial de cierres")
        dfc = pd.DataFrame(st.session_state.cierres_caja[::-1])
        st.dataframe(dfc, use_container_width=True, hide_index=True)
        st.download_button("Descargar historial de cierres CSV", dfc.to_csv(index=False).encode("utf-8-sig"), "cierres_caja_granizados_pl.csv", "text/csv")

st.caption("Granizados PL · Datos guardados en datos_granizados_pl/datos_pos.json")
