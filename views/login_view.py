import streamlit as st
import auth
import streamlit.components.v1 as components

def render_auth_screen():
    # Recover cookie from localStorage if browser lost it (after idle/restart).
    components.html(
        """
        <script>
        (function () {
          try {
              const token = localStorage.getItem("resto_auth_token");
              const attempted = sessionStorage.getItem("resto_auto_login_attempted");
              const hasCookie = document.cookie.split("; ").some((x) => x.trim().startsWith("resto_auth_token="));
              
              if (token && !hasCookie && !attempted) {
                sessionStorage.setItem("resto_auto_login_attempted", "1");
                const maxAge = 2592000; // 30 days
                const cookieStr = "resto_auth_token=" + encodeURIComponent(token) + "; path=/; max-age=" + maxAge + "; SameSite=Lax";
                
                document.cookie = cookieStr;
                try { window.parent.document.cookie = cookieStr; } catch(e) {}
                
                window.location.reload();
              }
          } catch (e) {
              console.error("Auto-login error", e);
          }
        })();
        </script>
        """,
        height=0
    )

    st.title("🔐 Вход в RestoAnalytic")
    tab_login, tab_register = st.tabs(["Вход", "Регистрация"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            login = st.text_input("Логин")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")
            if submitted:
                try:
                    user = auth.authenticate_user(login, password)
                    token = auth.create_runtime_session(
                        user["id"],
                        user_agent=st.context.headers.get("user-agent"),
                    )
                    st.session_state.auth_user = {
                        "id": user["id"],
                        "full_name": user["full_name"],
                        "login": user["login"],
                        "role": user["role"],
                        "status": user["status"],
                    }
                    st.session_state.auth_token = token
                    
                    # Persist browser cookie for refresh survival
                    # Use both document.cookie and parent.document.cookie for iframe compatibility
                    components.html(
                        f"""
                        <script>
                            var token = "{token}";
                            var maxAge = 2592000; // 30 days
                            var cookieStr = "resto_auth_token=" + encodeURIComponent(token) + "; path=/; max-age=" + maxAge + "; SameSite=Lax";
                            
                            document.cookie = cookieStr;
                            localStorage.setItem("resto_auth_token", token);
                            sessionStorage.removeItem("resto_auto_login_attempted");
                            
                            // Try setting on parent if inside iframe (Streamlit component)
                            try {{
                                window.parent.document.cookie = cookieStr;
                            }} catch (e) {{
                                console.log("Cross-origin frame block, normal behavior if different origin");
                            }}
                        </script>
                        """,
                        height=0
                    )
                    import time
                    time.sleep(1) # Give JS time to execute
                    st.rerun()
                except auth.InvalidCredentialsError as e:
                    st.error(str(e))

    with tab_register:
        with st.form("register_form", clear_on_submit=True):
            full_name = st.text_input("Имя *")
            login = st.text_input("Логин *")
            email = st.text_input("Почта *")
            phone = st.text_input("Номер телефона *")
            password = st.text_input("Пароль *", type="password")
            password_confirm = st.text_input("Подтверждение пароля *", type="password")
            submitted = st.form_submit_button("Зарегистрироваться")
            if submitted:
                if not all([full_name.strip(), login.strip(), email.strip(), phone.strip(), password, password_confirm]):
                    st.error("Заполните все обязательные поля.")
                elif password != password_confirm:
                    st.error("Пароли не совпадают.")
                elif len(password) < 8:
                    st.error("Пароль должен быть не короче 8 символов.")
                else:
                    try:
                        auth.create_user(full_name.strip(), login.strip(), email.strip(), phone.strip(), password)
                        st.success("Регистрация отправлена. Ожидайте одобрения администратора.")
                    except auth.UserAlreadyExistsError:
                        st.error("Логин или почта уже заняты.")
