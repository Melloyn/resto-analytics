import streamlit as st
import streamlit.components.v1 as components
import auth
from views import login_view

def init_session_state():
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
                if restored and restored[6] == "approved":
                    st.session_state.auth_user = {
                        "id": restored[0],
                        "full_name": restored[1],
                        "login": restored[2],
                        "role": restored[5],
                        "status": restored[6],
                    }
                    st.session_state.auth_token = token_from_cookie

def validate_current_session():
    if st.session_state.auth_user is not None:
        fresh_user = auth.get_user_by_id(st.session_state.auth_user["id"])
        if not fresh_user or fresh_user[6] != "approved":
            if st.session_state.auth_token:
                auth.drop_runtime_session(st.session_state.auth_token)
            clear_browser_auth_token()
            st.session_state.auth_user = None
            st.session_state.auth_token = None
            st.warning("Доступ отозван или аккаунт не одобрен.")
            login_view.render_auth_screen()
            st.stop()

        st.session_state.auth_user.update({
            "id": fresh_user[0],
            "full_name": fresh_user[1],
            "login": fresh_user[2],
            "role": fresh_user[5],
            "status": fresh_user[6],
        })
        
        if st.session_state.auth_token is None:
            try:
                current_ua = st.context.headers.get("user-agent")
            except Exception:
                current_ua = None
                
            st.session_state.auth_token = auth.create_runtime_session(
                fresh_user[0],
                user_agent=current_ua,
            )
            
        st.session_state.is_admin = st.session_state.auth_user.get("role") == "admin"

def logout():
    if st.session_state.auth_token:
        auth.drop_runtime_session(st.session_state.auth_token)
    clear_browser_auth_token()
    st.session_state.auth_user = None
    st.session_state.auth_token = None
    st.rerun()
