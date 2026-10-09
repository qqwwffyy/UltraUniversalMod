# Ultra Universal Mod: independent runtime entry, settings, and main UI.

default persistent.ultra_last_tab = "home"
default persistent.ultra_console_enabled = False
default persistent.ultra_hide_quick_menu = False
default persistent.ultra_unlimited_rollback = False
default persistent.ultra_notifications_enabled = True
default persistent.ultra_gallery_enabled = False
default persistent.ultra_gallery_mode = 2
default persistent.ultra_gallery_custom_screens = []
default persistent.ultra_search_type = "variable names"
default persistent.ultra_search_recursive = False
default persistent.ultra_search_persistent = True
default persistent.ultra_search_objects = True
default persistent.ultra_search_unsupported = False
default persistent.ultra_search_internal = False
default persistent.ultra_search_wildcards = False
default persistent.ultra_save_page = 1
default persistent.ultra_save_page_names = {}
default persistent.ultra_stop_skipping_on_path = False

define ULTRA_COLOR_BACKGROUND = "#181512"
define ULTRA_COLOR_SIDEBAR = "#211D18"
define ULTRA_COLOR_SURFACE = "#25211C"
define ULTRA_COLOR_SURFACE_ALT = "#302A23"
define ULTRA_COLOR_INPUT = "#211D18"
define ULTRA_COLOR_HOVER = "#40372D"
define ULTRA_COLOR_SELECTED = "#735538"
define ULTRA_COLOR_SELECTED_HOVER = "#866746"
define ULTRA_COLOR_DISABLED = "#25211C"
define ULTRA_COLOR_ALERT = "#3A2B21"
define ULTRA_COLOR_TEXT = "#E4DACE"
define ULTRA_COLOR_TEXT_BRIGHT = "#EEE4D7"
define ULTRA_COLOR_TEXT_MUTED = "#C1B3A2"
define ULTRA_COLOR_ACCENT = "#C49A70"
define ULTRA_MOD_VERSION = "0.1.0"
define ULTRA_OFFICIAL_LINKS = (
    ('updates.github_title', 'updates.github_description', "https://github.com/qqwwffyy/UltraUniversalMod"),
    ('updates.discord_title', 'updates.discord_description', "https://discord.gg/BSzJebe8M"),
    ('updates.telegram_title', 'updates.telegram_description', "https://t.me/+kd6BEw6gD-o5Y2Nk"),
)

init -999 python:
    if not renpy.music.channel_defined("ambience"):
        renpy.music.register_channel("ambience", "sfx", loop=True)

    def ultra_scale_px(value):
        """Scale reference pixels against a 1920 pixel Ren'Py viewport."""
        scale = max(0.85, min(1.0, config.screen_width / 1920.0))
        return int(float(value) * scale)

    def ultra_toggle_menu():
        chronology = getattr(store, "UltraChronology", None)
        if renpy.get_screen("ultra_main_menu"):
            renpy.hide_screen("ultra_main_menu")
            if chronology is not None:
                chronology.forget_clean_screenshot()
        else:
            if chronology is not None:
                chronology.forget_clean_screenshot()
            if not getattr(store, "main_menu", False):
                renpy.take_screenshot()
                if chronology is not None:
                    chronology.remember_clean_screenshot()
            renpy.show_screen("ultra_main_menu")

    def _ultra_apply_quick_menu_preference():
        store.quick_menu = not bool(persistent.ultra_hide_quick_menu)

    def _ultra_after_load():
        _ultra_apply_quick_menu_preference()
        if persistent.ultra_unlimited_rollback:
            config.rollback_length = 999999
            config.hard_rollback_limit = 999999

    if config.developer is not True:
        config.console = bool(persistent.ultra_console_enabled)
    if persistent.ultra_unlimited_rollback:
        config.rollback_length = 999999
        config.hard_rollback_limit = 999999
    if _ultra_apply_quick_menu_preference not in config.after_load_callbacks:
        config.after_load_callbacks.append(_ultra_apply_quick_menu_preference)
    if _ultra_apply_quick_menu_preference not in config.after_default_callbacks:
        config.after_default_callbacks.append(_ultra_apply_quick_menu_preference)
    if _ultra_after_load not in config.after_load_callbacks:
        config.after_load_callbacks.append(_ultra_after_load)

init 999 python:
    if "s_e_n" not in config.gestures:
        config.gestures["s_e_n"] = "alt_K_m"

style ultra_root is default:
    color ULTRA_COLOR_TEXT
    font "UltraUniversalMod/Comfortaa/Comfortaa-Medium.ttf"
    size ultra_scale_px(20)
    line_spacing ultra_scale_px(5)
    outlines []

style ultra_label_text is ultra_root:
    font "UltraUniversalMod/Comfortaa/Comfortaa-SemiBold.ttf"
    color ULTRA_COLOR_TEXT_BRIGHT
    size ultra_scale_px(24)

style ultra_page_title is ultra_label_text:
    size ultra_scale_px(32)

style ultra_card_title is ultra_label_text:
    size ultra_scale_px(21)

style ultra_description is ultra_root:
    color ULTRA_COLOR_TEXT_MUTED
    size ultra_scale_px(19)
    line_spacing ultra_scale_px(5)

style ultra_button_text is button_text:
    font "UltraUniversalMod/Comfortaa/Comfortaa-Medium.ttf"
    size ultra_scale_px(19)
    color ULTRA_COLOR_TEXT
    line_spacing ultra_scale_px(4)
    outlines []
    text_align 0.5
    xmaximum ultra_scale_px(300)

style selected_ultra_button_text is ultra_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_tab_text is ultra_button_text:
    size ultra_scale_px(19)
    color ULTRA_COLOR_TEXT
    text_align 0.5
    xalign 0.5
    xfill True

style selected_ultra_tab_text is ultra_tab_text:
    font "UltraUniversalMod/Comfortaa/Comfortaa-SemiBold.ttf"
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_input is input:
    font "UltraUniversalMod/Comfortaa/Comfortaa-Medium.ttf"
    size ultra_scale_px(19)
    ysize ultra_scale_px(48)
    color ULTRA_COLOR_TEXT
    outlines []
    caret Solid(ULTRA_COLOR_ACCENT, xysize=(ultra_scale_px(2), ultra_scale_px(24)))
    background Solid(ULTRA_COLOR_INPUT)
    padding (ultra_scale_px(12), ultra_scale_px(8))

style ultra_button is button:
    background Solid(ULTRA_COLOR_SURFACE_ALT)
    hover_background Solid(ULTRA_COLOR_HOVER)
    selected_background Solid(ULTRA_COLOR_SELECTED)
    selected_hover_background Solid(ULTRA_COLOR_SELECTED_HOVER)
    insensitive_background Solid(ULTRA_COLOR_DISABLED)
    padding (ultra_scale_px(12), ultra_scale_px(8))
    yminimum ultra_scale_px(46)
    xmaximum ultra_scale_px(300)

style ultra_small_button is ultra_button:
    padding (ultra_scale_px(11), ultra_scale_px(8))
    yminimum ultra_scale_px(42)
    xmaximum ultra_scale_px(220)

style ultra_small_button_text is ultra_button_text:
    size ultra_scale_px(19)
    xmaximum ultra_scale_px(220)

style selected_ultra_small_button_text is ultra_small_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_tab is button:
    background Solid(ULTRA_COLOR_SURFACE_ALT)
    hover_background Solid(ULTRA_COLOR_HOVER)
    selected_background Solid(ULTRA_COLOR_SELECTED)
    selected_hover_background Solid(ULTRA_COLOR_SELECTED_HOVER)
    insensitive_background Solid(ULTRA_COLOR_DISABLED)
    xfill True
    ysize ultra_scale_px(56)
    padding (ultra_scale_px(18), ultra_scale_px(10))

style ultra_feature_card is button:
    background Solid(ULTRA_COLOR_SURFACE)
    hover_background Solid(ULTRA_COLOR_HOVER)
    padding (ultra_scale_px(17), ultra_scale_px(14))

style ultra_feature_title is ultra_card_title:
    color ULTRA_COLOR_TEXT_BRIGHT

style ultra_feature_hint is ultra_root:
    color ULTRA_COLOR_ACCENT
    size ultra_scale_px(17)

style ultra_link_card is ultra_feature_card:
    insensitive_background Solid(ULTRA_COLOR_SURFACE)

style ultra_language_button is ultra_small_button:
    xmaximum None
    xsize ultra_scale_px(54)
    yminimum ultra_scale_px(38)
    padding (ultra_scale_px(6), ultra_scale_px(5))

style ultra_language_button_text is ultra_small_button_text:
    size ultra_scale_px(16)
    xmaximum None

style selected_ultra_language_button_text is ultra_language_button_text:
    color ULTRA_COLOR_TEXT_BRIGHT

screen ultra_main_menu():
    tag ultra_menu
    modal True
    zorder 200
    key "K_F5" action Function(ultra_toggle_menu)
    key "K_ESCAPE" action Function(ultra_toggle_menu)
    if not config.console and not config.developer:
        key "shift_K_o" action NullAction()

    frame:
        background Solid(ULTRA_COLOR_BACKGROUND)
        xfill True
        yfill True
        xmargin -3
        ymargin -3
        padding (ultra_scale_px(20), ultra_scale_px(16))

        vbox:
            xfill True
            yfill True
            spacing ultra_scale_px(10)

            hbox:
                xfill True
                yfill True
                spacing ultra_scale_px(16)

                if config.screen_height >= ultra_scale_px(500):
                    frame:
                        xsize ultra_scale_px(232)
                        yfill True
                        background None
                        padding (0, 0)
                        vbox:
                            xfill True
                            spacing ultra_scale_px(8)
                            use ultra_tab_button(ultra_ui_t('nav.home'), "home")
                            use ultra_tab_button(ultra_ui_t('nav.search'), "search")
                            use ultra_tab_button(ultra_ui_t('nav.dialogues'), "dialogues")
                            use ultra_tab_button(ultra_ui_t('nav.saves'), "gamesaves")
                            use ultra_tab_button(ultra_ui_t('nav.timeline'), "timeline")
                            use ultra_tab_button(ultra_ui_t('nav.gallery'), "gallery_unlock")
                            use ultra_tab_button(ultra_ui_t('nav.settings'), "settings")
                            use ultra_tab_button(ultra_ui_t('nav.updates'), "about")
                else:
                    viewport:
                        xsize ultra_scale_px(232)
                        yfill True
                        mousewheel True
                        pagekeys True
                        scrollbars None
                        frame:
                            xfill True
                            yfill True
                            background None
                            padding (0, 0)
                            vbox:
                                xfill True
                                spacing ultra_scale_px(8)
                                use ultra_tab_button(ultra_ui_t('nav.home'), "home")
                                use ultra_tab_button(ultra_ui_t('nav.search'), "search")
                                use ultra_tab_button(ultra_ui_t('nav.dialogues'), "dialogues")
                                use ultra_tab_button(ultra_ui_t('nav.saves'), "gamesaves")
                                use ultra_tab_button(ultra_ui_t('nav.timeline'), "timeline")
                                use ultra_tab_button(ultra_ui_t('nav.gallery'), "gallery_unlock")
                                use ultra_tab_button(ultra_ui_t('nav.settings'), "settings")
                                use ultra_tab_button(ultra_ui_t('nav.updates'), "about")

                frame:
                    xfill True
                    yfill True
                    background None
                    padding (ultra_scale_px(8), 0)
                    if ultra_settings.current_tab == "search":
                        use ultra_search_tab()
                    elif ultra_settings.current_tab == "dialogues":
                        use ultra_dialogues_tab()
                    elif ultra_settings.current_tab == "gamesaves":
                        use ultra_saves_tab()
                    elif ultra_settings.current_tab == "timeline":
                        use ultra_chronology_tab()
                    elif ultra_settings.current_tab == "gallery_unlock":
                        use ultra_gallery_tab()
                    elif ultra_settings.current_tab == "settings":
                        use ultra_settings_tab()
                    elif ultra_settings.current_tab == "about":
                        use ultra_about_tab()
                    else:
                        use ultra_home_tab()

screen ultra_tab_button(title, name):
    button:
        style "ultra_tab"
        selected (ultra_settings.current_tab == name)
        action Function(ultra_settings.select_tab, name)
        text title substitute False style "ultra_tab_text" xfill True xalign 0.5 yalign 0.5

screen ultra_home_tab():
    viewport:
        xfill True
        yfill True
        mousewheel True
        draggable True
        pagekeys True
        scrollbars None
        use ultra_home_content()

screen ultra_home_content():
    $ _content_width = min(config.screen_width - ultra_scale_px(330), ultra_scale_px(1420))
    $ _wide = _content_width >= ultra_scale_px(830)
    $ _card_width = (_content_width - ultra_scale_px(12)) // 2 if _wide else _content_width
    vbox:
        xsize _content_width
        xalign 0.5
        spacing ultra_scale_px(13)
        text "UltraUniversalMod" style "ultra_page_title"
        text ultra_ui_t('home.introduction') style "ultra_description" xfill True substitute False
        hbox:
            xfill True
            spacing ultra_scale_px(6)
            text ultra_ui_t('home.version').format(ULTRA_MOD_VERSION) style "ultra_feature_hint" yalign 0.5 substitute False
            null xfill True
            hbox:
                xfill False
                spacing 0
                textbutton "RU" style "ultra_language_button" xfill False selected (persistent.ultra_ui_language == "ru") action Function(ultra_set_ui_language, "ru")
                textbutton "EN" style "ultra_language_button" xfill False selected (persistent.ultra_ui_language == "en") action Function(ultra_set_ui_language, "en")
        frame:
            xfill True
            background Solid(ULTRA_COLOR_SURFACE_ALT)
            padding (ultra_scale_px(15), ultra_scale_px(12))
            text ultra_ui_t('home.f5_hint') style "ultra_root" xfill True substitute False
        text ultra_ui_t('home.features_heading') style "ultra_label_text" substitute False
        if _wide:
            hbox:
                spacing ultra_scale_px(12)
                use ultra_feature_card_screen(ultra_ui_t('nav.search'), ultra_ui_t('home.find_a_variable_value_or_game_label_to'), "search", _card_width)
                use ultra_feature_card_screen(ultra_ui_t('nav.dialogues'), ultra_ui_t('home.reread_lines_and_find_a_conversation_keep_important'), "dialogues", _card_width)
            hbox:
                spacing ultra_scale_px(12)
                use ultra_feature_card_screen(ultra_ui_t('nav.saves'), ultra_ui_t('home.browse_save_slots_and_name_pages_so_you'), "gamesaves", _card_width)
                use ultra_feature_card_screen(ultra_ui_t('nav.timeline'), ultra_ui_t('home.move_between_saved_story_moments_and_continue_from'), "timeline", _card_width)
            hbox:
                spacing ultra_scale_px(12)
                use ultra_feature_card_screen(ultra_ui_t('nav.gallery'), ultra_ui_t('home.unlock_hidden_content_and_choose_a_viewing_mode'), "gallery_unlock", _card_width)
                use ultra_feature_card_screen(ultra_ui_t('nav.settings'), ultra_ui_t('home.adjust_dialogue_and_fonts_hints_the_quick_menu'), "settings", _card_width)
        else:
            use ultra_feature_card_screen(ultra_ui_t('nav.search'), ultra_ui_t('home.find_a_variable_value_or_game_label_to'), "search", _card_width)
            use ultra_feature_card_screen(ultra_ui_t('nav.dialogues'), ultra_ui_t('home.reread_lines_and_find_a_conversation_keep_important'), "dialogues", _card_width)
            use ultra_feature_card_screen(ultra_ui_t('nav.saves'), ultra_ui_t('home.browse_save_slots_and_name_pages_so_you'), "gamesaves", _card_width)
            use ultra_feature_card_screen(ultra_ui_t('nav.timeline'), ultra_ui_t('home.move_between_saved_story_moments_and_continue_from'), "timeline", _card_width)
            use ultra_feature_card_screen(ultra_ui_t('nav.gallery'), ultra_ui_t('home.unlock_hidden_content_and_choose_a_viewing_mode'), "gallery_unlock", _card_width)
            use ultra_feature_card_screen(ultra_ui_t('nav.settings'), ultra_ui_t('home.adjust_dialogue_and_fonts_hints_the_quick_menu'), "settings", _card_width)

screen ultra_feature_card_screen(title, details, target_tab, card_width):
    button:
        style "ultra_feature_card"
        xsize card_width
        yminimum ultra_scale_px(166)
        action Function(ultra_settings.select_tab, target_tab)
        vbox:
            xfill True
            spacing ultra_scale_px(8)
            text title substitute False style "ultra_feature_title"
            text details substitute False style "ultra_description" xfill True
            text ultra_ui_t('common.open') substitute False style "ultra_feature_hint"

screen ultra_about_tab():
    viewport:
        xfill True
        yfill True
        mousewheel True
        draggable True
        pagekeys True
        scrollbars None
        use ultra_about_content()

screen ultra_about_content():
    $ _content_width = min(config.screen_width - ultra_scale_px(330), ultra_scale_px(1420))
    vbox:
        xsize _content_width
        xalign 0.5
        spacing ultra_scale_px(13)
        text ultra_ui_t('nav.updates') style "ultra_page_title" substitute False
        text ultra_ui_t('updates.version').format(ULTRA_MOD_VERSION) style "ultra_label_text" substitute False
        text ultra_ui_t('updates.source_code_and_new_releases_are_on_github') style "ultra_description" xfill True substitute False
        text ultra_ui_t('updates.official_links') style "ultra_label_text" substitute False
        text ultra_ui_t('updates.select_a_card_to_open_its_page_in') style "ultra_description" xfill True substitute False
        for link_title, link_details, link_url in ULTRA_OFFICIAL_LINKS:
            use ultra_about_link(ultra_ui_t(link_title), ultra_ui_t(link_details), link_url, _content_width)
        use ultra_about_note(ultra_ui_t('updates.development'), "qqwwffyy", _content_width)

screen ultra_about_link(title, details, url, card_width):
    button:
        style "ultra_link_card"
        xsize card_width
        yminimum ultra_scale_px(94)
        action OpenURL(url)
        vbox:
            xfill True
            spacing ultra_scale_px(6)
            text title substitute False style "ultra_card_title" xfill True
            text details substitute False style "ultra_description" xfill True
            text ultra_ui_t('common.open') style "ultra_feature_hint" substitute False

screen ultra_about_note(title, details, card_width, link_label=None, link_url=None):
    frame:
        xsize card_width
        yminimum ultra_scale_px(135)
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(16), ultra_scale_px(13))
        vbox:
            xfill True
            spacing ultra_scale_px(7)
            text title substitute False style "ultra_card_title"
            text details substitute False style "ultra_description" xfill True
            if link_url:
                button:
                    background None
                    hover_background None
                    padding (0, 0)
                    action OpenURL(link_url)
                    text link_label substitute False style "ultra_feature_hint"

screen ultra_settings_tab():
    viewport:
        xfill True
        yfill True
        mousewheel True
        draggable True
        pagekeys True
        scrollbars None
        use ultra_settings_content()

screen ultra_settings_content():
    $ _panel_width = min(config.screen_width - ultra_scale_px(330), ultra_scale_px(1420))
    $ _wide = _panel_width >= ultra_scale_px(900)
    $ _card_width = (_panel_width - ultra_scale_px(12)) // 2 if _wide else _panel_width
    vbox:
        xsize _panel_width
        xalign 0.5
        spacing ultra_scale_px(14)
        text ultra_ui_t('nav.settings') style "ultra_page_title" substitute False
        text ultra_ui_t('settings.make_the_mod_your_own_changes_are_saved') style "ultra_description" xsize _panel_width substitute False
        text ultra_ui_t('settings.during_the_game') style "ultra_label_text" substitute False
        if _wide:
            hbox:
                spacing ultra_scale_px(12)
                use ultra_settings_toggle_card(ultra_ui_t('settings.notifications'), ultra_ui_t('settings.small_hints_announce_choice_options_new_branches_and'), ultra_ui_t('settings.hints_are_on') if persistent.ultra_notifications_enabled else ultra_ui_t('settings.hints_are_off'), ultra_ui_t('settings.disable') if persistent.ultra_notifications_enabled else ultra_ui_t('settings.enable'), Function(ultra_settings.toggle_notifications), _card_width, ultra_scale_px(150))
                use ultra_settings_toggle_card(ultra_ui_t('settings.stop_before_a_branch'), ultra_ui_t('settings.when_skipping_the_mod_stops_before_the_next'), ultra_ui_t('settings.stopping_is_on') if persistent.ultra_stop_skipping_on_path else ultra_ui_t('settings.stopping_is_off'), ultra_ui_t('settings.do_not_stop') if persistent.ultra_stop_skipping_on_path else ultra_ui_t('settings.stop'), Function(ultra_settings.toggle_stop_skipping_on_path), _card_width, ultra_scale_px(230))
            hbox:
                spacing ultra_scale_px(12)
                use ultra_settings_toggle_card(ultra_ui_t('settings.quick_menu_label'), ultra_ui_t('settings.keeps_game_controls_within_reach_at_the_bottom'), ultra_ui_t('settings.menu_hidden') if persistent.ultra_hide_quick_menu else ultra_ui_t('settings.menu_shown'), ultra_ui_t('settings.show') if persistent.ultra_hide_quick_menu else ultra_ui_t('settings.hide'), Function(ultra_settings.toggle_quick_menu), _card_width, ultra_scale_px(150))
                use ultra_settings_shortcuts_card(_card_width)
        else:
            vbox:
                spacing ultra_scale_px(10)
                use ultra_settings_toggle_card(ultra_ui_t('settings.notifications'), ultra_ui_t('settings.small_hints_announce_choice_options_new_branches_and'), ultra_ui_t('settings.hints_are_on') if persistent.ultra_notifications_enabled else ultra_ui_t('settings.hints_are_off'), ultra_ui_t('settings.disable') if persistent.ultra_notifications_enabled else ultra_ui_t('settings.enable'), Function(ultra_settings.toggle_notifications), _card_width, ultra_scale_px(150))
                use ultra_settings_toggle_card(ultra_ui_t('settings.stop_before_a_branch'), ultra_ui_t('settings.when_skipping_the_mod_stops_before_the_next'), ultra_ui_t('settings.stopping_is_on') if persistent.ultra_stop_skipping_on_path else ultra_ui_t('settings.stopping_is_off'), ultra_ui_t('settings.do_not_stop') if persistent.ultra_stop_skipping_on_path else ultra_ui_t('settings.stop'), Function(ultra_settings.toggle_stop_skipping_on_path), _card_width, ultra_scale_px(230))
                use ultra_settings_toggle_card(ultra_ui_t('settings.quick_menu_label'), ultra_ui_t('settings.keeps_game_controls_within_reach_at_the_bottom'), ultra_ui_t('settings.menu_hidden') if persistent.ultra_hide_quick_menu else ultra_ui_t('settings.menu_shown'), ultra_ui_t('settings.show') if persistent.ultra_hide_quick_menu else ultra_ui_t('settings.hide'), Function(ultra_settings.toggle_quick_menu), _card_width, ultra_scale_px(150))
                use ultra_settings_shortcuts_card(_card_width)
        text ultra_ui_t('settings.game_appearance') style "ultra_label_text" substitute False
        use ultra_appearance_settings_card(_panel_width, _wide)
        text ultra_ui_t('settings.advanced') style "ultra_label_text" substitute False
        if _wide:
            hbox:
                spacing ultra_scale_px(12)
                use ultra_settings_toggle_card(ultra_ui_t('settings.developer_console'), ultra_ui_t('settings.open_with_shift_o_if_the_game_enables'), ultra_ui_t('settings.enabled_by_game') if config.developer is True else (ultra_ui_t('settings.console_enabled') if config.console else ultra_ui_t('settings.console_disabled')), ultra_ui_t('settings.controlled_by_game') if config.developer is True else (ultra_ui_t('settings.disable') if config.console else ultra_ui_t('settings.enable')), Function(ultra_settings.toggle_console), _card_width, ultra_scale_px(230), enabled=(config.developer is not True))
                use ultra_settings_toggle_card(ultra_ui_t('settings.extended_rollback_history'), ultra_ui_t('settings.lets_you_go_further_back_it_may_use'), ultra_ui_t('settings.after_restart_enabled') if persistent.ultra_unlimited_rollback else ultra_ui_t('settings.after_restart_disabled'), ultra_ui_t('settings.disable') if persistent.ultra_unlimited_rollback else ultra_ui_t('settings.enable'), Function(ultra_settings.toggle_unlimited_rollback), _card_width, ultra_scale_px(150))
        else:
            vbox:
                spacing ultra_scale_px(10)
                use ultra_settings_toggle_card(ultra_ui_t('settings.developer_console'), ultra_ui_t('settings.open_with_shift_o_if_the_game_enables'), ultra_ui_t('settings.enabled_by_game') if config.developer is True else (ultra_ui_t('settings.console_enabled') if config.console else ultra_ui_t('settings.console_disabled')), ultra_ui_t('settings.controlled_by_game') if config.developer is True else (ultra_ui_t('settings.disable') if config.console else ultra_ui_t('settings.enable')), Function(ultra_settings.toggle_console), _card_width, ultra_scale_px(230), enabled=(config.developer is not True))
                use ultra_settings_toggle_card(ultra_ui_t('settings.extended_rollback_history'), ultra_ui_t('settings.lets_you_go_further_back_it_may_use'), ultra_ui_t('settings.after_restart_enabled') if persistent.ultra_unlimited_rollback else ultra_ui_t('settings.after_restart_disabled'), ultra_ui_t('settings.disable') if persistent.ultra_unlimited_rollback else ultra_ui_t('settings.enable'), Function(ultra_settings.toggle_unlimited_rollback), _card_width, ultra_scale_px(150))
        text ultra_ui_t('settings.data') style "ultra_label_text" substitute False
        frame:
            xsize _panel_width
            background Solid(ULTRA_COLOR_SURFACE)
            padding (ultra_scale_px(16), ultra_scale_px(14))
            vbox:
                spacing ultra_scale_px(6)
                text ultra_ui_t('settings.saves_and_settings') style "ultra_card_title" substitute False
                text ultra_ui_t('settings.they_are_stored_in_the_game_s_save') style "ultra_description" xfill True substitute False
                if _panel_width >= ultra_scale_px(700):
                    text ultra_ui_t('settings.folder').format(getattr(config, "savedir", None) or ultra_ui_t('settings.unavailable')) substitute False style "ultra_description" xfill True

screen ultra_settings_toggle_card(title, details, status, button_label, button_action, card_width, button_width, enabled=True):
    $ _compact = card_width < ultra_scale_px(600)
    frame:
        xsize card_width
        yminimum (ultra_scale_px(170) if _compact else ultra_scale_px(190))
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(16), ultra_scale_px(14))
        vbox:
            xfill True
            spacing ultra_scale_px(7)
            text title substitute False style "ultra_card_title"
            text details substitute False style "ultra_description" xfill True
            if _compact:
                text status substitute False style "ultra_description" xfill True
                textbutton button_label substitute False style "ultra_button" xfill True sensitive enabled action button_action
            else:
                fixed:
                    xfill True
                    ysize ultra_scale_px(46)
                    text status substitute False style "ultra_description" xsize (card_width - ultra_scale_px(32) - button_width - ultra_scale_px(12)) yalign 0.5
                    textbutton button_label substitute False style "ultra_button" xsize button_width xalign 1.0 yalign 0.5 sensitive enabled action button_action

screen ultra_appearance_settings_card(card_width, wide):
    frame:
        xsize card_width
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(16), ultra_scale_px(14))
        vbox:
            xfill True
            spacing ultra_scale_px(10)
            text ultra_ui_t('settings.dialogue_and_font') style "ultra_card_title" substitute False
            text ultra_ui_t('settings.choose_a_dialogue_style_font_and_text_size') style "ultra_description" xfill True substitute False
            if wide:
                hbox:
                    xfill True
                    spacing ultra_scale_px(16)
                    use ultra_appearance_preset_choices((card_width - ultra_scale_px(48)) // 2)
                    use ultra_appearance_font_choices((card_width - ultra_scale_px(48)) // 2)
            else:
                use ultra_appearance_preset_choices(card_width - ultra_scale_px(32))
                use ultra_appearance_font_choices(card_width - ultra_scale_px(32))
            text ultra_ui_t('settings.adv_and_nvl_text_size') style "ultra_label_text" substitute False
            if card_width >= ultra_scale_px(620):
                hbox:
                    spacing ultra_scale_px(8)
                    for size_key, size_label in ultra_appearance.sizes:
                        textbutton ultra_ui_t(size_label) style "ultra_small_button" xsize ultra_scale_px(172) selected (ultra_appearance.size_mode == size_key) action Function(ultra_appearance.set_size, size_key) substitute False
            else:
                vbox:
                    spacing ultra_scale_px(6)
                    for size_key, size_label in ultra_appearance.sizes:
                        textbutton ultra_ui_t(size_label) style "ultra_small_button" xfill True selected (ultra_appearance.size_mode == size_key) action Function(ultra_appearance.set_size, size_key) substitute False
            text ultra_ui_t('settings.normal_uses_the_game_s_text_size_or') style "ultra_description" xfill True substitute False
            text ultra_ui_t('settings.to_add_a_font_place_a_ttf_or') style "ultra_description" xfill True substitute False
            textbutton ultra_ui_t('settings.restore_game_appearance') style "ultra_small_button" sensitive (ultra_appearance.preset != "original" or ultra_appearance.font != "original" or ultra_appearance.size_mode != "normal") action Function(ultra_appearance.reset) substitute False

screen ultra_appearance_preset_choices(column_width):
    vbox:
        xsize column_width
        spacing ultra_scale_px(7)
        text ultra_ui_t('settings.dialogue_preset') style "ultra_label_text" substitute False
        for preset_key, preset_name in ultra_appearance.presets:
            textbutton ultra_ui_t(preset_name) style "ultra_button" xfill True selected (ultra_appearance.preset == preset_key) action Function(ultra_appearance.set_preset, preset_key) substitute False

screen ultra_appearance_font_choices(column_width):
    vbox:
        xsize column_width
        spacing ultra_scale_px(7)
        text ultra_ui_t('settings.game_screen_font') style "ultra_label_text" substitute False
        viewport:
            xsize column_width
            ymaximum ultra_scale_px(280)
            mousewheel True
            draggable True
            scrollbars None
            vbox:
                xfill True
                spacing ultra_scale_px(6)
                textbutton ultra_ui_t('settings.original') style "ultra_button" xfill True selected (ultra_appearance.font == "original") action Function(ultra_appearance.set_font, "original") substitute False
                for font_path, font_name in ultra_appearance.fonts:
                    textbutton ultra_ui_t(font_name) style "ultra_button" xfill True selected (ultra_appearance.font == font_path) action Function(ultra_appearance.set_font, font_path) substitute False

screen ultra_settings_shortcuts_card(card_width):
    frame:
        xsize card_width
        yminimum ultra_scale_px(190)
        background Solid(ULTRA_COLOR_SURFACE)
        padding (ultra_scale_px(16), ultra_scale_px(14))
        vbox:
            xfill True
            spacing ultra_scale_px(7)
            text ultra_ui_t('settings.choice_hints') style "ultra_card_title" substitute False
            text ultra_ui_t('settings.alt_c_options_for_the_current_choice') style "ultra_description" substitute False
            text ultra_ui_t('settings.alt_a_conditions_of_the_next_branch') style "ultra_description" substitute False
            text ultra_ui_t('settings.available_during_the_game') style "ultra_description" substitute False

screen ultra_chronology_tab():
    use ultra_chronology_view()

screen ultra_gallery_tab():
    use ultra_gallery_settings_panel()

screen ultra_overlay():
    zorder 190
    if ultra_search_frozen:
        timer 0.1 repeat True action Function(ultra_search_enforce_freezes, True, _update_screens=False)
    if not renpy.get_screen("ultra_main_menu"):
        key "K_F5" action Function(ultra_toggle_menu)
    if config.developer is not True and not config.console:
        key "shift_K_o" action NullAction()
    if UltraChoiceInspector.current_node():
        key "alt_K_c" action Show("ultra_choices_modal")
    if UltraPathInspector.next_if():
        key "alt_K_a" action Show("ultra_paths_modal")
    if _in_replay:
        key "alt_K_e" action EndReplay(False)
        key "alt_K_m" action EndReplay(False)
    use ultra_notifications()

init 999 python:
    if "ultra_overlay" not in config.overlay_screens:
        config.overlay_screens.append("ultra_overlay")
