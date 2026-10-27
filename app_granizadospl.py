import streamlit as st
import pandas as pd
from supabase import create_client, Client
import bcrypt
from datetime import datetime

st.set_page_config(
    page_title="Granizados PL - POS Cloud",
    page_icon="🍧",
    layout="wide"
)

# Inicializar cliente de Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url.strip(), key.strip())

# Asegurar usuario admin al iniciar
def asegurar_usuario_admin():
    try:
        supabase = init_supabase()
        hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        res = supabase.table("usuarios").select("*").eq("username", "admin").execute()
        if not res.data:
            supabase.table("usuarios").insert({
                "username": "admin",
                "password_hash": hashed_password,
                "rol": "Administrador"
            }).execute()
        else:
            supabase.table("usuarios").update({
                "password_hash": hashed_password
            }).eq("username", "admin").execute()
    except Exception:
        pass

asegurar_usuario_admin()

# Estado de sesión
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "carrito" not in st.session_state:
    st.session_state.carrito = []

def verificar_credenciales(username, password):
    try:
        supabase = init_supabase()
        response = supabase.table("usuarios").select("*").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            user_record = response.data[0]
            stored_hash = user_record["password_hash"]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                return True, user_record["rol"]
        return False, None
    except Exception as e:
        st.error(f"Error al verificar credenciales: {e}")
        return False, None

# --- PANTALLA DE LOGIN ---
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🍧 Granizados PL</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Acceso Seguro - Sistema POS Cloud</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username_input = st.text_input("Usuario")
            password_input = st.text_input("Contraseña", type="password")
            submit_button = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit_button:
                is_valid, role = verificar_credenciales(username_input, password_input)
                if is_valid:
                    st.session_state.authenticated = True
                    st.session_state.user = username_input
                    st.session_state.role = role
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

# --- PANEL PRINCIPAL DE LA APLICACIÓN ---
else:
    supabase = init_supabase()
    
    st.sidebar.title("🍧 Granizados PL")
    st.sidebar.write(f"Usuario: **{st.session_state.user}**")
    st.sidebar.write(f"Rol: **{st.session_state.role}**")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.selectbox("Menú Principal", ["🛒 Ventas POS", "📦 Inventario", "📥 Compras", "💸 Gastos", "🔒 Cierres de Caja"])
    
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.carrito = []
        st.rerun()
        
    # --- 1. MÓDULO DE VENTAS POS ---
    if menu == "🛒 Ventas POS":
        st.header("🛒 Registrar Nueva Venta")
        
        # Cargar productos desde Supabase
        res_inv = supabase.table("inventario").select("*").execute()
        productos = res_inv.data if res_inv.data else []
        
        if not productos:
            st.warning("No hay productos en el inventario. Por favor agrega productos en la pestaña 'Inventario'.")
        else:
            col_v1, col_v2 = st.columns([2, 1])
            
            with col_v1:
                st.subheader("Agregar Productos al Carrito")
                df_prod = pd.DataFrame(productos)
                st.dataframe(df_prod[["id", "nombre", "precio", "stock"]], use_container_width=True)
                
                prod_nombres = [f"{p['id']} - {p['nombre']} (${p['precio']:,})" for p in productos]
                prod_sel = st.selectbox("Seleccionar Producto", prod_nombres)
                cant_sel = st.number_input("Cantidad", min_value=1, value=1, step=1)
                
                if st.button("➕ Agregar al Carrito"):
                    prod_id = int(prod_sel.split(" - ")[0])
                    producto_obj = next((p for p in productos if p["id"] == prod_id), None)
                    
                    if producto_obj:
                        if cant_sel > producto_obj.get("stock", 0):
                            st.error("No hay suficiente stock disponible.")
                        else:
                            subtotal = producto_obj["precio"] * cant_sel
                            st.session_state.carrito.append({
                                "id": producto_obj["id"],
                                "nombre": producto_obj["nombre"],
                                "precio": producto_obj["precio"],
                                "cantidad": cant_sel,
                                "subtotal": subtotal
                            })
                            st.success(f"{producto_obj['nombre']} agregado al carrito.")
            
            with col_v2:
                st.subheader("Resumen del Carrito")
                if len(st.session_state.carrito) == 0:
                    st.info("El carrito está vacío.")
                else:
                    df_carrito = pd.DataFrame(st.session_state.carrito)
                    st.table(df_carrito[["nombre", "cantidad", "subtotal"]])
                    
                    total_venta = sum(item["subtotal"] for item in st.session_state.carrito)
                    st.markdown(f"### **Total: ${total_venta:,.2f}**")
                    
                    metodo_pago = st.selectbox("Método de Pago", ["Efectivo", "Nequi/Daviplata", "Tarjeta", "Otro"])
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("✅ Procesar Venta", use_container_width=True):
                            try:
                                # 1. Registrar Venta
                                venta_resp = supabase.table("ventas").insert({
                                    "total": total_venta,
                                    "metodo_pago": metodo_pago,
                                    "vendedor": st.session_state.user,
                                    "fecha": datetime.now().isoformat()
                                }).execute()
                                
                                # 2. Descontar Stock
                                for item in st.session_state.carrito:
                                    prod_actual = next((p for p in productos if p["id"] == item["id"]), None)
                                    nuevo_stock = prod_actual["stock"] - item["cantidad"]
                                    supabase.table("inventario").update({"stock": nuevo_stock}).eq("id", item["id"]).execute()
                                
                                st.session_state.carrito = []
                                st.balloons()
                                st.success("¡Venta registrada con éxito!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al procesar la venta: {e}")
                                
                    with col_b2:
                        if st.button("🗑️ Vaciar Carrito", use_container_width=True):
                            st.session_state.carrito = []
                            st.rerun()

    # --- 2. MÓDULO DE INVENTARIO ---
    elif menu == "📦 Inventario":
        st.header("📦 Gestión de Inventario")
        
        tab1, tab2 = st.tabs(["Ver Inventario", "➕ Agregar / Editar Producto"])
        
        with tab1:
            try:
                res = supabase.table("inventario").select("*").execute()
                if res.data:
                    df_inv = pd.DataFrame(res.data)
                    st.dataframe(df_inv, use_container_width=True)
                else:
                    st.info("No hay productos registrados aún.")
            except Exception as e:
                st.error(f"Error al cargar inventario: {e}")
                
        with tab2:
            with st.form("form_producto"):
                nombre_p = st.text_input("Nombre del Producto / Granizado")
                categoria_p = st.text_input("Categoría", value="Granizados")
                precio_p = st.number_input("Precio de Venta", min_value=0.0, step=100.0)
                costo_p = st.number_input("Costo de Producción", min_value=0.0, step=100.0)
                stock_p = st.number_input("Stock Inicial", min_value=0, step=1)
                
                guardar_p = st.form_submit_button("Guardar Producto")
                if guardar_p:
                    if nombre_p.strip() == "":
                        st.error("El nombre del producto no puede estar vacío.")
                    else:
                        try:
                            supabase.table("inventario").insert({
                                "nombre": nombre_p,
                                "categoria": categoria_p,
                                "precio": precio_p,
                                "costo": costo_p,
                                "stock": stock_p
                            }).execute()
                            st.success(f"Producto '{nombre_p}' registrado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar producto: {e}")

    # --- 3. MÓDULO DE COMPRAS ---
    elif menu == "📥 Compras":
        st.header("📥 Registro de Compras e Insumos")
        with st.form("form_compras"):
            descripcion_compra = st.text_input("Descripción de la Compra / Insumo")
            monto_compra = st.number_input("Monto Total ($)", min_value=0.0, step=500.0)
            proveedor = st.text_input("Proveedor")
            
            btn_compra = st.form_submit_button("Registrar Compra")
            if btn_compra:
                try:
                    supabase.table("compras").insert({
                        "descripcion": descripcion_compra,
                        "monto": monto_compra,
                        "proveedor": proveedor,
                        "fecha": datetime.now().isoformat()
                    }).execute()
                    st.success("Compra registrada con éxito.")
                except Exception as e:
                    st.error(f"Error al registrar compra: {e}")

    # --- 4. MÓDULO DE GASTOS ---
    elif menu == "💸 Gastos":
        st.header("💸 Registro de Gastos Operativos")
        with st.form("form_gastos"):
            concepto_gasto = st.text_input("Concepto del Gasto (Ej. Servicios, Arriendo, Empaques)")
            monto_gasto = st.number_input("Monto ($)", min_value=0.0, step=500.0)
            categoria_gasto = st.selectbox("Categoría", ["Servicios Publicos", "Arriendo", "Mantenimiento", "Nomina", "Otros"])
            
            btn_gasto = st.form_submit_button("Registrar Gasto")
            if btn_gasto:
                try:
                    supabase.table("gastos").insert({
                        "concepto": concepto_gasto,
                        "monto": monto_gasto,
                        "categoria": categoria_gasto,
                        "fecha": datetime.now().isoformat()
                    }).execute()
                    st.success("Gasto registrado con éxito.")
                except Exception as e:
                    st.error(f"Error al registrar gasto: {e}")

    # --- 5. CIERRES DE CAJA ---
    elif menu == "🔒 Cierres de Caja":
        st.header("🔒 Cierre y Arqueo de Caja")
        st.write("Consulta del consolidado del día:")
        
        try:
            res_ventas = supabase.table("ventas").select("total").execute()
            total_v = sum([v["total"] for v in res_ventas.data]) if res_ventas.data else 0.0
            
            res_gastos = supabase.table("gastos").select("monto").execute()
            total_g = sum([g["monto"] for g in res_gastos.data]) if res_gastos.data else 0.0
            
            col_c1, col_c2, col_c3 = st.columns(3)
            col_c1.metric("Total Ventas", f"${total_v:,.2f}")
            col_c2.metric("Total Gastos", f"${total_g:,.2f}")
            col_c3.metric("Balance Neto", f"${(total_v - total_g):,.2f}")
            
            if st.button("🔒 Realizar Cierre de Caja del Día"):
                supabase.table("cierres_caja").insert({
                    "total_ventas": total_v,
                    "total_gastos": total_g,
                    "saldo_final": total_v - total_g,
                    "fecha_cierre": datetime.now().isoformat(),
                    "responsable": st.session_state.user
                }).execute()
                st.success("Cierre de caja guardado exitosamente.")
        except Exception as e:
            st.error(f"Error al realizar cierre de caja: {e}")
