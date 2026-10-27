import streamlit as st
import pandas as pd
from supabase import create_client, Client
import bcrypt

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

# Función para asegurar automáticamente el usuario admin y actualizar su hash bcrypt
def asegurar_usuario_admin():
    try:
        supabase = init_supabase()
        # Generar un hash fresco y seguro con bcrypt para 'admin123'
        hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        res = supabase.table("usuarios").select("*").eq("username", "admin").execute()
        
        if not res.data:
            # Si no existe, lo creamos
            supabase.table("usuarios").insert({
                "username": "admin",
                "password_hash": hashed_password,
                "rol": "Administrador"
            }).execute()
        else:
            # Si ya existe, actualizamos su contraseña al hash correcto actual
            supabase.table("usuarios").update({
                "password_hash": hashed_password
            }).eq("username", "admin").execute()
    except Exception as e:
        pass

# Ejecutar verificación y actualización de admin al iniciar
asegurar_usuario_admin()

# Estado de sesión para control de acceso
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None

# Función de verificación de credenciales con bcrypt
def verificar_credenciales(username, password):
    try:
        supabase = init_supabase()
        response = supabase.table("usuarios").select("*").eq("username", username).execute()
        
        if response.data and len(response.data) > 0:
            user_record = response.data[0]
            stored_hash = user_record["password_hash"]
            
            # Validar la contraseña ingresada con el hash almacenado
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                return True, user_record["rol"]
        return False, None
    except Exception as e:
        st.error(f"Error al verificar credenciales: {e}")
        return False, None

# Interfaz de Login
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
else:
    # Panel Principal de la Aplicación POS
    supabase = init_supabase()
    
    st.sidebar.title("🍧 Granizados PL")
    st.sidebar.write(f"Usuario: **{st.session_state.user}**")
    st.sidebar.write(f"Rol: **{st.session_state.role}**")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.selectbox("Menú Principal", ["Ventas", "Inventario", "Compras", "Gastos", "Cierres de Caja"])
    
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.role = None
        st.rerun()
        
    if menu == "Ventas":
        st.header("🛒 Módulo de Ventas")
        st.info("Registra las ventas y procesa los cobros diarios.")
        
    elif menu == "Inventario":
        st.header("📦 Control de Inventario")
        try:
            res = supabase.table("inventario").select("*").execute()
            if res.data:
                df_inv = pd.DataFrame(res.data)
                st.dataframe(df_inv, use_container_width=True)
            else:
                st.warning("No hay productos registrados en el inventario.")
        except Exception as e:
            st.error(f"Error al cargar el inventario: {e}")
            
    elif menu == "Compras":
        st.header("📥 Módulo de Compras")
        st.info("Gestiona el reabastecimiento de insumos y mercancía.")
        
    elif menu == "Gastos":
        st.header("💸 Registro de Gastos")
        st.info("Lleva el control de los gastos operativos del negocio.")
        
    elif menu == "Cierres de Caja":
        st.header("🔒 Cierres de Caja")
        st.info("Realiza y consulta los arqueos y cierres diarios.")
