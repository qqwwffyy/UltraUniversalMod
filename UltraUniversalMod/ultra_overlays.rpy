# Live notifications for replay, choices, and paths.

screen ultra_notifications():
    zorder 100
    default banner_width = ultra_scale_px(310)
    $ _upcoming_path = UltraPathInspector.next_if()
    $ _inspector_open = renpy.get_screen("ultra_choices_modal") or renpy.get_screen("ultra_paths_modal") or renpy.get_screen("ultra_code_view")
    if persistent.ultra_stop_skipping_on_path and config.skipping and _upcoming_path:
        timer 0.01 action Function(renpy.stop_skipping)
    vbox:
        xalign 0.0
        yoffset ultra_scale_px(5)
        spacing ultra_scale_px(3)
        if persistent.ultra_notifications_enabled and not _inspector_open and _in_replay:
            button:
                xminimum banner_width
                background Solid(ULTRA_COLOR_SURFACE)
                hover_background Solid(ULTRA_COLOR_HOVER)
                padding (ultra_scale_px(12), ultra_scale_px(10))
                action Confirm(ultra_ui_t('overlay.end_the_current_replay'), Function(renpy.end_replay))
                hbox:
                    spacing ultra_scale_px(8)
                    text "◉" color ULTRA_COLOR_ACCENT
                    text ultra_ui_t('overlay.end_replay') style "ultra_description" bold True substitute False
        if persistent.ultra_notifications_enabled and not _inspector_open and UltraChoiceInspector.current_node():
            button:
                xminimum banner_width
                background Solid(ULTRA_COLOR_SURFACE)
                hover_background Solid(ULTRA_COLOR_HOVER)
                padding (ultra_scale_px(12), ultra_scale_px(10))
                action Show("ultra_choices_modal")
                vbox:
                    text ultra_ui_t('overlay.choice_options_found') style "ultra_description" bold True substitute False
                    $ _hidden_choices = len([c for c in UltraChoiceInspector.choices() if not c["visible"]])
                    if _hidden_choices:
                        text ultra_ui_t('overlay.hidden_hidden_choices').format(_hidden_choices) style "ultra_description" substitute False
        if persistent.ultra_notifications_enabled and not _inspector_open and _upcoming_path:
            button:
                xminimum banner_width
                background Solid(ULTRA_COLOR_SURFACE)
                hover_background Solid(ULTRA_COLOR_HOVER)
                padding (ultra_scale_px(12), ultra_scale_px(10))
                action Show("ultra_paths_modal")
                vbox:
                    text ultra_ui_t('overlay.conditions_found') style "ultra_description" bold True substitute False
                    text ultra_ui_t('overlay.branches_len_ultrapathinspector_branches').format(len(UltraPathInspector.branches())) style "ultra_description" substitute False
