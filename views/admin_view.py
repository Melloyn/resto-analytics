import streamlit as st
import pandas as pd
import auth
import os
from services import category_service

def render_admin_panel(main_loader_slot):
    st.header("⚙️ Панель Администратора")
    
    tab_users, tab_cats, tab_debug = st.tabs(["👥 Пользователи", "🏷 Категории", "🐞 Debug"])

    # --- TAB 1: USERS ---
    with tab_users:
        with st.expander("🛡 Заявки и список", expanded=True):
            pending = auth.get_pending_users()
            if pending:
                st.warning(f"Ожидают одобрения: {len(pending)}")
                for u in pending:
                    user_id, full_name, login, email, phone, created_at = u
                    st.markdown(f"**{full_name}** (`{login}`)\n\n{email} | {phone}")
                    c1, c2, c3 = st.columns([1, 1, 1.2])
                    with c1:
                        if st.button("✅ Одобрить", key=f"approve_{user_id}", use_container_width=True):
                            auth.update_user_status(user_id, "approved")
                            st.rerun()
                    with c2:
                        if st.button("⛔ Отклонить", key=f"reject_{user_id}", use_container_width=True):
                            auth.update_user_status(user_id, "rejected")
                            st.rerun()
                    with c3:
                        role_choice = st.selectbox(
                            "Роль",
                            ["user", "admin"],
                            key=f"role_pending_{user_id}",
                            label_visibility="collapsed"
                        )
                        if st.button("💾 Роль", key=f"save_role_{user_id}", use_container_width=True):
                            auth.update_user_role(user_id, role_choice)
                            st.rerun()
                    st.divider()
            else:
                st.info("Нет новых заявок.")
    
            st.subheader("Все пользователи")
            users = auth.get_all_users()
            if users:
                users_df = pd.DataFrame(
                    users,
                    columns=["id", "Имя", "Логин", "Почта", "Телефон", "Роль", "Статус", "Создан"]
                )
                st.dataframe(users_df.drop(columns=["id"]), use_container_width=True, hide_index=True)

    # --- TAB 2: CATEGORIES ---
    with tab_cats:
        st.caption("Управление привязкой блюд к категориям. Данные сохраняются в `categories.json`.")
        
        # 1. SYNC
        c_sync1, c_sync2 = st.columns(2)
        yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
        
        with c_sync1:
            if st.button("☁️ Загрузить из Yandex.Disk"):
                if category_service.sync_from_yandex(yd_token):
                    st.success("Категории обновлены из облака!")
                    st.rerun()
                else:
                    st.error("Ошибка синхронизации (проверьте токен).")
        with c_sync2:
            if st.button("☁️ Сохранить в Yandex.Disk"):
                if category_service.sync_to_yandex(yd_token):
                    st.success("Категории сохранены в облако!")
                else:
                    st.error("Ошибка выгрузки.")

        st.divider()
        
        # 2. EDITOR
        current_map = category_service.load_categories()
        all_cats = category_service.get_all_known_categories()
        
        # Add New
        with st.form("add_cat_form", clear_on_submit=True):
            c_add1, c_add2 = st.columns([2, 1])
            new_item = c_add1.text_input("Название блюда (как в отчете)")
            new_cat = c_add2.selectbox("Категория", all_cats)
            if st.form_submit_button("➕ Добавить / Обновить"):
                if new_item.strip():
                    new_item = new_item.strip().lower() # Normalize key
                    category_service.save_categories({new_item: new_cat})
                    st.success(f"Сохранено: {new_item} -> {new_cat}")
                    st.rerun()
        
        # List / Delete
        if current_map:
            st.subheader(f"Текущие привязки ({len(current_map)})")
            
            # Filter
            search = st.text_input("🔍 Поиск по названию", "")
            filtered_items = {k:v for k,v in current_map.items() if search.lower() in k} if search else current_map
            
            # Show as table with delete buttons? Dataframe is faster for display
            df_map = pd.DataFrame(list(filtered_items.items()), columns=['Блюдо', 'Категория'])
            st.dataframe(df_map, use_container_width=True, height=300)
            
            # Delete specific
            to_delete = st.text_input("Удалить блюдо (введите точное название):")
            if st.button("🗑 Удалить запись") and to_delete:
                to_delete = to_delete.strip().lower()
                if to_delete in current_map:
                    del current_map[to_delete]
                    category_service.save_categories_full(current_map)
                    st.success(f"Удалено: {to_delete}")
                    st.rerun()
                else:
                    st.warning("Не найдено.")

    # --- TAB 3: DEBUG ---
    with tab_debug:
        st.write("### 🐞 Debug: Отброшенные позиции")
        if st.session_state.dropped_stats and st.session_state.dropped_stats['count'] > 0:
            st.write(f"**Кол-во:** {st.session_state.dropped_stats['count']}")
            st.write(f"**Cумма:** {st.session_state.dropped_stats['cost']:,.0f} ₽")
            
            items_df = pd.DataFrame(st.session_state.dropped_stats['items'])
            if not items_df.empty:
                items_df = items_df.sort_values(by='Себестоимость', ascending=False).head(50)
                st.dataframe(items_df, use_container_width=True)
                
                # Action to add to categories directly?
                sel_item = st.selectbox("Добавить в категории:", [""] + items_df['norm_name'].tolist())
                if sel_item:
                    st.info(f"Перейдите во вкладку 'Категории' и введите: {sel_item}")
        else:
            st.info("Нет отброшенных данных.")
