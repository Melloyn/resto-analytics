import streamlit as st
import auth
import sqlite3
import streamlit.components.v1 as components

def render_auth_screen():
    st.title("🔐 Вход в RestoAnalytic")
    tab_login, tab_register = st.tabs(["Вход", "Регистрация"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            login = st.text_input("Логин")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")
            if submitted:
                user, err = auth.authenticate_user(login, password)
                if err:
                    st.error(err)
                else:
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
                    components.html(
                        f"""
                        <script>
                            document.cookie = "resto_auth_token=" + encodeURIComponent("{token}") + "; path=/; max-age=2592000; SameSite=Lax";
                        </script>
                        """,
                        height=0
                    )
                    st.rerun()

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
                    except sqlite3.IntegrityError:
                        st.error("Логин или почта уже заняты.")
