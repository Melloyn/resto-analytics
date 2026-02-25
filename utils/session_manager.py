import streamlit as st
import streamlit.components.v1 as components
import auth
from use_cases.session_models import UserSession, is_admin, is_approved
from views import login_view

"""
SESSION STATE CONTRACT

Этот файл управляет состоянием пользовательской сессии Streamlit.

Ключи st.session_state:

auth_user: dict | None  
    текущий авторизованный пользователь  
    default: None  
    owner: auth/session_manager  

runtime_token: str | None  
    runtime токен текущей сессии  
    default: None  
    owner: auth/session_manager  

df_full: pd.DataFrame | None  
    основной датафрейм приложения  
    default: None  
    owner: analytics  

view_cache: dict  
    кеш UI представлений  
    default: {}  
    owner: ui  

session_diag_seen: bool  
    флаг, предотвращающий повторный показ диагностики cookie  
    default: False  
    owner: system
"""

def init_session_state():
    if "session_diag_seen" not in st.session_state:
        st.session_state.session_diag_seen = False
    if 'df_full' not in st.session_state:
        st.session_state.df_full = None
    if 'dropped_stats' not in st.session_state:
        st.session_state.dropped_stats = {'count': 0, 'cost': 0.0, 'items': []}
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'auth_user' not in st.session_state:
        st.session_state.auth_user = None
    if 'auth_token' not in st.session_state:
        st.session_state.auth_token = None
    if 'df_version' not in st.session_state:
        st.session_state.df_version = 0
    if 'categories_applied_sig' not in st.session_state:
        st.session_state.categories_applied_sig = None
    if 'view_cache' not in st.session_state:
        st.session_state.view_cache = {}
    if 'yandex_path' not in st.session_state:
        st.session_state.yandex_path = "RestoAnalytic"
    if 'edit_yandex_path' not in st.session_state:
        st.session_state.edit_yandex_path = False
    if 'admin_fullscreen' not in st.session_state:
        st.session_state.admin_fullscreen = False
    if 'admin_fullscreen_tab' not in st.session_state:
        st.session_state.admin_fullscreen_tab = None
    if 'categories_synced' not in st.session_state:
        st.session_state.categories_synced = False
    if 'users_synced' not in st.session_state:
        st.session_state.users_synced = False
    if "session_diag_seen" not in st.session_state:
        st.session_state.session_diag_seen = False

def clear_browser_auth_token():
    components.html(
        """
        <script>
          document.cookie = "resto_auth_token=; path=/; max-age=0; SameSite=Lax";
          localStorage.removeItem("resto_auth_token");
          sessionStorage.removeItem("resto_auto_login_attempted");
        </script>
        """,
        height=0,
    )

def check_and_restore_session():
    if st.session_state.auth_user is None:
        try:
            current_ua = st.context.headers.get("user-agent")
            token_from_cookie = st.context.cookies.get("resto_auth_token")
        except Exception:
            # During some tests contexts might not be fully available
            current_ua = None
            token_from_cookie = None
            
        if token_from_cookie:
            from urllib.parse import unquote
            token_from_cookie = unquote(token_from_cookie)
            uid = auth.resolve_runtime_session(token_from_cookie, user_agent=current_ua)
            if uid is not None:
                restored = auth.get_user_by_id(uid)
                if restored:
                    restored_user = UserSession(
                        id=restored[0],
                        full_name=restored[1],
                        login=restored[2],
                        role=restored[5],
                        status=restored[6],
                    )
                    if is_approved(restored_user):
                        st.session_state.auth_user = restored_user
                        st.session_state.auth_token = token_from_cookie
                    else:
                        if not st.session_state.session_diag_seen:
                            st.warning("Не удалось восстановить сессию. Выполните вход заново.")
                            st.session_state.session_diag_seen = True
                else:
                    if not st.session_state.session_diag_seen:
                        st.warning("Не удалось восстановить сессию. Выполните вход заново.")
                        st.session_state.session_diag_seen = True

def validate_current_session():
    if st.session_state.auth_user is not None:
        fresh_user = auth.get_user_by_id(st.session_state.auth_user.id)
        fresh_user_session = None
        if fresh_user:
            fresh_user_session = UserSession(
                id=fresh_user[0],
                full_name=fresh_user[1],
                login=fresh_user[2],
                role=fresh_user[5],
                status=fresh_user[6],
            )
        if fresh_user_session is None or not is_approved(fresh_user_session):
            if st.session_state.auth_token:
                auth.drop_runtime_session(st.session_state.auth_token)
            clear_browser_auth_token()
            st.session_state.auth_user = None
            st.session_state.auth_token = None
            st.warning("Доступ отозван или аккаунт не одобрен.")
            login_view.render_auth_screen()
            st.stop()

        st.session_state.auth_user = fresh_user_session
        
        if st.session_state.auth_token is None:
            try:
                current_ua = st.context.headers.get("user-agent")
            except Exception:
                current_ua = None
                
            st.session_state.auth_token = auth.create_runtime_session(
                fresh_user_session.id,
                user_agent=current_ua,
            )
            
        st.session_state.is_admin = is_admin(st.session_state.auth_user)

def logout():
    if st.session_state.auth_token:
        auth.drop_runtime_session(st.session_state.auth_token)
    clear_browser_auth_token()
    st.session_state.auth_user = None
    st.session_state.auth_token = None
    st.rerun()
