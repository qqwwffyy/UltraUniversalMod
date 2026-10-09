# Scoped and reversible access controls for Ren'Py Gallery, Replay, and MusicRoom.

init 999 python:
    _ultra_gallery_context_depth = 0
    _ultra_gallery_known_screens = (
        "_gallery", "gallery", "image_gallery", "cg", "cgs", "cg_gallery", "cggallery",
        "cg_room", "cgroom", "scene_gallery", "scenegallery", "scene_replay", "scene_replays",
        "scenes", "replay", "replays", "replay_gallery", "replaygallery", "replay_room",
        "replayroom", "memory", "memories", "memory_gallery", "memories_gallery", "recollection",
        "recollections", "extra", "extras", "extra_menu", "extras_menu", "bonus", "bonus_gallery",
        "achievement", "achievements", "music_room", "musicroom", "jukebox", "secret_gallery",
        "secretgallery", "gallery_menu", "gallery_screen", "gallery_main", "gallery_page",
    )

    def ultra_gallery_enabled():
        return bool(persistent.ultra_gallery_enabled)

    def ultra_gallery_mode():
        try:
            return 3 if int(persistent.ultra_gallery_mode) == 3 else 2
        except (TypeError, ValueError):
            return 2

    def ultra_gallery_mode_name():
        if not ultra_gallery_enabled():
            return ultra_t('gallery.off')
        return ultra_t('gallery.in_gallery') if ultra_gallery_mode() == 2 else ultra_t('gallery.throughout_the_game')

    def ultra_gallery_set_enabled(value):
        persistent.ultra_gallery_enabled = bool(value)
        renpy.save_persistent()
        renpy.restart_interaction()

    def ultra_gallery_toggle():
        ultra_gallery_set_enabled(not ultra_gallery_enabled())

    def ultra_gallery_set_mode(mode):
        try:
            mode = 3 if int(mode) == 3 else 2
        except (TypeError, ValueError):
            mode = 2
        persistent.ultra_gallery_mode = mode
        renpy.save_persistent()
        renpy.restart_interaction()

    def ultra_gallery_register_screen(name):
        if not name:
            return
        screens = list(persistent.ultra_gallery_custom_screens or [])
        if name not in screens:
            screens.append(name)
            persistent.ultra_gallery_custom_screens = screens
            renpy.save_persistent()

    def ultra_gallery_unregister_screen(name):
        screens = list(persistent.ultra_gallery_custom_screens or [])
        if name in screens:
            screens.remove(name)
            persistent.ultra_gallery_custom_screens = screens
            renpy.save_persistent()

    def ultra_gallery_screen_names():
        result = list(_ultra_gallery_known_screens)
        for name in persistent.ultra_gallery_custom_screens or []:
            if name not in result:
                result.append(name)
        return result

    def ultra_gallery_in_context():
        if _ultra_gallery_context_depth:
            return True
        for name in ultra_gallery_screen_names():
            try:
                if renpy.get_screen(name) is not None:
                    return True
            except Exception:
                pass
        return False

    def ultra_gallery_should_override():
        if not ultra_gallery_enabled():
            return False
        return ultra_gallery_mode() == 3 or ultra_gallery_in_context()

    def _ultra_gallery_strip_conditions(gallery):
        saved = []
        for button in getattr(gallery, "button_list", ()) or ():
            for obj in (button,) + tuple(getattr(button, "images", ()) or ()):
                try:
                    if hasattr(obj, "conditions"):
                        old = obj.conditions
                        saved.append((obj, old))
                        obj.conditions = []
                except Exception:
                    pass
        return saved

    def _ultra_gallery_restore_conditions(saved):
        for obj, conditions in saved:
            try:
                obj.conditions = conditions
            except Exception:
                pass

    def _ultra_gallery_wrap_method(owner, name, wrapper_factory):
        try:
            original = getattr(owner, name)
            marker = "_ultra_original_" + name
            if hasattr(owner, marker):
                return
            setattr(owner, marker, original)
            setattr(owner, name, wrapper_factory(original))
        except Exception as exc:
            renpy.log("Ultra gallery: {}.{}: {}".format(owner, name, exc))

    _ultra_gallery_class = getattr(store, "Gallery", None)
    if _ultra_gallery_class is not None:
        for _method_name in ("Action", "show", "get_fraction"):
            def _make_gallery_wrapper(original):
                def wrapped(self, *args, **kwargs):
                    if not ultra_gallery_enabled():
                        return original(self, *args, **kwargs)
                    saved = _ultra_gallery_strip_conditions(self)
                    global _ultra_gallery_context_depth
                    _ultra_gallery_context_depth += 1
                    try:
                        return original(self, *args, **kwargs)
                    finally:
                        _ultra_gallery_context_depth = max(0, _ultra_gallery_context_depth - 1)
                        _ultra_gallery_restore_conditions(saved)
                return wrapped
            _ultra_gallery_wrap_method(_ultra_gallery_class, _method_name, _make_gallery_wrapper)

    if hasattr(store, "Replay") and not hasattr(store, "_ultra_original_Replay"):
        store._ultra_original_Replay = store.Replay
        def _ultra_replay(label, scope=None, locked=None):
            if scope is None:
                scope = {}
            if ultra_gallery_enabled():
                locked = False
            return store._ultra_original_Replay(label, scope=scope, locked=locked)
        store.Replay = _ultra_replay

    _ultra_music_room = getattr(store, "MusicRoom", None)
    if _ultra_music_room is not None and hasattr(_ultra_music_room, "is_unlocked"):
        def _ultra_music_wrapper(original):
            def wrapped(self, filename):
                return True if ultra_gallery_enabled() else original(self, filename)
            return wrapped
        _ultra_gallery_wrap_method(
            _ultra_music_room,
            "is_unlocked",
            _ultra_music_wrapper,
        )

    _ultra_original_seen_label = renpy.seen_label
    _ultra_original_seen_image = renpy.seen_image
    def _ultra_seen_label(label):
        if ultra_gallery_should_override():
            return True
        return _ultra_original_seen_label(label)
    def _ultra_seen_image(name):
        if ultra_gallery_should_override():
            return True
        return _ultra_original_seen_image(name)
    renpy.seen_label = _ultra_seen_label
    renpy.seen_image = _ultra_seen_image
    if getattr(store, "seen_label", None) is _ultra_original_seen_label:
        store.seen_label = _ultra_seen_label
    if getattr(store, "seen_image", None) is _ultra_original_seen_image:
        store.seen_image = _ultra_seen_image

    try:
        _ultra_achievement = store.achievement
        _ultra_original_achievement_has = _ultra_achievement.has
        def _ultra_achievement_has(name):
            if ultra_gallery_should_override():
                return True
            return _ultra_original_achievement_has(name)
        _ultra_achievement.has = _ultra_achievement_has
    except Exception as exc:
        renpy.log("Ultra gallery: achievement.has: {}".format(exc))

screen ultra_gallery_settings_panel():
    $ _panel_width = min(config.screen_width - ultra_scale_px(330), ultra_scale_px(1420))
    $ _wide_cards = _panel_width >= ultra_scale_px(900)
    $ _card_width = (_panel_width - ultra_scale_px(12)) // 2 if _wide_cards else _panel_width
    viewport:
        xsize _panel_width
        xalign 0.0
        yfill True
        mousewheel True
        draggable True
        pagekeys True
        scrollbars None
        use ultra_gallery_content(_panel_width, _wide_cards, _card_width)

screen ultra_gallery_content(_panel_width, _wide_cards, _card_width):
    vbox:
        xsize _panel_width
        xalign 0.5
        spacing ultra_scale_px(16)
        text ultra_ui_t('nav.gallery') style "ultra_page_title" substitute False
        text ultra_ui_t('gallery.unlock_scenes_images_and_music_while_viewing_them') style "ultra_description" xsize _panel_width substitute False
        if _wide_cards:
            frame:
                xsize _panel_width
                ysize ultra_scale_px(126)
                background Solid(ULTRA_COLOR_SURFACE)
                padding (ultra_scale_px(20), ultra_scale_px(16))
                fixed:
                    xfill True
                    yfill True
                    vbox:
                        xsize (_panel_width - ultra_scale_px(330))
                        spacing ultra_scale_px(8)
                        text If(ultra_gallery_enabled(), ultra_ui_t('gallery.access_enabled'), ultra_ui_t('gallery.access_disabled')) style "ultra_label_text" substitute False
                        text If(ultra_gallery_enabled(), ultra_ui_t('gallery.you_can_view_locked_content_mode').format(ultra_gallery_mode_name()), ultra_ui_t('gallery.enable_access_here_when_you_want_to_browse')) style "ultra_description" xfill True substitute False
                    textbutton If(ultra_gallery_enabled(), ultra_ui_t('gallery.disable_access'), ultra_ui_t('gallery.enable_access')) style "ultra_search_submit_button" xsize ultra_scale_px(250) xalign 1.0 yalign 0.5 action Function(ultra_gallery_toggle) substitute False
        else:
            frame:
                xsize _panel_width
                background Solid(ULTRA_COLOR_SURFACE)
                padding (ultra_scale_px(16), ultra_scale_px(14))
                vbox:
                    spacing ultra_scale_px(8)
                    text If(ultra_gallery_enabled(), ultra_ui_t('gallery.access_enabled'), ultra_ui_t('gallery.access_disabled')) style "ultra_label_text" substitute False
                    text If(ultra_gallery_enabled(), ultra_ui_t('gallery.you_can_view_locked_content_mode').format(ultra_gallery_mode_name()), ultra_ui_t('gallery.enable_access_here_when_you_want_to_browse')) style "ultra_description" xfill True substitute False
                    textbutton If(ultra_gallery_enabled(), ultra_ui_t('gallery.disable_access'), ultra_ui_t('gallery.enable_access')) style "ultra_search_submit_button" xfill True action Function(ultra_gallery_toggle) substitute False
        text ultra_ui_t('gallery.where_access_applies') style "ultra_label_text" substitute False
        if _wide_cards:
            hbox:
                spacing ultra_scale_px(12)
                use ultra_gallery_mode_card(2, ultra_ui_t('gallery.gallery_only'), ultra_ui_t('gallery.recommended_for_scenes_and_images_access_applies_to'), _card_width)
                use ultra_gallery_mode_card(3, ultra_ui_t('gallery.throughout_the_game'), ultra_ui_t('gallery.also_applies_to_checks_within_the_story_choose'), _card_width)
        else:
            vbox:
                spacing ultra_scale_px(10)
                use ultra_gallery_mode_card(2, ultra_ui_t('gallery.gallery_only'), ultra_ui_t('gallery.recommended_for_scenes_and_images_access_applies_to'), _card_width)
                use ultra_gallery_mode_card(3, ultra_ui_t('gallery.throughout_the_game'), ultra_ui_t('gallery.also_applies_to_checks_within_the_story_choose'), _card_width)
        frame:
            xsize _panel_width
            background Solid(ULTRA_COLOR_ALERT if ultra_gallery_mode() == 3 else ULTRA_COLOR_SURFACE)
            padding (ultra_scale_px(20), ultra_scale_px(16))
            text If(ultra_gallery_mode() == 3, ultra_ui_t('gallery.this_mode_can_affect_story_checks_while_access'), ultra_ui_t('gallery.choose_a_mode_enable_access_and_open_the')) style "ultra_description" xfill True substitute False

screen ultra_gallery_mode_card(mode, title, details, card_width):
    button:
        xsize card_width
        ysize ultra_scale_px(168)
        padding (ultra_scale_px(18), ultra_scale_px(14))
        background Solid(ULTRA_COLOR_SELECTED if ultra_gallery_mode() == mode else ULTRA_COLOR_SURFACE_ALT)
        hover_background Solid(ULTRA_COLOR_SELECTED_HOVER)
        action Function(ultra_gallery_set_mode, mode)
        vbox:
            xfill True
            spacing ultra_scale_px(10)
            text title substitute False style "ultra_card_title"
            text details substitute False style "ultra_description" xfill True
