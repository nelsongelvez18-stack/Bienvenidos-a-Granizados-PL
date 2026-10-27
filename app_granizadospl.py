import base64
import hmac
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Granizados PL - Punto de Venta", page_icon="🍧", layout="wide")

# ---------------------------------------------------------------- CONFIGURACIÓN
TZ = timezone(timedelta(hours=-5))  # Colombia (sin horario de verano)
UMBRAL_BAJO = 5
CARPETA_DATOS = Path("datos_granizados_pl")
ARCHIVO_DATOS = CARPETA_DATOS / "datos_pos.json"
LOGO = Path("logo_pl.png")
CARPETA_DATOS.mkdir(parents=True, exist_ok=True)

PRECIOS_VENTA = {"SIN ALCOHOL": 13000, "CON ALCOHOL": 15000, "CREMOSOS": 15000}
PRECIOS_COMPRA = {"SIN ALCOHOL": 3100, "CON ALCOHOL": 3300, "CREMOSOS": 4100}
COLORES = {"SIN ALCOHOL": "#7dff3a", "CON ALCOHOL": "#ff8fc2", "CREMOSOS": "#ffe27a"}
METODOS_PAGO = ["Efectivo", "Transferencia Nequi / Billeteras virtuales"]
SABORES = {
    "SIN ALCOHOL": ["Bombombum", "Chicle", "Frutos Rojos", "Limonada Cerezada", "Limonada de Coco", "Limonada de Sandía", "Mango Biche", "Manzana Rosada", "Manzana Verde", "Maracumango", "Maracululo", "Maracupiña", "Mora Azul", "Uva"],
    "CON ALCOHOL": ["Agave Ice", "Andromeda Ice", "Bon Bon Bum Ice", "Candy Ice", "Cherryboom Ice", "Cosmico Ice", "Estelar Ice", "Fresa Salvaje Ice", "Fourloko Ice", "Interestelar Ice", "Luxury Ice", "Mango Explosivo Ice", "Miami Ice", "Monaco Ice", "Mora Azul Ice", "Nebula Ice", "Orion Ice", "Smirnoff Lulo Ice", "Smirnoff Limon Ice", "Tropical Caribeña Ice", "Velvet Ice"],
    "CREMOSOS": ["Bayleys", "Coco Loco", "Piña Colada"],
}
# Las adiciones (toppings) están en el inventario, pero NO se descuentan al vender.
EXTRAS = ["Minichicles (porción)", "Goma bandera (porción)", "Bombón (porción)", "Sal pimienta (porción)", "Bolas de chicle (porción)", "Goma gusano (porción)", "Goma splash (porción)", "Lluvia de chocolate (porción)", "Barquillo (und)"]


def clave_sabor(sabor):
    return "Sabor Maracupíña" if sabor == "Maracupiña" else f"Sabor {sabor}"


INVENTARIO_BASE = {"Vaso 12 oz (und)": 0, "Pitillos (und)": 0, "Bolsa de papel (und)": 0}
INVENTARIO_BASE.update({e: 0 for e in EXTRAS})
for _sabores in SABORES.values():
    for _s in _sabores:
        INVENTARIO_BASE[clave_sabor(_s)] = 0

PRODUCTOS_ELIMINADOS = {"Sachet 12 oz (und)", "Aguardiente (copa)", "Baileys (copa)", "Champaña (copa)", "Ron Blanco (copa)", "Tequila (copa)", "Vodka (copa)", "Whisky (copa)"}
CLAVES = ["inventario", "ventas", "movimientos", "gastos", "anulaciones", "cierres_caja", "compras"]


# ---------------------------------------------------------------------- UTILES
def ahora():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def hoy():
    return datetime.now(TZ).date()


def dinero(valor):
    return f"${int(round(valor)):,.0f}".replace(",", ".")


def dinero_html(valor):
    # "$" se escapa para que Markdown no lo confunda con fórmulas
    return dinero(valor).replace("$", "&#36;")


def suma(items, campo="Total"):
    return sum(int(i.get(campo, 0)) for i in items)


# ------------------------------------------------------------------------ DATOS
def cargar_datos():
    datos = {}
    if ARCHIVO_DATOS.exists():
        try:
            datos = json.loads(ARCHIVO_DATOS.read_text(encoding="utf-8"))
            if not isinstance(datos, dict):
                raise ValueError("estructura inesperada")
        except (ValueError, OSError):
            copia = ARCHIVO_DATOS.with_name(f"datos_pos.danado.{datetime.now(TZ):%Y%m%d%H%M%S}.json")
            try:
                ARCHIVO_DATOS.replace(copia)
            except OSError:
                pass
            datos = {}
            st.error(f"No se pudo leer datos_pos.json. Se guardó una copia ({copia.name}) y se inicia vacío.")
    inventario = dict(INVENTARIO_BASE)
    for k, v in datos.get("inventario", {}).items():
        if k not in PRODUCTOS_ELIMINADOS:
            try:
                inventario[k] = int(v)
            except (ValueError, TypeError):
                inventario[k] = 0
    resultado = {k: datos.get(k, []) for k in CLAVES if k != "inventario"}
    resultado["inventario"] = inventario
    return resultado


def guardar_datos():
    temporal = ARCHIVO_DATOS.with_suffix(".tmp")
    temporal.write_text(json.dumps({k: st.session_state[k] for k in CLAVES}, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ARCHIVO_DATOS)


def avisar(mensaje, icono=None):
    """Guarda un aviso, que se muestra tras recargar la pantalla, y recarga."""
    st.session_state["_aviso"] = (mensaje, icono)
    st.rerun()


def verificar_acceso():
    """Si existe `clave_app` en .streamlit/secrets.toml, pide la contraseña."""
    try:
        clave = st.secrets.get("clave_app", None)
    except Exception:
        clave = None
    if not clave or st.session_state.get("acceso_ok"):
        return
    st.title("Granizados PL")
    intento = st.text_input("Contraseña", type="password")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(str(intento), str(clave)):
            st.session_state["acceso_ok"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()


verificar_acceso()

if "datos_inicializados" not in st.session_state:
    for _k, _v in cargar_datos().items():
        st.session_state[_k] = _v
    st.session_state.datos_inicializados = True

if "_aviso" in st.session_state:
    _msg, _ico = st.session_state.pop("_aviso")
    st.toast(_msg, icon=_ico)


# ------------------------------------------------------------------- LÓGICA
def registrar_movimiento(producto, tipo, cantidad, detalle="", referencia=""):
    st.session_state.movimientos.append({"Fecha": ahora(), "Producto": producto, "Tipo": tipo, "Cantidad": int(cantidad), "Detalle": detalle, "Referencia": referencia})


def registrar_anulacion(tipo, identificador, detalle):
    st.session_state.anulaciones.append({"Fecha": ahora(), "Tipo": tipo, "ID": identificador, "Detalle": detalle})


def ventas_vigentes(desde=None, hasta=None):
    resultado = []
    for v in st.session_state.ventas:
        if v.get("Estado", "Vigente") != "Vigente":
            continue
        f = v.get("Fecha", "")[:10]
        if (desde and f < str(desde)) or (hasta and f > str(hasta)):
            continue
        resultado.append(v)
    return resultado


def compras_vigentes():
    return [c for c in st.session_state.compras if c.get("Estado", "Vigente") == "Vigente"]


def gastos_vigentes(fecha=None):
    return [g for g in st.session_state.gastos if not g.get("Anulado", False) and (fecha is None or g.get("Fecha", "")[:10] == str(fecha))]


def resumen_dia(fecha):
    f = str(fecha)
    ventas, gastos = ventas_vigentes(f, f), gastos_vigentes(f)
    efectivo = suma([v for v in ventas if v.get("Medio de pago") == "Efectivo"])
    transf = suma([v for v in ventas if v.get("Medio de pago") != "Efectivo"])
    gastos_total = suma(gastos, "Valor")
    gastos_efectivo = suma([g for g in gastos if g.get("Medio de pago") == "Efectivo"], "Valor")
    return {"ventas": ventas, "gastos": gastos, "efectivo": efectivo, "transferencias": transf,
            "gastos_total": gastos_total, "caja_efectivo": efectivo - gastos_efectivo,
            "neto": efectivo + transf - gastos_total, "unidades": suma(ventas, "Cantidad")}


def marcar_cierre_desactualizado(fecha):
    for c in st.session_state.cierres_caja:
        if c.get("Fecha cierre") == fecha:
            c["Desactualizado"] = True


def anular_venta(venta_id):
    venta = next((v for v in st.session_state.ventas if v.get("ID") == venta_id and v.get("Estado", "Vigente") == "Vigente"), None)
    if not venta:
        return False, "No se encontró la venta vigente."
    for producto, cantidad in venta.get("Consumos", {}).items():
        st.session_state.inventario[producto] = int(st.session_state.inventario.get(producto, 0)) + int(cantidad)
        registrar_movimiento(producto, "Entrada por anulación de venta", cantidad, "Devolución de inventario", venta_id)
    venta["Estado"], venta["Fecha anulación"] = "Anulada", ahora()
    marcar_cierre_desactualizado(venta["Fecha"][:10])
    registrar_anulacion("Venta", venta_id, "Venta anulada")
    guardar_datos()
    return True, "Venta anulada; el inventario consumido fue devuelto."


def anular_compra(compra_id):
    compra = next((c for c in compras_vigentes() if c.get("ID") == compra_id), None)
    if not compra:
        return False, "No se encontró la compra vigente."
    producto, cantidad = compra["Producto"], int(compra["Cantidad"])
    disponible = int(st.session_state.inventario.get(producto, 0))
    if disponible < cantidad:
        return False, f"No se puede anular: hay {disponible} unidades de {producto} y se deben retirar {cantidad}."
    st.session_state.inventario[producto] = disponible - cantidad
    registrar_movimiento(producto, "Salida por anulación de compra", cantidad, "Reversión de compra", compra_id)
    compra["Estado"], compra["Fecha anulación"] = "Anulada", ahora()
    for g in st.session_state.gastos:
        if g.get("Compra ID") == compra_id:
            g["Anulado"] = True
            marcar_cierre_desactualizado(g["Fecha"][:10])
    registrar_anulacion("Compra", compra_id, "Compra anulada")
    guardar_datos()
    return True, "Compra anulada; se retiraron las unidades y el gasto quedó excluido."


def anular_gasto(gasto_id):
    gasto = next((g for g in gastos_vigentes() if g.get("ID") == gasto_id), None)
    if not gasto:
        return False, "No se encontró el gasto vigente."
    if gasto.get("Compra ID"):
        return False, "Este gasto viene de una compra de granizados; anúlalo desde «Compras vigentes»."
    producto, unidades = gasto.get("Producto"), int(gasto.get("Unidades", 0))
    if producto and unidades:
        disponible = int(st.session_state.inventario.get(producto, 0))
        if disponible < unidades:
            return False, f"No se puede anular: hay {disponible} de {producto} y se deben retirar {unidades}."
        st.session_state.inventario[producto] = disponible - unidades
        registrar_movimiento(producto, "Salida por anulación de gasto", unidades, "Reversión de gasto", gasto_id)
    gasto["Anulado"], gasto["Fecha anulación"] = True, ahora()
    marcar_cierre_desactualizado(gasto["Fecha"][:10])
    registrar_anulacion("Gasto", gasto_id, "Gasto anulado")
    guardar_datos()
    return True, "Gasto anulado; si incluía adiciones, se retiraron del inventario."


def consumos_venta(sabor, presentacion):
    """Solo lo esencial consume inventario. Las adiciones NO descuentan nada."""
    consumos = {clave_sabor(sabor): 1, "Pitillos (und)": 1, "Bolsa de papel (und)": 1}
    if presentacion == "Vaso 12 oz":
        consumos["Vaso 12 oz (und)"] = 1
    return consumos


# --------------------------------------------------------------------- ESTILO
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bungee&display=swap');
.block-container{padding-top:1.5rem;max-width:1200px}
.bg{font-family:'Bungee',sans-serif;font-weight:400}
.banner{background:#ffd23f;border-radius:24px;padding:16px 28px;display:flex;align-items:center;gap:24px;color:#14141c;margin-bottom:12px}
.banner img{width:104px;height:104px;border-radius:18px}
.banner-logo{width:104px;height:104px;border-radius:18px;background:#14141c;color:#fff;display:flex;align-items:center;justify-content:center;font:400 40px 'Bungee',sans-serif}
.banner-texto{flex:1}
.banner-titulo{font:400 34px/1.1 'Bungee',sans-serif}
.banner-sub{font-size:17px;font-weight:500;margin-top:6px}
.banner-ventas{background:#14141c;color:#fff;border-radius:16px;padding:14px 20px;min-width:210px}
.banner-ventas span{display:block;font-size:14px}
.banner-ventas b{display:block;font:400 28px 'Bungee',sans-serif;color:#b6ff3c}
.cobro{background:#14141c;border:3px solid #ff3d9a;border-radius:20px;padding:20px 24px;color:#fff;margin-bottom:10px}
.cobro span{display:block;font-size:15px;color:#d9d9e8}
.cobro b{display:block;font-size:44px;line-height:1.2;color:#b6ff3c}
.cobro p{margin:4px 0 0;font-size:14px;color:#d9d9e8}
.tile{padding:14px 18px;border-radius:16px;color:#14141c;margin-bottom:10px}
.tile span{display:block;font-size:14px;font-weight:500}
.tile b{display:block;font:400 26px 'Bungee',sans-serif}
.chip-cat{display:inline-block;border-radius:999px;padding:4px 14px;font-weight:700;color:#14141c}
[data-testid^="stBaseButton-primary"]{background:#ff3d9a;border:0;min-height:3rem}
[data-testid^="stBaseButton-primary"]:hover{background:#ff5aac}
[data-testid^="stBaseButton-primary"] p{color:#14141c;font-weight:700}
</style>
""", unsafe_allow_html=True)


def tile(etiqueta, valor, color):
    return f'<div class="tile" style="background:{color}"><span>{etiqueta}</span><b>{valor}</b></div>'


def logo_html():
    if LOGO.exists():
        b64 = base64.b64encode(LOGO.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{b64}" alt="Logo Granizados PL">'
    return '<div class="banner-logo">PL</div>'


def encabezado():
    total_hoy = suma(ventas_vigentes(hoy(), hoy()))
    st.markdown(
        f'<div class="banner">{logo_html()}<div class="banner-texto">'
        '<div class="banner-titulo">Punto de venta</div>'
        '<div class="banner-sub">El sabor que nos une · Túquerres, Nariño</div></div>'
        f'<div class="banner-ventas"><span>Ventas de hoy</span><b>{dinero_html(total_hoy)}</b></div></div>',
        unsafe_allow_html=True)


def alerta_inventario():
    """Resume el stock bajo. Las adiciones no se incluyen: no se descuentan al vender."""
    bajo = [(p, int(q)) for p, q in st.session_state.inventario.items() if int(q) <= UMBRAL_BAJO and p not in EXTRAS]
    if not bajo:
        return
    agotados = sum(1 for _, q in bajo if q == 0)
    titulo = f"⚠️ {len(bajo)} productos con poco stock" + (f" · {agotados} agotados" if agotados else "")
    grupos = {"🍧 Sabores": [], "🥤 Insumos": []}
    for p, q in sorted(bajo, key=lambda x: (x[1], x[0])):
        grupos["🍧 Sabores" if p.startswith("Sabor ") else "🥤 Insumos"].append((p.removeprefix("Sabor "), q))
    with st.expander(titulo):
        for col, (nombre, items) in zip(st.columns(2), grupos.items()):
            with col:
                st.markdown(f"**{nombre}** ({len(items)})")
                if not items:
                    st.caption("Todo en orden")
                for p, q in items:
                    estado = "agotado" if q == 0 else f"{q} und"
                    st.markdown(f":{'red' if q == 0 else 'orange'}[●] {p}: **{estado}**")


def elegir(etiqueta, opciones, defecto, clave, **kw):
    valor = st.segmented_control(etiqueta, opciones, default=defecto, key=clave, **kw)
    if valor is None:
        st.caption(f"Sin selección: se usará «{defecto}».")
        return defecto
    return valor


CFG_DINERO = {c: st.column_config.NumberColumn(c, format="$ %d") for c in
              ["Total", "Precio unitario", "Costo unitario", "Costo por unidad", "Valor", "Efectivo", "Transferencias", "Gastos", "Saldo neto estimado", "Caja en efectivo", "Efectivo contado", "Diferencia"]}


def tabla(df):
    st.dataframe(df, hide_index=True, width="stretch", column_config=CFG_DINERO)


def sin_consumos(registros):
    return pd.DataFrame([{k: v for k, v in r.items() if k != "Consumos"} for r in registros])


# ------------------------------------------------------------------------ APP
encabezado()
alerta_inventario()

tab_ventas, tab_inventario, tab_historial, tab_caja, tab_reportes, tab_cierre = st.tabs(
    ["🛒 Ventas", "📦 Inventario", "🧾 Historial", "💵 Caja y gastos", "📊 Reportes", "🔒 Cerrar caja"])

# ---------------------------------------------------------------------- VENTAS
with tab_ventas:
    col_form, col_cobro = st.columns([2, 1], gap="large")
    with col_form:
        with st.container(border=True):
            st.subheader("Nueva venta")
            categoria = elegir("1. Elige la categoría", list(SABORES), "SIN ALCOHOL", "categoria_venta",
                               format_func=lambda c: f"{c.title()} · {dinero(PRECIOS_VENTA[c])}")
            st.markdown(f'<span class="chip-cat" style="background:{COLORES[categoria]}">{categoria.title()}</span>', unsafe_allow_html=True)
            sabores = list(dict.fromkeys(SABORES[categoria]))
            sabor = st.pills("2. Toca un sabor", sabores, default=sabores[0], key=f"sabor_venta_{categoria}")
            c1, c2, c3 = st.columns(3)
            with c1:
                presentacion = elegir("Presentación", ["Vaso 12 oz", "Sachet 12 oz"], "Vaso 12 oz", "presentacion_venta")
            with c2:
                metodo_pago = elegir("Medio de pago", METODOS_PAGO, METODOS_PAGO[0], "pago_venta",
                                     format_func=lambda m: "Efectivo" if m == "Efectivo" else "Nequi / Billeteras")
            with c3:
                cantidad = st.number_input("Cantidad", min_value=1, max_value=50, value=1, step=1, key="cantidad_venta")
            extras = st.multiselect("Adiciones", EXTRAS, key="extras_venta",
                                    help="Se anotan en la venta, pero no descuentan inventario.")
            c4, c5 = st.columns(2)
            cliente = c4.text_input("Cliente (opcional)", key="cliente_venta")
            observacion = c5.text_input("Observación (opcional)", key="obs_venta")

    precio_unitario = PRECIOS_VENTA[categoria]
    total = precio_unitario * int(cantidad)
    with col_cobro:
        pago_corto = "Efectivo" if metodo_pago == "Efectivo" else "Nequi"
        st.markdown(
            f'<div class="cobro"><span>Total a cobrar</span><b class="bg">{dinero_html(total)}</b>'
            f'<p>{int(cantidad)} × {sabor or "—"} · {presentacion} · {pago_corto}</p></div>',
            unsafe_allow_html=True)
        guardar_venta = st.button("Registrar venta", type="primary", width="stretch", disabled=sabor is None)
        r_hoy = resumen_dia(hoy())
        st.markdown("**Resumen de hoy**")
        st.markdown(
            tile("Ventas", len(r_hoy["ventas"]), "#7dff3a")
            + tile("Efectivo", dinero_html(r_hoy["efectivo"]), "#ffe27a")
            + tile("Transferencias", dinero_html(r_hoy["transferencias"]), "#ff8fc2"),
            unsafe_allow_html=True)

    if guardar_venta and sabor:
        consumos = {p: q * int(cantidad) for p, q in consumos_venta(sabor, presentacion).items()}
        faltantes = [(p, q, int(st.session_state.inventario.get(p, 0))) for p, q in consumos.items()
                     if int(st.session_state.inventario.get(p, 0)) < q]
        if faltantes:
            st.error("Inventario insuficiente: " + "; ".join(f"{p}: requiere {q}, disponible {d}" for p, q, d in faltantes))
        else:
            venta_id = "V-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
            for producto, unidades in consumos.items():
                st.session_state.inventario[producto] -= unidades
                registrar_movimiento(producto, "Salida por venta", unidades, f"Venta de {sabor}", venta_id)
            st.session_state.ventas.append({
                "ID": venta_id, "Fecha": ahora(), "Cliente": cliente.strip() or "Cliente general",
                "Categoría": categoria, "Sabor": sabor, "Presentación": presentacion,
                "Cantidad": int(cantidad), "Precio unitario": precio_unitario, "Total": total,
                "Medio de pago": metodo_pago, "Observación": observacion, "Adiciones": extras,
                "Consumos": consumos, "Estado": "Vigente"})
            guardar_datos()
            for k in ("cantidad_venta", "extras_venta", "cliente_venta", "obs_venta"):
                st.session_state.pop(k, None)
            avisar(f"Venta registrada por {dinero(total)}", "✅")

# ------------------------------------------------------------------- INVENTARIO
with tab_inventario:
    st.header("Inventario")
    st.caption("Las adiciones están aquí, pero no se descuentan al vender: ajústalas a mano o al registrar su compra como gasto.")
    with st.expander("Registrar entrada o ajuste manual"):
        with st.form("form_inventario"):
            producto_inv = st.selectbox("Producto", sorted(st.session_state.inventario))
            tipo_inv = st.selectbox("Tipo", ["Entrada / reabastecimiento", "Ajuste: sumar", "Ajuste: restar"])
            cantidad_inv = st.number_input("Unidades", min_value=1, max_value=10000, value=1, step=1)
            detalle_inv = st.text_input("Detalle del movimiento")
            guardar_inv = st.form_submit_button("Guardar movimiento")
        if guardar_inv:
            actual = int(st.session_state.inventario.get(producto_inv, 0))
            sumar = tipo_inv != "Ajuste: restar"
            if not sumar and actual < int(cantidad_inv):
                st.error("El ajuste dejaría el inventario negativo.")
            else:
                st.session_state.inventario[producto_inv] = actual + int(cantidad_inv) if sumar else actual - int(cantidad_inv)
                registrar_movimiento(producto_inv, "Entrada manual" if sumar else "Ajuste de salida", cantidad_inv, detalle_inv)
                guardar_datos()
                avisar("Inventario actualizado.", "📦")
    df_inv = pd.DataFrame([
        {"Producto": p, "Existencias": int(q),
         "Estado": "Sin control" if p in EXTRAS else ("⚠️ Bajo" if int(q) <= UMBRAL_BAJO else "Disponible")}
        for p, q in sorted(st.session_state.inventario.items())])
    tabla(df_inv)
    st.download_button("Descargar inventario CSV", df_inv.to_csv(index=False).encode("utf-8-sig"), "inventario_granizados_pl.csv", "text/csv")
    if st.session_state.movimientos:
        st.subheader("Últimos movimientos")
        tabla(pd.DataFrame(st.session_state.movimientos[-100:][::-1]))

# -------------------------------------------------------------------- HISTORIAL
with tab_historial:
    st.header("Historial de ventas")
    efectivas = ventas_vigentes()
    if efectivas:
        tabla(sin_consumos(efectivas[::-1]).drop(columns=["ID"], errors="ignore"))
        etiquetas = {v["ID"]: f"{v['Fecha'][5:16]} · {v['Sabor']} ×{v['Cantidad']} · {dinero(v['Total'])}" for v in efectivas[::-1]}
        with st.form("form_anular_venta"):
            id_venta = st.selectbox("Venta vigente para anular", list(etiquetas), format_func=etiquetas.get)
            confirmar = st.checkbox("Confirmo que deseo anular esta venta")
            enviar = st.form_submit_button("Anular venta")
        if enviar:
            if not confirmar:
                st.error("Debes confirmar la anulación.")
            else:
                ok, mensaje = anular_venta(id_venta)
                if ok:
                    avisar(mensaje, "↩️")
                st.error(mensaje)
    else:
        st.info("No hay ventas efectivas registradas.")
    if st.session_state.anulaciones:
        with st.expander("Registro de anulaciones (auditoría)"):
            tabla(pd.DataFrame(st.session_state.anulaciones[::-1]))

# ------------------------------------------------------------------------- CAJA
with tab_caja:
    st.header("Caja y gastos")
    r = resumen_dia(hoy())
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ventas en efectivo", dinero(r["efectivo"]), border=True)
    m2.metric("Transferencias", dinero(r["transferencias"]), border=True)
    m3.metric("Gastos de hoy", dinero(r["gastos_total"]), border=True)
    m4.metric("Efectivo en caja", dinero(r["caja_efectivo"]), border=True, help="Ventas en efectivo menos gastos pagados en efectivo.")

    with st.container(border=True):
        st.subheader("Registrar compra de granizados")
        cc1, cc2 = st.columns(2)
        with cc1:
            categoria_compra = elegir("Categoría de compra", list(SABORES), "SIN ALCOHOL", "categoria_compra", format_func=str.title)
            sabor_compra = st.selectbox("Sabor comprado", SABORES[categoria_compra], key=f"sabor_compra_{categoria_compra}")
            cantidad_compra = st.number_input("Cantidad comprada", min_value=1, max_value=10000, value=1, step=1, key="cantidad_compra")
        costo_unitario = PRECIOS_COMPRA[categoria_compra]
        with cc2:
            st.metric("Costo por unidad", dinero(costo_unitario))
            st.metric("Total de la compra", dinero(costo_unitario * int(cantidad_compra)))
            medio_compra = st.selectbox("Medio de pago", METODOS_PAGO, key="medio_pago_compra")
            detalle_compra = st.text_input("Proveedor / detalle (opcional)", key="detalle_compra")
        if st.button("Registrar compra y sumar al inventario", type="primary"):
            producto = clave_sabor(sabor_compra)
            compra_id = "C-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
            total_compra = int(cantidad_compra) * costo_unitario
            st.session_state.compras.append({"ID": compra_id, "Fecha": ahora(), "Categoría": categoria_compra, "Sabor": sabor_compra, "Producto": producto, "Cantidad": int(cantidad_compra), "Costo unitario": costo_unitario, "Valor": total_compra, "Medio de pago": medio_compra, "Detalle": detalle_compra, "Estado": "Vigente"})
            st.session_state.inventario[producto] = int(st.session_state.inventario.get(producto, 0)) + int(cantidad_compra)
            registrar_movimiento(producto, "Entrada por compra de granizados", cantidad_compra, detalle_compra, compra_id)
            st.session_state.gastos.append({"ID": "G-" + compra_id, "Fecha": ahora(), "Concepto": f"Compra de granizados: {sabor_compra}", "Valor": total_compra, "Medio de pago": medio_compra, "Detalle": detalle_compra, "Compra ID": compra_id, "Anulado": False})
            guardar_datos()
            avisar(f"Compra registrada por {dinero(total_compra)}; inventario actualizado.", "🛒")

    st.subheader("Compras vigentes")
    compras = compras_vigentes()
    if compras:
        tabla(pd.DataFrame(compras[::-1]).drop(columns=["ID", "Producto"], errors="ignore"))
        etiq_compras = {c["ID"]: f"{c['Fecha'][5:16]} · {c['Sabor']} ×{c['Cantidad']} · {dinero(c['Valor'])}" for c in compras[::-1]}
        with st.form("form_anular_compra"):
            compra_anular = st.selectbox("Compra para anular", list(etiq_compras), format_func=etiq_compras.get)
            confirmar_compra = st.checkbox("Confirmo que deseo anular esta compra")
            enviar_compra = st.form_submit_button("Anular compra")
        if enviar_compra:
            if not confirmar_compra:
                st.error("Debes confirmar la anulación.")
            else:
                ok, mensaje = anular_compra(compra_anular)
                if ok:
                    avisar(mensaje, "↩️")
                st.error(mensaje)
    else:
        st.info("No hay compras vigentes registradas.")

    with st.container(border=True):
        st.subheader("Registrar otro gasto")
        with st.form("form_gasto", clear_on_submit=True):
            concepto = st.text_input("Concepto del gasto", placeholder="Ej. transporte, servicios, bolsas")
            valor_gasto = st.number_input("Valor ($)", min_value=0, max_value=100000000, value=0, step=500)
            metodo_gasto = st.selectbox("Medio de pago", METODOS_PAGO, key="medio_pago_gasto")
            detalle_gasto = st.text_input("Detalle del gasto")
            st.markdown("**¿Este gasto repone adiciones del inventario?** (opcional)")
            ga1, ga2 = st.columns(2)
            adicion_gasto = ga1.selectbox("Adición comprada", ["No aplica"] + EXTRAS, key="adicion_gasto")
            unidades_gasto = ga2.number_input("Porciones o unidades que entran", min_value=0, max_value=100000, value=0, step=1,
                                              help="Si compraste un paquete, escribe cuántas porciones rinde.", key="unidades_adicion")
            guardar_gasto = st.form_submit_button("Guardar gasto")
        if guardar_gasto:
            es_adicion = adicion_gasto != "No aplica"
            if es_adicion and not concepto.strip():
                concepto = f"Compra de adición: {adicion_gasto}"
            if not concepto.strip() or valor_gasto <= 0:
                st.error("Escribe el concepto y un valor mayor que cero.")
            elif es_adicion and unidades_gasto <= 0:
                st.error("Indica cuántas porciones o unidades entran al inventario.")
            else:
                gasto_id = "G-" + datetime.now(TZ).strftime("%Y%m%d%H%M%S%f")
                gasto = {"ID": gasto_id, "Fecha": ahora(), "Concepto": concepto.strip(), "Valor": int(valor_gasto),
                         "Medio de pago": metodo_gasto, "Detalle": detalle_gasto, "Anulado": False}
                if es_adicion:
                    gasto.update({"Producto": adicion_gasto, "Unidades": int(unidades_gasto),
                                  "Costo por unidad": round(valor_gasto / unidades_gasto)})
                    st.session_state.inventario[adicion_gasto] = int(st.session_state.inventario.get(adicion_gasto, 0)) + int(unidades_gasto)
                    registrar_movimiento(adicion_gasto, "Entrada por gasto (adición)", unidades_gasto, detalle_gasto, gasto_id)
                st.session_state.gastos.append(gasto)
                guardar_datos()
                avisar("Gasto registrado" + (f" y {int(unidades_gasto)} unidades sumadas a {adicion_gasto}." if es_adicion else "."), "💸")

    st.subheader("Gastos vigentes de hoy")
    gastos_hoy = r["gastos"]
    if gastos_hoy:
        tabla(pd.DataFrame(gastos_hoy[::-1]).drop(columns=["ID", "Anulado"], errors="ignore"))
        st.download_button("Descargar gastos CSV", pd.DataFrame(gastos_hoy).to_csv(index=False).encode("utf-8-sig"), "gastos_granizados_pl.csv", "text/csv")
        etiq_gastos = {g["ID"]: f"{g['Fecha'][11:16]} · {g['Concepto']} · {dinero(g['Valor'])}" for g in gastos_hoy[::-1] if not g.get("Compra ID")}
        if etiq_gastos:
            with st.form("form_anular_gasto"):
                gasto_anular = st.selectbox("Gasto para anular", list(etiq_gastos), format_func=etiq_gastos.get)
                confirmar_gasto = st.checkbox("Confirmo que deseo anular este gasto")
                enviar_gasto = st.form_submit_button("Anular gasto")
            if enviar_gasto:
                if not confirmar_gasto:
                    st.error("Debes confirmar la anulación.")
                else:
                    ok, mensaje = anular_gasto(gasto_anular)
                    if ok:
                        avisar(mensaje, "↩️")
                    st.error(mensaje)
    else:
        st.info("No hay gastos vigentes registrados hoy.")

# --------------------------------------------------------------------- REPORTES
with tab_reportes:
    st.header("Reportes")
    col1, col2 = st.columns(2)
    desde = col1.date_input("Desde", value=hoy(), key="reporte_desde")
    hasta = col2.date_input("Hasta", value=hoy(), key="reporte_hasta")
    if desde > hasta:
        st.error("La fecha inicial no puede ser posterior a la fecha final.")
    else:
        periodo = ventas_vigentes(desde, hasta)
        a, b, c = st.columns(3)
        a.metric("Ventas vigentes", len(periodo), border=True)
        b.metric("Unidades vendidas", suma(periodo, "Cantidad"), border=True)
        c.metric("Ingresos", dinero(suma(periodo)), border=True)
        if periodo:
            dfp = sin_consumos(periodo)
            tabla(dfp.drop(columns=["ID"], errors="ignore"))
            st.subheader("Ingresos por categoría")
            st.bar_chart(pd.DataFrame(periodo).groupby("Categoría")["Total"].sum())
            st.download_button("Descargar reporte CSV", dfp.to_csv(index=False).encode("utf-8-sig"), "reporte_ventas_granizados_pl.csv", "text/csv")
        else:
            st.info("No hay ventas vigentes para el período seleccionado.")

# ----------------------------------------------------------------------- CIERRE
with tab_cierre:
    st.header("Cerrar caja")
    st.write("Genera un resumen diario. El cierre se guarda en el historial; no elimina las ventas ni los gastos.")
    fecha_cierre = st.date_input("Fecha que desea cerrar", value=hoy(), key="fecha_cierre")
    ftxt = fecha_cierre.isoformat()
    rc = resumen_dia(ftxt)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Efectivo", dinero(rc["efectivo"]), border=True)
    k2.metric("Transferencias", dinero(rc["transferencias"]), border=True)
    k3.metric("Gastos", dinero(rc["gastos_total"]), border=True)
    k4.metric("Efectivo esperado en caja", dinero(rc["caja_efectivo"]), border=True)
    st.write(f"**Ventas vigentes:** {len(rc['ventas'])} · **Unidades vendidas:** {rc['unidades']} · **Saldo neto estimado:** {dinero(rc['neto'])}")
    contado = st.number_input("Efectivo contado en caja (opcional)", min_value=0, max_value=100000000, value=0, step=500, key="efectivo_contado")
    if contado > 0:
        diferencia = int(contado) - rc["caja_efectivo"]
        st.info(f"Diferencia: {dinero(diferencia)} ({'sobra' if diferencia > 0 else 'falta' if diferencia < 0 else 'cuadra'})")
    with st.expander("Detalle de ventas"):
        if rc["ventas"]:
            tabla(sin_consumos(rc["ventas"]).drop(columns=["ID"], errors="ignore"))
        else:
            st.info("No hay ventas vigentes en esa fecha.")
    with st.expander("Detalle de gastos"):
        if rc["gastos"]:
            tabla(pd.DataFrame(rc["gastos"]).drop(columns=["ID", "Anulado"], errors="ignore"))
        else:
            st.info("No hay gastos vigentes en esa fecha.")
    if st.button("Guardar cierre de caja", type="primary"):
        if any(c.get("Fecha cierre") == ftxt for c in st.session_state.cierres_caja):
            st.warning("Ya existe un cierre guardado para esa fecha.")
        else:
            st.session_state.cierres_caja.append({
                "Fecha cierre": ftxt, "Fecha y hora de registro": ahora(), "Cantidad de ventas": len(rc["ventas"]),
                "Unidades vendidas": rc["unidades"], "Efectivo": rc["efectivo"], "Transferencias": rc["transferencias"],
                "Gastos": rc["gastos_total"], "Saldo neto estimado": rc["neto"], "Caja en efectivo": rc["caja_efectivo"],
                "Efectivo contado": int(contado) or None,
                "Diferencia": (int(contado) - rc["caja_efectivo"]) if contado > 0 else None})
            guardar_datos()
            avisar("Cierre de caja guardado.", "🔒")
    if st.session_state.cierres_caja:
        st.subheader("Historial de cierres")
        if any(c.get("Desactualizado") for c in st.session_state.cierres_caja):
            st.warning("Hay cierres marcados como desactualizados: se anuló una venta, compra o gasto de una fecha ya cerrada.")
        dfc = pd.DataFrame(st.session_state.cierres_caja[::-1])
        tabla(dfc)
        st.download_button("Descargar historial de cierres CSV", dfc.to_csv(index=False).encode("utf-8-sig"), "cierres_caja_granizados_pl.csv", "text/csv")

st.caption("Granizados PL · Datos guardados en datos_granizados_pl/datos_pos.json")
