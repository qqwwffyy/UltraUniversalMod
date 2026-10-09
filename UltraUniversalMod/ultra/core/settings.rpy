init -999 python:
    class UltraSettings(object):
        """Own Ultra's persistent preferences and Ren'Py setting effects."""

        tabs = ("home", "search", "dialogues", "gamesaves", "timeline", "gallery_unlock", "settings", "about")

        def __init__(self):
            self._normalize()

        def _normalize(self):
            if persistent.ultra_last_tab not in self.tabs:
                persistent.ultra_last_tab = "home"
            if getattr(persistent, "ultra_ui_language", None) not in ("ru", "en"):
                persistent.ultra_ui_language = "ru"
            if persistent.ultra_save_page not in ("auto", "quick"):
                try:
                    persistent.ultra_save_page = max(1, int(persistent.ultra_save_page))
                except (TypeError, ValueError):
                    persistent.ultra_save_page = 1
            if not isinstance(persistent.ultra_save_page_names, dict):
                persistent.ultra_save_page_names = {}
            if persistent.ultra_gallery_mode not in (2, 3):
                persistent.ultra_gallery_mode = 2
            if not isinstance(persistent.ultra_gallery_custom_screens, list):
                persistent.ultra_gallery_custom_screens = []

        @property
        def current_tab(self):
            return persistent.ultra_last_tab

        def select_tab(self, name):
            if name not in self.tabs:
                name = "home"
            persistent.ultra_last_tab = name
            renpy.save_persistent()
            renpy.restart_interaction()

        def toggle_notifications(self):
            persistent.ultra_notifications_enabled = not bool(persistent.ultra_notifications_enabled)
            renpy.save_persistent()
            renpy.restart_interaction()

        def toggle_stop_skipping_on_path(self):
            persistent.ultra_stop_skipping_on_path = not bool(persistent.ultra_stop_skipping_on_path)
            renpy.save_persistent()
            renpy.restart_interaction()

        def toggle_quick_menu(self):
            persistent.ultra_hide_quick_menu = not bool(persistent.ultra_hide_quick_menu)
            store.quick_menu = not persistent.ultra_hide_quick_menu
            renpy.save_persistent()
            renpy.restart_interaction()
            renpy.notify(ultra_ui_t('settings.quick_menu_notification').format(
                ultra_t('settings.quick_menu_hidden_word') if persistent.ultra_hide_quick_menu else ultra_t('settings.quick_menu_shown_word')))

        def toggle_console(self):
            if config.developer is True:
                renpy.notify(ultra_ui_t('settings.the_developer_mode_has_enabled_the_console'))
                return
            persistent.ultra_console_enabled = not bool(config.console)
            config.console = persistent.ultra_console_enabled
            renpy.save_persistent()
            renpy.notify(ultra_ui_t('settings.ren_py_console').format(
                ultra_t('settings.console_enabled_word') if config.console else ultra_t('settings.console_disabled_word')))
            renpy.restart_interaction()

        def toggle_unlimited_rollback(self):
            persistent.ultra_unlimited_rollback = not bool(persistent.ultra_unlimited_rollback)
            renpy.save_persistent()
            renpy.restart_interaction()
            renpy.notify(ultra_ui_t('settings.extended_rollback_restart_the_game_to_apply_this').format(
                ultra_t('settings.rollback_enabled_word') if persistent.ultra_unlimited_rollback else ultra_t('settings.rollback_disabled_word')))

init -998 python:
    ultra_settings = UltraSettings()
