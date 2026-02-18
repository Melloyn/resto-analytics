import streamlit as st
import pandas as pd
import auth
import os
import requests
from services import category_service
from services import parsing_service

from datetime import datetime

def _render_misc_tab():
    st.caption("Позиции с категорией '📦 Прочее'. Здесь можно быстро разнести их по правильным категориям.")
    df_full = st.session_state.get("df_full")
    if df_full is None or df_full.empty:
        st.info("Нет загруженных данных.")
        return
    if "Категория" not in df_full.columns or "Блюдо" not in df_full.columns:
        st.info("В данных нет колонки 'Категория' или 'Блюдо'.")
        return

    other_df = df_full[df_full["Категория"] == "📦 Прочее"].copy()
    if other_df.empty:
        st.success("Позиции 'Прочее' не найдены.")
        return

    agg = other_df.groupby("Блюдо").agg({
        "Выручка с НДС": "sum",
        "Количество": "sum"
    }).reset_index().sort_values("Выручка с НДС", ascending=False)
    agg["Новая категория"] = ""
    all_cats = category_service.get_all_known_categories()

    st.write(f"Найдено позиций: {len(agg)}")
    edited = st.data_editor(
        agg,
        use_container_width=True,
        height=500,
        column_config={
            "Выручка с НДС": st.column_config.NumberColumn(format="%.0f ₽"),
            "Количество": st.column_config.NumberColumn(format="%.0f"),
            "Новая категория": st.column_config.SelectboxColumn(
                options=all_cats,
                required=False
            ),
        }
    )

    if st.button("💾 Сохранить назначения", type="primary"):
        updates = {}
        for _, row in edited.iterrows():
            new_cat = str(row.get("Новая категория") or "").strip()
            dish = str(row.get("Блюдо") or "").strip()
            if dish and new_cat:
                updates[parsing_service.normalize_name(dish)] = new_cat
        if updates:
            category_service.save_categories(updates)
            yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
            if yd_token:
                category_service.sync_to_yandex(yd_token)
            df_full = category_service.apply_categories(df_full)
            st.session_state.df_full = df_full
            st.session_state.df_version += 1
            st.session_state.categories_applied_sig = datetime.utcnow().isoformat()
            st.success(f"Обновлено категорий: {len(updates)}")
            st.rerun()
        else:
            st.info("Нет выбранных назначений.")

def render_admin_panel(main_loader_slot, default_tab=None):
    st.header("⚙️ Панель Администратора")

    if default_tab == "misc":
        _render_misc_tab()
        return
    
    tab_users, tab_cats, tab_misc, tab_debug = st.tabs(["👥 Пользователи", "🏷 Категории", "📦 Прочее", "🐞 Debug"])

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
                    yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
                    if yd_token:
                        category_service.sync_to_yandex(yd_token)
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
                    yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
                    if yd_token:
                        category_service.sync_to_yandex(yd_token)
                    st.success(f"Удалено: {to_delete}")
                    st.rerun()
                else:
                    st.warning("Не найдено.")

    # --- TAB 3: MISC / OTHER ---
    with tab_misc:
        _render_misc_tab()

    # --- TAB 4: DEBUG ---
    with tab_debug:
        st.write("### 🐞 Debug: Отброшенные позиции")
        if st.session_state.dropped_stats and st.session_state.dropped_stats['count'] > 0:
            st.write(f"**Кол-во:** {st.session_state.dropped_stats['count']}")
            st.write(f"**Cумма:** {st.session_state.dropped_stats['cost']:,.0f} ₽")
            
            items_df = pd.DataFrame(st.session_state.dropped_stats['items'])
            if not items_df.empty:
                items_df = items_df.sort_values(by='Себестоимость', ascending=False).head(50)
                st.dataframe(items_df, use_container_width=True)
                
                sel_item = st.selectbox("Добавить в категории:", [""] + items_df['norm_name'].tolist())
                if sel_item:
                    st.info(f"Перейдите во вкладку 'Категории' и введите: {sel_item}")
        else:
            st.info("Нет отброшенных данных.")

        st.divider()
        st.write("### ☁️ Debug: Yandex Disk")
        if st.button("🔍 Показать файлы на Yandex Disk"):
            yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
            if yd_token:
                st.write(f"Токен найден: {yd_token[:5]}...")
                headers = {'Authorization': f'OAuth {yd_token}'}
                try:
                    # Check root
                    st.write("#### Root /RestoAnalytic")
                    resp = requests.get(
                        "https://cloud-api.yandex.net/v1/disk/resources",
                        headers=headers,
                        params={"path": "RestoAnalytic", "limit": 100}
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("_embedded", {}).get("items", [])
                        st.json([{"name": i["name"], "type": i["type"]} for i in items])
                    else:
                        st.error(f"Error Root: {resp.status_code} {resp.text}")
                    
                    # Check config
                    st.write("#### /RestoAnalytic/config")
                    resp_conf = requests.get(
                        "https://cloud-api.yandex.net/v1/disk/resources",
                        headers=headers,
                        params={"path": "RestoAnalytic/config", "limit": 100}
                    )
                    if resp_conf.status_code == 200:
                        items = resp_conf.json().get("_embedded", {}).get("items", [])
                        st.json([{"name": i["name"], "type": i["type"]} for i in items])
                    else:
                        st.warning(f"Error Config: {resp_conf.status_code} (Folder might not exist)")
                        
                except Exception as e:
                    st.error(f"Exception: {e}")
            else:
                st.error("Нет токена Yandex.")
